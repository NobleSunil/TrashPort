# TRASHPORT: SMART MUNICIPAL WASTE MANAGEMENT & LOGISTICS PLATFORM
## Complete Academic Project Report

---

# DATABASE STRUCTURE

### Database Entity Specification Table

The TrashPort relational database schema is normalized to Third Normal Form (3NF) to eliminate data redundancy and preserve referential integrity. Core user authentication is isolated from role-specific profile attributes, while operational transactions maintain strict foreign key relationships. The collection pricing model operates on a direct Pay-Per-Collection basis.

| Table Name | Field Name | Data Type | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- |
| **users_user** | `id` | BigAutoField | Primary Key | Unique user record identifier |
| | `email` | EmailField | Unique, Not Null | Primary user authentication identity |
| | `name` | CharField(255) | Blank | Full legal / display name |
| | `password` | CharField(128) | Not Null | Hashed password credential (Argon2 / PBKDF2) |
| | `role` | CharField(20) | Choices: `CITIZEN`, `COLLECTOR`, `ADMIN` | User access control persona |
| | `verification_status` | CharField(20) | Choices: `PENDING`, `APPROVED`, `REJECTED` | KYC status of collector registration |
| | `firebase_uid` | CharField(255) | Unique, Nullable | Firebase JWT user identifier mapping |
| | `phone_number` | CharField(20) | Nullable | Primary contact telephone number |
| | `is_active` | BooleanField | Default: `True` | Account operational status |
| | `is_staff` | BooleanField | Default: `False` | Django admin panel access authorization |
| | `is_superuser` | BooleanField | Default: `False` | Administrative superuser access |
| | `date_joined` | DateTimeField | Auto Now Add | Account registration timestamp |
| | `last_login` | DateTimeField | Nullable | Most recent successful login timestamp |
| **users_citizenprofile** | `id` | BigAutoField | Primary Key | Unique citizen profile record identifier |
| | `user_id` | OneToOneField (User) | `on_delete=CASCADE`, Unique | 3NF linked user reference |
| | `wallet_points` | IntegerField | Default: `0` | Recycled metal rewards earned by citizen |
| **users_collectorprofile** | `id` | BigAutoField | Primary Key | Unique collector profile record identifier |
| | `user_id` | OneToOneField (User) | `on_delete=CASCADE`, Unique | 3NF linked user reference |
| | `wallet_balance` | DecimalField(10,2) | Default: `0.00` | Collector cash earnings balance (Rs.) |
| | `vehicle_number` | CharField(50) | Nullable | Waste collection vehicle registration plate |
| | `license_number` | CharField(50) | Nullable | Driving/commercial collector license ID |
| **waste_management_address** | `id` | BigAutoField | Primary Key | Unique address record identifier |
| | `user_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Owning citizen reference |
| | `address_line1` | CharField(255) | Not Null | Street address / house / building number |
| | `address_line2` | CharField(255) | Nullable | Apartment, suite, or landmark details |
| | `city` | CharField(100) | Not Null | Municipal city name |
| | `state` | CharField(100) | Not Null | Administrative state jurisdiction |
| | `postal_code` | CharField(20) | Not Null | Postal PIN / ZIP code |
| | `latitude` | DecimalField(9,6) | Nullable | Geospatial latitude coordinate |
| | `longitude` | DecimalField(9,6) | Nullable | Geospatial longitude coordinate |
| | `is_default` | BooleanField | Default: `False` | Primary collection location flag |
| | `is_hidden` | BooleanField | Default: `False` | Soft-delete flag (hidden from UI, preserved in DB) |
| | `created_at` | DateTimeField | Auto Now Add | Address creation timestamp |
| | `updated_at` | DateTimeField | Auto Now | Last address update timestamp |
| **waste_management_wastecategory** | `id` | BigAutoField | Primary Key | Unique category identifier |
| | `name` | CharField(100) | Unique, Not Null | Waste designation (Plastic, Metal, Organic, E-Waste) |
| | `description` | TextField | Nullable | Disposal guidelines and category details |
| | `fee_per_kg` | DecimalField(6,2) | Default: `0.00` | Standard collection fee per kg (Rs.) |
| | `points_per_kg` | IntegerField | Default: `0` | Reward points credited per kg recycled |
| | `max_weight_kg` | DecimalField(6,2) | Default: `100.00`, Min: `0.01` | Maximum allowed weight per single booking |
| | `created_at` | DateTimeField | Auto Now Add | Category creation timestamp |
| | `updated_at` | DateTimeField | Auto Now | Category modification timestamp |
| **waste_management_collectorpayoutsetting** | `id` | BigAutoField | Primary Key | Singleton configuration ID |
| | `base_min_payout` | DecimalField(8,2) | Default: `25.00`, Min: `0.00` | Guaranteed base minimum driver payout (Rs.) |
| | `rate_per_km` | DecimalField(6,2) | Default: `2.00`, Min: `0.00` | Rate paid per transit kilometer (Rs./km) |
| | `extra_weight_commission_percent` | DecimalField(5,2) | Default: `20.00`, Range: 0-100% | Driver commission on excess weight penalty fees |
| | `updated_at` | DateTimeField | Auto Now | Last configuration update timestamp |
| **waste_management_pickuprequest** | `id` | BigAutoField | Primary Key | Global database sequential ID |
| | `user_pickup_number` | PositiveIntegerField | Nullable | Per-citizen sequential counter starting at #1 |
| | `citizen_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Requesting citizen reference |
| | `collector_id` | ForeignKey (User) | `on_delete=SET_NULL`, Nullable | Assigned collection operative reference |
| | `address_id` | ForeignKey (Address) | `on_delete=SET_NULL`, Nullable | Scheduled collection location |
| | `category_id` | ForeignKey (WasteCategory) | `on_delete=PROTECT`, Not Null | Waste category reference |
| | `latitude` | DecimalField(9,6) | Nullable | Pinpointed collection latitude |
| | `longitude` | DecimalField(9,6) | Nullable | Pinpointed collection longitude |
| | `weight_kg` | DecimalField(6,2) | Default: `1.00`, Min: `0.01` | Estimated waste weight declared by citizen |
| | `quantity_estimate` | CharField(100) | Nullable | Visual volume notes (e.g. "3 boxes") |
| | `actual_weight_kg` | DecimalField(6,2) | Nullable | Verified on-site scale weight by collector |
| | `fee` | DecimalField(10,2) | Default: `0.00` | Total collection charge calculated |
| | `extra_fee` | DecimalField(10,2) | Default: `0.00` | 2x rate surcharge on excess weight |
| | `distance_km` | DecimalField(6,2) | Default: `5.00` | Collection route distance in km |
| | `collector_earnings` | DecimalField(10,2) | Default: `0.00` | Driver payout: Base + Dist*Rate + Excess Comm |
| | `is_weight_verified` | BooleanField | Default: `False` | True once collector measures scale weight |
| | `points_earned` | IntegerField | Default: `0` | Recycled points calculated |
| | `is_paid` | BooleanField | Default: `False` | Settlement completion status |
| | `schedule_date` | DateTimeField | Not Null | Date/time of pickup (>= now + 3h) |
| | `status` | CharField(20) | Choices: `PENDING`, `AWAITING_PAYMENT`, `ASSIGNED`, `IN_TRANSIT`, `COMPLETED`, `CANCELLED` | Lifecycle state of pickup workflow |
| | `feedback_rating` | IntegerField | Min: `1`, Max: `5`, Nullable | Post-collection service rating |
| | `feedback_comments` | TextField | Nullable | Post-collection citizen commentary |
| | `cancellation_reason` | TextField | Nullable | Reason provided upon cancellation |
| | `cancelled_at` | DateTimeField | Nullable | Timestamp of cancellation |
| | `created_at` | DateTimeField | Auto Now Add | Booking creation timestamp |
| | `updated_at` | DateTimeField | Auto Now | Booking status update timestamp |
| **waste_management_complaint** | `id` | BigAutoField | Primary Key | Unique complaint identifier |
| | `citizen_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Complainant citizen reference |
| | `pickup_request_id` | ForeignKey (PickupRequest) | `on_delete=SET_NULL`, Nullable | Linked pickup job reference |
| | `title` | CharField(200) | Not Null | Grievance subject line |
| | `description` | TextField | Not Null | Detailed issue description |
| | `status` | CharField(20) | Choices: `PENDING`, `RESOLVED` | Grievance resolution status |
| | `created_at` | DateTimeField | Auto Now Add | Submission timestamp |
| | `updated_at` | DateTimeField | Auto Now | Resolution timestamp |
| **waste_management_anonymousfeedback** | `id` | BigAutoField | Primary Key | Unique feedback identifier |
| | `category` | CharField(50) | Choices: `SUGGESTION`, `COLLECTION_ISSUE`, `WEBSITE_BUG`, `GENERAL` | Categorization of user feedback |
| | `subject` | CharField(200) | Nullable | Feedback topic line |
| | `message` | TextField | Not Null | Anonymous feedback body sent to admin |
| | `is_reviewed` | BooleanField | Default: `False` | Admin review status flag |
| | `admin_notes` | TextField | Nullable | Internal administrative notes |
| | `created_at` | DateTimeField | Auto Now Add | Submission timestamp |
| **payments_paymenttransaction** | `id` | BigAutoField | Primary Key | Unique transaction record ID |
| | `user_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Paying user reference |
| | `amount` | DecimalField(10,2) | Not Null | Monetary charge amount |
| | `currency` | CharField(10) | Default: `USD` / `INR` | Currency code |
| | `payment_method` | CharField(20) | Choices: `STRIPE`, `WALLET`, `COD` | Selected payment settlement method |
| | `status` | CharField(20) | Choices: `PENDING`, `COMPLETED`, `FAILED`, `REFUNDED` | Gateway processing status |
| | `transaction_id` | CharField(255) | Unique, Nullable | Gateway charge identifier |
| | `description` | CharField(255) | Blank | Transaction purpose description |
| | `created_at` | DateTimeField | Auto Now Add | Transaction creation timestamp |
| | `updated_at` | DateTimeField | Auto Now | Transaction status update timestamp |
| **payments_wallethistory** | `id` | BigAutoField | Primary Key | Unique ledger sequence ID |
| | `user_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Account owner reference |
| | `points_delta` | IntegerField | Not Null | Points added (+) or deducted (-) |
| | `reason` | CharField(255) | Not Null | Justification for point adjustment |
| | `created_at` | DateTimeField | Auto Now Add | Ledger transaction timestamp |
| **payments_upipayoutrequest** | `id` | BigAutoField | Primary Key | Unique payout record ID |
| | `collector_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Requesting collector reference |
| | `amount` | DecimalField(10,2) | Not Null | Cash earnings amount withdrawn |
| | `upi_id` | CharField(100) | Not Null | Destination UPI VPA address |
| | `transaction_ref` | CharField(100) | Unique, Nullable | Bank transfer transaction reference |
| | `status` | CharField(20) | Choices: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` | Payout settlement status |
| | `note` | CharField(255) | Default: "Redeemed to UPI" | Payout audit memo |
| | `created_at` | DateTimeField | Auto Now Add | Withdrawal request timestamp |
| | `updated_at` | DateTimeField | Auto Now | Transfer completion timestamp |
| **notifications_notification** | `id` | BigAutoField | Primary Key | Unique notification alert ID |
| | `user_id` | ForeignKey (User) | `on_delete=CASCADE`, Not Null | Recipient user reference |
| | `title` | CharField(255) | Not Null | Alert headline |
| | `message` | TextField | Not Null | Full notification body |
| | `notification_type` | CharField(20) | Choices: `PICKUP`, `PAYMENT`, `COMPLAINT`, `SYSTEM` | Alert categorization |
| | `is_read` | BooleanField | Default: `False` | Read acknowledgement flag |
| | `created_at` | DateTimeField | Auto Now Add | Notification dispatch timestamp |
| **maps_servicezone** | `id` | BigAutoField | Primary Key | Unique service zone identifier |
| | `name` | CharField(100) | Unique, Not Null | Sector / Zone geographical name |
| | `code` | CharField(20) | Unique, Not Null | Zone administrative shortcode |
| | `center_latitude` | DecimalField(9,6) | Default: `9.9312` | Geometric center latitude |
| | `center_longitude` | DecimalField(9,6) | Default: `76.2673` | Geometric center longitude |
| | `radius_km` | DecimalField(5,2) | Default: `25.00` | Operational radius boundary |
| | `is_active` | BooleanField | Default: `True` | Service availability status |
| | `created_at` | DateTimeField | Auto Now Add | Zone creation timestamp |
| **maps_collectorlocation** | `id` | BigAutoField | Primary Key | Unique location record ID |
| | `collector_id` | OneToOneField (User)| `on_delete=CASCADE`, Not Null | Linked collector reference |
| | `latitude` | DecimalField(9,6) | Not Null | Real-time GPS latitude |
| | `longitude` | DecimalField(9,6) | Not Null | Real-time GPS longitude |
| | `speed` | FloatField | Default: `0.0` | Travel speed (km/h) |
| | `heading` | FloatField | Default: `0.0` | Compass orientation (degrees) |
| | `updated_at` | DateTimeField | Auto Now | Last GPS broadcast timestamp |
| **dispatch_dispatchbatch** | `id` | BigAutoField | Primary Key | Unique dispatch batch ID |
| | `algorithm_used` | CharField(50) | Choices: `NEAREST`, `LEAST_BUSY`, `ZONE_BASED` | Algorithmic assignment rule |
| | `assigned_count` | IntegerField | Default: `0` | Number of pickups successfully allocated |
| | `unassigned_count`| IntegerField | Default: `0` | Number of unallocated pickups remaining |
| | `executed_by_id` | ForeignKey (User) | `on_delete=SET_NULL`, Nullable | Administrator trigger reference |
| | `details` | JSONField | Default: `dict` | JSON mapping of assigned pickup IDs |
| | `created_at` | DateTimeField | Auto Now Add | Execution timestamp |
| **chatbot_chatsession** | `id` | BigAutoField | Primary Key | Unique conversation session ID |
| | `user_id` | ForeignKey (User) | `on_delete=CASCADE`, Nullable | Authenticated user reference |
| | `session_key` | CharField(100) | Unique, Not Null | Ephemeral/browser session identifier |
| | `created_at` | DateTimeField | Auto Now Add | Chat initiation timestamp |
| | `updated_at` | DateTimeField | Auto Now | Last conversation activity timestamp |
| **chatbot_chatmessage** | `id` | BigAutoField | Primary Key | Unique message sequence ID |
| | `session_id` | ForeignKey (ChatSession)| `on_delete=CASCADE`, Not Null | Parent conversation session |
| | `sender` | CharField(10) | Choices: `USER`, `BOT`, `SYSTEM` | Originating message entity |
| | `text` | TextField | Not Null | Conversational message content |
| | `intent` | CharField(100) | Blank | Classified NLP intent |
| | `action_data` | JSONField | Default: `dict` | Structured slot-filling parameters |
| | `created_at` | DateTimeField | Auto Now Add | Message transmission timestamp |
| **chatbot_faq** | `id` | BigAutoField | Primary Key | Unique FAQ record ID |
| | `question` | CharField(500) | Not Null | User inquiry string |
| | `answer` | TextField | Not Null | Static answer response |
| | `category` | CharField(20) | Choices: `pickup`, `payment`, `account`, `general` | Inquiry categorization |
| | `is_active` | BooleanField | Default: `True` | Display visibility flag |
| | `created_at` | DateTimeField | Auto Now Add | Record creation timestamp |
| | `updated_at` | DateTimeField | Auto Now | Record modification timestamp |
| **chatbot_chatfeedback** | `id` | BigAutoField | Primary Key | Unique feedback record ID |
| | `user_id` | ForeignKey (User) | `on_delete=SET_NULL`, Nullable | Providing user reference |
| | `session_id` | ForeignKey (ChatSession)| `on_delete=SET_NULL`, Nullable | Linked chat session reference |
| | `user_message` | TextField | Blank | User prompt being evaluated |
| | `bot_message` | TextField | Blank | AI assistant response evaluated |
| | `rating` | CharField(20) | Choices: `thumbs_up`, `thumbs_down` | Evaluative binary rating |
| | `session_key` | CharField(100) | Blank | Session tracking string |
| | `created_at` | DateTimeField | Auto Now Add | Rating submission timestamp |
| **chatbot_chatlog** | `id` | BigAutoField | Primary Key | Unique LLM telemetry record ID |
| | `user_id` | ForeignKey (User) | `on_delete=SET_NULL`, Nullable | Prompting user reference |
| | `user_message` | TextField | Not Null | Original raw user input |
| | `raw_llm_output` | TextField | Not Null | Unparsed Groq LLM completion |
| | `parsed_output` | JSONField | Default: `dict` | Extracted JSON payload |
| | `was_valid` | BooleanField | Default: `True` | Format and syntax validation flag |
| | `action_taken` | CharField(100) | Blank | System action executed |
| | `error_message` | TextField | Blank | Parser or execution exception details |
| | `created_at` | DateTimeField | Auto Now Add | Log entry creation timestamp |

---

### Database Relationships (ER Diagram Notation)

```
[User] 1 -------- 0..1 [CitizenProfile]        : "has 3NF attributes"
[User] 1 -------- 0..1 [CollectorProfile]      : "has 3NF attributes"
[User] 1 -------- 0..* [Address]               : "registers / owns"
[User] 1 -------- 0..* [PickupRequest]         : "books as Citizen"
[User] 1 -------- 0..* [PickupRequest]         : "assigned as Collector"
[User] 1 -------- 0..* [Complaint]             : "files"
[User] 1 -------- 0..* [PaymentTransaction]    : "transacts"
[User] 1 -------- 0..* [WalletHistory]         : "owns ledger points"
[User] 1 -------- 0..* [UPIPayoutRequest]      : "withdraws earnings"
[User] 1 -------- 0..* [Notification]          : "receives"
[User] 1 -------- 0..1 [CollectorLocation]     : "broadcasts GPS"
[User] 1 -------- 0..* [DispatchBatch]         : "executes as Admin"
[User] 1 -------- 0..* [ChatSession]           : "initiates"

[Address]          1 -------- 0..* [PickupRequest]     : "serves as pickup location"
[WasteCategory]    1 -------- 0..* [PickupRequest]     : "classifies waste type"
[PickupRequest]    1 -------- 0..* [Complaint]         : "is disputed by"
[ChatSession]      1 -------- 0..* [ChatMessage]       : "contains dialogue"
[ChatSession]      1 -------- 0..* [ChatFeedback]      : "receives quality ratings"

(Singleton) [CollectorPayoutSetting]                   : "provides dynamic rate parameters"
(Independent) [AnonymousFeedback]                     : "collects unauthenticated feedback"
```

---

# PROJECT STRUCTURE (Reference Directory Map)

```
TrashPort/
├── .devcontainer/                         # Development container specifications for VS Code
│   └── devcontainer.json                  # Remote container definition
├── compose/                               # Container specifications and runtime entrypoints
│   ├── local/django/Dockerfile            # Multi-stage Python 3.13 image with uv cache
│   ├── local/django/start                 # Startup script: migrates DB and runs Daphne server
│   ├── production/django/entrypoint       # Validates PostgreSQL readiness via wait-for-it
│   └── production/postgres/Dockerfile     # PostgreSQL 16 image with backup maintenance scripts
├── config/                                # Root project configuration
│   ├── settings/
│   │   ├── base.py                        # Common settings: apps, auth, database, and logging
│   │   ├── local.py                       # Local settings: debug toolbar, allowed hosts, static files
│   │   ├── production.py                  # Production settings: security headers, WhiteNoise, HTTPS
│   │   └── test.py                        # Fast test settings: MD5 hashing and in-memory caches
│   ├── api_router.py                      # REST API router registering DRF viewsets
│   ├── asgi.py                            # ASGI root routing HTTP to Django and WS to Channels
│   ├── celery_app.py                      # Celery worker application configuration
│   ├── urls.py                            # Master URL dispatcher including web and API routes
│   └── wsgi.py                            # Standard WSGI web server deployment handler
├── docs/                                  # Sphinx technical documentation suite
├── keys/                                  # Credentials folder containing serviceAccountKey templates
├── locale/                                # Internationalization message translation catalogs
├── staticfiles/                           # Consolidated production static assets
├── tests/                                 # Root test scripts and environment parsers
├── trashport/                             # Main application source directory
│   ├── admins/                            # Administrator domain logic, reports, and live map
│   │   ├── forms.py                       # Collector creation, category, and wallet forms
│   │   ├── urls.py                        # Admin routing endpoints
│   │   ├── views.py                       # Live map, dashboard metrics, operations report, CSV exports
│   │   └── templates/admin/               # Administrative HTML layouts and views
│   ├── chatbot/                           # AI conversational agent system
│   │   ├── actions/                       # Slot-filling handlers (schedule, cancel, complaint, etc.)
│   │   ├── consumers.py                   # ASGI WebSocket consumer handling real-time chat
│   │   ├── models.py                      # ChatSession, ChatMessage, FAQ, ChatFeedback, ChatLog
│   │   ├── rate_limiter.py                # Redis-backed sliding window chat rate limiter
│   │   ├── routing.py                     # WebSocket URL routes (ws/chatbot/)
│   │   ├── services/                      # Groq LLM API client integration and prompt wrappers
│   │   ├── system_prompt.py               # Conversational persona guidelines and rules
│   │   └── views.py                       # REST fallback endpoints and user feedback submission
│   ├── citizens/                          # Citizen self-service portal
│   │   ├── forms.py                       # Address book, pickup request, and complaint forms
│   │   ├── urls.py                        # Citizen specific web routes
│   │   ├── views.py                       # Citizen dashboard, pickup wizard, invoices, checkout
│   │   └── templates/citizen/             # Citizen interface templates
│   ├── collectors/                        # Field operative logistics portal
│   │   ├── urls.py                        # Collector operation endpoints
│   │   ├── views.py                       # Proximity feed, OSRM routing, scale verification, UPI
│   │   └── templates/collector/           # Mobile-responsive driver interface templates
│   ├── dispatch/                          # Automated fleet assignment engine
│   │   ├── algorithms/                    # Nearest, Least-Busy, and Zone-Based assignment logic
│   │   ├── models.py                      # DispatchBatch entity
│   │   ├── scheduler.py                   # Batch execution orchestration controller
│   │   ├── serializers.py                 # DRF serializers for dispatch batches
│   │   ├── urls.py                        # Dispatch trigger and inspection endpoints
│   │   └── views.py                       # Dispatch execution REST views
│   ├── firebase/                          # Cross-platform authentication layer
│   │   ├── authentication.py              # Custom DRF authentication backend verifying Firebase JWTs
│   │   ├── urls.py                        # Token verification endpoints
│   │   └── views.py                       # Identity validation views
│   ├── maps/                              # Geospatial routing and live telemetry
│   │   ├── consumers.py                   # WebSocket consumers broadcasting live driver coordinates
│   │   ├── models.py                      # ServiceZone and CollectorLocation models
│   │   ├── routing.py                     # WebSocket routes (ws/maps/tracking/ and admin-live/)
│   │   ├── services.py                    # Haversine distance and Project OSRM road routing engine
│   │   ├── urls.py                        # Map telemetry endpoints
│   │   └── views.py                       # Coordinate update and route computation views
│   ├── notifications/                     # User communication and alert engine
│   │   ├── models.py                      # In-app Notification entity
│   │   ├── services.py                    # Dispatcher creating database alerts and sending emails
│   │   ├── urls.py                        # Notification read state routes
│   │   └── views.py                       # Notification list and read toggle views
│   ├── payments/                          # Monetary settlement and point exchange
│   │   ├── models.py                      # PaymentTransaction, WalletHistory, UPIPayoutRequest
│   │   ├── serializers.py                 # DRF serializers for payment intents
│   │   ├── services.py                    # Card simulation, UPI validator, and Wallet redemption
│   │   ├── urls.py                        # Checkout, wallet history, and webhook endpoints
│   │   ├── views.py                       # Payment transaction listings and intent creation
│   │   └── webhooks.py                    # Stripe webhook receiver
│   ├── static/                            # Static frontend assets
│   │   ├── css/                           # Styling (Tailwind, project styles, chatbot bubbles)
│   │   ├── js/                            # JavaScript (Leaflet map scripts, chat WebSocket, Stripe)
│   │   └── images/                        # Logos, icons, and platform graphics
│   ├── templates/                         # Shared base templates, error pages (403, 404, 500)
│   ├── users/                             # Custom user model and authentication pipelines
│   │   ├── adapters.py                    # Allauth account adapter overrides
│   │   ├── forms.py                       # Signup and profile update forms with name validation
│   │   ├── managers.py                    # Custom UserManager enforcing email as primary key
│   │   ├── models.py                      # User model with Roles, KYC statuses, and wallet fields
│   │   ├── urls.py                        # User profile and login/logout URL endpoints
│   │   ├── validators.py                  # Strict password complexity validators
│   │   ├── views.py                       # Profile update and redirect views
│   │   ├── views_firebase.py              # Firebase and direct password session login views
│   │   └── views_google_oauth.py          # Server-side Google OAuth 2.0 flow
│   └── utils/                             # Shared utility wrappers (Redis connection client)
├── waste_management/                      # Core domain entities and dispatch layer
│   ├── admin.py                           # Django admin model registrations
│   ├── models.py                          # PickupRequest, WasteCategory, Address, CollectorPayoutSetting, AnonymousFeedback
│   ├── serializers.py                     # DRF ModelSerializers for domain entities
│   ├── tests.py                           # Core model validation test suite
│   ├── urls.py                            # Public and unified role dispatch web URLs
│   └── views.py                           # Role-based dashboard/detail routing and DRF Viewsets
├── .env.example                           # Dummy configuration template for developers
├── .gitignore                             # Secret exclusions (.env, credentials.json, serviceAccountKey)
├── docker-compose.local.yml               # Local multi-container Docker specification
├── docker-compose.production.yml          # Production multi-container Docker specification
├── Dockerfile                             # Root container specification
├── manage.py                              # Django CLI management executable
├── pyproject.toml                         # Dependency specification file
└── uv.lock                                # Dependency lockfile
```

---

# ABSTRACT

Municipal solid waste management in urban areas faces critical bottlenecks, including irregular collection cycles, lack of transparency in billing, absence of route optimization, and minimal civic incentives for recycling. TrashPort is an end-to-end, role-based web and logistics platform developed to modernize solid waste collection, scheduling, verification, and recycling incentive distribution. Built on Python 3.13, Django 6.0, Django REST Framework, and Django Channels (ASGI/Daphne) with PostgreSQL and Redis, TrashPort connects three primary actors: Citizens, Collectors, and Administrators. Citizens can book on-demand waste pickups on a transparent Pay-Per-Collection model, choose geospatial pickup locations via interactive Leaflet/OpenStreetMap interfaces, make payments through Card, UPI, or redeemed recycling wallet points, track collectors in real time, and converse with an AI assistant powered by Groq/Llama LLMs over WebSockets. Waste Collectors verify waste weights on-site (triggering a 2× surcharge for excess weight), navigate using turn-by-turn road routes generated via the Project OSRM engine, and earn algorithmic payouts (governed by configurable admin rules: guaranteed base minimum, rate per kilometer, and excess commission) redeemable to bank accounts via UPI. Administrators access real-time dispatch algorithms (Nearest, Least-Busy, and Zone-Based), a live control room map, collector KYC verification workflows, operational reporting, and automated CSV data exports. TrashPort delivers an integrated, automated, and auditable digital infrastructure for modern urban waste ecosystems.

---

# CHAPTER 1: INTRODUCTION

### 1.1 Problem Statement
Urban solid waste management systems frequently suffer from severe operational, economic, and logistical inefficiencies:
1. **Unpredictable Collection and Poor Citizen Visibility**: Citizens lack reliable digital channels to request on-demand waste disposal, verify pickup schedules, or track arriving collection vehicles in real time.
2. **Inaccurate Weight Assessment and Revenue Leakage**: Manual waste collection lacks on-site verification. When citizens discard waste far exceeding initial estimates, municipalities and private operators absorb disposal surcharges without fair compensatory pricing.
3. **Suboptimal Routing and Manual Dispatch**: Waste collection fleets operate on rigid, unoptimized routes rather than dynamic demand-driven clusters, causing excessive fuel consumption, vehicle wear, and delayed pickups.
4. **Absence of Recycling Incentives**: Conventional waste collection does not provide tangible citizen rewards for segregating valuable recyclables (such as aluminum, copper, and steel), suppressing recycling participation.
5. **Lack of Transparent Driver/Collector Compensation**: Independent waste collectors often lack verifiable job assignment metrics, automated mileage tracking, and frictionless daily wage/commission payout mechanisms.

### 1.2 Proposed System
TrashPort addresses these challenges through a modular, role-based architecture uniting Citizens, Collectors, and Municipal Administrators:
- **Citizen Domain**: Provides multi-address geospatial management, dynamic per-kg collection fee calculators, instant online payments (Card, UPI, and recycling wallet points), real-time collector tracking via WebSockets, official GST-compliant downloadable/printable invoices, issue dispute lodging, and an integrated AI conversational assistant.
- **Collector Domain**: Implements an on-duty operations dashboard displaying nearby unassigned pickups sorted by Haversine proximity, turn-by-turn road navigation via Project OSRM (Open Source Routing Machine), on-site physical weight measurement and verification (with automated 2× excess weight penalties), wallet earnings calculation (governed by dynamic admin rates), and instant UPI balance redemption.
- **Administrator Domain**: Supplies a centralized control room featuring a real-time Leaflet map of collectors and pickups, automated dispatch execution (Nearest Collector, Least-Busy Collector, and Zone-Based Dispatch algorithms), collector KYC review and status approval/rejection, user account controls, category rate management, payout parameter configuration, comprehensive operational analytics, and CSV data export capabilities.

### 1.3 Features of the Proposed System
- **Multi-Method User Authentication**: Dual support for standard Argon2/PBKDF2 email-password credentials, Firebase ID Token verification, and server-side Google OAuth 2.0 redirect flow.
- **Geospatial Address Book**: Interactive Leaflet.js map integration with draggable pin placement, reverse geocoding fallback, and default address selection.
- **Scheduled & Categorized Waste Pickups**: Waste categorization (dry, wet, electronic, recyclable metals) with per-kg pricing and minimum 3-hour advance scheduling validation.
- **Sequential User-Specific Pickup Numbering**: Independent sequential IDs (`user_pickup_number`) displayed to citizens starting from #1 for personal record-keeping alongside system-wide primary keys.
- **Pay-Per-Collection Model**: Transparent per-collection pricing based on verified mass and category rates (`fee = weight_kg * fee_per_kg`).
- **Multi-Gateway Payment Processing**: Realistic payment processing supporting mock Credit/Debit cards with decline simulation, validated UPI Virtual Payment Addresses (VPAs), and direct recycling points wallet redemption (at 100 points = Rs. 1.00).
- **Tax Invoicing**: Automatic generation of printable tax invoices detailing base charges, excess weight penalties, CGST (9%), SGST (9%), and payment transaction IDs.
- **Real-Time GPS Tracking via WebSockets**: Bi-directional ASGI Channels WebSocket server (`ws/maps/tracking/<pickup_id>/` and `ws/maps/admin-live/`) streaming live collector coordinates to citizen and administrative map interfaces.
- **Turn-by-Turn OSRM Navigation**: Integration with Project OSRM driving API calculating actual road paths, distance in kilometers, and estimated transit duration in minutes, with 15-minute server-side Redis/cache persistence and Haversine fallback.
- **Weight Verification & Excess Surcharge Engine**: Field verification interface for collectors to enter verified scales; weights exceeding citizen estimates automatically incur a 2.0× penalty rate on surplus kilograms.
- **Configurable Collector Payout Rules**: Dynamic administrative settings (`CollectorPayoutSetting`) defining guaranteed base payout, rate per kilometer, and excess commission percentage credited to collector wallet balances upon pickup completion.
- **Instant UPI Payout Redemption**: Workflow for collectors to redeem earned wallet balances directly to their UPI VPA, logged as `UPIPayoutRequest`.
- **Automated Dispatch Engine**: Administrative batch-assignment engine executing Nearest Collector (Haversine minimum), Least Busy Collector (minimum active job queue), or Zone-Based dispatch algorithms.
- **AI-Powered Customer Assistant**: Streaming LLM chatbot powered by Groq API (`llama-3.1-8b-instant`), supporting intent recognition, dynamic slot-filling, FAQs, pickup cancellation, status checks, and thumbs up/down user feedback logging.
- **Issue Tracking & Complaint Management**: Dispute logging linked directly to specific pickup requests with administrative resolution workflows.
- **Anonymous Feedback Box**: Public and citizen feedback submission system routing categorised suggestions and bug reports directly to administrators.
- **Operational Reporting & Data Export**: Tabular summaries of daily request volume, category breakdown, financial margins, and one-click streaming CSV exports for pickups and revenue.

---

# CHAPTER 2: FUNCTIONAL REQUIREMENTS

### 2.1 User Management & Authentication Module
- **FR-AUTH-01**: The system shall allow users to register as a Citizen or apply as a Collector using unique email addresses, passwords, and full names.
- **FR-AUTH-02**: The system shall restrict Collector registration status to `PENDING` until approved by an Administrator.
- **FR-AUTH-03**: The system shall allow users to authenticate using email and password, Firebase authentication tokens, or Google OAuth 2.0 server-side callback.
- **FR-AUTH-04**: The system shall redirect authenticated users to their specific role dashboard (`/dashboard/`) upon login based on role (`CITIZEN`, `COLLECTOR`, `ADMIN`).
- **FR-AUTH-05**: The system shall allow users to view, update, and delete their profile information and request password reset tokens via email.

### 2.2 Address Management Module
- **FR-ADDR-01**: The system shall allow citizens to save multiple pickup addresses with address line 1, line 2, city, state, postal code, latitude, and longitude.
- **FR-ADDR-02**: The system shall provide an interactive Leaflet map interface allowing citizens to select coordinates by clicking or dragging a marker.
- **FR-ADDR-03**: The system shall ensure only one address per citizen is designated as default by automatically unsetting previous defaults upon new default designation.
- **FR-ADDR-04**: The system shall allow citizens to view, edit, and soft-delete their saved addresses (`is_hidden=True`).

### 2.3 Pickup Scheduling & Invoicing Module
- **FR-PICK-01**: The system shall allow citizens to schedule waste pickups by selecting a saved address or entering a new location, choosing a waste category, specifying estimated weight (minimum 0.01 kg), providing optional quantity notes, and picking a date/time.
- **FR-PICK-02**: The system shall validate that all scheduled pickup times are set at least 3 hours ahead of the current local timestamp.
- **FR-PICK-03**: The system shall compute estimated collection fees (`weight_kg * fee_per_kg`) and recycle reward points (`weight_kg * points_per_kg`).
- **FR-PICK-04**: The system shall compute collection fees based on declared weight and category rates, initializing status to `AWAITING_PAYMENT` (or `PENDING` if fee is 0.00).
- **FR-PICK-05**: The system shall generate an independent per-user sequential pickup number (`user_pickup_number`) starting at 1 for each citizen.
- **FR-PICK-06**: The system shall generate a formal printable invoice for completed or paid pickups displaying itemized rates, excess fees, and 18% GST (9% CGST + 9% SGST).
- **FR-PICK-07**: The system shall allow citizens to cancel unassigned pickup requests with a stated reason and record the cancellation timestamp.
- **FR-PICK-08**: The system shall allow citizens to submit a 1–5 star rating and textual feedback upon completion of a pickup.

### 2.4 Payment & Wallet Module
- **FR-PAY-01**: The system shall provide a payment checkout interface supporting Card, UPI, and Wallet Points.
- **FR-PAY-02**: The system shall validate card payments against a simulated card catalog supporting instant success (Visa/Mastercard) and specific decline scenarios (insufficient funds, expired card, invalid CVC).
- **FR-PAY-03**: The system shall validate UPI VPA formats against the regex pattern `^[\w.\-]+@[\w]+$`.
- **FR-PAY-04**: The system shall allow citizens to redeem recycling wallet points to settle pickup fees at a fixed exchange rate of 100 points = Rs. 1.00.
- **FR-PAY-05**: The system shall transition a pickup from `AWAITING_PAYMENT` to `PENDING` upon successful payment verification and record an audit log in `PaymentTransaction`.
- **FR-PAY-06**: The system shall log all additions and deductions of wallet points with balance tracking in `WalletHistory`.
- **FR-PAY-07**: The system shall support Stripe webhook event consumption for external payment confirmation.

### 2.5 Collector Operations & Dispatch Module
- **FR-COL-01**: The system shall prevent unverified collectors (`is_verified = False`) from accepting pickups or accessing job claiming actions.
- **FR-COL-02**: The system shall display unassigned pickup requests to verified collectors, sorted in ascending order of proximity using the Haversine spherical distance formula.
- **FR-COL-03**: The system shall allow collectors to claim an unassigned pickup, transitioning its status to `ASSIGNED`.
- **FR-COL-04**: The system shall allow collectors to mark a pickup as `IN_TRANSIT` and broadcast live GPS coordinates via HTTP endpoint (`/api/maps/locations/update/`) and WebSockets.
- **FR-COL-05**: The system shall query Project OSRM to render turn-by-turn road paths, travel distance (km), and ETA (minutes) on the collector route map.
- **FR-COL-06**: The system shall require collectors to verify actual waste weight upon collection. If `actual_weight_kg > weight_kg`, the system shall compute an excess fee at 2× the category rate per surplus kilogram.
- **FR-COL-07**: The system shall calculate collector earnings dynamically based on active `CollectorPayoutSetting` (guaranteed base minimum + mileage rate + excess weight commission) and credit the collector's wallet balance upon marking status as `COMPLETED`.
- **FR-COL-08**: The system shall allow collectors to submit a UPI payout request to withdraw accumulated cash earnings to a valid UPI ID.

### 2.6 Dispatch Engine & Administration Module
- **FR-ADM-01**: The system shall allow administrators to view high-level metrics including total revenue, completed pickups, recycled tonnage, collector payouts, active complaints, and volume trends.
- **FR-ADM-02**: The system shall provide an administrative control room with a live Leaflet map rendering all active citizen pickup points and collector locations.
- **FR-ADM-03**: The system shall execute automated dispatch runs using one of three selectable algorithms: Nearest Collector, Least-Busy Collector, or Zone-Based Dispatch.
- **FR-ADM-04**: The system shall log each dispatch execution into a `DispatchBatch` record containing assigned count, unassigned count, and JSON payload of assigned IDs.
- **FR-ADM-05**: The system shall allow administrators to approve or reject pending collector verification applications (`CollectorVerificationView`).
- **FR-ADM-06**: The system shall allow administrators to toggle user active status and manually adjust citizen wallet points with recorded reasons.
- **FR-ADM-07**: The system shall allow administrators to create, update, and view Waste Categories (with fees and reward points per kg) and Collector Payout Settings.
- **FR-ADM-08**: The system shall stream live CSV exports of pickup request data and revenue analytics directly to administrative clients.
- **FR-ADM-09**: The system shall allow administrators to resolve citizen complaints with status transitions from `PENDING` to `RESOLVED` and review anonymous user feedbacks.

### 2.7 AI Chatbot & Communication Module
- **FR-BOT-01**: The system shall provide a floating interactive chat widget supporting bi-directional communication over WebSockets (`ws/chatbot/`) and HTTP fallback (`/api/chatbot/send-message/`).
- **FR-BOT-02**: The system shall enforce rate-limiting on chatbot messages per user and IP address using Redis cache buckets.
- **FR-BOT-03**: The system shall classify conversational intent and perform slot-filling for scheduling pickups, checking payment status, cancelling pickups, and filing complaints.
- **FR-BOT-04**: The system shall store conversational audit logs (`ChatLog`) containing user messages, raw LLM completions, parsed JSON actions, and execution validity.
- **FR-BOT-05**: The system shall allow users to submit binary feedback (thumbs up / thumbs down) recorded in `ChatFeedback`.
- **FR-NOTIF-01**: The system shall create in-app notifications (`Notification`) for pickup status updates, payments, and complaint resolutions.
- **FR-NOTIF-02**: The system shall allow users to retrieve unread notifications, mark individual notifications as read, and mark all notifications as read.

---

# CHAPTER 3: NON-FUNCTIONAL REQUIREMENTS

### 3.1 Performance
- **Evidence in Code**:
  - Connection pooling configured in `config/settings/base.py` via `CONN_MAX_AGE = 60` to reuse PostgreSQL connections.
  - Caching of Project OSRM road geometry in Redis/cache for 900 seconds (15 minutes) in `trashport/maps/services.py` (`cache_key = f"osrm_route_..."`) avoiding redundant network calls.
  - Collector dashboard query optimization: unassigned pickups capped to the 50 nearest candidates using an in-memory Haversine sort (`trashport/collectors/views.py`), preventing browser DOM freezing.
  - Database queries use `.select_related()` on ForeignKeys (`citizen`, `address`, `category`, `collector`) across views to prevent N+1 query overhead.
  - WhiteNoise compression and caching middleware (`whitenoise.storage.CompressedManifestStaticFilesStorage`) configured for instant static asset delivery.
  - Admin dashboard tables implement fixed-height 5-row viewports with vertical scrolling and sticky table headers, preventing large dataset DOM rendering lag.

### 3.2 Security
- **Evidence in Code**:
  - Custom user model uses Django's password hashing pipeline (`Argon2PasswordHasher`, `PBKDF2PasswordHasher`, `PBKDF2SHA1PasswordHasher`).
  - Custom password validators configured in `trashport/users/validators.py` enforcing minimum length (8), uppercase letters, numeric digits, and special characters.
  - CSRF protection enforced across all POST/PUT/DELETE forms via `{% csrf_token %}` and `django.middleware.csrf.CsrfViewMiddleware`.
  - Content Security headers enforced: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`.
  - Authentication checks enforced using `LoginRequiredMixin` on class-based views and DRF `IsAuthenticated` / `IsAdminUser` permissions on API views.
  - Sensitive environment variables (`DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`, `GROQ_API_KEY`, `GOOGLE_OAUTH_CLIENT_SECRET`) externalized through `.env` and `.gitignore`.

### 3.3 Usability
- **Evidence in Code**:
  - Responsive layouts styled using Tailwind CSS and Bootstrap 5 with mobile navigation toggles (`#mobile-menu-btn`).
  - Interactive Leaflet.js maps with custom SVG markers indicating pickup locations, collectors, and live routes.
  - Role-specific dashboard routing: a single unified `/dashboard/` URL automatically resolves to Citizen, Collector, or Admin interfaces.
  - Multi-step interactive modal feedback and animated thinking bubbles (`.thinking-dots`) in the AI chatbot.

### 3.4 Reliability
- **Evidence in Code**:
  - Atomic database transactions implemented via `@db_transaction.atomic` across payment processing (`trashport/payments/services.py`) and pickup completions, ensuring wallet balances, transaction records, and pickup statuses update consistently or roll back completely.
  - Fallback mechanisms: OSRM route failure gracefully defaults to mathematical Haversine calculations without crashing the UI.
  - Chatbot fallback: LLM client failure or JSON parsing errors fall back to deterministic FAQ lookup and standard help responses.
  - Database-level integrity constraints: Foreign keys protect referential integrity (`on_delete=models.PROTECT` on `WasteCategory` to prevent orphaned pickup records).

### 3.5 Scalability
- **Evidence in Code**:
  - Asynchronous event-driven architecture using ASGI/Daphne and Django Channels with Redis channel layers (`channels_redis.core.RedisChannelLayer`) enabling horizontal scaling of WebSocket connections.
  - Redis cache backend (`django_redis.cache.RedisCache`) for session storage and rate limiting.
  - Celery infrastructure configured in `config/celery_app.py` for offloading background tasks (notifications and dispatch sweeps).

### 3.6 Maintainability
- **Evidence in Code**:
  - Separation of concerns across modular Django apps: `users`, `citizens`, `collectors`, `admins`, `waste_management`, `payments`, `maps`, `dispatch`, `chatbot`, and `notifications`.
  - Codebase linting and formatting configured with Ruff (`ruff.toml` / `.pre-commit-config.yaml`) and type annotations checked with `django-stubs` / `mypy`.
  - Comprehensive automated test suite comprising unit and integration tests across all modules.

### 3.7 Portability
- **Evidence in Code**:
  - Containerization using Docker and Docker Compose (`docker-compose.local.yml` and `docker-compose.production.yml`) isolating application, database, and cache dependencies.
  - Cross-platform configuration support: database connection switches between PostgreSQL in production/Docker and SQLite for lightweight local development via `DATABASE_URL`.

---

# CHAPTER 4: UML DIAGRAMS

### 4.1 Use Cases

| Actor | Use Case | Description |
| :--- | :--- | :--- |
| **Citizen** | Register / Login | Create account or authenticate via Password, Google OAuth, or Firebase. |
| **Citizen** | Manage Address Book | Add, view, edit, set default, or delete saved addresses with map coordinates. |
| **Citizen** | Book Waste Pickup | Create a pickup request specifying address, category, weight, quantity, and date. |
| **Citizen** | Make Payment | Settle pickup fees using Card, UPI, or redeemed recycling wallet points. |
| **Citizen** | Track Collector Live | Monitor approaching collection vehicle location and route on an interactive map. |
| **Citizen** | Download / Print Invoice | View official tax invoice with GST breakdown and user pickup numbering. |
| **Citizen** | Cancel Pickup | Cancel unassigned pending pickup requests with stated reason. |
| **Citizen** | Submit Feedback | Rate completed pickups (1 to 5 stars) and submit text comments. |
| **Citizen** | File Complaint | Lodge a formal dispute or grievance against a specific pickup request. |
| **Citizen** | Submit Anonymous Feedback | Send unauthenticated suggestions or bug reports to system administration. |
| **Citizen** | Chat with AI Assistant | Query FAQs, request pickups, check payments, or file issues via chat. |
| **Collector** | Register Account | Submit collector registration with vehicle and driver license numbers. |
| **Collector** | View Proximity Jobs | View unassigned pickups sorted by Haversine distance from current position. |
| **Collector** | Claim Pickup | Accept an unassigned pickup request and change status to `ASSIGNED`. |
| **Collector** | Update Transit Status | Mark pickup as `IN_TRANSIT` and broadcast live coordinates via WebSockets. |
| **Collector** | Navigate Route | View turn-by-turn OSRM driving directions to citizen pickup coordinates. |
| **Collector** | Verify Waste Weight | Input measured weight on-site; system computes 2× fee penalty on excess weight. |
| **Collector** | Complete Pickup | Mark pickup as `COMPLETED`, crediting dynamic earnings to wallet. |
| **Collector** | Redeem Earnings to UPI | Submit request to withdraw accumulated cash wallet balance to a UPI VPA. |
| **Administrator** | Manage Users | View users, toggle active accounts, and inspect profile details. |
| **Administrator** | Verify Collectors | Review collector KYC documents and approve or reject verification status. |
| **Administrator** | Adjust Citizen Wallet | Manually award or deduct recycling points with audit reason tracking. |
| **Administrator** | Manage Master Data | Create and update Waste Categories and Collector Payout Settings. |
| **Administrator** | Control Room Live Map | View all active citizen pickup markers and moving collector markers in real time. |
| **Administrator** | Run Auto-Dispatch | Trigger automated batch assignment using Nearest, Least-Busy, or Zone algorithms. |
| **Administrator** | Resolve Complaints | Review citizen grievances and transition status from `PENDING` to `RESOLVED`. |
| **Administrator** | Review Feedback Box | Inspect citizen anonymous feedback submissions and add administrative audit notes. |
| **Administrator** | Export Data (CSV) | Stream live CSV files for all pickup records and financial revenue transactions. |
| **Administrator** | View Operations Report | Inspect metrics, volume trends, category distribution, and financial summaries. |
| **AI Assistant** | Process NLP Intent | Classify conversational input and execute slot-filling for scheduling/cancellations. |

---

### 4.2 Use Case Diagram
```
========================================================================================
                                TRASHPORT USE CASE MODEL
========================================================================================

                 +-------------------------------------------------------+
                 |                     TRASHPORT                         |
                 |                                                       |
   (Citizen) --->|-- (UC01: Register & Authenticate)                     |
         |       |-- (UC02: Manage Address Book)                         |
         |       |-- (UC03: Schedule Waste Pickup)                       |
         |       |        |                                              |
         |       |        +-- <<include>> --> (UC04: Calculate Fee & Pts)|
         |       |        +-- <<extend>>  --> (UC05: Settle Bill/Payment)|
         |       |-- (UC05: Settle Bill/Payment)                         |
         |       |        |                                              |
         |       |        +-- <<extend>> (Card / UPI / Wallet Points)    |
         |       |-- (UC06: Track Collector Live via WebSocket)          |
         |       |-- (UC07: View / Print Tax Invoice)                    |
         |       |-- (UC08: Lodge Complaint)                             |
         |       |-- (UC09: Submit Anonymous Feedback)                   |
         |       |-- (UC10: Chat with AI Assistant)                      |
         |       |                                                       |
 (Collector) --->|-- (UC11: Register as Collector [Pending KYC])         |
         |       |-- (UC12: View Nearby Jobs [Haversine Sorted])         |
         |       |-- (UC13: Claim Unassigned Pickup)                     |
         |       |-- (UC14: Broadcast Live Location)                     |
         |       |-- (UC15: Navigate OSRM Road Route)                    |
         |       |-- (UC16: Verify Scale Weight [2x Excess Surcharge])   |
         |       |-- (UC17: Complete Pickup & Credit Earnings)           |
         |       |-- (UC18: Redeem Earnings to UPI ID)                   |
         |       |                                                       |
     (Admin) --->|-- (UC19: Verify / Approve Collector KYC)             |
         |       |-- (UC20: Monitor Live Control Room Map)               |
         |       |-- (UC21: Execute Auto-Dispatch Algorithm)             |
         |       |        |                                              |
         |       |        +-- <<extend>> (Nearest / Least-Busy / Zone)   |
         |       |-- (UC22: Manage Categories & Payout Settings)         |
         |       |-- (UC23: Audit Wallets & Adjust Points)               |
         |       |-- (UC24: Resolve Complaints & Review Feedback)        |
         |       |-- (UC25: Export CSV Reports [Pickups & Revenue])      |
         |       +-------------------------------------------------------+
========================================================================================
```

---

### 4.3 Activity Diagram

#### 4.3.1 Workflow 1: Citizen Pickup Request Booking & Payment
**Ordered Activity Steps**:
1. Citizen navigates to Pickup Booking Form.
2. System loads saved addresses and waste categories.
3. Citizen selects address (or pins a new address on Leaflet map), selects category, enters estimated weight, and chooses pickup time.
4. Citizen submits booking request.
5. System validates that scheduled time is >= 3 hours in advance.
6. If validation fails, system re-renders form with error message.
7. System calculates fee (`weight_kg * fee_per_kg`).
8. System marks status as `AWAITING_PAYMENT` and redirects to Payment Checkout.
9. On checkout, Citizen selects payment method (Card, UPI, or Wallet Points).
10. System processes transaction through `PaymentGatewayService`.
11. If payment succeeds, system marks pickup as paid (`is_paid = True`), changes status to `PENDING`, and displays confirmation.
12. System assigns per-citizen sequential pickup number (`user_pickup_number`).

**Text-Flow Notation**:
```
Start 
  -> [Navigate to Pickup Booking] 
  -> [Input Address, Category, Weight, Schedule Time] 
  -> Decision {Schedule Time >= Current Time + 3 Hours?}
       -> [No]  -> [Display Validation Error] -> [Re-enter Data] -> Decision
       -> [Yes] -> [Calculate Base Fee (Weight * Rate)] 
                -> [Set Status = AWAITING_PAYMENT] 
                -> [Redirect to Payment Checkout] 
                -> [Select Card / UPI / Wallet Points] 
                -> Decision {Payment Transaction Succeeded?}
                     -> [No]  -> [Record Failed Txn & Show Decline Alert] -> End
                     -> [Yes] -> [Set is_paid = True] 
                              -> [Set Status = PENDING] 
                              -> [Assign user_pickup_number] 
                              -> [Generate Invoice Link] 
                              -> End
```

---

#### 4.3.2 Workflow 2: Collector Pickup Fulfillment, Verification, and Earnings Credit
**Ordered Activity Steps**:
1. Collector logs into dashboard. System checks if collector is verified (`is_verified == True`).
2. If unverified, system displays "Pending Administrator Approval" banner and halts execution.
3. If verified, system computes distance to all unassigned pickups using the Haversine formula and sorts ascending.
4. Collector claims a pickup request; status updates to `ASSIGNED`.
5. Collector begins journey; updates status to `IN_TRANSIT`.
6. Collector queries Project OSRM driving engine to display turn-by-turn route and estimated travel time.
7. Collector's mobile browser transmits live GPS coordinates to `/api/maps/locations/update/` and ASGI WebSocket channel.
8. Collector arrives on-site, inspects waste, and inputs verified scale weight (`actual_weight_kg`).
9. System evaluates: Does `actual_weight_kg > estimated weight_kg`?
   - If yes: System calculates excess surcharge: `extra_fee = (actual - estimated) * fee_per_kg * 2.0`. Total fee is increased.
10. Collector confirms job completion; status updates to `COMPLETED`.
11. System calculates collector earnings based on `CollectorPayoutSetting`: `earnings = base_min + (distance_km * rate_km) + (extra_fee * excess_comm_pct)`.
12. System credits collector's cash wallet balance (`wallet_balance += collector_earnings`).
13. System credits citizen's recycling reward points (`wallet_points += points_earned`).

**Text-Flow Notation**:
```
Start 
  -> [Collector Logs In] 
  -> Decision {Is Collector Verified by Admin?}
       -> [No]  -> [Display KYC Pending Notice & Disable Actions] -> End
       -> [Yes] -> [Compute Haversine Proximity to Unassigned Pickups] 
                -> [Display Ranked Available Opportunities] 
                -> [Collector Claims Job] 
                -> [Set Status = ASSIGNED] 
                -> [Set Status = IN_TRANSIT] 
                -> [Fetch OSRM Road Route & Stream GPS Coordinates] 
                -> [Collector Measures Actual Weight on Scale] 
                -> Decision {Actual Weight > Estimated Weight?}
                     -> [Yes] -> [Apply 2x Excess Weight Surcharge to Fee] 
                              -> [Update Pickup Fee]
                     -> [No]  -> [Retain Standard Fee]
                -> [Set Status = COMPLETED] 
                -> [Calculate Collector Commission using Payout Settings] 
                -> [Credit Collector wallet_balance] 
                -> [Credit Citizen wallet_points] 
                -> End
```

---

#### 4.3.3 Workflow 3: Administrator Automated Dispatch Run
**Ordered Activity Steps**:
1. Administrator accesses Control Room Dispatch interface.
2. System queries all unassigned pickups with `status = 'PENDING'` and `collector__isnull = True`.
3. System fetches all active verified collectors (`is_active = True`).
4. Administrator selects algorithm: Nearest Collector, Least-Busy Collector, or Zone-Based.
5. System executes chosen algorithm:
   - Nearest: Assigns pickup to the collector with minimum spherical distance.
   - Least-Busy: Assigns pickup to the collector with the lowest count of currently active jobs.
   - Zone-Based: Matches pickup service zone to collector service zone.
6. System updates assigned pickups (`collector = assigned_collector`, `status = ASSIGNED`).
7. System creates `DispatchBatch` record storing algorithm type, counts, and JSON list of IDs.
8. System sends notifications to assigned collectors.

**Text-Flow Notation**:
```
Start 
  -> [Admin Opens Dispatch Management] 
  -> [Fetch Unassigned PENDING Pickups & Active Collectors] 
  -> Decision {Select Dispatch Strategy}
       -> [Strategy = NEAREST]    -> [Execute NearestCollectorDispatch (Haversine)] -> [Merge]
       -> [Strategy = LEAST_BUSY] -> [Execute LeastBusyCollectorDispatch (Min Queue)] -> [Merge]
       -> [Strategy = ZONE_BASED] -> [Execute ZoneBasedDispatch (Service Zone Code)] -> [Merge]
  -> [Merge] 
  -> [Update Pickups: Assign Collector & Status = ASSIGNED] 
  -> [Log DispatchBatch Audit Record] 
  -> [Broadcast In-App Notifications to Collectors] 
  -> End
```

---

### 4.4 Class Diagram
```
+-----------------------------------------------------------------------------------------+
|                                        User                                             |
+-----------------------------------------------------------------------------------------+
| - id: Integer (PK)                                                                      |
| - email: EmailField {unique}                                                            |
| - name: CharField(255)                                                                  |
| - role: CharField(20) [CITIZEN, COLLECTOR, ADMIN]                                       |
| - verification_status: CharField(20) [PENDING, APPROVED, REJECTED]                      |
| - firebase_uid: CharField(255) {unique, nullable}                                       |
+-----------------------------------------------------------------------------------------+
| + is_verified(): Boolean {property}                                                     |
| + wallet_points(): Integer {property -> CitizenProfile}                                 |
| + wallet_balance(): Decimal {property -> CollectorProfile}                              |
| + vehicle_number(): String {property -> CollectorProfile}                               |
| + license_number(): String {property -> CollectorProfile}                               |
| + save(*args, **kwargs): void                                                           |
| + get_absolute_url(): String                                                            |
+-----------------------------------------------------------------------------------------+
          | 1             | 1             | 1            | 1            | 1
          |               |               |              |              |
          | 0..*          | 0..*          | 0..*         | 0..*         | 0..1
          v               v               v              v              v
    +-----------+  +-----------+ +--------------+ +--------------------+
    |  Address  |  | Complaint | | PaymentTxn   | | CollectorLocation  |
    +-----------+  +-----------+ +--------------+ +--------------------+
          ^               |                                                 ^
          | 1             |                                                 |
          | 0..*          |                                                 |
          |               |                                                 |
          | 1             |                                                 |
          |               |                                                 |
          | 0..*          v                                                 |
+------------------------------------------------------------------------+  |
|                             PickupRequest                              |  |
+------------------------------------------------------------------------+  |
| - id: Integer (PK)                                                     |  |
| - user_pickup_number: PositiveIntegerField {nullable}                  |  |
| - citizen: ForeignKey(User)                                            |  |
| - collector: ForeignKey(User) {nullable} ------------------------------+--+
| - address: ForeignKey(Address) {nullable}                              |
| - category: ForeignKey(WasteCategory)                                  |
| - latitude: DecimalField(9, 6) {nullable}                              |
| - longitude: DecimalField(9, 6) {nullable}                             |
| - weight_kg: DecimalField(6, 2)                                        |
| - quantity_estimate: CharField(100) {nullable}                         |
| - actual_weight_kg: DecimalField(6, 2) {nullable}                      |
| - fee: DecimalField(10, 2)                                             |
| - extra_fee: DecimalField(10, 2) (2x excess surcharge)                 |
| - distance_km: DecimalField(6, 2)                                      |
| - collector_earnings: DecimalField(10, 2)                              |
| - is_weight_verified: BooleanField                                     |
| - points_earned: IntegerField                                          |
| - is_paid: BooleanField                                                |
| - schedule_date: DateTimeField                                         |
| - status: CharField(20) [PENDING, AWAITING_PAYMENT,                    |
|                          ASSIGNED, IN_TRANSIT, COMPLETED, CANCELLED]   |
| - feedback_rating: IntegerField (1..5) {nullable}                      |
| - feedback_comments: TextField {nullable}                              |
| - cancellation_reason: TextField {nullable}                            |
| - cancelled_at: DateTimeField {nullable}                               |
+------------------------------------------------------------------------+
| + display_id(): Integer                                                |
| + effective_latitude(): Float                                          |
| + effective_longitude(): Float                                         |
| + calculate_collector_earnings(): Decimal                              |
| + save(*args, **kwargs): void                                          |
+------------------------------------------------------------------------+
          | *
          |
          | 1
          v
+------------------------------------------------------------------------+
|                             WasteCategory                              |
+------------------------------------------------------------------------+
| - id: Integer (PK)                                                     |
| - name: CharField(100) {unique}                                        |
| - description: TextField {nullable}                                    |
| - fee_per_kg: DecimalField(6, 2)                                       |
| - points_per_kg: IntegerField                                          |
| - max_weight_kg: DecimalField(6, 2)                                    |
+------------------------------------------------------------------------+

+-------------------------------------+      +-------------------------------------+
|        CollectorPayoutSetting       |      |          AnonymousFeedback          |
+-------------------------------------+      +-------------------------------------+
| - id: Integer (PK)                  |      | - id: Integer (PK)                  |
| - base_min_payout: Decimal(8, 2)    |      | - category: CharField(50)           |
| - rate_per_km: Decimal(6, 2)        |      | - subject: CharField(200)           |
| - extra_weight_commission_percent   |      | - message: TextField                |
+-------------------------------------+      | - is_reviewed: BooleanField         |
| + get_settings(): Instance          |      | - admin_notes: TextField            |
+-------------------------------------+      +-------------------------------------+

+-------------------------------------+      +-------------------------------------+
|            DispatchBatch            |      |            UPIPayoutRequest         |
+-------------------------------------+      +-------------------------------------+
| - id: Integer (PK)                  |      | - id: Integer (PK)                  |
| - algorithm_used: CharField(50)     |      | - collector: ForeignKey(User)       |
| - assigned_count: IntegerField      |      | - amount: DecimalField(10, 2)       |
| - unassigned_count: IntegerField    |      | - upi_id: CharField(100)            |
| - executed_by: ForeignKey(User)     |      | - transaction_ref: CharField(100)   |
| - details: JSONField                |      | - status: CharField(20)             |
+-------------------------------------+      +-------------------------------------+

+-------------------------------------+      +-------------------------------------+
|             ChatSession             |      |             ChatMessage             |
+-------------------------------------+      +-------------------------------------+
| - id: Integer (PK)                  | 1  * | - id: Integer (PK)                  |
| - user: ForeignKey(User) {nullable} |----->| - session: ForeignKey(ChatSession)  |
| - session_key: CharField(100)       |      | - sender: CharField(10)             |
+-------------------------------------+      | - text: TextField                   |
                                             | - intent: CharField(100)            |
                                             | - action_data: JSONField            |
                                             +-------------------------------------+
```

---

# CHAPTER 5: TEST CASES

| Test ID | Feature | Test Scenario | Input | Expected Output | Actual Output | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-01** | Authentication | Valid Citizen registration | Email: `cit@tp.org`, Name: `Jane Doe`, Role: `CITIZEN`, Pass: `Secure#123` | User record created; role set to `CITIZEN`; `verification_status="APPROVED"`; redirect to dashboard | | |
| **TC-AUTH-02** | Authentication | Collector registration requires KYC | Email: `col@tp.org`, Role: `COLLECTOR`, License: `DL-908`, Pass: `Secure#123` | User record created; `verification_status="PENDING"`; `is_verified=False` | | |
| **TC-AUTH-03** | Authentication | Invalid password complexity rejection | Password: `short` | Validation error: password must contain minimum 8 chars, uppercase, digit, special symbol | | |
| **TC-PICK-01** | Pickup Booking | Standard pickup advance scheduling | Scheduled date: `Current Time + 4 Hours`, Category: Plastic (Rs 5/kg), Weight: 10 kg | Pickup created; status `AWAITING_PAYMENT`; Fee = Rs. 50.00; Points = 0 | | |
| **TC-PICK-02** | Pickup Booking | Reject booking under 3-hour minimum | Scheduled date: `Current Time + 1 Hour` | Form validation error: "Pickup must be scheduled at least 3 hours in advance" | | |
| **TC-PICK-03** | Pickup Booking | Pay-per-collection fee calculation | Citizen books 10 kg plastic pickup (Rate: Rs. 1.50/kg, 2 pts/kg) | Fee calculated as `Rs. 15.00`; Points earned = 20; status `AWAITING_PAYMENT` | | |
| **TC-PICK-04** | Pickup Booking | Per-user sequential numbering | Citizen's 3rd consecutive pickup creation | `user_pickup_number` assigned exactly as `3` | | |
| **TC-PAY-01** | Payments | Successful dummy card payment | Card: `4242424242424242`, CVV: `123`, Expiry: `12/28` | Transaction status `COMPLETED`; Pickup `is_paid=True`; status changed to `PENDING` | | |
| **TC-PAY-02** | Payments | Card decline on insufficient funds | Card: `4000000000009995`, CVV: `123`, Expiry: `12/28` | Transaction status `FAILED`; decline message: "Insufficient funds. Please use a different payment method." | | |
| **TC-PAY-03** | Payments | Valid UPI ID payment settlement | UPI ID: `citizen@okhdfcbank` | `PaymentTransaction` marked `COMPLETED`; pickup marked paid | | |
| **TC-PAY-04** | Payments | Invalid UPI ID regex format | UPI ID: `invalid-upi-string` | Returns error: "Invalid UPI ID format. Please enter a valid VPA." | | |
| **TC-PAY-05** | Payments | Wallet points redemption | Pickup Fee: Rs. 10.00; Citizen Points: 1,500 pts | 1,000 points deducted; balance after = 500; `WalletHistory` logged; pickup marked paid | | |
| **TC-PAY-06** | Payments | Insufficient wallet points redemption | Pickup Fee: Rs. 50.00 (requires 5,000 pts); Balance: 200 pts | Returns error specifying exact points required and monetary shortfall | | |
| **TC-COL-01** | Collector Ops | Prevent unverified collector job claiming | Unverified collector clicks "Claim Pickup" | Action blocked with 403 Forbidden / message prompting KYC approval | | |
| **TC-COL-02** | Collector Ops | Excess weight surcharge calculation | Estimated: 5.0 kg; Actual verified: 10.0 kg; Rate: Rs 10/kg | Extra weight = 5 kg; Extra fee = `5 * 10 * 2.0 = Rs. 100.00`; Total fee = Rs. 150.00 | | |
| **TC-COL-03** | Collector Ops | Collector earnings calculation | Total Fee: Rs. 100.00; Distance: 10.0 km; Settings: Base Rs 25, Rs 2/km, 20% excess | Earnings = `max(25, 25 + (10 * 2) + (0 * 0.20)) = Rs. 45.00`; credited to collector wallet | | |
| **TC-COL-04** | Collector Ops | Collector UPI payout redemption | Wallet Balance: Rs. 500.00; Withdraw: Rs. 200.00; UPI: `col@upi` | Wallet balance reduced to Rs. 300.00; `UPIPayoutRequest` created with status `COMPLETED` | | |
| **TC-DISP-01** | Dispatch Engine | Nearest Collector auto-dispatch run | 2 pickups in Indiranagar; Collector A at 1.2 km; Collector B at 4.5 km | Pickup assigned to Collector A; `DispatchBatch` created with `algorithm_used="NEAREST"` | | |
| **TC-DISP-02** | Dispatch Engine | Least-Busy Collector auto-dispatch | Collector A (3 active jobs); Collector B (0 active jobs) | Pickup assigned to Collector B; workload balanced across fleet | | |
| **TC-MAP-01** | Maps & Routing | Project OSRM driving route resolution | Start: `(9.9312, 76.2673)`, End: `(9.9816, 76.2999)` | Returns JSON with GeoJSON coordinates, distance in km, duration in mins; cached 15 min | | |
| **TC-MAP-02** | Maps & Routing | OSRM network timeout fallback | OSRM server unreachable / timeout | Graceful fallback to Haversine straight-line coordinates without throwing unhandled exception | | |
| **TC-BOT-01** | AI Chatbot | Slot-filling waste pickup via chat | User message: "Schedule 5 kg plastic pickup tomorrow" | Chatbot identifies intent `schedule_pickup`, extracts slot entities, prompts for address | | |
| **TC-EXP-01** | Reporting | Admin CSV Pickups export stream | Administrator requests `/manage/export/pickups/` | HTTP 200 with `Content-Type: text/csv` streaming all pickups with headers | | |

---

# CHAPTER 6: INPUT DESIGN AND OUTPUT DESIGN

### 6.1 Input Design

| Form / Interface | Field Name | Input Type | Validation Rules & Constraints | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **User Signup** | `email` | EmailInput | Valid email format; unique in database | Primary authentication identity |
| **User Signup** | `name` | TextInput | Required; regex `^[a-zA-Z\s]+$` (letters and spaces only) | User display name |
| **User Signup** | `role` | Select | Choices: `CITIZEN`, `COLLECTOR` | User persona selection |
| **User Signup** | `password` | PasswordInput | Min 8 chars, 1 uppercase, 1 digit, 1 special character | Account credential protection |
| **Address Form** | `address_line1` | TextInput | Required; max 255 chars | Street name and door number |
| **Address Form** | `address_line2` | TextInput | Optional; max 255 chars | Apartment / landmark details |
| **Address Form** | `city` | TextInput | Required; max 100 chars | City identifier |
| **Address Form** | `state` | TextInput | Required; max 100 chars | State jurisdiction |
| **Address Form** | `postal_code` | TextInput | Required; max 20 chars | Postal / ZIP code |
| **Address Form** | `latitude` | HiddenInput | Decimal (max 9 digits, 6 decimal places) | Geospatial latitude coordinate |
| **Address Form** | `longitude` | HiddenInput | Decimal (max 9 digits, 6 decimal places) | Geospatial longitude coordinate |
| **Address Form** | `is_default` | CheckboxInput | Boolean | Mark address as citizen's primary |
| **Pickup Booking** | `address` | Select | FK to Address; belongs to logged-in user | Selection of existing saved location |
| **Pickup Booking** | `new_address_line1` | TextInput | Optional if saved address selected; required otherwise | Direct street address input |
| **Pickup Booking** | `category` | Select | FK to WasteCategory; required | Type of waste (Plastic, Metal, etc.) |
| **Pickup Booking** | `weight_kg` | NumberInput | Required; Decimal; min: `0.01`, step: `0.01` | Estimated waste mass in kilograms |
| **Pickup Booking** | `quantity_estimate` | TextInput | Optional; max 100 chars (e.g. "2 bags") | Visual volume indicator for fleet |
| **Pickup Booking** | `schedule_date` | DateTimeLocal | Required; must be >= current time + 3 hours | Date and time of requested collection |
| **Payment Checkout** | `payment_method` | RadioSelect | Choices: `card`, `upi`, `wallet` | Selection of payment gateway channel |
| **Payment Checkout** | `card_number` | TextInput | 16-digit numeric string | Card number matching dummy catalog |
| **Payment Checkout** | `expiry` | TextInput | Format `MM/YY` | Card expiration verification |
| **Payment Checkout** | `cvv` | PasswordInput | 3 or 4 digits | Card security code |
| **Payment Checkout** | `upi_id` | TextInput | Regex `^[\w.\-]+@[\w]+$` | Virtual Payment Address for UPI |
| **Collector Scale** | `actual_weight_kg` | NumberInput | Required; Decimal; min: `0.01`, step: `0.01` | On-site measured physical scale weight |
| **UPI Redemption** | `amount` | NumberInput | Decimal; <= collector.wallet_balance | Requested withdrawal amount |
| **UPI Redemption** | `upi_id` | TextInput | Valid UPI VPA syntax | Destination UPI address for payout |
| **Feedback Form** | `feedback_rating` | NumberInput | Integer between 1 and 5 inclusive | Citizen service satisfaction score |
| **Feedback Form** | `feedback_comments` | Textarea | Optional; free text | Detailed citizen feedback comments |
| **Complaint Form** | `pickup_request` | Select | FK to PickupRequest belonging to citizen | Association of issue with specific job |
| **Complaint Form** | `title` | TextInput | Required; max 200 chars | Brief summary of grievance |
| **Complaint Form** | `description` | Textarea | Required; free text | Full description of complaint |
| **Feedback Box** | `category` | Select | Choices: Suggestion, Issue, Bug, General | Categorization of public feedback |
| **Feedback Box** | `subject` | TextInput | Optional; max 200 chars | Summary topic |
| **Feedback Box** | `message` | Textarea | Required; free text | User message to system administrators |
| **Category Admin** | `fee_per_kg` | NumberInput | Decimal; min: `0.00`, step: `0.01` | Unit service charge |
| **Category Admin** | `points_per_kg` | NumberInput | Integer; min: `0` | Incentive reward points awarded |
| **Category Admin** | `max_weight_kg` | NumberInput | Decimal; min: `0.01`, step: `0.01` | Upper limit booking threshold |
| **Payout Settings** | `base_min_payout` | NumberInput | Decimal; min: `0.00`, step: `0.01` | Guaranteed minimum driver fee |
| **Payout Settings** | `rate_per_km` | NumberInput | Decimal; min: `0.00`, step: `0.01` | Travel compensation per km |
| **Payout Settings** | `extra_weight_comm`| NumberInput | Decimal; range 0.00 to 100.00% | Excess surcharge share for driver |
| **Wallet Adjust** | `points` | NumberInput | Integer (positive or negative) | Point adjustment delta |
| **Wallet Adjust** | `reason` | TextInput | Required; max 255 chars | Audit description for wallet adjustment |

---

### 6.2 Output Design

| Output Item | Media / Format | Triggering Event | Description / Content |
| :--- | :--- | :--- | :--- |
| **Citizen Dashboard** | Web HTML / Responsive UI | Citizen navigates to `/dashboard/` | Active pickups, completed history, recycling points balance, unread notifications |
| **Collector Dashboard** | Web HTML / Leaflet Map | Collector navigates to `/dashboard/` | Verification banner, cash wallet balance, nearby unassigned opportunities sorted by distance, active jobs |
| **Admin Dashboard** | Web HTML / Chart.js Charts | Admin navigates to `/dashboard/` | Total revenue, collection volume (kg), completion rate (%), category distribution doughnut chart, volume trend line chart, 5-row scrollable data viewports |
| **Live Control Room Map** | Full-Screen Leaflet View | Admin navigates to `/manage/live-map/` | Interactive map rendering color-coded pins for citizen pickups and live moving icons for active collectors |
| **Collector Route Navigation** | Leaflet Map / OSRM Polyline | Collector clicks "View Route" on active job | Turn-by-turn road driving path, route distance in km, estimated travel duration in minutes |
| **Citizen Tracking View** | Leaflet Map / WebSocket Push | Citizen views active pickup detail | Live moving collector vehicle icon updating dynamically as collector moves towards citizen home |
| **Official Tax Invoice** | Printable HTML / PDF View | Citizen or Admin clicks "View Invoice" | Formatted tax invoice detailing invoice number, user pickup ID, base charges, excess fees, CGST (9%), SGST (9%), total paid, and transaction reference |
| **Payment Receipt View** | Web HTML Modal | Successful payment completion | Visual success confirmation, transaction ID, payment method badge, and link to invoice |
| **Operations Report** | Web HTML Table | Admin views `/manage/reports/operations/` | Tabular breakdown of collection metrics, category volumes, operator payout totals, and profit margins |
| **Anonymous Feedback Box** | Web HTML Table | Admin clicks Feedback Box in Control Center | Filterable list of suggestions, bugs, and feedback with modal review actions |
| **Pickups CSV Export** | Downloadable `.csv` file | Admin clicks "Export Pickups CSV" | Direct stream containing ID, User Pickup Number, Citizen, Collector, Category, Weights, Fees, Status, and Timestamp |
| **Revenue CSV Export** | Downloadable `.csv` file | Admin clicks "Export Revenue CSV" | Direct stream containing Transaction ID, User, Amount, Payment Method, Status, and Timestamp |
| **In-App Notifications** | HTML Dropdown & List | System events (pickup assigned, paid, verified) | Notification records with title, message body, read status, and direct detail links |
| **AI Chat Responses** | WebSocket JSON / Markdown Bubble | Citizen sends text message in chat widget | Conversational answers, dynamic chips for slot-filling, action confirmations (e.g. cancellation success) |

---

# CHAPTER 7: SYSTEM IMPLEMENTATION

### 7.1 Architectural Pattern & Tech Stack
TrashPort is built upon the **Model-View-Template (MVT)** and **Layered Service-Oriented Architecture (SOA)**, coupled with an asynchronous event-driven layer:
- **Presentation Layer**: Django Templates rendered using Tailwind CSS, Bootstrap 5 (django-crispy-forms), Leaflet.js 1.9 for mapping, and Chart.js for data visualization.
- **Application / Controller Layer**: Standard Django Class-Based Views (CBVs) for UI routing, Django REST Framework (DRF) Viewsets for RESTful APIs, and Daphne ASGI Consumers for WebSockets.
- **Service & Domain Layer**: Isolated service classes (`PaymentGatewayService`, `WalletService`, `GeoService`, `DispatchScheduler`, `GroqLLMClient`) separating business and algorithmic logic from HTTP request handling.
- **Persistence Layer**: Object-Relational Mapping (ORM) powered by PostgreSQL 16 (production/Docker) or SQLite (testing), managed with Django migrations.
- **Caching & Message Broker**: Redis 6/8 providing channel layers for WebSockets, caching for OSRM route queries, and rate-limiting counters.

```
+-------------------------------------------------------------------------+
|                       CLIENT TIER (Browser / Mobile)                    |
|       Tailwind CSS | Bootstrap 5 | Leaflet.js | Chart.js | WebSockets   |
+-------------------------------------------------------------------------+
                                    |
                    HTTP / HTTPS    |    WSS (WebSockets)
                                    v
+-------------------------------------------------------------------------+
|                  ASGI SERVER LAYER (Daphne / Django 6.0)                |
|       ProtocolTypeRouter -> URLRouter -> AuthMiddlewareStack            |
+-------------------------------------------------------------------------+
          |                                                 |
          v                                                 v
+-----------------------------------+             +-----------------------+
|        HTTP / REST CONTROLLERS    |             |   WEBSOCKET CONSUMERS |
|   - Class-Based Views (MVT)       |             |   - ChatbotConsumer   |
|   - DRF ViewSets (api_router)     |             |   - LiveTrackingCons. |
+-----------------------------------+             +-----------------------+
          |                                                 |
          +------------------------+------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                         SERVICE & ALGORITHM LAYER                       |
|   - GeoService (Haversine & Project OSRM Turn-by-Turn Routing)          |
|   - DispatchScheduler (Nearest, Least-Busy, Zone-Based Algorithms)      |
|   - PaymentGatewayService (Card Simulation, UPI, Wallet Redemption)     |
|   - GroqLLMClient & IntentClassifier (Chatbot Slot-Filling Engine)      |
+-------------------------------------------------------------------------+
          |                                                 |
          v                                                 v
+-----------------------------------+             +-----------------------+
|      PERSISTENCE (PostgreSQL 16)  |             |      CACHE / BROKER   |
|   - Users, Addresses, Pickups     |             |      (Redis 6/8)      |
|   - Complaints, Feedback          |             |   - Channel Layers    |
|   - Transactions, DispatchBatches |             |   - OSRM Route Cache  |
+-----------------------------------+             +-----------------------+
```

### 7.2 Key Libraries & Frameworks
1. **Django 6.0**: High-level web framework providing the ORM, authentication, template rendering, and security middleware.
2. **Django Channels 4.3 & Daphne 4.2**: ASGI implementation enabling persistent WebSocket connections for live driver tracking and conversational streaming.
3. **Django REST Framework (DRF) 3.17 & drf-spectacular 0.30**: Automated OpenAPI 3.0 documentation and REST endpoints for mobile/third-party clients.
4. **django-allauth 65.18**: Robust authentication suite handling password resets, email verification, and social identity federation.
5. **google-auth-oauthlib 1.4**: Server-side Google OAuth 2.0 flow implementation.
6. **firebase-admin 7.5**: Verification of Firebase JWT tokens for mobile cross-platform authentication.
7. **Redis 8.0 & django-redis 7.0**: High-throughput in-memory data store for caching geospatial polyline computations and managing Channel Layer message backplanes.
8. **Requests 2.34**: HTTP client used for querying Project OSRM routing endpoints and exchanging Google OAuth tokens.

### 7.3 Deployment & Container Setup
- **Docker Compose Configuration** (`docker-compose.local.yml` / `docker-compose.yml`):
  - `django`: Multi-stage build based on `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`, running under Daphne on port `8001:8001` with hot-reloading code mounts.
  - `postgres`: PostgreSQL 16 container mounting persistent volume `trashport_local_postgres_data` on port `5432:5432`.
  - `redis`: `redis:7-alpine` running on port `6379:6379`.
- **Environment Management**: Consolidated `.env` file specifying database credentials, Redis URLs, Groq API keys, and email SMTP parameters.

### 7.4 Codebase Directory Structure
*(See Section: PROJECT STRUCTURE above)*

---

# CHAPTER 8: FUTURE ENHANCEMENTS

> [!NOTE]
> *Academic Disclaimer: The following recommendations are inferred from code comments, stubbed methods, architecture gaps, and future project opportunities. This section requires the student's personal review and final judgment.*

1. **Hardware IoT Smart Bin Telemetry**:
   - *Code Evidence*: The landing page (`pages/home.html`) references "Hardware Sensors", but no IoT model currently exists.
   - *Enhancement*: Introduce an `IoTBin` model communicating via MQTT/CoAP to report real-time fill levels (ultrasonic sensor readings) and battery health, automatically triggering pickup requests when capacity exceeds 80%.
2. **Real Production Payment Gateway Integration**:
   - *Code Evidence*: `PaymentGatewayService` in `trashport/payments/services.py` uses a dummy card catalog (`DUMMY_CARDS`) and mock UPI IDs.
   - *Enhancement*: Implement live production integrations with Razorpay, Cashfree, or Stripe Payment Intents using secure server-side webhook signatures for actual automated bank reconciliation.
3. **Automated Optical Character Recognition (OCR) for KYC Verification**:
   - *Code Evidence*: Collector verification in `CollectorVerificationView` requires manual Administrator approval of license numbers.
   - *Enhancement*: Integrate computer vision models (e.g. Tesseract or Google Cloud Vision API) to extract and verify driving license IDs and vehicle registration plates automatically upon registration.
4. **Multi-Stop Vehicle Routing Problem (VRP) Optimization**:
   - *Code Evidence*: `GeoService.get_optimized_route` uses a greedy Nearest Neighbor heuristic.
   - *Enhancement*: Replace the greedy algorithm with an advanced Genetic Algorithm or Google OR-Tools solver to solve the Capacitated Vehicle Routing Problem with Time Windows (CVRPTW), taking vehicle cargo capacity into account.
5. **Mobile Native Applications**:
   - *Code Evidence*: Complete REST API endpoints and OpenAPI schemas are generated via `drf-spectacular`, and Firebase authentication is configured.
   - *Enhancement*: Build native cross-platform mobile apps (using Flutter or React Native) for collectors and citizens consuming the existing DRF and WebSocket endpoints.

---

# CHAPTER 9: CONCLUSION

TrashPort was designed and implemented to solve systemic inefficiencies in urban solid waste management by uniting Citizens, Collectors, and Administrators on a unified, real-time web platform. By leveraging a modern tech stack comprising Django 6.0, Django Channels, PostgreSQL, Redis, Leaflet.js, and Groq LLMs, the platform successfully bridges the gap between waste generation, physical logistics, and transparent billing.

The system meets every objective established in the problem statement: citizens can easily schedule pickups with geospatial accuracy, access transparent automated pricing on a Pay-Per-Collection basis, track collectors in real time, and redeem recycling points. Collectors are equipped with Haversine-sorted job queues, turn-by-turn road navigation via OSRM, verified weight adjustment tools with excess surcharges, and direct UPI commission redemptions. Municipal administrators gain automated dispatch intelligence, live control room oversight, flexible payout rule configuration, and data export tools for auditability. TrashPort establishes an automated, scalable, and operationally viable blueprint for intelligent municipal waste management.

---

# ANNEXURE

### A. Screenshots Required for Report
The student should capture screenshots of the following distinct user interface screens found within the codebase:

1. **Public Web Portal**:
   - Home Landing Page (`trashport/templates/pages/home.html`)
   - About & Platform Overview Page (`trashport/templates/pages/about.html`)
2. **Authentication Screens**:
   - User Sign In Page (`trashport/templates/account/login.html`)
   - User Registration / Role Selection Page (`trashport/templates/account/signup.html`)
   - Password Reset Request Page (`trashport/templates/account/password_reset.html`)
3. **Citizen Module**:
   - Citizen Operations Dashboard (`trashport/citizens/templates/citizen/dashboard.html`)
   - Address Book & Map Picker (`trashport/citizens/templates/citizen/address_list.html`, `address_form.html`)
   - Waste Pickup Request Booking Form (`trashport/citizens/templates/citizen/pickup_form.html`)
   - Pickup Detail & Live Collector Tracking Map (`trashport/citizens/templates/citizen/pickup_detail.html`)
   - Payment Checkout Screen [Card / UPI / Wallet] (`trashport/citizens/templates/citizen/payment_checkout.html`)
   - Payment Success & Receipt Modal (`trashport/citizens/templates/citizen/payment_success.html`)
   - Official Tax Invoice Printable Document (`trashport/citizens/templates/citizen/invoice.html`)
   - Citizen Complaint Registration & History (`trashport/citizens/templates/citizen/complaint_list.html`, `complaint_form.html`)
4. **Collector Module**:
   - Collector Operations Dashboard with Nearby Opportunities Feed (`trashport/collectors/templates/collector/dashboard.html`)
   - Collector Job Detail, Turn-by-Turn OSRM Route & Scale Weight Verification Form (`trashport/collectors/templates/collector/pickup_detail.html`)
5. **Administrator Module**:
   - Administrative Metrics Dashboard with Chart.js Graphs and 5-Row Data Scrollboxes (`trashport/admins/templates/admin/dashboard.html`)
   - Control Room Real-Time Map Overview (`trashport/admins/templates/admin/live_map.html`)
   - User Administration & Collector KYC Verification Table (`trashport/admins/templates/admin/user_list.html`, `user_detail.html`)
   - Waste Category Master Form & Pricing List (`trashport/admins/templates/admin/category_list.html`, `category_form.html`)
   - Collector Payout Rates Configuration Form (`trashport/admins/templates/admin/payout_setting_form.html`)
   - Anonymous Feedback Box Review Interface (`trashport/admins/templates/admin/feedback_list.html`)
   - Operations Analytics & Financial Summary Report (`trashport/admins/templates/admin/operations_report.html`)
   - Complaint Resolution Interface (`trashport/admins/templates/admin/complaint_detail.html`)
6. **AI Conversational Assistant**:
   - Floating Chatbot Widget with Thinking Indicators and Action Buttons (`trashport/templates/partials/_chatbot_widget.html`)

---

### B. Ethical Clearance Form
*Not derivable from code — manual document required.*
*(This form must be obtained from your academic department/institution and completed with project advisor signatures prior to thesis submission.)*
