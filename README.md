# Consumer Attention Mapping System

An enterprise analytics and computer vision framework for processing, analyzing, and tracking consumer attention dynamics and visual engagement metrics across targeted touchpoints. The platform combines real-time video intelligence with role-based dashboards to help retail teams optimize shelf placement, product visibility, and campaign performance.

## Core Engineering Tasks

* **Attention Extraction Infrastructure:** Developed and improved deep learning models to map users' attention sequences, frame telemetry, and spatial dwell times.
* **Pipeline Optimization:** Built modular, async FastAPI scripts to consume structural datasets and streaming feeds with optimized latency overheads.
* **Fault-Tolerant Video Engine:** Engineered an isolated multi-threaded OpenCV video pipeline (`video.py`) featuring dynamic failover mechanisms between local asset files, live webcams, and RTSP CCTV feeds.
* **Database & Schema Synchronization:** Implemented SQLAlchemy ORM models mapped to a PostgreSQL backend with strict Pydantic runtime schema validation.
* **API Gateway & Service Routing:** Built a centralized FastAPI gateway (`api_gateway/main.py`) handling authentication, request routing to backend microservices, and CORS policy enforcement across the platform.
* **Role-Based Reporting Engine:** Implemented a dynamic PDF export system (ReportLab) that generates role-scoped analytical reports — Store Manager, Retail Analyst, and Marketing Manager each receive only the data relevant to their function.
* **Environment Configuration:** Containerization and dynamic environment management (`config.py`, Docker Compose) to mimic enterprise runtimes and prevent hardcoded credential leaks.

---

## Roles & Access

The platform enforces role-based access control across dashboards and exported reports:

| Role | Dashboard Focus |
|---|---|
| **Store Manager** | Floor heatmaps, shelf zone attention rates, footfall status, inventory/misplacement alerts |
| **Retail Analyst** | Product attractiveness scoring, gaze counts, cross-merchandising strategy recommendations |
| **Marketing Manager** | Campaign A/B visual saliency scores, dwell duration, demographic engagement impact |
| **Administrator** | User management, platform analytics, camera management, system monitoring |

Each role's PDF export (`/api/analytics/export/pdf?role=<role>`) is scoped to show only that role's relevant tables and metrics.

---

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy, Pydantic
**Frontend:** JavaScript, React.js
**Databases:** PostgreSQL (primary), MongoDB (secondary)
**Computer Vision & AI:** YOLOv8, OpenCV, MediaPipe, PyTorch
**Reporting & Export:** ReportLab (PDF), openpyxl (Excel)
**Infrastructure:** Docker, Docker Compose, JWT Authentication

---

## Workspace Contributor

To maintain strict project workflows and team branch boundaries, this workspace represents isolated feature tracking for:

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/vanigupta-dev">
        <img src="https://github.com/vanigupta-dev.png" width="90px;" alt="Vani Gupta"/>
        <br /><sub><b>Vani Gupta</b></sub>
      </a>
      <br /> AI Intern
    </td>
  </tr>
</table>

_All functional commits, pipeline files, and architectural modifications are only present in the tracking logs of the `Vani_G` development branch._

---

## Architectural Data Flow

```text
       [ Video Ingestion Engine ]
  (Local MP4 / Live Webcam / RTSP CCTV)
                 │
                 ▼
       [ app/services/video.py ]
   (OpenCV Frame Capture & Threading)
                 │
                 ▼
       [ app/api/store.py ]
   (Pydantic Telemetry Validation)
                 │
                 ▼
       [ app/core/db.py & models.py ]
   (SQLAlchemy ORM -> PostgreSQL Warehouse)
                 │
                 ▼
       [ API Gateway (api_gateway/main.py) ]
   (Auth Routing, CORS, Role-Based PDF/Excel Export)
                 │
                 ▼
       [ Live Interactive Dashboard ]
   (React Frontend / Swagger UI / WebSocket Pushes)
```

### Service Ports (Docker Compose)

| Service | Port | Role |
|---|---|---|
| `frontend` | 5173 | React dashboard UI |
| `api_gateway` | 8000 | Public-facing gateway — auth, routing, PDF export |
| `backend` | 8008 | Core services — video processing, store/shelf management |
| `postgres` | 5432 | Primary relational database |
