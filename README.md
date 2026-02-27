# 🔗 ShrinKit

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)

A high-performance, full-stack URL shortening service engineered with production-level reliability and scalability in mind. Moving beyond a simple tutorial implementation, this system showcases modern backend engineering patterns including collision-safe concurrency, database normalization, and asynchronous observability.

---

## 🚀 Technical Highlights

* **Collision-Safe Shortening**: Implements optimistic concurrency with recursive retry loops and database-level unique constraints to manage billion-plus code combinations safely.
* **Idempotent Link Generation**: Prevents database bloat by returning existing short codes for duplicate URL submissions.
* **Custom Aliases & Normalization**: Supports user-defined vanity URLs with strict regex validation, reserved path blocking, and case-normalization.
* **Asynchronous Analytics**: Captures detailed visit metadata (IP, User-Agent, Referrer) using FastAPI Background Tasks to ensure analytics logging never increases redirection latency.
* **Optimized Redirection**: Leverages B-Tree indexing on short-code columns to maintain sub-50ms performance.
* **Service Protection**: Integrated rate limiting (SlowAPI) and health-check monitoring to protect against abuse.

---

## 🏗️ System Architecture

The application follows a decoupled client-server architecture. The backend acts as a high-throughput redirection engine and analytics ingestion API.

---

## 🗄️ Database Schema

The database is normalized into two primary tables to separate static link data from high-volume, time-series visit events.

### `urls` (Link Metadata)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | BIGINT | Primary Key |
| `short_code` | VARCHAR | Indexed, Unique (3-20 chars) |
| `original_url` | TEXT | The destination URL |
| `clicks` | INTEGER | Fast-read total click counter |
| `expires_at` | TIMESTAMPTZ | Automated link expiration logic |

### `url_visits` (Time-Series Analytics)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | BIGINT | Primary Key |
| `url_id` | BIGINT | Foreign Key -> `urls(id)` |
| `visited_at` | TIMESTAMPTZ | Timestamp of the click |
| `referrer` | TEXT | HTTP Referrer for traffic sources |

---

## 📡 API Request Flow

### Core Endpoints

#### `POST /shorten`
Generates a new short link or custom alias.

**Request**
```json
{
  "url": "https://example.com",
  "custom_code": "my-portfolio"
}

```

**Response (201 Created)**

```json
{
  "short_url": "http://localhost:8000/my-portfolio",
  "code": "my-portfolio",
  "created_at": "2026-02-24T12:00:00Z",
  "expires_at": "2026-03-26T12:00:00Z"
}

```

---

## 💻 Local Setup & Installation

### Prerequisites

* **Python 3.9+** installed on your machine.
* A **PostgreSQL** database (this project uses [Supabase](https://supabase.com/)).
* **Git** for version control.

### Step-by-Step Guide

**1. Clone the repository**

```bash
git clone https://github.com/yourusername/production-url-shortener.git
cd production-url-shortener

```

**2. Create and activate a virtual environment**

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

```

**3. Install dependencies**

```bash
pip install -r requirements.txt

```

**4. Configure Environment Variables**
Create a `.env` file in the root directory and add your Supabase connection string and base URL:

```env
DATABASE_URL=postgresql://postgres.your_project_ref:your_password@aws-0-region.pooler.supabase.com:6543/postgres
BASE_URL=http://127.0.0.1:8000
APP_NAME="APP_name"

```

**5. Run the server**

```bash
uvicorn main:app --reload

