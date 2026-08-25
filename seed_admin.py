import sys

from app.database import SessionLocal
from app.models import Role, User
from app.security import hash_password


def seed_admin(email: str, password: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, hashed_password=hash_password(password), role=Role.ADMIN)
            db.add(user)
            action = "Created"
        else:
            user.role = Role.ADMIN
            action = "Promoted existing"
        db.commit()
        print(f"{action} admin user: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: uv run python seed_admin.py <email> <password>")
        sys.exit(1)
    seed_admin(sys.argv[1], sys.argv[2])
