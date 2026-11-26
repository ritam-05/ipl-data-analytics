import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Any
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import text

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVAL_DIR = os.path.join(ROOT_DIR, "eval")
GOLDEN_PATH = os.path.join(EVAL_DIR, "golden_questions.json")
JSON_REPORT_PATH = os.path.join(EVAL_DIR, "eval_report.json")
MD_REPORT_PATH = os.path.join(EVAL_DIR, "eval_report.md")

QUERY_INTERVAL_SECONDS = 60.0

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

from backend.app.agents.ipl_agent import run_ipl_agent, get_engine, get_embedder


def load_golden_questions() -> list[dict[str, Any]]:
    if not os.path.exists(GOLDEN_PATH):
        raise FileNotFoundError(f"Golden test file not found at {GOLDEN_PATH}")
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise ValueError("golden_questions.json must contain a non-empty JSON list.")
    return data


def check_rag_recall(question: str, expected_keys: list[str], k: int = 4) -> dict[str, Any]:
    if not expected_keys:
        return {"checked": False, "hit": None, "reciprocal_rank": None, "retrieved_keys": []}

    embedder = get_embedder()
    q_emb = embedder.encode(
        [f"Represent this sentence for searching relevant passages: {question}"],
        normalize_embeddings=True,
    )[0]
    q_emb_str = "[" + ",".join(f"{x:.6f}" for x in q_emb.tolist()) + "]"

    sql = text("""
        SELECT doc_key
        FROM public.rag_documents
        ORDER BY embedding <=> CAST(:q_emb AS vector)
        LIMIT :k;
    """)
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"q_emb": q_emb_str, "k": k}).fetchall()

    retrieved_keys = [r[0] for r in rows]
    rank_hit = None
    for idx, key in enumerate(retrieved_keys, start=1):
        if key in expected_keys:
            rank_hit = idx
            break

    return {
        "checked": True,
        "hit": rank_hit is not None,
        "reciprocal_rank": (1.0 / rank_hit) if rank_hit else 0.0,
        "retrieved_keys": retrieved_keys,
    }


def evaluate_case(case: dict[str, Any], top_k: int = 4) -> dict[str, Any]:
    question = case["question"]
    rag_eval = check_rag_recall(question, case.get("expected_doc_keys", []), k=top_k)

    t0 = time.perf_counter()
    out = run_ipl_agent(question=question)
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    answer = out.get("answer") or ""
    sql_err = out.get("sql_error")
    has_chart = out.get("chart_spec") is not None

    must_any = case.get("must_contain_any") or []
    contains_ok = True if not must_any else any(tok.lower() in answer.lower() for tok in must_any)

    must_not = case.get("must_not_contain") or []
    matched_forbidden = [tok for tok in must_not if tok.lower() in answer.lower()]
    forbidden_ok = len(matched_forbidden) == 0

    expected_chart = bool(case.get("expect_chart", False))
    chart_ok = has_chart is expected_chart
    no_sql_err = sql_err is None

    passed = no_sql_err and contains_ok and forbidden_ok and chart_ok
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return {
        "timestamp": timestamp,
        "id": case["id"],
        "category": case.get("category", "general"),
        "question": question,
        "passed": passed,
        "intent": out.get("intent"),
        "latency_ms": latency_ms,
        "sql_row_count": out.get("sql_row_count", 0),
        "sql_error": sql_err,
        "contains_ok": contains_ok,
        "forbidden_ok": forbidden_ok,
        "matched_forbidden": matched_forbidden,
        "chart_ok": chart_ok,
        "has_chart": has_chart,
        "expected_chart": expected_chart,
        "rag_eval": rag_eval,
        "answer_preview": " ".join(answer.split())[:240],
    }


def init_markdown_log(md_path: str, total_cases: int, interval_seconds: float) -> None:
    header = [
        "# cricketmama.exe Live Evaluation Log & Report",
        "",
        f"- **Total Cases:** {total_cases}",
        f"- **Per-Query Pacing:** {interval_seconds:.0f}s",
        "",
        "## Live Test Execution Logs",
        "",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header))


def append_case_log_to_md(md_path: str, index: int, total: int, r: dict[str, Any]) -> None:
    status_label = "PASS" if r["passed"] else "FAIL"
    rag_info = (
        f"hit={r['rag_eval']['hit']}, rr={r['rag_eval']['reciprocal_rank']}, top_k={r['rag_eval']['retrieved_keys']}"
        if r["rag_eval"].get("checked")
        else "n/a"
    )
    entry = [
        f"### [{index}/{total}] `{r['id']}` — **{status_label}**",
        f"- **Time:** {r['timestamp']}",
        f"- **Category / Intent:** `{r['category']}` / `{r['intent']}`",
        f"- **Latency:** `{r['latency_ms']} ms` | **Rows:** `{r['sql_row_count']}`",
        f"- **Checks:** sql_err=`{r['sql_error']}`, contains=`{r['contains_ok']}`, forbidden=`{r['forbidden_ok']}`, chart=`{r['chart_ok']}` (actual=`{r['has_chart']}`, expected=`{r['expected_chart']}`)",
        f"- **RAG Recall:** {rag_info}",
        f"- **Question:** {r['question']}",
        f"- **Answer Preview:** {r['answer_preview']}",
        "",
    ]
    with open(md_path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry) + "\n")


def append_summary_to_md(summary: dict[str, Any], md_path: str) -> None:
    lines = [
        "---",
        "",
        "## Final Evaluation Summary",
        "",
        f"- **Pass Rate:** {summary['pass_rate']}",
        f"- **RAG Hit Rate @ 4:** {summary['rag_hit_rate_at_4']}",
        f"- **RAG MRR @ 4:** {summary['rag_mrr_at_4']}",
        f"- **Average Latency:** {summary['avg_latency_ms']} ms",
        f"- **P95 Latency:** {summary['p95_latency_ms']} ms",
        "",
        "| # | Case ID | Category | Intent | Status | Chart OK | Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, r in enumerate(summary["cases"], start=1):
        lines.append(
            f"| {i} | {r['id']} | {r['category']} | {r['intent']} | "
            f"{'PASS' if r['passed'] else 'FAIL'} | {'Yes' if r['chart_ok'] else 'No'} | {r['latency_ms']} |"
        )
    lines.append("")
    with open(md_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_evaluation(top_k: int = 4, interval_seconds: float = QUERY_INTERVAL_SECONDS) -> dict[str, Any]:
    os.makedirs(EVAL_DIR, exist_ok=True)
    cases = load_golden_questions()
    init_markdown_log(MD_REPORT_PATH, total_cases=len(cases), interval_seconds=interval_seconds)

    results: list[dict[str, Any]] = []

    for idx, case in enumerate(cases):
        case_start = time.monotonic()
        case_num = idx + 1
        print(f"\n[{case_num}/{len(cases)}] Starting test: {case['id']} ({case['question']})", flush=True)

        res = evaluate_case(case, top_k=top_k)
        results.append(res)

        # Print immediate log to CMD and append immediately to eval_report.md
        print(
            f"[{case_num}/{len(cases)}] LOG | id={res['id']} | status={'PASS' if res['passed'] else 'FAIL'} | "
            f"intent={res['intent']} | latency={res['latency_ms']}ms | rows={res['sql_row_count']} | "
            f"chart_ok={res['chart_ok']} | sql_err={res['sql_error']}",
            flush=True,
        )
        print(f"  Preview: {res['answer_preview']}", flush=True)
        append_case_log_to_md(MD_REPORT_PATH, case_num, len(cases), res)

        if idx < len(cases) - 1:
            elapsed = time.monotonic() - case_start
            sleep_for = max(0.0, interval_seconds - elapsed)
            if sleep_for > 0:
                print(
                    f"  Waiting {sleep_for:.1f}s before next query ({interval_seconds:.0f}s pacing)...",
                    flush=True,
                )
                time.sleep(sleep_for)

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    latencies = [r["latency_ms"] for r in results]

    rag_cases = [r["rag_eval"] for r in results if r["rag_eval"]["checked"]]
    hit_rate = (
        round(sum(1 for x in rag_cases if x["hit"]) / len(rag_cases), 3)
        if rag_cases
        else None
    )
    mrr = (
        round(sum(x["reciprocal_rank"] for x in rag_cases) / len(rag_cases), 3)
        if rag_cases
        else None
    )

    summary = {
        "total_cases": total,
        "passed_cases": passed_count,
        "pass_rate": f"{passed_count}/{total} ({round(passed_count / total * 100, 1)}%)" if total else "0/0",
        "rag_hit_rate_at_4": hit_rate,
        "rag_mrr_at_4": mrr,
        "avg_latency_ms": round(float(np.mean(latencies)), 1) if latencies else 0.0,
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 1) if latencies else 0.0,
        "cases": results,
    }

    with open(JSON_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    append_summary_to_md(summary, MD_REPORT_PATH)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"\nSaved JSON report to {JSON_REPORT_PATH}", flush=True)
    print(f"Saved Markdown log & report to {MD_REPORT_PATH}", flush=True)
    return summary


if __name__ == "__main__":
    run_evaluation()