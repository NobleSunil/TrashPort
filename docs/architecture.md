# TrashPort System Architecture

## Overview
TrashPort is an enterprise-grade, intelligent smart waste collection and logistics orchestration platform built with **Django 6**, **Django Rest Framework**, **Firebase Authentication**, **Tailwind CSS**, and **PostgreSQL / SQLite**.

```
TrashPort/
├── config/              # Central settings, routing, WSGI/ASGI, Celery
├── trashport/           # Domain-driven apps and presentation layer
│   ├── users/           # Custom User model & profile management
│   ├── firebase/        # Firebase token authentication & Admin SDK bridge
│   ├── citizens/        # Citizen pickup bookings, addresses, complaints
│   ├── collectors/      # Collector dashboards, job executions & live GPS
│   ├── admins/          # Master configurations, tiers, reports, audit
│   ├── payments/        # Stripe payments, subscription handling, wallet ledger
│   ├── maps/            # Geo service, zones, live location streaming
│   ├── notifications/   # Email notifications & in-app alerts
│   ├── dispatch/        # Automated assignment engines (Nearest, Least-Busy, Zone)
│   ├── chatbot/         # AI assistant, intent classification, action dispatching
│   ├── static/          # Modular CSS, JS widgets, and visual assets
│   └── templates/       # Component partials and domain templates
├── waste_management/    # Core waste models & shared business logic
├── scripts/             # Data seeding and operational utilities
└── docs/                # Architecture, API, and deployment documentation
```

## Security & Auth
- Multi-channel authentication supporting Firebase Google Auth, Firebase Email/Password, and native Django password credentials.
- Role-based permissions (`CITIZEN`, `COLLECTOR`, `ADMIN`).
