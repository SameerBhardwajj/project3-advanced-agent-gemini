from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from .agent import run_agent
from .config import FRONTEND_ORIGIN
from .db import Base, engine, get_db
from .models import User, Chat, Message
from .schemas import LoginRequest, TokenResponse, ChatCreate, ChatMessageRequest
from .security import get_current_user, verify_password, create_access_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Project 3 Advanced Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/auth/login", response_model=TokenResponse)
def login(p: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == p.email))
    if not user or not verify_password(p.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password.")
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    }

@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "role": user.role, "department": user.department, "job_title": user.job_title
    }

@app.get("/api/chats")
def chats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Chat).where(Chat.user_id == user.id).order_by(Chat.id.desc())).all()

@app.post("/api/chats")
def new_chat(p: ChatCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = Chat(user_id=user.id, title=p.title)
    db.add(c); db.commit(); db.refresh(c)
    return c

@app.get("/api/chats/{chat_id}/messages")
def get_messages(chat_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.scalar(select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id))
    if not c:
        raise HTTPException(404, "Chat not found.")
    return db.scalars(select(Message).where(Message.chat_id == chat_id).order_by(Message.id)).all()

@app.post("/api/chats/{chat_id}/messages")
def send(chat_id: int, p: ChatMessageRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.scalar(select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id))
    if not c:
        raise HTTPException(404, "Chat not found.")

    rows = db.scalars(select(Message).where(Message.chat_id == chat_id).order_by(Message.id)).all()
    history = [(m.role, m.content) for m in rows]
    db.add(Message(chat_id=chat_id, role="user", content=p.message))
    db.flush()

    result = run_agent(db, user, p.message, history)
    db.add(Message(chat_id=chat_id, role="assistant", content=result.answer))
    if c.title == "New chat":
        c.title = p.message[:60]
    db.commit()
    return result.model_dump()