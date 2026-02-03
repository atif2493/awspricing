# Pricing sources — AWS Pricing Calculator and this app

**Version:** 1.0  
**Purpose:** Clarify how awspricing relates to the AWS Pricing Calculator and what can/cannot be “pulled” from it.

---

## Can you pull pricing from the AWS Pricing Calculator?

**Short answer:** You cannot pull pricing *from* the calculator itself. You can (and this app does) use the **same underlying data** the calculator uses.

### AWS Pricing Calculator (web)

- **What it is:** A free web-based tool at [calculator.aws](https://calculator.aws) for building cost estimates.
- **API:** There is **no public API** to query the calculator or scrape its results. It is a web app only.
- **Data source:** The calculator uses the **AWS Price List** (same as this app): the public price list files and/or the Price List API (`GetProducts`).

So the calculator does not expose a “pricing from calculator” API; it consumes the same Price List data we already use.

### BCM Pricing Calculator API

- **What it is:** An AWS API (`bcm-pricing-calculator`) for creating **bill estimates** and **workload estimates** programmatically (e.g. “what would my bill look like if I added this usage?”).
- **Operations:** `create_bill_estimate`, `create_workload_estimate`, `get_bill_estimate`, `list_bill_estimate_line_items`, etc.
- **Credentials:** Required (IAM).
- **Use case:** Scenario-based estimates (add/change usage, apply discounts, compare to your bill). It returns **estimated totals and line items**, not raw SKU rates like “$X per GB-month.”
- **Latency:** Bill estimates can take **20 minutes to 12 hours** to generate; they are not suitable for real-time “refresh prices” in a UI.

So the BCM Pricing Calculator API is for **estimates from scenarios**, not for “give me the current $/GB rate for S3 Standard in us-east-1.” That kind of data comes from the **Price List** (which this app already uses).

---

## What this app uses (same source as the calculator)

| Source | Used by awspricing? | Used by AWS Pricing Calculator (web)? |
|--------|---------------------|---------------------------------------|
| **AWS public price list** (e.g. `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/index.json`) | Yes (primary, no credentials) | Yes (behind the scenes) |
| **AWS Price List API** (`pricing:GetProducts`) | Yes (fallback, with credentials) | Yes (behind the scenes) |
| **BCM Pricing Calculator API** (bill/workload estimates) | No | No (calculator web app ≠ this API) |

So **awspricing already uses the same pricing source as the AWS Pricing Calculator**: the AWS Price List (public files + optional Price List API). We do not “pull from” the calculator; we use the same data the calculator uses.

---

## Summary

- **“Pull pricing from AWS Pricing Calculator”** — The web calculator has no API to pull from. The BCM Pricing Calculator API is for scenario-based bill/workload estimates, not raw SKU rates.
- **Same rates as the calculator** — Yes. This app’s rates come from the AWS Price List, which is the same source the AWS Pricing Calculator uses.

For more detail on how we resolve prices (public URLs, GetProducts fallback, region mapping), see the root [README](../README.md) and [docs/README.md](README.md).

**See also:** [AWS S3 & AWS Backup — what they are and how pricing works](AWS-S3-AND-BACKUP-PRICING.md) (what S3 and AWS Backup are, how they are priced, and why “Backup not in public price list for this region” can appear).
