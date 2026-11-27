"""Populate rag_documents embeddings with Voyage voyage-4-lite vectors."""

import os
import time
from pathlib import Path

import voyageai
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from voyageai.error import RateLimitError


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

vo = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])
engine = create_engine(os.environ["SUPABASE_DB_URL"])

with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT doc_key, content FROM public.rag_documents ORDER BY doc_key")
    ).fetchall()

batch_size = 64
completed = 0
for index in range(0, len(rows), batch_size):
    batch = rows[index : index + batch_size]
    while True:
        try:
            embeddings = vo.embed(
                [row[1] for row in batch],
                model="voyage-4-lite",
                input_type="document",
            ).embeddings
            break
        except RateLimitError:
            print(f"Rate limited before batch {index // 20 + 1}; waiting 60 seconds.", flush=True)
            time.sleep(60)

    if any(len(embedding) != 1024 for embedding in embeddings):
        raise RuntimeError("Voyage returned an embedding with an unexpected dimension.")

    with engine.begin() as conn:
        for (doc_key, _), embedding in zip(batch, embeddings):
            vector = "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"
            conn.execute(
                text(
                    "UPDATE public.rag_documents "
                    "SET embedding = CAST(:embedding AS vector) "
                    "WHERE doc_key = :doc_key"
                ),
                {"embedding": vector, "doc_key": doc_key},
            )

    completed += len(batch)
    print(f"Completed {completed}/{len(rows)} rows.", flush=True)
    if index + batch_size < len(rows):
        # The configured Voyage account is constrained to one reliable request
        # per minute, even though its advertised RPM is higher.
        time.sleep(62)

with engine.connect() as conn:
    total, embedded, min_dimensions, max_dimensions = conn.execute(
        text("""
            SELECT count(*), count(embedding), min(vector_dims(embedding)), max(vector_dims(embedding))
            FROM public.rag_documents
        """)
    ).one()

print(f"Populated {completed} rows with 1024-dim voyage-4-lite embeddings.")
print(
    f"Verification: total={total}, embedded={embedded}, "
    f"dimensions={min_dimensions}..{max_dimensions}"
)
