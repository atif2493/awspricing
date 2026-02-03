# awspricing — Detailed Documentation

**Version:** 1.0  
**Location:** `docs/` — extended project documentation.  
**Dependencies:** See root README. **Ports:** UI 3001, API 8000.

---

## Table of contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Pricing resolution](#3-pricing-resolution)
4. [Calculation logic](#4-calculation-logic)
5. [API reference](#5-api-reference)
6. [Configuration & credentials](#6-configuration--credentials)
7. [Container deployment](#7-container-deployment)
8. [Testing](#8-testing)
9. [Limitations & troubleshooting](#9-limitations--troubleshooting)

---

## 1. Overview

**awspricing** is a containerized FinOps-style web app that:

- Fetches **live pricing** from the AWS Pricing API (no hardcoded $/GB).
- Compares **AWS Backup for S3** storage costs vs **S3 storage with versioning** (modeled overhead).
- Provides **interactive inputs** (region, currency, TB conversion, preset/custom size, S3 class, versioning overhead, add-ons) and **table outputs** (preset 10–90 TB and scenario comparison).
- Exposes a **transparency footer** (region, currency, TB method, S3 class, add-ons, last refreshed, cache TTL) and **advanced pricing details** (matched SKU/terms).
- Supports **export** (copy tables to clipboard, download CSV).

All pricing is resolved server-side via the AWS Pricing API; the UI never uses hardcoded rates.

---

## 2. Architecture

### 2.1 High-level

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (localhost:3001)                                        │
│  React + Vite UI → /api/* proxied to backend                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (localhost:8000)                                        │
│  FastAPI → Pricing Resolver → AWS Pricing API (us-east-1)        │
│           Cost Engine (pure math)                                │
│           TTL Cache (24h default)                                │
└─────────────────────────────────────────────────────────────────┘
```

- **Frontend:** React + Vite + TypeScript. Build served by nginx in Docker; `/api` and `/health` proxied to the backend.
- **Backend:** FastAPI (Python). Calls AWS Pricing API (`GetProducts`), normalizes rates to USD/GB-month, caches responses. Cost math is in a pure module (unit tested).

### 2.2 Project layout

| Path | Purpose |
|------|--------|
| `docker-compose.yml` | Runs backend (8000) and frontend (3001→80). Optional `.env` for AWS creds. |
| `backend/` | FastAPI app, pricing resolver, region mapping, cost engine, cache. |
| `backend/app/main.py` | Routes: `/api/pricing/aws-backup`, `/api/pricing/s3-storage`, `/api/calc`, `/api/regions`, `/health`. |
| `backend/app/pricing_resolver.py` | `GetProducts` for AWS Backup and S3; normalizes to USD/GB-month; returns flat rate or tier bands + debug payload. |
| `backend/app/region_mapping.py` | Maps region codes (e.g. `us-east-1`) to Pricing API location strings. |
| `backend/app/cost_engine.py` | TB↔GB, versioning overhead, copy multiplier, tier band math. |
| `backend/app/cache.py` | In-memory TTL cache for pricing responses. |
| `frontend/src/App.tsx` | Main UI: inputs, Table A, Table B, transparency footer, export. |
| `frontend/src/api/client.ts` | API client for pricing and regions. |
| `frontend/src/lib/costEngine.ts` | Client-side cost math (mirrors backend). |
| `docs/README.md` | This detailed documentation. |

### 2.3 Data flow

1. User selects region, currency, S3 class, etc.
2. Frontend calls `GET /api/pricing/aws-backup` and `GET /api/pricing/s3-storage` (with optional `refresh=true` to bypass cache).
3. Backend uses **Pricing Resolver** to call AWS Pricing API, map region→location, normalize to USD/GB-month, optionally cache.
4. Frontend uses **Cost Engine** (client-side) with fetched rates to compute Table A (10–90 TB) and Table B (AWS Backup vs S3 Versioning).
5. Transparency footer and “Advanced pricing details” show region, TB method, add-ons, last refreshed, and matched SKU/terms.

---

## 3. Pricing resolution

### 3.1 Source

- **API:** AWS Pricing API `GetProducts`, called from the **us-east-1** endpoint (Pricing API is only available in `us-east-1` and `ap-south-1` for India).
- **Filtering:** By `location` (from region mapping), `productFamily`, and (for S3) `storageClass`. All returned rates are normalized to **USD per GB-Month**.

### 3.2 AWS Backup storage

- **Service:** `AWS Backup`.
- **Filters:** `productFamily=Storage`, `location=<mapped location>`.
- **Output:** Single flat rate (USD/GB-month). Resolver prefers OnDemand terms and validates unit (GB-Mo). Returns SKU, product attributes, term code, and price dimension for “Advanced pricing details”.

### 3.3 S3 storage

- **Service:** `Amazon S3`.
- **Filters:** `productFamily=Storage`, `location=<mapped location>`, `storageClass=<selected class>` (e.g. Standard, Standard-IA).
- **Output:** Either a **flat rate** or **tier bands** (from `beginRange`/`endRange` in price dimensions). Tier bands are sorted by `from_gb`; open-ended tiers use a large sentinel value for JSON compatibility.
- **Storage classes supported in UI:** Standard, Standard-IA, Intelligent-Tiering, Glacier Instant Retrieval, Glacier Flexible Retrieval, Glacier Deep Archive.

### 3.4 Region mapping

- **File:** `backend/app/region_mapping.py`.
- **Role:** Maps region codes (e.g. `us-east-1`) to Pricing API location strings (e.g. `US East (N. Virginia)`).
- **Coverage:** All standard AWS regions; new regions require an entry in `REGION_TO_LOCATION`.
- **Tests:** `tests/test_region_mapping.py` (roundtrip, unknown region).

### 3.5 Caching

- **Implementation:** In-memory TTL cache (`backend/app/cache.py`). Default TTL: 24 hours (`PRICING_CACHE_TTL_SECONDS=86400`).
- **Cache keys:** `service`, `region`, `currency`, and (for S3) `storage_class`.
- **Bypass:** Use `refresh=true` query parameter on pricing endpoints or “Refresh prices” in the UI.

---

## 4. Calculation logic

### 4.1 Units

- **TB → GB:**  
  - **Binary (default):** 1 TB = 1024 GB.  
  - **Decimal:** 1 TB = 1000 GB.  
- Controlled by the “TB conversion” toggle in the UI.

### 4.2 AWS Backup cost

- **Base:** `aws_backup_cost = GB × aws_backup_rate` (rate from API, USD/GB-month).
- **Add-ons (copy model):** `copy_multiplier = 1 + number_of_enabled_copy_addons` (logical air gap, cross-region, secondary vault each count as +1).
- **Total:** `aws_backup_total = aws_backup_cost × copy_multiplier + flat_addon_usd`.

### 4.3 S3 versioning cost

- **Effective stored:** `versioned_gb = GB × (1 + overhead_pct)` (e.g. 25% overhead → 1.25 × base).
- **S3 cost:** Uses tier bands from the pricing resolver; blended cost computed by applying each tier’s rate to the portion of `versioned_gb` in that tier.
- **Add-ons:** Same copy multiplier and flat add-on as AWS Backup.  
  `s3_versioning_total = s3_versioning_cost × copy_multiplier + flat_addon_usd`.

### 4.4 Deltas (Table B)

- **Delta vs AWS Backup ($):** `s3_total - aws_backup_total` (reference = AWS Backup total).
- **Delta vs AWS Backup (%):** `(s3_total - reference) / reference × 100`; 0% if reference is 0.

---

## 5. API reference

Base URL: `http://localhost:8000` (or backend host in Docker).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pricing/aws-backup?region=&currency=&refresh=` | AWS Backup storage rate (USD/GB-month). Optional `refresh=true` to bypass cache. |
| GET | `/api/pricing/s3-storage?region=&currency=&storageClass=&refresh=` | S3 storage rate or tier bands. Optional `refresh=true`. |
| POST | `/api/calc` | Server-side calc (optional). Body: `CalcInput` (data_tb, region, currency, aws_backup_rate_per_gb_month, s3_tiers or s3_flat_rate_per_gb_month, versioning_overhead_pct, num_copy_addons, flat_addon_usd, etc.). |
| GET | `/api/regions` | List of supported regions (code + location name). |
| GET | `/health` | Health check for containers. Returns `{"status":"ok","service":"awspricing-api"}`. |

### 5.1 Example: fetch AWS Backup pricing

```bash
curl "http://localhost:8000/api/pricing/aws-backup?region=us-east-1&currency=USD"
```

### 5.2 Example: fetch S3 Standard pricing

```bash
curl "http://localhost:8000/api/pricing/s3-storage?region=us-east-1&currency=USD&storageClass=Standard"
```

---

## 6. Configuration & credentials

### 6.1 Environment variables

| Variable | Where | Purpose |
|----------|--------|---------|
| `AWS_ACCESS_KEY_ID` | Backend (optional) | AWS access key for Pricing API (local dev). |
| `AWS_SECRET_ACCESS_KEY` | Backend (optional) | AWS secret key. |
| `AWS_REGION` | Backend (optional) | Default `us-east-1`; Pricing API is called in us-east-1, location filter selects region prices. |
| `PRICING_CACHE_TTL_SECONDS` | Backend | Cache TTL; default `86400` (24h). |

### 6.2 Credential modes

1. **Local dev:** Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` in `.env` or environment; or use `~/.aws/credentials`.
2. **AWS runtime:** Use IAM role (ECS Task Role, EKS Pod IRSA, EC2 instance profile). No keys needed.
3. **Read-only fallback:** If credentials are missing or the API fails, the UI shows “Pricing unavailable” and does not use hardcoded rates.

### 6.3 IAM policy (minimum)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["pricing:GetProducts"],
      "Resource": "*"
    }
  ]
}
```

If you add Price List file retrieval later, add `pricing:ListPriceLists` and `pricing:GetPriceListFileUrl`.

---

## 7. Container deployment

### 7.1 Build and run

```bash
# From project root
docker compose up
```

- **UI:** http://localhost:3001 (nginx serves frontend, proxies `/api` and `/health` to backend).
- **API:** http://localhost:8000 (direct).
- **Health:** http://localhost:8000/health.

### 7.2 Docker Compose services

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000 | FastAPI app; healthcheck via `/health`; optional `env_file: .env`. |
| `frontend` | 3001→80 | Vite build + nginx; proxies `/api` and `/health` to `backend:8000`; depends on backend healthy. |

### 7.3 Dockerfiles

- **Backend:** Python 3.12-slim; installs ksh, curl, wget, vim; `uvicorn app.main:app --host 0.0.0.0 --port 8000`; HEALTHCHECK with curl to `/health`.
- **Frontend:** Multi-stage; Node build, then nginx:alpine with static files and proxy config for `/api` and `/health` to `http://backend:8000`.

---

## 8. Testing

### 8.1 Backend unit tests

```bash
cd backend && PYTHONPATH=. python3 -m pytest tests/ -v
```

**Coverage:**

- **Cost engine:** TB↔GB (binary/decimal), versioned GB, copy multiplier, cost from flat rate, cost from tiers (single and multiple), AWS Backup total, S3 versioning total, delta USD/%.
- **Region mapping:** `us-east-1`→location, unknown region, location→region, roundtrip for all mapped regions.

### 8.2 Functional acceptance

- With region `us-east-1`, storage class Standard, overhead 25%: tables show correct GB conversions and totals; rates come from API (no hardcoded values); “last refreshed” is shown.
- If the pricing API fails: UI shows a clear error and does not compute with unknown rates unless cached data exists.

---

## 9. Limitations & troubleshooting

### 9.1 Known limitations

- **Tier interpretation:** S3 tier bands are used as returned by the API; units (e.g. bytes vs GB) may need extra normalization in the resolver for edge cases.
- **Region mapping:** Only regions defined in `region_mapping.py` are supported; new regions must be added there.
- **AWS Backup for S3:** Resolver targets Backup *storage* with Storage family and GB-Mo; product attributes can vary by AWS offering.
- **Currency:** UI currently uses USD; API supports a currency parameter for future use.

### 9.2 Troubleshooting

| Symptom | Check |
|--------|--------|
| “Pricing unavailable” | AWS credentials (env, file, or IAM role); IAM includes `pricing:GetProducts`. |
| Wrong or missing region | Region exists in `backend/app/region_mapping.py`. |
| Stale rates | Use “Refresh prices” or `refresh=true` on pricing endpoints; confirm cache TTL. |
| Tables empty or N/A | Backend logs for Pricing API errors; “Advanced pricing details” for matched SKU/terms. |
| Container won’t start | Backend healthcheck: `curl -f http://localhost:8000/health`; ensure port 8000 and 3001 free. |

### 9.3 Debug payload (Advanced pricing details)

The UI “Advanced pricing details” section shows the **debug payload** from the pricing resolver:

- **SKU** matched.
- **Product attributes** used to filter.
- **Term code** (e.g. OnDemand).
- **Price dimension** and **raw filter** (service, location, storage class).

Use this to verify which product/term was selected and to troubleshoot missing or unexpected rates.

---

*End of detailed documentation. For quick start and minimal README, see the root [README.md](../README.md).*
