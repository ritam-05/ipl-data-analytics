"""One-time migration of RAG embeddings to Voyage voyage-4-lite (1024 dimensions)."""

import os

import voyageai
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
EMBEDDING_MODEL_NAME = "voyage-4-lite"
EMBEDDING_BATCH_SIZE = 64

load_dotenv(os.path.join(ROOT_DIR, ".env"))


def reembed_documents() -> None:
    db_url = os.getenv("SUPABASE_DB_URL")
    voyage_api_key = os.getenv("VOYAGE_API_KEY")
    if not db_url:
        raise ValueError("SUPABASE_DB_URL is not set in environment variables.")
    if not voyage_api_key:
        raise ValueError("VOYAGE_API_KEY is not set in environment variables.")

    client = voyageai.Client(api_key=voyage_api_key)
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
        pool_recycle=300,
        connect_args={"prepare_threshold": None},
    )

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT doc_key, content FROM public.rag_documents ORDER BY doc_key")
        ).fetchall()

        # Existing 384-dimensional values cannot be cast to 1024 dimensions.
        # Rebuild the HNSW index after resetting the column and before repopulating it.
        conn.execute(text("DROP INDEX IF EXISTS public.idx_rag_documents_embedding"))
        conn.execute(
            text(
                "ALTER TABLE public.rag_documents "
                "ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector(1024)"
            )
        )

        for start in range(0, len(rows), EMBEDDING_BATCH_SIZE):
            batch = rows[start : start + EMBEDDING_BATCH_SIZE]
            embeddings = client.embed(
                [row.content for row in batch],
                model=EMBEDDING_MODEL_NAME,
                input_type="document",
            ).embeddings
            for row, embedding in zip(batch, embeddings):
                vector = "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"
                conn.execute(
                    text(
                        "UPDATE public.rag_documents "
                        "SET embedding = CAST(:embedding AS vector) "
                        "WHERE doc_key = :doc_key"
                    ),
                    {"embedding": vector, "doc_key": row.doc_key},
                )

        conn.execute(
            text(
                "CREATE INDEX idx_rag_documents_embedding "
                "ON public.rag_documents USING hnsw (embedding vector_cosine_ops)"
            )
        )

    print(
        f"Re-embedded {len(rows)} documents with {EMBEDDING_MODEL_NAME} "
        "(1024 dimensions)."
    )


if __name__ == "__main__":
    reembed_documents()
