from app.db import Base, SessionLocal, engine
from app.models import KnowledgeChunk
from app.embeddings import index_document

Base.metadata.create_all(bind=engine)

DOCUMENTS = [
    ("leave-policy.md", """Company Leave Policy
Employees receive 24 annual leave days.
Leave requests must have a start date, end date and reason.
Requests remain pending until approved by a manager or admin.
Leave cannot be approved if the employee does not have enough remaining balance."""),
    ("agent-security.md", """Agent Security Policy
The LLM may request tools, but backend authorization must always be enforced by Python.
The authenticated user's identity comes from the JWT and must never be supplied by the model.
Sensitive credentials, tokens and secrets must not be stored in long-term memory."""),
    ("engineering-handbook.md", """Engineering Handbook
Engineering teams use code review before merging changes.
Production changes should have tests, observability and rollback planning.
Managers are responsible for approving team leave requests."""),
]

with SessionLocal() as db:
    existing = {x.source for x in db.query(KnowledgeChunk).all()}
    for source, content in DOCUMENTS:
        if source in existing:
            print(f"Skipping existing source: {source}")
            continue
        index_document(db, source, content)
        print(f"Indexed: {source}")

print("Knowledge indexing complete.")