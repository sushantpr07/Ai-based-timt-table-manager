import logging
from pathlib import Path
import shutil

from app.db import SessionLocal
from app.models import User, Institution, Role
from app.security import hash_password

logger = logging.getLogger("dayleaf.auto_seed")


def restore_seed_db_if_needed():
    """Copy pre-seeded database if campusflow-local.db is missing or empty."""
    local_candidates = [Path("campusflow-local.db"), Path("apps/api/campusflow-local.db")]
    seed_candidates = [Path("campusflow-seed.db"), Path("apps/api/campusflow-seed.db")]

    seed_file = next((p for p in seed_candidates if p.exists()), None)
    if not seed_file:
        return

    for target in local_candidates:
        if not target.exists() or target.stat().st_size < 10000:
            try:
                shutil.copy(seed_file, target)
                logger.info(f"Restored {target} from {seed_file}")
            except Exception as e:
                logger.warning(f"Could not copy {seed_file} to {target}: {e}")


def ensure_users_exist():
    """Ensure Sushant Prakash and Dayleaf admin accounts exist with Dayleaf@2026."""
    db = SessionLocal()
    try:
        inst = db.query(Institution).first()
        if not inst:
            inst = Institution(name="Dayleaf University")
            db.add(inst)
            db.flush()

        default_pwd = hash_password("Dayleaf@2026")
        admin_emails = [
            ("sushantprakash2003@gmail.com", "Sushant Prakash", Role.college_admin),
            ("juug25btech16379@jainuniversity.ac.in", "Admin (Jain)", Role.college_admin),
        ]

        for email, name, role in admin_emails:
            u = db.query(User).filter_by(email=email).first()
            if not u:
                u = User(
                    institution_id=inst.id,
                    email=email,
                    full_name=name,
                    password_hash=default_pwd,
                    role=role,
                    is_active=True,
                    email_verified=True,
                )
                db.add(u)
            else:
                u.password_hash = default_pwd
                u.is_active = True
                u.email_verified = True
                if not u.institution_id:
                    u.institution_id = inst.id

        db.commit()
        logger.info("Dayleaf default users verified.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error ensuring users exist: {e}")
    finally:
        db.close()
