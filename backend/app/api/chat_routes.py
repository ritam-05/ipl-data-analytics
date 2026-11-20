from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.app.core.auth import get_current_user, get_supabase_client
from backend.app.agents.ipl_agent import run_ipl_agent

router = APIRouter(prefix="/api", tags=["AI Assistant & User Data"])


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New IPL Analysis", max_length=120)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str = Field(..., min_length=2, max_length=1000)


class SaveAnalysisRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    question: str
    summary: str
    sql_query: Optional[str] = None
    chart_spec: Optional[dict] = None


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    favourite_team: Optional[str] = Field(default=None, max_length=100)
    favourite_player: Optional[str] = Field(default=None, max_length=100)


# ============================================================================
# CHAT SESSIONS & AI ASSISTANT
# ============================================================================

@router.get("/chat/sessions")
def list_chat_sessions(user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    res = (
        sb.table("chat_sessions")
        .select("*")
        .eq("user_id", user["id"])
        .order("updated_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/chat/sessions")
def create_chat_session(req: CreateSessionRequest, user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    res = (
        sb.table("chat_sessions")
        .insert({"user_id": user["id"], "title": req.title})
        .execute()
    )
    return res.data[0]


@router.get("/chat/sessions/{session_id}/messages")
def get_session_messages(session_id: str, user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    res = (
        sb.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .eq("user_id", user["id"])
        .order("created_at", desc=False)
        .execute()
    )
    return res.data


@router.post("/chat")
def chat_with_agent(req: ChatRequest, user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    user_id = user["id"]

    # 1. Create a session automatically if none provided
    session_id = req.session_id
    if not session_id:
        title = req.question[:60] + ("..." if len(req.question) > 60 else "")
        sess = sb.table("chat_sessions").insert({"user_id": user_id, "title": title}).execute()
        session_id = sess.data[0]["id"]
    else:
        # Verify the session belongs to this user
        check = (
            sb.table("chat_sessions")
            .select("id")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not check.data:
            raise HTTPException(status_code=404, detail="Chat session not found.")

    # 2. Fetch user preferences for personalization
    prof = sb.table("user_profiles").select("favourite_team, favourite_player").eq("id", user_id).execute()
    user_prefs = prof.data[0] if prof.data else {}

    # 3. Fetch recent chat history (last 6 messages)
    hist_res = (
        sb.table("chat_messages")
        .select("role, content")
        .eq("session_id", session_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(6)
        .execute()
    )
    chat_history = list(reversed(hist_res.data)) if hist_res.data else []

    # 4. Save user message
    sb.table("chat_messages").insert({
        "session_id": session_id,
        "user_id": user_id,
        "role": "user",
        "content": req.question,
    }).execute()

    # 5. Run LangGraph AI Agent
    agent_output = run_ipl_agent(
        question=req.question,
        user_preferences=user_prefs,
        chat_history=chat_history,
    )

    # 6. Save assistant response
    sb.table("chat_messages").insert({
        "session_id": session_id,
        "user_id": user_id,
        "role": "assistant",
        "content": agent_output["answer"],
        "sql_query": agent_output["sql_query"],
        "chart_spec": agent_output["chart_spec"],
    }).execute()

    return {
        "session_id": session_id,
        **agent_output,
    }


# ============================================================================
# SAVED ANALYSES & USER PROFILE
# ============================================================================

@router.get("/saved-analyses")
def list_saved_analyses(user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    res = (
        sb.table("saved_analyses")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/saved-analyses")
def save_analysis(req: SaveAnalysisRequest, user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    res = (
        sb.table("saved_analyses")
        .insert({
            "user_id": user["id"],
            "title": req.title,
            "question": req.question,
            "summary": req.summary,
            "sql_query": req.sql_query,
            "chart_spec": req.chart_spec,
        })
        .execute()
    )
    return res.data[0]


@router.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    res = sb.table("user_profiles").select("*").eq("id", user["id"]).execute()
    if not res.data:
        return {"id": user["id"], "email": user["email"], "display_name": None, "favourite_team": None, "favourite_player": None}
    return {**res.data[0], "email": user["email"]}


@router.put("/profile")
def update_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    sb = get_supabase_client()
    payload = {
        "id": user["id"],
        "display_name": req.display_name,
        "favourite_team": req.favourite_team,
        "favourite_player": req.favourite_player,
    }
    res = sb.table("user_profiles").upsert(payload).execute()
    return res.data[0]