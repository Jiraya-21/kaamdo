# KaamDo System Architecture

## 1. Architectural Philosophy

KaamDo is designed with a **decoupled, modular monolith** architecture:
- **Decoupled**: The client interface (HTML, CSS, Vanilla JS) is completely separated from the server application. The frontend communicates with the server strictly via standard JSON REST APIs.
- **Modular Monolith**: The backend is organized into distinct Django applications based on domain boundaries (`accounts`, `workers`, `jobs`, `equipment`, `reviews`, `notifications`). This ensures clean boundaries while avoiding the complexity, latency, and maintenance overhead of premature microservices.
- **Beginner-Friendly & Maintainable**: Standard Django conventions and native web standards are used. No complex bundlers, build steps, or heavyweight frameworks are required to run or understand the system.

---

## 2. System Component Diagram

```text
+--------------------------------------------------------------------------+
|                         CLIENT LAYER (Frontend)                         |
|                                                                          |
|   HTML5 Pages            CSS3 Styling             Vanilla JavaScript     |
|   - Homepage             - Design Tokens (main)   - Page Controllers     |
|   - Auth & Dashboard     - Components             - Central API Client   |
|   - Directory & Profile  - Responsive Layout      - Geolocation Helper   |
|   - Jobs & Equipment                              - Local Storage Sync   |
+--------------------------------------------------------------------------+
                                     |
                          JSON REST API (Fetch HTTP)
                                     v
+--------------------------------------------------------------------------+
|                         SERVER LAYER (Django Backend)                    |
|                                                                          |
|   config/urls.py (Master API Router: /api/v1/...)                        |
|                                                                          |
|   +---------------+ +---------------+ +---------------+                  |
|   |   accounts    | |    workers    | |     jobs      |                  |
|   |  - Auth/Roles | |  - Profiles   | |  - Postings   |                  |
|   |  - Permissions| |  - 20km Geo   | |  - Agreements |                  |
|   +---------------+ +---------------+ +---------------+                  |
|                                                                          |
|   +---------------+ +---------------+ +---------------+                  |
|   |   equipment   | |    reviews    | | notifications |                  |
|   |  - Machinery  | |  - Job-Linked | |  - In-App     |                  |
|   |  - Rentals    | |  - Moderation | |  - SMS Stubs  |                  |
|   +---------------+ +---------------+ +---------------+                  |
+--------------------------------------------------------------------------+
                                     |
                               ORM Interface
                                     v
+--------------------------------------------------------------------------+
|                          PERSISTENCE LAYER                               |
|                                                                          |
|   SQLite locally. PostgreSQL is optional and needs psycopg.          |
+--------------------------------------------------------------------------+
```

---

## 3. Data Flow & Communication Pattern

1. **User Action**: The user performs an action on the UI (e.g., filters workers within a 20 km radius).
2. **Page Controller**: The respective page controller (e.g., `workerDirectory.js`) gathers filter inputs and user coordinates.
3. **API Client**: The request is passed to `workersApi.js`, which invokes the centralized `apiClient.js`.
4. **Token Injection**: `apiClient.js` automatically attaches the active Authorization token from `localStorage` (if authenticated).
5. **Django Routing**: Django receives the request at `/api/v1/workers/?radius=20&lat=...&lng=...` and routes it to `workers.views`.
6. **Business Logic & Service**: The view validates inputs through DRF serializers, calls `workers.services` for distance calculations, and fetches matching records.
7. **JSON Response**: Serialized JSON data is returned with appropriate HTTP status codes (200, 201, 400, 401, 403, 404).
8. **UI Rendering**: The page controller receives the JSON response and updates the DOM using reusable template components.

---

## 4. Scalability & Extensibility Roadmap

The structure allows seamless future extensions without refactoring existing code:
- **Payment Processing**: A dedicated `payments` app can be plugged in to handle escrow or online transactions alongside the price agreement records.
- **External Identity Verification**: Can be integrated into `accounts/services.py` or `workers/services.py` (e.g., Aadhaar / National ID verification APIs).
- **Multilingual Support**: Can be implemented on the frontend via JSON locale dictionaries and on the backend via Django’s built-in `gettext` internationalization (i18n).
- **Real-Time WebSockets / SMS**: Django's ASGI entry point (`config/asgi.py`) and notifications service are structured to easily attach channels or SMS gateways (e.g., Twilio, Gupshup).
