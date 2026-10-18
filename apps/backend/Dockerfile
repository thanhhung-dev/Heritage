FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INFERENCE_BACKEND=llama_server \
    LLAMA_SERVER_URL=http://llm:8080

WORKDIR /app

COPY apps/backend/requirements.docker.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY alembic.ini /app/alembic.ini
COPY apps/__init__.py /app/apps/__init__.py
COPY apps/backend /app/apps/backend
COPY corpus /app/corpus

EXPOSE 8000

CMD ["uvicorn", "apps.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
