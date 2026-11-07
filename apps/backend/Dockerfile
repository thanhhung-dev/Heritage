FROM python:3.12.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY apps/backend/requirements.docker.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.9.1+cpu \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

FROM python:3.12.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    INFERENCE_BACKEND=llama_server \
    LLAMA_SERVER_URL=http://llm:8080

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY apps/__init__.py /app/apps/__init__.py
COPY apps/backend /app/apps/backend
COPY corpus /app/corpus
COPY pipelines/graph /app/pipelines/graph

EXPOSE 8000

CMD ["uvicorn", "apps.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
