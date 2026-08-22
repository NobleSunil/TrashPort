# TrashPort - Project Summary & Development Roadmap

## 📌 Executive Overview
**TrashPort** is an end-to-end web-based smart waste collection and recycling management platform built with **Django**, **Django REST Framework**, and modern web technologies. The platform connects **Citizens**, **Collectors**, and **Municipal Administrators** within a single unified web application.

---

## 🏗️ Architecture & Technology Stack
* **Backend Framework:** Django 5+ (Python 3.13 / 3.14 via `uv`)
* **API Engine:** Django REST Framework (DRF) with OpenAPI/Swagger schemas (`drf-spectacular`)
* **Database:** PostgreSQL (Production / Docker) & SQLite (Local rapid development)
* **Frontend Web Stack:** Django Templates, Vanilla CSS, Bootstrap 5 UI components, Chart.js for data visualization
* **DevOps & Infrastructure:** Docker & Docker Compose (`docker-compose.local.yml`, `docker-compose.production.yml`), Traefik, Redis, Nginx, GitHub Actions CI

---

## ✅ 1. Completed Features

### 👤 Citizen Web Portal (`trashport/citizens/`)
* **Citizen Dashboard:** Central hub displaying active pickups, historical records, wallet reward balance, active subscription status, and logged complaints.
* **Pickup Request Booking:** Web form allowing citizens to select saved addresses, choose waste categories, provide weight/quantity estimates, and pick scheduling dates.
* **Subscription Management:** View available tiers, choose subscription packages that waive per-pickup charges, and manage active plans.
* **Address Book CRUD:** Complete web interface to add, update, set default, or delete residential/commercial pickup addresses.
* **Payment Flow Simulation:** Built-in web payment simulator for handling fee calculations on billable pickup requests.
* **Feedback & Ratings:** 1 to 5-star rating system with written feedback submissions for completed collections.
* **Complaint Ticketing:** Issue submission form linked directly to specific pickup requests with real-time status tracking.

---

### 🚚 Collector Web Portal (`trashport/collectors/`)
* **Collector Dashboard:** Real-time view of active assigned collections, historical job logs, and unassigned system-wide pickups.
* **Open Job Claiming:** Collectors can browse open/pending requests in the pool and claim them.
* **Pickup Lifecycle Management:** Step-by-step status transitions (`ASSIGNED` ➔ `IN_TRANSIT` ➔ `COMPLETED`).
* **Pickup Details:** Direct access to citizen address, notes, contact details, and waste specifications.

---

### 🛡️ Administrator Web Portal (`trashport/admins/`)
* **Analytics & Metrics Dashboard:**
  * Real-time metrics: Total pickups, completed/pending requests, gross revenue, total recycled kg, and completion rates.
  * Interactive Chart.js charts: Waste category distributions, daily pickup trends, and status breakdowns.
* **Pickup Dispatch & Reassignment:** Tools to manually assign or reassign collectors to pickup requests.
* **Waste Category & Pricing Management:** Web interfaces to create and modify categories, fee-per-kg rates, and reward points per kg.
* **Subscription Tier Administration:** Create and configure recurring subscription tiers and pricing.
* **Collector User Provisioning:** Dedicated form to create and register authorized collector accounts.
* **Wallet Points Adjustments:** Administrative tooling to credit, debit, or audit citizen wallet points.
* **Complaint Resolution Center:** Ticket management system to review, respond to, and mark complaints as resolved.

---

### ⚙️ Core Domain & Engine (`waste_management/` & `users/`)
* **Multi-Role Custom User Model:** Custom `User` model (`CITIZEN`, `COLLECTOR`, `ADMIN`) with email-based authentication and wallet balances.
* **Automated Pricing & Rewards Logic:**
  * Auto-calculates fees based on category rate × estimated weight.
  * Fee waiver when the citizen holds an active subscription.
  * Automatic credit of reward points to citizen wallets upon collection completion for valuable recyclables (e.g. scrap metal, copper, aluminum).
* **Complete REST API:** DRF endpoints for all models under `/api/` with interactive OpenAPI documentation at `/api/docs/`.

---

## 🚀 2. Future Roadmap & What To Build Next (Web Platform)

### 💳 1. Real Payment Gateway Integration
* Replace mock payments with a production gateway (**Razorpay**, **Stripe**, or **PayPal**) for web checkouts.
* Implement automated recurring billing and webhooks for subscription renewals.

### 🗺️ 2. Interactive Web Maps & Route Visualization
* Integrate **Leaflet.js** or **Mapbox** into the web portals:
  * **Citizens:** View real-time collector transit status on a live interactive web map.
  * **Collectors:** View daily assigned stops on an interactive web map with route planning.

### 🔔 3. Real-Time Web Notifications & Email/SMS Alerts
* Configure **Celery + Redis** for asynchronous task execution.
* Send automated email/SMS alerts (via SendGrid / Twilio) on pickup confirmations, driver transit updates, and completions.
* Implement browser Web Push notifications or WebSocket updates via Django Channels.

### 🎁 4. Citizen Rewards & Eco-Marketplace Web Store
* Build an e-commerce style **Rewards Store** page where citizens can redeem accumulated `wallet_points` for:
  * Utility bill / municipal waste charge discounts.
  * Partner discount coupons and eco-friendly merchandise.
  * Free future pickup credits.

### 📷 5. Browser-Based QR Code Verification
* Generate a unique QR code on the citizen's web ticket.
* Enable collectors to use a **Webcam/Mobile-Browser HTML5 QR Scanner** to scan citizen tickets at the doorstep for fraud-free job verification.

### 🤖 6. Automated Proximity-Based Smart Dispatch
* Implement a backend scheduling algorithm to automatically assign pending requests to the closest available collector based on postal codes, ward boundaries, or geo-coordinates.

### 📊 7. Advanced Reporting & Data Export
* Add CSV, Excel, and PDF export functionality for administrators (e.g., monthly collection summaries, revenue reports, and municipal compliance audits).
