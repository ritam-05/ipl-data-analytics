"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { apiFetch } from "@/lib/api";
import DynamicChart, { ChartSpec } from "@/components/DynamicChart";
import { Bot, Send, Plus, Bookmark, Code2, MessageSquare, Check } from "lucide-react";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
}

interface ChatMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sql_query?: string | null;
  chart_spec?: ChartSpec | null;
}

interface ChatApiResponse {
  session_id: string;
  intent: string;
  answer: string;
  sql_query: string | null;
  sql_row_count: number;
  sql_error: string | null;
  chart_spec: ChartSpec | null;
}

const SAMPLE_PROMPTS = [
  "Who are the top 5 all-time run scorers in IPL history?",
  "Show the average first innings score by season from 2018 to 2026.",
  "How is bowling economy rate calculated in IPL cricket?",
  "Which 5 venues have the highest chasing win percentage (min 15 matches)?",
];

export default function AssistantPage() {
  const [isAuthed, setIsAuthed] = useState<boolean | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedIndices, setSavedIndices] = useState<Record<number, boolean>>({});

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const authed = Boolean(data.session);
      setIsAuthed(authed);
      if (authed) {
        loadSessions();
      }
    });
  }, []);

  async function loadSessions() {
    try {
      const data = await apiFetch<ChatSession[]>("/api/chat/sessions", {}, true);
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chat sessions.");
    }
  }

  async function selectSession(sessionId: string) {
    setActiveSessionId(sessionId);
    setError(null);
    setSavedIndices({});
    try {
      const msgs = await apiFetch<ChatMessage[]>(
        `/api/chat/sessions/${sessionId}/messages`,
        {},
        true
      );
      setMessages(msgs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages.");
    }
  }

  function startNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setSavedIndices({});
    setError(null);
  }

  async function sendMessage(questionText?: string) {
    const q = (questionText ?? input).trim();
    if (!q || sending) return;

    setInput("");
    setError(null);
    setSending(true);
    setMessages((prev) => [...prev, { role: "user", content: q }]);

    try {
      const res = await apiFetch<ChatApiResponse>(
        "/api/chat",
        {
          method: "POST",
          body: JSON.stringify({
            session_id: activeSessionId,
            question: q,
          }),
        },
        true
      );

      if (!activeSessionId) {
        setActiveSessionId(res.session_id);
        loadSessions();
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          sql_query: res.sql_query,
          chart_spec: res.chart_spec,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get response from AI Assistant.");
    } finally {
      setSending(false);
    }
  }

  async function handleSaveAnalysis(msgIndex: number, msg: ChatMessage) {
    const prevUserMsg = messages[msgIndex - 1];
    const question = prevUserMsg?.role === "user" ? prevUserMsg.content : "IPL Analysis";
    const title = question.length > 70 ? `${question.slice(0, 70)}...` : question;

    try {
      await apiFetch(
        "/api/saved-analyses",
        {
          method: "POST",
          body: JSON.stringify({
            title,
            question,
            summary: msg.content,
            sql_query: msg.sql_query ?? null,
            chart_spec: msg.chart_spec ?? null,
          }),
        },
        true
      );
      setSavedIndices((prev) => ({ ...prev, [msgIndex]: true }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save analysis.");
    }
  }

  if (isAuthed === null) {
    return <div className="py-16 text-center text-sm text-slate-400">Checking session...</div>;
  }

  if (!isAuthed) {
    return (
      <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center">
        <Bot className="mx-auto h-10 w-10 text-amber-400" />
        <h1 className="mt-4 text-xl font-bold text-white">Sign in to use the AI Assistant</h1>
        <p className="mt-2 text-sm text-slate-400">
          Your chat history, dynamic SQL charts, and saved analyses are securely stored in your account.
        </p>
        <Link
          href="/login"
          className="mt-6 inline-block rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400"
        >
          Sign In / Sign Up
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-4">
      {/* Sidebar: Chat Sessions */}
      <aside className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 lg:col-span-1">
        <button
          onClick={startNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400"
        >
          <Plus className="h-4 w-4" />
          New Analysis
        </button>

        <div className="mt-4 space-y-1.5">
          <p className="px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Recent Sessions
          </p>
          {sessions.length === 0 ? (
            <p className="px-2 py-4 text-xs text-slate-500">No saved chats yet.</p>
          ) : (
            sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => selectSession(s.id)}
                className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${
                  activeSessionId === s.id
                    ? "bg-amber-500/15 text-amber-400"
                    : "text-slate-300 hover:bg-slate-800/70"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{s.title}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <section className="flex h-[75vh] flex-col rounded-2xl border border-slate-800 bg-slate-900/60 lg:col-span-3">
        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <Bot className="h-10 w-10 text-amber-400" />
              <h2 className="mt-3 text-lg font-semibold text-white">
                Ask IPL Intelligence Anything
              </h2>
              <p className="mt-1 max-w-md text-xs text-slate-400">
                Powered by Groq + LangGraph Hybrid RAG &amp; Text-to-SQL over 19 IPL seasons (2008–2026).
              </p>
              <div className="mt-6 grid w-full max-w-xl gap-2 sm:grid-cols-2">
                {SAMPLE_PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => sendMessage(p)}
                    className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-left text-xs text-slate-300 hover:border-amber-500/50 hover:text-white"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-3xl rounded-2xl px-4 py-3 text-sm ${
                    m.role === "user"
                      ? "bg-amber-500 text-slate-950 font-medium"
                      : "w-full border border-slate-800 bg-slate-950/80 text-slate-200"
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>

                  {m.role === "assistant" && m.chart_spec && (
                    <DynamicChart spec={m.chart_spec} />
                  )}

                  {m.role === "assistant" && m.sql_query && (
                    <details className="mt-3 rounded-lg border border-slate-800 bg-slate-900/70 p-2.5 text-xs">
                      <summary className="flex cursor-pointer items-center gap-1.5 font-medium text-slate-400 hover:text-slate-200">
                        <Code2 className="h-3.5 w-3.5" />
                        View Generated PostgreSQL Query
                      </summary>
                      <pre className="mt-2 overflow-x-auto text-[11px] text-emerald-400">
                        {m.sql_query}
                      </pre>
                    </details>
                  )}

                  {m.role === "assistant" && (
                    <div className="mt-3 flex justify-end">
                      <button
                        onClick={() => handleSaveAnalysis(idx, m)}
                        disabled={Boolean(savedIndices[idx])}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:border-emerald-800 disabled:text-emerald-400"
                      >
                        {savedIndices[idx] ? (
                          <>
                            <Check className="h-3.5 w-3.5" />
                            Saved
                          </>
                        ) : (
                          <>
                            <Bookmark className="h-3.5 w-3.5" />
                            Save Analysis
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {sending && (
            <div className="text-xs text-amber-400">
              Analyzing IPL data (routing RAG / Text-to-SQL)...
            </div>
          )}
        </div>

        {error && (
          <div className="mx-6 mb-2 rounded-lg border border-red-800 bg-red-950/50 px-3 py-2 text-xs text-red-300">
            {error}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
          className="flex items-center gap-2 border-t border-slate-800 p-4"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about IPL players, teams, venues, or seasons..."
            className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-amber-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="flex items-center gap-1.5 rounded-xl bg-amber-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            Send
          </button>
        </form>
      </section>
    </div>
  );
}