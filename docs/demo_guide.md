# AYUSH EMR Terminology Microservice — Demonstration & Integration Guide

This guide provides a comprehensive 5–7 minute demonstration script, architectural references, environment setup, external dependency configurations, and system troubleshooting for the AYUSH EMR Terminology Microservice.

---

## 🚀 5–7 Minute Demonstration Script

### DEMO 1 — AI Search & 3-Tier Cascade (2 Minutes)

1. **Exact Search (Tier 1 Hash Lookup)**
   * **Action**: Open the EMR Clinician Search Widget and type `udAnavAtakopaH` or `jwara`.
   * **Observed Result**:
     * Instantaneous ($O(1)$) in-memory hash index hit.
     * Match method badge displays **`EXACT`**.
     * Displays `source_term`: `udAnavAtakopaH`, `display_name`: `vitiated udānavāyu`, `tm2_code`: `AAA-2.3`, `system`: `Ayurveda`.
     * `icd11_code` is returned as `null` (not fabricated, maintaining strict data integrity).

2. **Substring Search (Tier 2 SQL ILIKE)**
   * **Action**: Type `vitiated` or partial symptom text.
   * **Observed Result**:
     * Triggers SQL ILIKE query on PostgreSQL `concepts` table.
     * Match method badge displays **`SUBSTRING`**.

3. **Semantic Vector Search & XAI Token Attention (Tier 3 BioBERT + pgvector)**
   * **Action**: Type a non-exact symptom description such as `feeling hot with fever and shivering`.
   * **Observed Result**:
     * Triggers BioBERT dense vector embedding search against PostgreSQL pgvector HNSW index (`vector_cosine_ops`).
     * Match method badge displays **`SEMANTIC`** with cosine similarity score (e.g. `85.4%`).
     * **XAI Token Highlight Box**: Renders token-level attention weights (`feeling`, `fever`, `shivering`) with visual alpha intensity scaling.
     * Displays explicit non-causal disclaimer: *"Attention / relevance visualization — reflects model feature weighting, not causal medical explanation."*

---

### DEMO 2 — Dual-Code Validation, FHIR Bundles & NHCX Claims (2.5 Minutes)

1. **Concept Selection & FHIR R4 Bundle Assembly**
   * **Action**: Click a terminology search result card (e.g., `jwara` / `TM2-001`).
   * **Observed Result**: Active Selection banner updates. The Bundle Submitter auto-constructs valid FHIR R4 `Condition` and `Bundle` resources.

2. **Invalid Code Combination & ICD-11 Structure Rule Check**
   * **Action**: In the Practitioner Code Override field, enter an invalid code format such as `INVALID-PREFIX-999` and click **Submit FHIR Bundle to Backend**.
   * **Observed Result**:
     * Backend returns **`422 Unprocessable Entity`**.
     * Rule violation details display Rule ID `DEV-ICD11-001`: *"TM2 code does not start with a recognised prefix (TM2- or AAA-)."*
     * Remediation suggestion is provided.

3. **Code Correction & Resubmission**
   * **Action**: Update code override to valid TM2 code `TM2-001` and click **Submit FHIR Bundle to Backend**.
   * **Observed Result**:
     * Status updates to **`✓ Bundle Processed`** with unique Bundle UUID.
     * ICD-11 Validation status passes.
     * **Correction Log**: Practitioners override is appended to audit trail (`CORRECTION_SUBMITTED`) preserving original AI suggestions without overwriting.

4. **NHCX Claim Readiness Verification**
   * **Action**: Open NHCX Portal tab.
   * **Observed Result**:
     * Displays encounter ID, claim readiness status, readiness score ($0 - 100\%$), and rule failure explanations.
     * Selecting **Remediate** opens `ClaimFixer` to update system URIs or codes and re-submit for live re-validation.

---

### DEMO 3 — Ministry Public Health Analytics (1.5 Minutes)

1. **District Morbidity Density Heatmap**
   * **Action**: Open Ministry Analytics Dashboard $\rightarrow$ **District Morbidity Heatmap**.
   * **Observed Result**: Visualizes state/district encounter density and top AYUSH system per district (e.g., Central Delhi: Ayurveda, Chennai: Siddha, Lucknow: Unani).
   * **Provenance Tag**: Displays **`PROVENANCE: DEMO / SYNTHETIC`** badge when database contains demo/synthetic records.

2. **Empirical Conditional Probability Table**
   * **Action**: Switch tab to **Co-occurrence Probability Table**.
   * **Observed Result**: Displays joint co-occurrences of traditional patterns and biomedical diagnoses, calculating:
     $$P(\text{biomedical diagnosis} \mid \text{traditional pattern}) = \frac{\text{Count}(\text{joint})}{\text{Count}(\text{traditional pattern})}$$

3. **30-Day Clinical Encounter Volume Trends**
   * **Action**: Switch tab to **30-Day Encounter Trends**.
   * **Observed Result**: Visualizes daily clinical encounter volume broken down by AYUSH coding system over the past 30 days.

---

## 🛠 Startup & Test Commands

### 1. Run via Docker Compose (Recommended)

```bash
# 1. Validate Docker Compose syntax
docker compose config

# 2. Build images
docker compose build

# 3. Launch PostgreSQL + pgvector, FastAPI Backend & React Frontend
docker compose up -d

# Check running containers
docker compose ps
```

* **React EMR Consumer**: [http://localhost:5173](http://localhost:5173)
* **FastAPI Backend Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Run Locally without Docker

```bash
# Backend Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000

# Frontend Setup
cd frontend
npm install
npm run dev
```

### 3. Run Complete Test Suite

```bash
# Run all backend pytest tests (197 tests)
python -m pytest --tb=short

# Run all frontend Vitest tests (12 tests)
cd frontend
npm test

# Run frontend production build
npm run build
```

---

## 🔑 Environment Variables Reference

| Variable | Default Value | Description |
|---|---|---|
| `APP_NAME` | `AYUSH EMR Terminology Microservice` | Microservice title |
| `APP_ENV` | `development` | `development`, `staging`, or `production` |
| `DATABASE_URL` | `postgresql://ayush_user:ayush_password@db:5432/ayush_terminology_db` | PostgreSQL connection string |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` | CORS allowed origins |
| `ABHA_INTROSPECT_URL` | `""` (empty) | ABHA OAuth introspection URL. Empty triggers `MockABHAProvider`. |
| `ABHA_CLIENT_ID` | `""` | ABHA production Client ID |
| `ABHA_CLIENT_SECRET` | `""` | ABHA production Client Secret |
| `WHO_USE_MOCK` | `true` | `true` uses `MockWHOProvider`; `false` connects to live WHO ICD-11 API |
| `WHO_API_URL` | `https://id.who.int/icd/release/11/mms` | WHO ICD-11 MMS REST base URL |
| `WHO_TOKEN_URL` | `https://icdaccessmanagement.who.int/connect/token` | WHO OAuth 2.0 token URL |
| `WHO_CLIENT_ID` | `""` | WHO API Client ID |
| `WHO_CLIENT_SECRET` | `""` | WHO API Client Secret |
| `ICD11_RULES_PATH` | `""` (default dev rules) | Path to JSON ICD-11 structure rule file |
| `NHCX_RULES_PATH` | `""` (default dev rules) | Path to JSON NHCX payer rule file |

---

## 🏛 Real vs Synthetic Components

| Component | Status | Description |
|---|---|---|
| **Raw Dataset (NAMASTE)** | **REAL** | Ingested directly from real source terminology CSV (`term`, `english`, `tm2_code`, `system`). |
| **Hash & Substring Search** | **REAL** | Built on real dataset records ($O(1)$ in-memory hash + PostgreSQL ILIKE). |
| **BioBERT Vector Encoder** | **REAL / MOCK OPTION** | Real `dmis-lab/biobert-v1.1` encoder with fallback to `MockBioBERTEncoder` in CI/testing. |
| **Audit Logger** | **REAL** | Append-only PostgreSQL logging with immutability guarantees. |
| **PBAC Engine** | **REAL** | Role-based policy enforcement (`doctor`, `insurance_clerk`, `researcher`, `admin`). |
| **Offline Snapshot & WASM** | **REAL** | Portable SQLite generator + row SHA-256 checksums + WASM reference search engine. |
| **ICD-11 & NHCX Rules** | **DEV / TEST** | Structured rule trees clearly labelled as development/test rules until official regulatory rule files are mounted. |
| **Public Health Data** | **DEMO / SYNTHETIC** | Aggregates return synthetic demo data with explicit provenance tags when live hospital records are absent. |

---

## ⚠️ Known Limitations & Troubleshooting

1. **PostgreSQL Driver on Windows**:
   * If `psycopg2` or `pgvector` binaries are missing in an isolated local Python environment, `db/session.py` gracefully falls back to in-memory SQLite for unit tests.
2. **BioBERT Torch Installation**:
   * Downloading full PyTorch BioBERT weights requires ~1.5 GB. Set `BIOBERT_USE_MOCK=true` or use `MockBioBERTEncoder` for instant startup without GPU/weights.
3. **ABHA / WHO Credentials**:
   * Production credentials for ABHA OAuth and WHO ICD-11 require registration with ABDM (India) and WHO. In the absence of production keys, `MockABHAProvider` and `MockWHOProvider` supply fully functional mock authentication and Flexisearch fallbacks.
