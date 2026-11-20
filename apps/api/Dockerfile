FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN groupadd --system --gid 10001 campusflow && useradd --system --uid 10001 --gid campusflow --create-home campusflow
COPY --chown=campusflow:campusflow app ./app
COPY --chown=campusflow:campusflow migrations ./migrations
COPY --chown=campusflow:campusflow alembic.ini ./alembic.ini
USER 10001:10001
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log --log-level ${LOG_LEVEL:-info}"]
