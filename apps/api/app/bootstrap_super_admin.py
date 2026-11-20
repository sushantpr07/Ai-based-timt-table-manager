from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditEvent, Role, User
from app.security import hash_password


def main():
    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.role == Role.super_admin).limit(1)):
            raise SystemExit("A super-admin account already exists; bootstrap is disabled.")
        try:
            email = TypeAdapter(EmailStr).validate_python(input("Super-admin email: ")).lower()
        except ValidationError as exc:
            raise SystemExit(f"Invalid email address: {exc.errors()[0]['msg']}")
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("An account already uses this email address.")
        full_name = input("Full name: ").strip()
        if len(full_name) < 2:
            raise SystemExit("Full name must contain at least two characters.")
        password = getpass("Password (at least 12 characters): ")
        if len(password) < 12:
            raise SystemExit("Password must contain at least 12 characters.")
        if password != getpass("Confirm password: "):
            raise SystemExit("Passwords did not match.")
        account = User(institution_id=None, department_id=None, email=email, full_name=full_name,
                       password_hash=hash_password(password), role=Role.super_admin, email_verified=True)
        db.add(account)
        db.flush()
        db.add(AuditEvent(institution_id=None, actor_id=account.id, action="bootstrap_created",
                          resource_type="super_admin", resource_id=str(account.id)))
        db.commit()
        print(f"Created verified super-admin account for {email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
