# TrashPort REST API Reference

Swagger UI is available interactively at `/api/docs/` and OpenAPI Schema at `/api/schema/`.

## Authentication Endpoints
- `POST /api/firebase/verify/`: Verify Firebase ID token and log in / create user.
- `GET /api/firebase/me/`: Retrieve authenticated user identity and role.

## Payments & Wallet
- `POST /api/payments/intent/create/`: Create a Stripe payment intent.
- `GET /api/payments/history/`: Retrieve payment transactions.
- `GET /api/payments/wallet/history/`: Retrieve points adjustment history.
- `POST /api/payments/webhook/stripe/`: Stripe asynchronous webhook listener.

## Maps & Geolocation
- `GET /api/maps/zones/`: List active service zones.
- `GET /api/maps/locations/`: List collector GPS coordinates.
- `POST /api/maps/locations/update/`: Update current collector location.

## Automated Dispatch
- `GET /api/dispatch/batches/`: Retrieve dispatch batch audit logs.
- `POST /api/dispatch/trigger/`: Trigger automated assignment algorithm.

## AI Assistant & Chatbot
- `POST /api/chatbot/message/`: Process interactive conversation with TrashPort AI.
