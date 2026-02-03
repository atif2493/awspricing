# awspricing

**Version:** 1.0  
**Purpose:** Containerized web app that pulls **live pricing from AWS** (no hardcoded rates) and calculates **AWS Backup for S3** costs vs **S3 storage with versioning** (modeled overhead), with interactive inputs and table outputs.  
**Dependencies:** Docker, AWS credentials (for pricing API).  
**Ports:** UI 3001, API 8000.

---

## Quick start

```bash
# Optional: create .env with AWS credentials for local dev
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1

docker compose up
```

- **UI:** http://localhost:3001  
- **API:** http://localhost:8000  
- **Health:** http://localhost:8000/health  

**Live reload:** Backend app code is mounted from `./backend/app` and uvicorn runs with `--reload`, so edits to Python files take effect immediately. For frontend live reload, uncomment the `frontend` service override in `docker-compose.override.yml` (uses Vite dev server with `./frontend` mounted).  

---

## How pricing is resolved (same source as AWS Pricing Calculator)

The **AWS Pricing Calculator** (calculator.aws) is a web app with **no public API** to pull from; it uses the **AWS Price List** behind the scenes. This app uses the **same data source**: the AWS Price List (public URLs and optionally the Price List API). So you get the same underlying rates the calculator uses.

- **Primary (no credentials):** The app fetches pricing from **AWS public price list** URLs (`https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/...`). These are **open to the public** and require **no AWS credentials**. The resolver tries the public price list first for AWS Backup and S3.
- **Fallback (optional):** If the public fetch fails or returns no match, the app falls back to the **AWS Pricing API** (`GetProducts`), which requires AWS credentials. If you have no credentials and the public list fails, you’ll see a clear message.
- **AWS Backup:** Public URL `.../AWSBackup/current/<region>/index.json` (or global index); filtered by `productFamily=Storage` and `location`. Rate normalized to **USD per GB-Month**.
- **S3:** Public URL `.../AmazonS3/current/<region>/index.json` (or global); filtered by `productFamily=Storage`, `location`, and `storageClass`. Returns **flat rate** or **tier bands**; all normalized to **USD per GB-Month**.
- **Region mapping:** Region codes (e.g. `us-east-1`) are mapped to location strings (e.g. `US East (N. Virginia)`) in `backend/app/region_mapping.py`.
- **Caching:** Pricing responses are cached in memory (24h TTL). Use **Refresh prices** in the UI to bypass cache.

**Further reading:** [AWS S3 & AWS Backup — what they are and how pricing works](docs/AWS-S3-AND-BACKUP-PRICING.md) | [Pricing sources (calculator, API)](docs/PRICING-SOURCES.md) | [Detailed docs](docs/README.md)

---

## Credential setup

**Pricing works without credentials** using the public AWS price list. Credentials are only needed for the optional fallback (Pricing API).

1. **No credentials (default)**  
   - The app uses the **public price list** (no AWS keys). This is the primary path.

2. **Optional: credentials for fallback**  
   - If the public list fails (e.g. network), the app tries the Pricing API. Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_REGION`, or use `~/.aws/credentials` or an IAM role (ECS/EKS/EC2).

3. **If both fail**  
   - The UI shows **Pricing unavailable** with guidance. No hardcoded rates are used.

---

## IAM policy (minimum)

The runtime needs read-only access to the Pricing API:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pricing:GetProducts"
      ],
      "Resource": "*"
    }
  ]
}
```

If you add **Price List file** retrieval (ListPriceLists, GetPriceListFileUrl) as a fallback, add:

- `pricing:ListPriceLists`
- `pricing:GetPriceListFileUrl`

**Note:** AWS Pricing is served from the **us-east-1** (or ap-south-1) endpoint; the app uses the selected **location** attribute to return region-specific prices.

---

## Known limitations

- **Tier interpretation:** S3 tier bands from the API are used as returned; edge cases (e.g. units in bytes vs GB) may require extra normalization in the resolver.
- **Region mapping:** Only regions in `region_mapping.py` are supported; new regions must be added to the mapping.
- **AWS Backup for S3:** Filtering targets Backup *storage*; product attributes may vary by AWS offering—the resolver prefers Storage family and GB-Mo units.
- **Currency:** Only USD is wired in the UI; the API supports the currency parameter for future use.

---

## Project layout

```
awspricing/
├── docker-compose.yml    # Backend (8000) + frontend (3001)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # FastAPI, /api/pricing/*, /api/calc, /health
│   │   ├── pricing_resolver.py  # GetProducts, AWS Backup + S3
│   │   ├── region_mapping.py     # region code ↔ location
│   │   ├── cost_engine.py       # TB/GB, versioning, tiers, copy multiplier
│   │   └── cache.py            # TTL cache
│   └── tests/
├── frontend/
│   ├── Dockerfile        # Vite build + nginx (proxy /api to backend)
│   ├── src/
│   │   ├── App.tsx       # Inputs, Table A/B, transparency footer, export
│   │   ├── api/client.ts
│   │   ├── lib/costEngine.ts
│   │   └── components/
│   └── ...
└── README.md
```

---

## Example screenshots

1. **Inputs (left):** Region, currency, TB conversion, preset/custom size, S3 class, versioning overhead %, add-ons (logical air gap, cross-region, secondary vault, flat $).  
2. **Table A:** Preset 10–90 TB AWS Backup monthly cost (data size TB/GB, resolved rate, monthly $).  
3. **Table B:** AWS Backup (base / with add-ons) vs S3 Versioning (base / with add-ons): effective GB, price source, rate(s), monthly $, delta $ and %.  
4. **Transparency footer:** Region, currency, TB method, S3 class, overhead %, add-ons, last refreshed, cache TTL.  
5. **Advanced:** Expandable SKU / term match details from the pricing resolver.  
6. **Export:** Copy Table A/B to clipboard, Download CSV.

---

## Testing

```bash
cd backend && PYTHONPATH=. python3 -m pytest tests/ -v
```

Unit tests cover: TB↔GB conversion (binary/decimal), versioning overhead, copy multiplier, tier band math, region↔location mapping.

---

## Git sync (commit and push)

```bash
git add .
git status   # confirm what will be committed
git commit -m "Your message: version, what changed, deps, port"
git push
```

**If rebase was in progress (e.g. after resolving conflicts):**

```bash
git add README.md   # or the files you fixed
git rebase --continue
git push
```

To abort a rebase instead: `git rebase --abort`.
