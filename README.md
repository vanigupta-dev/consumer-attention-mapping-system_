# Consumer Attention Mapping System

An enterprise analytics and computer vision framework for processing, analyzing, and tracking consumer attention dynamics and visual engagement metrics across targeted touchpoints.

## Core Engineering Tasks
* **Attention Extraction Infrastructure:** Developed and improved deep learning models to map users’ attention sequences, frame telemetry, and spatial dwell times.
* **Pipeline Optimization:** Built modular, async FastAPI scripts to consume structural datasets and streaming feeds with optimized latency overheads.
* **Fault-Tolerant Video Engine:** Engineered an isolated multi-threaded OpenCV video pipeline (`video.py`) featuring dynamic failover mechanisms between local asset files, live webcams, and RTSP CCTV feeds.
* **Database & Schema Synchronization:** Implemented SQLAlchemy ORM models mapped to a PostgreSQL backend with strict Pydantic runtime schema validation.
* **Environment Configuration:** Containerization and dynamic environment management (`config.py`) to mimic enterprise runtimes and prevent hardcoded credential leaks.

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
       [ Live Interactive Dashboard ]
      (Swagger UI / WebSockets Pushes)
