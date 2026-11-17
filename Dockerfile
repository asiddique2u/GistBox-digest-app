FROM python:3.13-slim-bookworm

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.3

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend ./backend

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sh", "-c", "uvicorn --app-dir backend main:app --host 0.0.0.0 --port ${PORT:-10000}"]
