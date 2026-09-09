FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/venv \
    PATH="/venv/bin:$PATH"

WORKDIR /app

# Install system dependencies required for psycopg and Django
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    gettext \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (leveraging Docker layer cache)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy project source code
COPY . .

# Finalize uv sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

EXPOSE 8001

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8001"]
