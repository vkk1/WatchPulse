# WatchPulse

WatchPulse is a data-driven platform that estimates luxury watch wait times and tracks real-world market prices for a single brand (e.g., Rolex or Patek).

It ingests secondary-market listing data daily, computes model-level statistics (median price, premium over MSRP, scarcity signals), and produces a **Wait-Time Index** with an estimated wait band.

For each watch model, WatchPulse provides:

* Current median market price
* Premium over MSRP
* Historical price trend
* Wait-Time Index (0–1 score)
* Estimated wait band (0–6 months → 5–8+ years)

Wait times are derived from observable market signals and are not official authorized dealer waitlists.

---

## Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The API will run at:

```
http://127.0.0.1:8000
```

---

### 2. Run Ingestion

```bash
python -m app.ingest.run_ingest --brand rolex --date YYYY-MM-DD
```

This command:

* Pulls listing data
* Computes daily model statistics
* Updates the Wait-Time Index

The ingestion process is idempotent (safe to re-run for the same date).

---

### 3. Frontend

Open directly:

```
frontend/index.html
```

Or serve locally:

```bash
cd frontend
python -m http.server 8000
```

Then visit:

```
http://localhost:8000
```

---

### 4. Run Tests

```bash
pytest
```

---

WatchPulse focuses on clean system design, reproducible daily stats, and transparent wait-time estimation using measurable market signals.
