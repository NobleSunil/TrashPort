# Multi-stage optimized Dockerfile for TrashPort

# Stage 1: Build virtual environment with uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS python-build-stage

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app

# Build-time dependencies for native extensions
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install production dependencies only (no dev packages)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Stage 2: Lean runtime stage
FROM python:3.13-slim-bookworm AS python-run-stage

ARG APP_HOME=/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

WORKDIR ${APP_HOME}

# Create non-root django user
RUN addgroup --system django \
    && adduser --system --ingroup django --home /home/django django

# Runtime dependencies only
RUN apt-get update && apt-get install --no-install-recommends -y \
    gettext \
    wait-for-it \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /root/.cache

# Copy prebuilt virtual environment
COPY --from=python-build-stage /venv /venv

# Copy entrypoint and start scripts
COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

COPY ./compose/production/django/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Copy application source code
COPY --chown=django:django . ${APP_HOME}

# Ensure media directory exists with right permissions
RUN mkdir -p ${APP_HOME}/trashport/media && chown -R django:django ${APP_HOME}

USER django

# Compile locale translations
RUN DATABASE_URL="postgres://dummy" \
    DJANGO_SETTINGS_MODULE="config.settings.test" \
    python manage.py compilemessages

EXPOSE 5000

ENTRYPOINT ["/entrypoint"]
CMD ["/start"]
