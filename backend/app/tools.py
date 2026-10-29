from datetime import date
from sqlalchemy import select
from .models import User, LeaveBalance, LeaveRequest, UserMemory
from .embeddings import search_knowledge
from .datetime_tools import (
    get_current_datetime,
    resolve_datetime,
)


def search_company_knowledge(db, query, limit=5):
    return {"results": search_knowledge(db, query, limit)}

def get_profile(db, uid):
    u = db.get(User, uid)
    return {
        "name": u.name, "email": u.email, "role": u.role,
        "department": u.department, "job_title": u.job_title
    }

def get_leave_balance(db, uid):
    b = db.get(LeaveBalance, uid)
    if not b:
        return {"found": False}
    return {
        "found": True, "annual_total": b.annual_total,
        "annual_used": b.annual_used,
        "remaining": b.annual_total - b.annual_used
    }

def list_leave_requests(db, uid):
    rows = db.scalars(
        select(LeaveRequest).where(LeaveRequest.user_id == uid).order_by(LeaveRequest.id.desc())
    ).all()
    return {"requests": [
        {"id": r.id, "start_date": r.start_date.isoformat(),
         "end_date": r.end_date.isoformat(), "reason": r.reason, "status": r.status}
        for r in rows
    ]}

def create_leave_request(db, uid, start_date, end_date, reason):
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if end < start:
        return {"success": False, "error": "End date cannot be before start date."}
    days = (end - start).days + 1
    b = db.get(LeaveBalance, uid)
    if not b:
        return {"success": False, "error": "Leave balance does not exist."}
    remaining = b.annual_total - b.annual_used
    if days > remaining:
        return {"success": False, "error": f"Insufficient balance: requested {days}, remaining {remaining}."}
    r = LeaveRequest(
        user_id=uid, start_date=start, end_date=end,
        reason=reason, status="pending"
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return {
        "success": True, "request_id": r.id, "status": "pending",
        "requested_days": days, "remaining_before_approval": remaining
    }

def get_memory(db, uid):
    rows = db.scalars(select(UserMemory).where(UserMemory.user_id == uid)).all()
    return {"memories": [{"key": r.memory_key, "value": r.memory_value} for r in rows]}

def save_memory(db, uid, key, value):
    forbidden = {"password", "api_key", "token", "jwt", "secret", "credit_card"}
    if any(x in key.lower() for x in forbidden):
        return {"success": False, "error": "Sensitive memory keys are not allowed."}
    r = db.scalar(select(UserMemory).where(UserMemory.user_id == uid, UserMemory.memory_key == key))
    if r:
        r.memory_value = value
    else:
        db.add(UserMemory(user_id=uid, memory_key=key, memory_value=value))
    db.commit()
    return {"success": True, "key": key, "value": value}

def approve_leave_request(db, manager_id, request_id):
    manager = db.get(User, manager_id)
    if manager.role not in {"manager", "admin"}:
        return {"success": False, "error": "Authorization denied: manager/admin role required."}
    r = db.get(LeaveRequest, request_id)
    if not r:
        return {"success": False, "error": "Leave request not found."}
    if r.status != "pending":
        return {"success": False, "error": f"Request is already {r.status}."}
    b = db.get(LeaveBalance, r.user_id)
    days = (r.end_date - r.start_date).days + 1
    if not b or b.annual_used + days > b.annual_total:
        return {"success": False, "error": "Insufficient balance at approval time."}
    r.status = "approved"
    b.annual_used += days
    db.commit()
    return {"success": True, "request_id": r.id, "status": "approved", "days_deducted": days}

TOOLS = [
    {"name": "get_profile", "description": "Get the authenticated user's profile.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_leave_balance", "description": "Get the authenticated user's annual leave balance.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "list_leave_requests", "description": "List the authenticated user's leave requests.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "create_leave_request", "description": "Create a leave request for the authenticated user.",
     "parameters": {"type": "object", "properties": {
         "start_date": {"type": "string", "description": "YYYY-MM-DD"},
         "end_date": {"type": "string", "description": "YYYY-MM-DD"},
         "reason": {"type": "string"}}, "required": ["start_date", "end_date", "reason"]}},
    {"name": "get_memory", "description": "Get long-term memory for the authenticated user.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
    {"name": "save_memory", "description": "Save a non-sensitive long-term user preference or fact.",
     "parameters": {"type": "object", "properties": {
         "memory_key": {"type": "string"}, "memory_value": {"type": "string"}},
         "required": ["memory_key", "memory_value"]}},
    {"name": "approve_leave_request", "description": "Approve a pending leave request. Only managers/admins may do this.",
     "parameters": {"type": "object", "properties": {
         "request_id": {"type": "integer"}}, "required": ["request_id"]}},
    {
    "name": "get_current_datetime",
    "description": "Get the current date and time in Asia/Kolkata.",
    "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
    "name": "resolve_datetime",
    "description": """
Resolve a natural-language date or time expression into an exact
ISO-8601 datetime.

Use this whenever the user refers to:
- today
- tomorrow
- yesterday
- next week
- next Monday
- in 3 days
- in 2 hours
- a future date
- a future time
- relative dates or times

Do not ask the user for the exact calendar date if it can be
resolved automatically.
""",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Natural language date/time expression."
            },
            "timezone": {
                "type": "string",
                "description": "IANA timezone such as Asia/Kolkata."
            }
        },
        "required": ["expression"]
    }
},
]