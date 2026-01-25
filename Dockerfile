FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    sqlalchemy \
    asyncpg \
    alembic \
    pydantic \
    pydantic-settings \
    httpx \
    python-json-logger

EXPOSE 8000
