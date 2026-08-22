.PHONY: help install run migrate makemigrations test check seed lint format

help:
	@echo "TrashPort Makefile commands:"
	@echo "  make install         - Sync dependencies using uv"
	@echo "  make run             - Run local Django development server"
	@echo "  make migrate         - Apply database migrations"
	@echo "  make makemigrations  - Generate new database migrations"
	@echo "  make test            - Run pytest test suite"
	@echo "  make check           - Run Django system check"
	@echo "  make seed            - Seed demo data and zones"
	@echo "  make lint            - Run ruff linter"
	@echo "  make format          - Format code with ruff"

install:
	uv sync

run:
	uv run python manage.py runserver 0.0.0.0:8000

migrate:
	uv run python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

test:
	uv run pytest

check:
	uv run python manage.py check

seed:
	uv run python scripts/seed_data.py
	uv run python scripts/seed_zones.py

lint:
	uv run ruff check .

format:
	uv run ruff format .
