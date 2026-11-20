from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.security import create_access_token, decode_access_token
from app.core.config import Settings


def test_settings_reject_short_session_signing_keys():
    with pytest.raises(ValidationError, match="JWT_SECRET must contain at least 32 bytes"):
        Settings(jwt_secret="too-short")
    with pytest.raises(ValidationError, match="Every JWT_PREVIOUS_SECRETS key must contain at least 32 bytes"):
        Settings(jwt_previous_secrets="short-previous-key")


def test_production_settings_reject_placeholder_session_signing_keys():
    with pytest.raises(ValidationError, match="unique random value"):
        Settings(jwt_secret="replace-with-a-strong-random-secret-value-000000",
                 web_origin="https://campus.example.edu", api_origin="https://api.example.edu")


def test_tokens_signed_with_previous_key_remain_valid_during_rotation(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "current-test-signing-key-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "jwt_previous_secrets", " previous-test-signing-key-with-32-bytes , retired-test-signing-key-with-32-bytes ")
    claims = {
        "sub": str(uuid4()), "role": "college_admin", "institution_id": None,
        "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
    }
    old_token = jwt.encode(claims, "previous-test-signing-key-with-32-bytes", algorithm="HS256")

    assert decode_access_token(old_token)["sub"] == claims["sub"]


def test_new_tokens_use_only_the_current_signing_key(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "current-test-signing-key-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "jwt_previous_secrets", "previous-test-signing-key-with-32-bytes")
    user = SimpleNamespace(id=uuid4(), role=SimpleNamespace(value="college_admin"), institution_id=None)

    token = create_access_token(user)
    assert decode_access_token(token)["sub"] == str(user.id)
    with pytest.raises(jwt.InvalidTokenError):
        jwt.decode(token, "previous-test-signing-key-with-32-bytes", algorithms=["HS256"],
                   issuer=settings.jwt_issuer, audience=settings.jwt_audience)


def test_tokens_signed_by_removed_key_are_rejected(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "current-test-signing-key-with-at-least-32-bytes")
    monkeypatch.setattr(settings, "jwt_previous_secrets", "")
    claims = {
        "sub": str(uuid4()), "role": "college_admin", "institution_id": None,
        "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
    }
    retired_token = jwt.encode(claims, "retired-test-signing-key-with-32-bytes", algorithm="HS256")

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(retired_token)
