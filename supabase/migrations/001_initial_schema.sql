-- ============================================================================
-- IPL INTELLIGENCE - INITIAL DATABASE MIGRATION (001)
-- ============================================================================

-- 1. Enable pgvector extension for Hybrid RAG embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- SECTION A: IPL ANALYTICAL DATA (GOLD LAYER)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.dim_seasons (
    season INTEGER PRIMARY KEY,
    total_matches INTEGER NOT NULL,
    season_start_date TEXT,
    season_end_date TEXT
);

CREATE TABLE IF NOT EXISTS public.dim_teams (
    team_name TEXT PRIMARY KEY,
    total_matches_played INTEGER NOT NULL,
    first_season INTEGER,
    last_season INTEGER
);

CREATE TABLE IF NOT EXISTS public.dim_venues (
    venue_name TEXT PRIMARY KEY,
    total_matches INTEGER NOT NULL,
    first_season INTEGER,
    last_season INTEGER
);

CREATE TABLE IF NOT EXISTS public.dim_players (
    player_name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS public.fact_matches (
    match_id INTEGER PRIMARY KEY,
    season INTEGER NOT NULL REFERENCES public.dim_seasons(season),
    start_date TEXT,
    venue TEXT,
    team_1 TEXT NOT NULL,
    team_2 TEXT NOT NULL,
    innings_1_runs INTEGER,
    innings_1_wickets INTEGER,
    innings_2_runs INTEGER,
    innings_2_wickets INTEGER,
    winner TEXT,
    win_type TEXT,
    win_margin INTEGER
);

CREATE TABLE IF NOT EXISTS public.fact_player_batting_season (
    player_name TEXT NOT NULL,
    season INTEGER NOT NULL,
    team TEXT NOT NULL,
    matches INTEGER NOT NULL,
    runs INTEGER NOT NULL,
    balls_faced INTEGER NOT NULL,
    fours INTEGER NOT NULL,
    sixes INTEGER NOT NULL,
    highest_score INTEGER,
    dismissals INTEGER NOT NULL,
    batting_average DOUBLE PRECISION,
    strike_rate DOUBLE PRECISION,
    PRIMARY KEY (player_name, season, team)
);

CREATE TABLE IF NOT EXISTS public.fact_player_bowling_season (
    player_name TEXT NOT NULL,
    season INTEGER NOT NULL,
    team TEXT NOT NULL,
    matches INTEGER NOT NULL,
    legal_balls INTEGER NOT NULL,
    runs_conceded INTEGER NOT NULL,
    wickets INTEGER NOT NULL,
    overs DOUBLE PRECISION,
    economy_rate DOUBLE PRECISION,
    bowling_average DOUBLE PRECISION,
    bowling_strike_rate DOUBLE PRECISION,
    PRIMARY KEY (player_name, season, team)
);

CREATE TABLE IF NOT EXISTS public.fact_venue_stats (
    venue TEXT PRIMARY KEY,
    total_matches INTEGER NOT NULL,
    avg_first_innings_score DOUBLE PRECISION,
    highest_first_innings_score INTEGER,
    lowest_first_innings_score INTEGER,
    bat_first_wins INTEGER NOT NULL,
    chase_wins INTEGER NOT NULL,
    chase_win_pct DOUBLE PRECISION
);

-- Indexes for fast dashboard filtering & Text-to-SQL queries
CREATE INDEX IF NOT EXISTS idx_matches_season ON public.fact_matches(season);
CREATE INDEX IF NOT EXISTS idx_matches_venue ON public.fact_matches(venue);
CREATE INDEX IF NOT EXISTS idx_batting_season ON public.fact_player_batting_season(season);
CREATE INDEX IF NOT EXISTS idx_batting_runs ON public.fact_player_batting_season(runs DESC);
CREATE INDEX IF NOT EXISTS idx_bowling_season ON public.fact_player_bowling_season(season);
CREATE INDEX IF NOT EXISTS idx_bowling_wickets ON public.fact_player_bowling_season(wickets DESC);

-- ============================================================================
-- SECTION B: VECTOR KNOWLEDGE BASE (PGVECTOR - BGE-SMALL 384 DIM)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.rag_documents (
    id BIGSERIAL PRIMARY KEY,
    doc_key TEXT UNIQUE NOT NULL,
    doc_type TEXT NOT NULL, -- 'player_summary', 'team_history', 'season_summary', 'venue_info', 'cricket_term'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding VECTOR(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
    ON public.rag_documents USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- SECTION C: APPLICATION & PERSONALIZATION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    favourite_team TEXT,
    favourite_player TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New IPL Analysis',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sql_query TEXT,
    chart_spec JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.saved_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    question TEXT NOT NULL,
    summary TEXT NOT NULL,
    sql_query TEXT,
    chart_spec JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON public.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON public.chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_saved_analyses_user ON public.saved_analyses(user_id);

-- ============================================================================
-- SECTION D: ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.dim_seasons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_venues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dim_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_player_batting_season ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_player_bowling_season ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fact_venue_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rag_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_analyses ENABLE ROW LEVEL SECURITY;

-- Public READ-ONLY access for IPL analytical tables & RAG docs
CREATE POLICY "Public read dim_seasons" ON public.dim_seasons FOR SELECT USING (true);
CREATE POLICY "Public read dim_teams" ON public.dim_teams FOR SELECT USING (true);
CREATE POLICY "Public read dim_venues" ON public.dim_venues FOR SELECT USING (true);
CREATE POLICY "Public read dim_players" ON public.dim_players FOR SELECT USING (true);
CREATE POLICY "Public read fact_matches" ON public.fact_matches FOR SELECT USING (true);
CREATE POLICY "Public read fact_player_batting_season" ON public.fact_player_batting_season FOR SELECT USING (true);
CREATE POLICY "Public read fact_player_bowling_season" ON public.fact_player_bowling_season FOR SELECT USING (true);
CREATE POLICY "Public read fact_venue_stats" ON public.fact_venue_stats FOR SELECT USING (true);
CREATE POLICY "Public read rag_documents" ON public.rag_documents FOR SELECT USING (true);

-- Strict per-user RLS for personal tables
CREATE POLICY "Users manage own profile"
    ON public.user_profiles FOR ALL
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users manage own chat sessions"
    ON public.chat_sessions FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own chat messages"
    ON public.chat_messages FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own saved analyses"
    ON public.saved_analyses FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);