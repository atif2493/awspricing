# AWS S3 & AWS Backup — What They Are and How Pricing Works

**Version:** 1.0  
**Purpose:** Clarify what AWS S3 and AWS Backup are, how they are priced, and how this app gets those prices.

---

## What is Amazon S3?

**Amazon S3 (Simple Storage Service)** is an object storage service. You store and retrieve arbitrary data (objects) in buckets. There is no minimum fee; you pay for storage used, requests, and data transfer.

- **Storage:** Billed by **GB-month** (average storage over the month). Price depends on **region**, **storage class**, and **volume** (tiered: first X TB at one rate, next Y TB at another, etc.).
- **Storage classes:** Standard (frequent access), Intelligent-Tiering, Standard-IA, One Zone-IA, Glacier tiers, etc. Each has different $/GB-month and retrieval costs.
- **Other charges:** PUT/GET/LIST requests, data transfer out, replication, and optional features (e.g. S3 Select).

**How S3 gets its prices:** AWS publishes S3 prices in the **AWS Price List**. The same numbers appear on the [S3 pricing page](https://aws.amazon.com/s3/pricing/), in the AWS Pricing Calculator, and in the price list files/API. There is no separate “S3-only” source; it’s all the same Price List.

---

## What is AWS Backup?

**AWS Backup** is a **managed backup service**. You define backup plans (frequency, retention) and assign them to resources (EBS, EFS, RDS, DynamoDB, **S3**, etc.). AWS Backup runs the backups and stores them in a backup vault.

- **Storage:** For **AWS Backup storage** (data in a backup vault), you pay by **GB-month** (average storage over the month). Rate varies by **region**.
- **AWS Backup for S3:** When you back up S3 buckets with AWS Backup, that backup storage is billed as **AWS Backup** (GB-month), not as S3. There can be a lower-cost “warm” tier for S3 backups after a minimum retention (e.g. 60 days).
- **Other charges:** Restore (GB restored), cross-region copy, and (for some resources) early-deletion fees.

**How AWS Backup gets its prices:** Same as S3 — the **AWS Price List**. AWS Backup has its own **service/offer code** in that list (e.g. `AWSBackup`). The [AWS Backup pricing page](https://aws.amazon.com/backup/pricing/) and the Pricing Calculator both use this same Price List. Not all regions may have Backup SKUs in every price list format (e.g. some regions might appear only in the API or in regional files).

---

## How Does This App Get Prices?

The app needs two things:

1. **S3 storage price** — For the chosen region and storage class (e.g. Standard), in **USD per GB-month** (flat or tiered).
2. **AWS Backup storage price** — For the chosen region, in **USD per GB-month** (for backup vault storage, comparable to “Backup for S3” usage).

Both come from the **same underlying source**: the **AWS Price List**.

### Two ways to read the Price List

| Method | Credentials | What it is |
|-------|-------------|------------|
| **Public price list (JSON/CSV)** | **None** | Static files at `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/...`. Example: `.../AmazonS3/current/index.json` or `.../AWSBackup/current/region/index.json`. Same numbers as the pricing pages. |
| **Price List API** (`pricing:GetProducts`) | **Required** (IAM) | Billing/Cost Management API in `us-east-1` (and `ap-south-1` for India). Returns the same products/prices as the public files, with filtering by service, region, product family, etc. |

So:

- **S3:** The app fetches the **public** S3 offer file (global or regional), finds products for the selected **location** and **storage class**, and normalizes to **USD per GB-month** (flat rate or tiers).
- **AWS Backup:** The app first tries the **public** Backup offer file (e.g. `AWSBackup`), looks for **Storage** (or backup storage) products for the selected **location**, and normalizes to **USD per GB-month**. If the public list has no Backup product for that region, the app can use a **fallback** (e.g. us-east-1 rate) and show a warning, or use the **GetProducts** API if credentials are configured.

### Why “AWS Backup not in public price list for this region”?

The **public** index may list Backup under a service code like `AWSBackup`. The actual **products** inside the file are keyed by attributes such as `productFamily`, `location`, and `usageType`. Not every region has a Backup **product** in every public file (e.g. some regions might only be in regional files or in the API). So for some regions you can get S3 from the public list but not Backup; hence the message and the optional fallback to another region’s Backup rate or to the Pricing API.

---

## Summary

| Topic | Summary |
|-------|---------|
| **What is S3?** | Object storage; pay for storage (GB-month), requests, and transfer. Prices by region, storage class, and tier. |
| **What is AWS Backup?** | Managed backup service; backup storage billed as GB-month by region. “AWS Backup for S3” means S3 backups stored in Backup vaults. |
| **Where do S3/Backup prices come from?** | The **AWS Price List** (same source as the AWS pricing pages and Pricing Calculator). |
| **How does this app get them?** | **Public price list** URLs (no credentials) for S3 and Backup; optional **GetProducts** fallback (with credentials) and optional **Backup rate fallback** (e.g. us-east-1) when the public list has no Backup product for the selected region. |

For implementation details (URLs, filters, region mapping), see [README](README.md) and [PRICING-SOURCES.md](PRICING-SOURCES.md).
