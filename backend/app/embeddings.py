from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL
from .models import KnowledgeChunk

client = genai.Client(api_key=GEMINI_API_KEY)

def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    result = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return list(result.embeddings[0].values)

def index_document(db: Session, source: str, content: str):
    vector = embed_text(content, "RETRIEVAL_DOCUMENT")
    chunk = KnowledgeChunk(source=source, content=content, embedding=vector)
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk

def search_knowledge(db: Session, query: str, limit: int = 5):
    vector = embed_text(query, "RETRIEVAL_QUERY")
    distance = KnowledgeChunk.embedding.cosine_distance(vector)
    rows = db.scalars(
        select(KnowledgeChunk)
        .order_by(distance)
        .limit(limit)
    ).all()
    return [
        {"id": r.id, "source": r.source, "content": r.content}
        for r in rows
    ]