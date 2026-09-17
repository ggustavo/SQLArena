# SQLArena - End-to-End Testing Guide

This guide provides instructions for setting up the local AWS environment (Ministack), running the FastAPI backend service and the asynchronous evaluation worker, and executing end-to-end integration tests.

---

## Prerequisites

- **Docker** and **Docker Compose** installed and running.
- **Python 3.10+** installed.
- Three terminal windows/tabs for concurrent execution.

---

## Step 1: Start and Provision Local Infrastructure (Ministack)

Ministack emulates AWS services on port `4566`: S3, SQS, DynamoDB, RDS (PostgreSQL), and ElastiCache (Redis).

From the repository root, in **Terminal 1**:

```bash
# Navigate to the ministack directory
cd ministack

# Start the Ministack container
docker compose up -d

# Provision the PostgreSQL (port 15432) and Redis (port 16379) containers
python setup_all.py
```

Allow a few seconds for the spawned Docker containers to complete their startup routines.

---

## Step 2: Configure the Backend Environment

In **Terminal 2**:

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
# On Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# On Windows:
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3: Start the FastAPI Application

In **Terminal 2** (with the virtual environment activated):

```bash
uvicorn api.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Documentation (Swagger UI): `http://localhost:8000/docs`
- Healthcheck endpoint: `http://localhost:8000/health`

---

## Step 4: Start the Standalone Evaluation Worker

In **Terminal 3**:

```bash
# Navigate to the backend directory and activate the virtual environment
cd backend

# On Linux / macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# Start the worker process
python -m worker.main
```

The worker connects to the SQS queue (`sqlarena-submissions-queue`) and begins long-polling for student query submissions.

---

## Step 5: End-to-End Testing Scenarios

All endpoints can be exercised via the interactive Swagger UI at `http://localhost:8000/docs` or using `curl`.

### 5.1 Register and Authenticate a Teacher

1. Register a teacher account:

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "securePassword123",
    "role": "teacher"
  }'
```

2. Obtain a stateless JWT access token:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "securePassword123"
  }'
```

Copy the returned `access_token`.

---

### 5.2 Teacher Registers a SQL Exercise

Sample schema and data files are located in `backend/samples/`:
- `backend/samples/ddl_sample.sql` (defines `customers` and `orders` tables)
- `backend/samples/dml_sample.sql` (seeds rows into `customers` and `orders`)

Using `curl` from the repository root (replace `<TEACHER_TOKEN>` with the token from Step 5.1):

```bash
curl -X POST "http://localhost:8000/questions" \
  -H "Authorization: Bearer <TEACHER_TOKEN>" \
  -F "title=Top Customers by Spending" \
  -F "context=Calculate total purchase amounts per customer, ordered from highest to lowest." \
  -F "expected_query=SELECT c.name, SUM(o.amount) AS total FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name ORDER BY total DESC;" \
  -F "timeout_seconds=5" \
  -F "ddl_file=@backend/samples/ddl_sample.sql" \
  -F "dml_file=@backend/samples/dml_sample.sql"
```

Execution flow:
1. The API uploads both `.sql` scripts to S3.
2. A record is inserted into RDS 1 with status `creating_tables`.
3. A background task creates the isolated schema `question_1` in RDS 2, executes the DDL and batch DML, updates the question status to `ready` in RDS 1, and invalidates the Redis cache.

---

### 5.3 Register and Authenticate a Student

1. Register a student account:

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "securePassword123",
    "role": "student"
  }'
```

2. Authenticate as the student:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "securePassword123"
  }'
```

Copy the returned student `access_token`.

---

### 5.4 Student Views Catalog and Question Context (Cache-Aside Verification)

1. Fetch question catalog:

```bash
curl -X GET "http://localhost:8000/questions" \
  -H "Authorization: Bearer <STUDENT_TOKEN>"
```

- Initial request: Cache miss against Redis; reads from RDS 1 and populates Redis with a 300-second TTL.
- Subsequent requests: Cache hit served directly from Redis.

2. Fetch question context (omits `expected_query`):

```bash
curl -X GET "http://localhost:8000/questions/1" \
  -H "Authorization: Bearer <STUDENT_TOKEN>"
```

---

### 5.5 Student Submits a Correct Query (Full Match)

Submit the solution query:

```bash
curl -X POST "http://localhost:8000/questions/1/submit" \
  -H "Authorization: Bearer <STUDENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT c.name, SUM(o.amount) AS total FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name ORDER BY total DESC;"
  }'
```

Response: Returns HTTP `202 Accepted` with a `submission_id`.

In **Terminal 3 (Worker)**, observe the real-time processing:
1. The message is consumed from SQS.
2. The student query is executed in RDS 2 with `SET TRANSACTION READ ONLY;`, `SET statement_timeout = 5000;`, and `SET search_path TO question_1;`.
3. The result set is compared against the reference output.
4. Similarity evaluation produces: `Score: 100.00% (Status: SUCCESS)`.
5. An immutable audit record is written to DynamoDB.
6. The student's best score is updated in RDS 1.

---

### 5.6 Test Mandatory ORDER BY Enforcement

Submit a query matching the data but omitting the `ORDER BY` clause:

```bash
curl -X POST "http://localhost:8000/questions/1/submit" \
  -H "Authorization: Bearer <STUDENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT c.name, SUM(o.amount) AS total FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.name;"
  }'
```

In the Worker logs:
- The validator detects that the expected output contains multiple rows and that `ORDER BY` is missing.
- The 20% ordering weight is set to 0.0.
- The result receives a score of 80.00% and status `WRONG_RESULT`.

---

### 5.7 Inspect Student Consolidated Score

Retrieve the student's highest scores from RDS 1:

```bash
curl -X GET "http://localhost:8000/scores/me" \
  -H "Authorization: Bearer <STUDENT_TOKEN>"
```

Expected output:

```json
[
  {
    "question_id": 1,
    "best_score": 100.0,
    "updated_at": "..."
  }
]
```
