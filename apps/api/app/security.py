from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.models import User

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user.id), "role": user.role.value, "institution_id": str(user.institution_id) if user.institution_id else None,
        "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes),
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
    }, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    previous_secrets = [secret.strip() for secret in settings.jwt_previous_secrets.split(",") if secret.strip()]
    verification_secrets = list(dict.fromkeys([settings.jwt_secret, *previous_secrets]))
    last_error = None
    for secret in verification_secrets:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"], issuer=settings.jwt_issuer,
                              audience=settings.jwt_audience)
        except jwt.InvalidTokenError as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise jwt.InvalidTokenError("No JWT verification keys are configured.")
