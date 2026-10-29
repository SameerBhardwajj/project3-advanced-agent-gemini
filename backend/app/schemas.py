from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class ChatCreate(BaseModel):
    title: str = Field(default="New chat", max_length=200)

class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)

class AgentAction(BaseModel):
    tool: str
    status: Literal["success", "denied", "failed", "skipped"]
    summary: str

class AgentResponse(BaseModel):
    answer: str
    intent: str
    actions: list[AgentAction] = Field(default_factory=list)
    memory_used: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False