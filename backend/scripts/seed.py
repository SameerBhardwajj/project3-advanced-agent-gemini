import secrets
from sqlalchemy import select
from app.db import Base, SessionLocal, engine
from app.models import User, LeaveBalance, UserMemory
from app.security import hash_password

Base.metadata.create_all(bind=engine)

DEMO = [
    ("Demo Employee", "employee@example.com", "demo-password", "employee", "Engineering", "Senior Software Engineer", 5),
    ("Demo Manager", "manager@example.com", "demo-password", "manager", "Engineering", "Engineering Manager", 8),
]

with SessionLocal() as db:
    for name, email, password, role, dept, title, used in DEMO:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.password_hash = hash_password(password)
            continue
        user = User(
            name=name, email=email, password_hash=hash_password(password),
            role=role, department=dept, job_title=title
        )
        db.add(user)
        db.flush()
        db.add(LeaveBalance(user_id=user.id, annual_total=24, annual_used=used))
        db.add(UserMemory(
            user_id=user.id,
            memory_key="communication_style",
            memory_value="concise" if role == "employee" else "detailed"
        ))
    db.commit()

print("Seed complete.")
print("Employee: manager@example.com / demo-password")
print("Manager:  manager@example.com / demo-password")