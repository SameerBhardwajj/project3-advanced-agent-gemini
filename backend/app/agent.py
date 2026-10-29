import json
import time
from typing import Any
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from .config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT
from .models import User
from .tools import (
    TOOLS, get_profile, get_leave_balance, list_leave_requests,
    create_leave_request, get_memory, save_memory, approve_leave_request, search_company_knowledge
)
from .datetime_tools import (
    get_current_datetime,
    resolve_datetime,
)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=GEMINI_API_KEY)

class FinalAction(BaseModel):
    tool: str
    status: str
    summary: str

class FinalAgentResponse(BaseModel):
    answer: str
    intent: str
    actions: list[FinalAction] = Field(default_factory=list)
    memory_used: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False

def call_gemini(contents, config, attempts=3):
    for attempt in range(attempts):
        try:
            return client.models.generate_content(
                model=GEMINI_MODEL, contents=contents, config=config
            )
        except Exception as exc:
            if "503" not in str(exc) or attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)

def execute_tool(db: Session, user: User, name: str, args: dict[str, Any]):
    uid = user.id
    if name == "get_profile":
        return get_profile(db, uid)
    if name == "get_leave_balance":
        return get_leave_balance(db, uid)
    if name == "list_leave_requests":
        return list_leave_requests(db, uid)
    if name == "get_memory":
        return get_memory(db, uid)
    if name == "save_memory":
        return save_memory(db, uid, args["memory_key"].strip(), args["memory_value"].strip())
    if name == "create_leave_request":
        return create_leave_request(
            db, uid, args["start_date"], args["end_date"], args["reason"]
        )
    if name == "approve_leave_request":
        return approve_leave_request(db, uid, int(args["request_id"]))
    if name == "get_current_datetime":
        return get_current_datetime()
    if name == "resolve_datetime":
        return resolve_datetime(
            args["expression"],
            args.get("timezone", "Asia/Kolkata"),
        )
    return {"success": False, "error": "Unknown tool"}

def run_agent(db: Session, user: User, user_message: str, history):
    memories = get_memory(db, user.id)["memories"]

    contents = []
    for role, content in history[-20:]:
        contents.append(types.Content(
            role="model" if role == "assistant" else "user",
            parts=[types.Part.from_text(text=content)]
        ))

    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=(
            f"AUTHENTICATED USER ID: {user.id}\n"
            f"ROLE: {user.role}\n"
            f"LONG-TERM MEMORY: {json.dumps(memories)}\n\n"
            f"REQUEST:\n{user_message}"
        ))]
    ))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(function_declarations=TOOLS)]
    )

    actions = []
    final_text = None

    # Agent loop: model -> tool -> observation -> model -> ...
    for _ in range(6):
        response = call_gemini(contents, config)
        contents.append(response.candidates[0].content)
        calls = response.function_calls or []

        if not calls:
            final_text = response.text
            break

        for call in calls:
            result = execute_tool(db, user, call.name, dict(call.args or {}))
            err = str(result.get("error", ""))
            status = (
                "denied" if "denied" in err.lower() or "not authorized" in err.lower()
                else "failed" if result.get("success") is False
                else "success"
            )
            actions.append({
                "tool": call.name,
                "status": status,
                "summary": err or f"{call.name} completed."
            })

            # Omit id for compatibility with SDK versions that do not accept it.
            function_response = types.Part.from_function_response(
                name=call.name,
                response={"result": result},
            )
            contents.append(types.Content(
                role="user", parts=[function_response]
            ))

    if final_text is None:
        final_text = "I could not safely complete the task."

    # Final structured-output pass. Tool calls have already been executed.
    prompt = f"""Return JSON matching the schema.
Original request: {user_message}
Draft answer: {final_text}
Tool actions: {json.dumps(actions)}
Do not invent actions or facts."""

    structured = call_gemini(
        [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
        types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=FinalAgentResponse,
        )
    )

    try:
        return FinalAgentResponse.model_validate_json(structured.text)
    except Exception:
        return FinalAgentResponse(
            answer=final_text,
            intent="general",
            actions=[FinalAction(**a) for a in actions],
            memory_used=[m["key"] for m in memories],
        )