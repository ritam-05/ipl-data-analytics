import os
import re
import json
from typing import TypedDict, Optional, Literal
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Compact schema context for Text-to-SQL (kept concise to stay well within Groq's 8K TPM free limit)
GOLD_SCHEMA_PROMPT = """
PostgreSQL Schema (all tables in schema 'public'):
1. dim_seasons(season INT PK, total_matches INT, season_start_date TEXT, season_end_date TEXT)
2. dim_teams(team_name TEXT PK, total_matches_played INT, first_season INT, last_season INT)
3. dim_venues(venue_name TEXT PK, total_matches INT, first_season INT, last_season INT)
4. dim_players(player_name TEXT PK)
5. fact_matches(match_id INT PK, season INT, start_date TEXT, venue TEXT, team_1 TEXT, team_2 TEXT, innings_1_runs INT, innings_1_wickets INT, innings_2_runs INT, innings_2_wickets INT, winner TEXT, win_type TEXT, win_margin INT)
   -- win_type is 'runs' (bat first won), 'wickets' (chasing team won), 'tie', or 'no_result'.
6. fact_player_batting_season(player_name TEXT, season INT, team TEXT, matches INT, runs INT, balls_faced INT, fours INT, sixes INT, highest_score INT, dismissals INT, batting_average FLOAT, strike_rate FLOAT)
   -- Note: For career batting average, use SUM(runs)::numeric / NULLIF(SUM(dismissals), 0). For career strike rate, use (SUM(runs)::numeric / NULLIF(SUM(balls_faced), 0)) * 100.
7. fact_player_bowling_season(player_name TEXT, season INT, team TEXT, matches INT, legal_balls INT, runs_conceded INT, wickets INT, overs FLOAT, economy_rate FLOAT, bowling_average FLOAT, bowling_strike_rate FLOAT)
   -- Note: For career economy, use (SUM(runs_conceded)::numeric / NULLIF(SUM(legal_balls), 0)) * 6.
8. fact_venue_stats(venue TEXT PK, total_matches INT, avg_first_innings_score FLOAT, highest_first_innings_score INT, lowest_first_innings_score INT, bat_first_wins INT, chase_wins INT, chase_win_pct FLOAT)
"""

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)

# Lazy singletons so Hugging Face Spaces only loads models once
_engine = None
_embedder = None
_llm = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = os.getenv("SUPABASE_DB_URL")
        if not db_url:
            raise ValueError("SUPABASE_DB_URL is not set.")
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedder


def get_llm():
    global _llm
    if _llm is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        _llm = ChatGroq(api_key=api_key, model=model_name, temperature=0.1, max_retries=2)
    return _llm


class AgentState(TypedDict):
    question: str
    user_preferences: dict
    chat_history: list[dict]
    intent: Literal["rag", "sql", "hybrid"]
    rag_context: list[dict]
    sql_query: Optional[str]
    sql_results: list[dict]
    sql_error: Optional[str]
    chart_spec: Optional[dict]
    answer: str


# ============================================================================
# GRAPH NODES
# ============================================================================

def classify_intent_node(state: AgentState) -> dict:
    llm = get_llm()
    prompt = (
        "Classify the user's IPL cricket question into exactly one label:\n"
        "- 'rag': definitions, cricket rules, general summaries, or conceptual questions.\n"
        "- 'sql': exact rankings, comparisons, filtering by season/team/player/venue, or custom stats.\n"
        "- 'hybrid': needs both exact database numbers AND conceptual/statistical explanation.\n"
        "Respond with ONLY one word: rag, sql, or hybrid."
    )
    resp = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=state["question"])])
    label = resp.content.strip().lower()
    if label not in ("rag", "sql", "hybrid"):
        label = "hybrid"
    return {"intent": label}


def rag_retrieve_node(state: AgentState) -> dict:
    embedder = get_embedder()
    q_emb = embedder.encode(
        [f"Represent this sentence for searching relevant passages: {state['question']}"],
        normalize_embeddings=True,
    )[0]
    q_emb_str = "[" + ",".join(f"{x:.6f}" for x in q_emb.tolist()) + "]"

    sql = text("""
        SELECT doc_key, doc_type, content,
               ROUND((1 - (embedding <=> CAST(:q_emb AS vector)))::numeric, 4) AS similarity
        FROM public.rag_documents
        ORDER BY embedding <=> CAST(:q_emb AS vector)
        LIMIT 4;
    """)
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"q_emb": q_emb_str}).fetchall()

    docs = [
        {"doc_key": r[0], "doc_type": r[1], "content": r[2], "similarity": float(r[3])}
        for r in rows
    ]
    return {"rag_context": docs}


def sql_generate_node(state: AgentState) -> dict:
    llm = get_llm()
    system_prompt = (
        "You are an expert PostgreSQL analyst for IPL cricket data.\n"
        f"{GOLD_SCHEMA_PROMPT}\n"
        "Rules:\n"
        "1. Write ONLY a single valid PostgreSQL SELECT query.\n"
        "2. Use ILIKE for player, team, or venue name matching (e.g., player_name ILIKE '%Kohli%').\n"
        "3. Always include a LIMIT clause (max 50).\n"
        "4. Return ONLY raw SQL with no markdown fences, no explanation, and no trailing semicolon."
    )
    resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=state["question"])])
    raw_sql = resp.content.strip()
    # Strip markdown code fences if the model included them
    raw_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql, flags=re.IGNORECASE)
    raw_sql = re.sub(r"\s*```$", "", raw_sql).strip().rstrip(";")
    return {"sql_query": raw_sql}


def sql_validate_execute_node(state: AgentState) -> dict:
    sql_query = (state.get("sql_query") or "").strip()

    if not sql_query:
        return {"sql_results": [], "sql_error": "No SQL query generated."}

    # Strict read-only guardrails
    if not re.match(r"^(SELECT|WITH)\b", sql_query, re.IGNORECASE):
        return {"sql_results": [], "sql_error": "Blocked: Only SELECT/WITH read-only queries are allowed."}

    if FORBIDDEN_SQL_KEYWORDS.search(sql_query) or ";" in sql_query:
        return {"sql_results": [], "sql_error": "Blocked: Query contains forbidden SQL keywords or multiple statements."}

    # Enforce row limit if missing
    if not re.search(r"\bLIMIT\s+\d+\b", sql_query, re.IGNORECASE):
        sql_query = f"{sql_query} LIMIT 50"

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SET LOCAL statement_timeout = '5000';"))
            result = conn.execute(text(sql_query))
            columns = list(result.keys())
            rows = [
                {col: (float(val) if hasattr(val, "is_finite") else val) for col, val in zip(columns, row)}
                for row in result.fetchall()
            ]
        return {"sql_query": sql_query, "sql_results": rows, "sql_error": None}
    except Exception as e:
        return {"sql_results": [], "sql_error": str(e)}


def generate_chart_node(state: AgentState) -> dict:
    rows = state.get("sql_results") or []
    if len(rows) < 2:
        return {"chart_spec": None}

    columns = list(rows[0].keys())
    if len(columns) < 2:
        return {"chart_spec": None}

    # Pick first categorical/season column as X and first numeric column as Y
    x_col = columns[0]
    y_col = None
    for c in columns[1:]:
        sample_val = rows[0].get(c)
        if isinstance(sample_val, (int, float)) and not isinstance(sample_val, bool):
            y_col = c
            break

    if not y_col:
        return {"chart_spec": None}

    chart_type = "scatter" if x_col.lower() in ("season", "year", "start_date") else "bar"
    trace = {
        "type": chart_type,
        "x": [r.get(x_col) for r in rows],
        "y": [r.get(y_col) for r in rows],
        "name": y_col.replace("_", " ").title(),
    }
    if chart_type == "scatter":
        trace["mode"] = "lines+markers"

    chart_spec = {
        "data": [trace],
        "layout": {
            "title": f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
            "xaxis": {"title": x_col.replace("_", " ").title()},
            "yaxis": {"title": y_col.replace("_", " ").title()},
        },
    }
    return {"chart_spec": chart_spec}


def synthesize_response_node(state: AgentState) -> dict:
    llm = get_llm()
    prefs = state.get("user_preferences") or {}
    rag_docs = state.get("rag_context") or []
    sql_rows = state.get("sql_results") or []
    sql_err = state.get("sql_error")

    context_parts = []
    if prefs:
        context_parts.append(f"User Preferences: {json.dumps(prefs)}")
    if rag_docs:
        rag_text = "\n".join(f"- [{d['doc_type']}] {d['content']}" for d in rag_docs)
        context_parts.append(f"Retrieved Knowledge Base:\n{rag_text}")
    if sql_rows:
        context_parts.append(f"SQL Query Executed: {state.get('sql_query')}")
        context_parts.append(f"SQL Results (top {len(sql_rows)} rows):\n{json.dumps(sql_rows[:20], default=str)}")
    elif sql_err:
        context_parts.append(f"SQL Note: Query could not execute ({sql_err}). Rely on retrieved knowledge if available.")

    system_prompt = (
        "You are IPL Intelligence, an expert cricket data analyst.\n"
        "Answer the user's question accurately using ONLY the provided context and SQL results. "
        "Never fabricate statistics. Format numbers cleanly and keep the explanation concise and insightful."
    )
    user_msg = f"Question: {state['question']}\n\nContext:\n" + "\n\n".join(context_parts)
    resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
    return {"answer": resp.content.strip()}


# ============================================================================
# CONDITIONAL ROUTING & GRAPH COMPILATION
# ============================================================================

def route_after_intent(state: AgentState) -> str:
    if state["intent"] == "sql":
        return "sql_generate"
    return "rag_retrieve"


def route_after_rag(state: AgentState) -> str:
    if state["intent"] == "hybrid":
        return "sql_generate"
    return "synthesize"


def build_ipl_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("sql_generate", sql_generate_node)
    graph.add_node("sql_validate_execute", sql_validate_execute_node)
    graph.add_node("generate_chart", generate_chart_node)
    graph.add_node("synthesize", synthesize_response_node)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_after_intent,
        {"rag_retrieve": "rag_retrieve", "sql_generate": "sql_generate"},
    )
    graph.add_conditional_edges(
        "rag_retrieve",
        route_after_rag,
        {"sql_generate": "sql_generate", "synthesize": "synthesize"},
    )
    graph.add_edge("sql_generate", "sql_validate_execute")
    graph.add_edge("sql_validate_execute", "generate_chart")
    graph.add_edge("generate_chart", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


_compiled_graph = None


def run_ipl_agent(
    question: str,
    user_preferences: Optional[dict] = None,
    chat_history: Optional[list[dict]] = None,
) -> dict:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_ipl_graph()

    initial_state: AgentState = {
        "question": question,
        "user_preferences": user_preferences or {},
        "chat_history": chat_history or [],
        "intent": "hybrid",
        "rag_context": [],
        "sql_query": None,
        "sql_results": [],
        "sql_error": None,
        "chart_spec": None,
        "answer": "",
    }
    final_state = _compiled_graph.invoke(initial_state)
    return {
        "intent": final_state["intent"],
        "answer": final_state["answer"],
        "sql_query": final_state["sql_query"],
        "sql_row_count": len(final_state["sql_results"]),
        "sql_error": final_state["sql_error"],
        "chart_spec": final_state["chart_spec"],
    }