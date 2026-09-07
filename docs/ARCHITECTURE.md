# MedAlly - System Architecture & Technical Design

MedAlly is a cross-platform medication tracking system designed specifically to bridge the gap between caregivers and elderly family members. It prioritizes zero-friction adoption for older users via a unique code-based login while providing robust management tools for caregivers.

---

## 1. High-Level Architecture

The system follows a decoupled client-server architecture:
* **Frontend (Client)**: Built with **Flutter** (Dart) supporting cross-platform deployment (Android/iOS).
* **Backend (Server)**: Built with **FastAPI** (Python), providing asynchronous routing, data validation via Pydantic, and ORM mapping via SQLAlchemy.
* **Data Layer**: **SQLite** for lightweight, reliable relational data storage during local development and MVP phase.


┌─────────────────────────┐               ┌─────────────────────────┐
│     Flutter Mobile      │               │     FastAPI Backend     │
│  (Caregiver & Patient   │ ──HTTP/REST─> │   (Python, SQLAlchemy,  │
│        Dashboards)      │ <──JSON────── │         SQLite)         │
└─────────────────────────┘               └─────────────────────────┘

---

## 2. Core Authentication Models

MedAlly implements a dual-authentication pattern tailored to user technical literacy:

1. **Caregiver Authentication (Traditional)**:
   * Standard Email and Password registration/login.
   * Caregivers manage their profiles, view linked family members, and generate access codes.

2. **Patient Authentication ("Magic Code" / Frictionless)**:
   * Designed for elderly users who struggle with passwords, usernames, or app registration.
   * Caregivers generate a unique 4-digit alphanumeric code for the patient.
   * The patient inputs this code once to securely bind their device. Local session state is managed via Flutter's `shared_preferences` to ensure they stay logged in without needing to re-enter the code.

---

## 3. API Contract Reference

| Endpoint | Method | Description | Payload / Parameters |
| :--- | :--- | :--- | :--- |
| `/auth/register-caregiver` | `POST` | Registers a new caregiver account | `{"name": "...", "email": "...", "password": "..."}` |
| `/auth/login-caregiver` | `POST` | Authenticates a caregiver | `{"email": "...", "password": "..."}` |
| `/auth/patient-code-login` | `POST` | Logs in patient via 4-digit code | `{"access_code": "..."}` |
| `/patients/add` | `POST` | Adds a family member & generates code | `{"name": "...", "caregiver_id": int}` |
| `/users/family/{id}` | `GET` | Fetches all patients linked to caregiver | Path parameter: `caregiver_id` |
| `/medications` | `POST` | Schedules a new medication | `{"patient_id": int, "medicine_name": "...", "dosage": "...", "schedule_time": "..."}` |
| `/medications/{id}` | `GET` | Fetches active medications for patient | Path parameter: `patient_id` |

---

## 4. Environment Strategy & Roadmap

* **Current State (Local Development)**:
  * Backend runs locally via `uvicorn` on `0.0.0.0:8000`.
  * Android emulator communicates with the host machine using the loopback alias `10.0.2.2:8000`.
  * SQLite database stored locally.
* **Production Roadmap**:
  * Migrate backend hosting to a cloud platform (e.g., Render, Fly.io, or Railway).
  * Transition from local SQLite to a managed PostgreSQL instance or persistent volume.
  * Update API base URL in Flutter app configuration dynamically based on environment flags.