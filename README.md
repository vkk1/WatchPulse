# WatchPulse

WatchPulse is a data-driven platform that estimates luxury watch scarcity and tracks real-world market prices for Rolex.

It ingests secondary-market listing data, computes model-level statistics (median price, premium over MSRP, scarcity signals), and produces a **Scarcity Index** with an estimated scarcity band.

For each watch model, WatchPulse provides:

- Current median market price
- Premium over MSRP
- Historical price trend
- Scarcity Index (0-1 score)
- Estimated scarcity band (0-6 months -> 5-8+ years)

Scarcity estimates are derived from observable market signals and are not official authorized-dealer waitlists.

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

```env
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

---

### 2. Run Ingestion

```bash
python -m app.ingest.run_ingest --brand rolex --date YYYY-MM-DD
```

This command:

- Pulls listing data
- Computes daily model statistics
- Updates the Scarcity Index

The ingestion process is idempotent (safe to re-run for the same date).

---

### 3. Frontend

Open directly:

```text
frontend/index.html
```

Or serve locally:

```bash
cd frontend
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000
```

---

### 4. Run Tests

```bash
pytest
```

---

WatchPulse focuses on clean system design, reproducible daily stats, and transparent scarcity estimation using measurable market signals.
