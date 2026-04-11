# CertiChain — Backend Setup Guide

> FastAPI + Neon PostgreSQL backend for the CertiChain frontend.  
> Fake-blockchain UX, real database persistence, real SHA-256 hashing.

---

## What this gives you

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python) |
| Database | Neon (serverless PostgreSQL) |
| Auth | JWT tokens (PyJWT) |
| Hashing | SHA-256 via Python `hashlib` |
| "Blockchain" | Simulated Polygon Mainnet receipts |

---

## File structure

```
your-project/
├── frontend/                  ← your existing HTML files (unchanged)
│   ├── index.html
│   ├── student.html
│   ├── university.html
│   ├── employer.html
│   ├── university-issue.html
│   ├── university-revoke.html
│   ├── university-archive.html
│   ├── university-notifications.html
│   ├── university-template.html
│   ├── privacy.html
│   ├── terms.html
│   ├── registry.html
│   ├── shared.css
│   │
│   ├── app.js                 ← REPLACE with the new app.js from this folder
│   ├── student-login.html     ← NEW — add this to frontend/
│   └── university-login.html  ← NEW — add this to frontend/
│
└── backend/
    ├── main.py                ← FastAPI app
    ├── requirements.txt
    ├── .env.example           ← copy to .env and fill in
    └── .env                   ← your secrets (never commit)
```

---

## Step 1 — Set up Neon (free PostgreSQL)

1. Go to **https://neon.tech** and create a free account.
2. Create a new **Project** (name it `certichain`).
3. In the project dashboard, click **Connection Details**.
4. Copy the **Connection string** — it looks like:
   ```
   postgresql://alex:password@ep-cool-rain-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
5. Keep this tab open — you'll need it in Step 3.

---

## Step 2 — Install Python dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate it
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

---

## Step 3 — Configure environment variables

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` and fill in your values:

```env
DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=some-random-long-string-change-this
```

Replace the `DATABASE_URL` value with your Neon connection string from Step 1.

---

## Step 4 — Run the backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
✅ DB initialised
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The database tables are created automatically on first run.

**API docs** (auto-generated): http://localhost:8000/docs

---

## Step 5 — Connect the frontend

1. **Copy** `app.js` from this folder into your `frontend/` directory, **replacing** the old `app.js`.
2. **Copy** `student-login.html` and `university-login.html` into your `frontend/` directory.
3. Open `app.js` and confirm the API URL at the top:
   ```js
   const API = "http://localhost:8000";   // ← matches your backend port
   ```
4. Open `index.html` in your browser (or use Live Server in VS Code).

---

## Step 6 — Test the full flow

### University uploads credentials

1. Go to **university-login.html**
2. Login with: `registrar` / `admin123`
3. Navigate to **Issue** tab
4. Upload a CSV in this format (save as `graduates.csv`):

```csv
legal_name,student_id,program,degree_class,wallet_address,graduation_date
"Suyog Patil","ST-1001","Computer Science","B.Tech Hons","0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb","2024-05-15"
"Aaditya Sharma","ST-1002","Machine Learning","M.Tech","0x8f3d12Cc5541C0532811a2b933Bc8d6484f1cDa","2024-05-15"
```

5. Click **Queue for signing** — watch the fake blockchain receipt appear.

### Student views vault

1. Go to **student-login.html**
2. Login with: `suyog` / `123`
3. Your credentials appear (matched by name from the uploaded CSV).
4. Click the copy icon to copy a certificate hash.

### Employer verifies

1. Go to **employer.html**
2. Paste the hash you copied.
3. Click **Look Up** — see VERIFIED or REVOKED result.

### University revokes

1. Go to **university-login.html** → **Revoke** tab.
2. Click **Revoke** next to any credential.
3. Re-verify the same hash on employer.html — it now shows REVOKED.

---

## API endpoints reference

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/student/login` | None | Student login → JWT |
| POST | `/api/auth/university/login` | None | University login → JWT |
| POST | `/api/university/upload-csv` | University JWT | Upwards legacy CSV parsing, hash + store rows |
| GET | `/api/university/credentials` | University JWT | List issued credentials |
| POST | `/api/university/revoke` | University JWT | Set is_revoked = TRUE |
| GET | `/api/university/stats` | University JWT | Dashboard stats |
| GET | `/api/student/credentials` | Student JWT | Credentials for logged-in student |
| GET | `/api/credentials/student/{student_did}` | None | Fetches all credentials associated with a student UID including Merkle proofs and IPFS CID |
| GET | `/api/credentials/student/{student_did}/qrs` | None | Performs internal check and bakes validity status into a JSON QR payload |
| POST | `/api/credentials/batch/add` | None | Manually stages individual JSON credentials to Memory array |
| POST | `/api/credentials/batch/upload-csv` | None | Stages a batch CSV array into Memory |
| POST | `/api/credentials/batch/commit` | None | Aggregates tracking payload mapping Merkle tree securely onto chain |
| POST | `/api/credentials/verify-with-proof` | None | Validates chain credential hashes safely processing Proof parameters |
| GET | `/api/credentials/{batch_id}/{leaf_index}/share-link` | None | Generates automated URL verification parameter string for Employers |
| POST | `/api/verify` | None | Verify by hash (legacy public) |
| GET | `/api/verify/{hash}` | None | Verify by hash via GET |
| GET | `/api/health` | None | Health check |

---

## Predefined accounts

### Students
| Username | Password | Name |
|---|---|---|
| suyog | 123 | Suyog Patil |
| aaditya | 456 | Aaditya Sharma |
| priya | 789 | Priya Singh |
| rahul | 321 | Rahul Verma |
| ananya | 654 | Ananya Iyer |

### Universities
| Username | Password | Institution |
|---|---|---|
| registrar | admin123 | Sardar Patel Institute of Technology |
| spce_admin | spce2024 | SPCE Mumbai |

---

## Database schema

```sql
CREATE TABLE credentials (
    id              SERIAL PRIMARY KEY,
    hash            TEXT UNIQUE NOT NULL,        -- SHA-256 of student JSON
    student_data    JSONB NOT NULL,              -- full CSV row as JSON
    university      TEXT NOT NULL,               -- issuing institution name
    issued_by       TEXT NOT NULL,               -- registrar username
    issued_at       TIMESTAMPTZ DEFAULT NOW(),
    is_revoked      BOOLEAN DEFAULT FALSE,
    revoked_at      TIMESTAMPTZ,
    block_number    BIGINT,                      -- fake Polygon block
    tx_hash         TEXT,                        -- fake tx hash
    chain_id        INT DEFAULT 137,             -- 137 = Polygon Mainnet
    polygon_address TEXT                         -- fake contract address
);
```

---

## Frontend changes summary

### Files you need to update / add

| File | Action |
|---|---|
| `frontend/app.js` | **Replace** entirely with the new `app.js` |
| `frontend/student-login.html` | **Add** this new file |
| `frontend/university-login.html` | **Add** this new file |

### HTML files that need `data-*` attribute additions

The new `app.js` hooks into the existing HTML by:

- **`university-issue.html`** — Add these IDs to the existing elements:
  - Dropzone `<div>` → add `id="csv-dropzone"`
  - Add a hidden `<input type="file" id="csv-file-input" accept=".csv" class="hidden"/>`
  - "Queue for signing" `<button>` → add `id="queue-btn"`
  - Add `<div id="issue-result" hidden></div>` below the buttons

- **`university.html`** — Add these IDs to the stat numbers:
  - Total issued `<p>` → `id="stat-total"`
  - Anchored today `<p>` → `id="stat-today"`
  - Revoked `<p>` → `id="stat-revoked"`
  - Recent anchors `<ul>` → `id="recent-anchors"`

- **`university-revoke.html`** — Replace the static `<ul>` with:
  ```html
  <ul id="revoke-list" class="space-y-0"></ul>
  ```

- **`student.html`** — Add IDs:
  - Name header → `id="student-name"`
  - Wallet address span → `id="student-wallet"`
  - Credentials grid → `id="credentials-grid"`
  - Credential count `<p>` → `id="credential-count"`

- **All pages** — Add `data-logout` attribute to any logout buttons you add:
  ```html
  <button data-logout>Sign Out</button>
  ```

- **`employer.html`** — The verify button needs: find the "Look Up" button and the hash input — the script finds them automatically by matching text/placeholder.

---

## Deploying to production

### Backend (Railway / Render / Fly.io)

```bash
# Example for Railway
railway login
railway init
railway up
```

Set environment variables in your host's dashboard:
- `DATABASE_URL` → your Neon connection string
- `SECRET_KEY` → a long random string

### Frontend

Update `app.js` line 4:
```js
const API = "https://your-backend.railway.app";
```

Then deploy your `frontend/` folder to Netlify, Vercel, or GitHub Pages.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection refused` on API calls | Make sure `uvicorn` is running on port 8000 |
| CORS error in browser | Backend already allows all origins in dev. In prod, update `allow_origins` in `main.py` |
| `relation "credentials" does not exist` | The `init_db()` function runs on startup — check your `DATABASE_URL` is correct |
| Student sees no credentials | Make sure the CSV `legal_name` column value matches the student's `name` in `STUDENT_USERS` |
| `SSL SYSCALL error` from Neon | Neon requires `?sslmode=require` at the end of the connection string |

---

© 2026 CertiChain Ledger