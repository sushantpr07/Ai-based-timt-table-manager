import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import EmailVerificationToken, PasswordResetToken, User


def mail_password_link(address: str, token: str):
    message = EmailMessage()
    message["Subject"] = "Set or reset your CampusFlow password"
    message["From"] = settings.mail_from
    message["To"] = address
    message.set_content(f"Use this link within 30 minutes to set or reset your password: {settings.web_origin}/reset-password?token={token}\nIf you did not request this, ignore this email.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password or "")
        smtp.send_message(message)


def queue_password_link(db: Session, background_tasks: BackgroundTasks, user: User):
    if not (settings.smtp_host and settings.mail_from):
        raise HTTPException(status_code=503, detail="Email delivery is not configured. Set SMTP_HOST and MAIL_FROM before inviting users.")
    now = datetime.now(timezone.utc)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id,
                                        PasswordResetToken.used_at.is_(None)).update(
        {PasswordResetToken.used_at: now}, synchronize_session=False)
    token = secrets.token_urlsafe(36)
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                              expires_at=now + timedelta(minutes=30)))
    background_tasks.add_task(mail_password_link, user.email, token)


def mail_verification_link(address: str, token: str):
    message = EmailMessage()
    message["Subject"] = "Verify your CampusFlow email"
    message["From"] = settings.mail_from
    message["To"] = address
    message.set_content(f"Verify your email within 60 minutes: {settings.web_origin}/verify-email?token={token}\nIf you did not create this account, ignore this email.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password or "")
        smtp.send_message(message)


def queue_email_verification(db: Session, background_tasks: BackgroundTasks, user: User):
    if not (settings.smtp_host and settings.mail_from):
        raise HTTPException(status_code=503, detail="Email verification is enabled, but email delivery is not configured.")
    now = datetime.now(timezone.utc)
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id,
                                            EmailVerificationToken.used_at.is_(None)).update(
        {EmailVerificationToken.used_at: now}, synchronize_session=False)
    token = secrets.token_urlsafe(36)
    db.add(EmailVerificationToken(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                  expires_at=now + timedelta(minutes=60)))
    background_tasks.add_task(mail_verification_link, user.email, token)
