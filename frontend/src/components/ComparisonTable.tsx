/**
 * ComparisonTable - Table B: AWS Backup vs S3 Versioning comparison.
 * v1.0. Port: N/A.
 */

import type { TierBand } from "../lib/costEngine";

type Props = {
  dataGb: number;
  effectiveOverhead: number;
  awbRate: number | null;
  awbTotal: number | null;
  s3Class: string;
  s3Tiers: TierBand[];
  s3Total: number | null;
  copyMult: number;
  numCopyAddons: number;
  flatAddonUsd: number;
  s3DeltaUsd: number | null;
  s3DeltaPct: number | null;
  loading: boolean;
};

function fmtUsd(n: number | null): string {
  if (n == null) return "N/A";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function rateLabel(awbRate: number | null): string {
  if (awbRate != null) return `$${awbRate.toFixed(6)}/GB-mo`;
  return "N/A";
}

function s3RateLabel(tiers: TierBand[]): string {
  if (tiers.length === 0) return "N/A";
  if (tiers.length === 1 && tiers[0].to_gb === Infinity)
    return `$${tiers[0].rate_per_gb_month.toFixed(6)}/GB-mo`;
  return "Tiered";
}

export function ComparisonTable({
  dataGb,
  effectiveOverhead,
  awbRate,
  awbTotal,
  s3Class,
  s3Tiers,
  s3Total,
  copyMult,
  numCopyAddons,
  flatAddonUsd,
  s3DeltaUsd,
  s3DeltaPct,
  loading,
}: Props) {
  const versionedGb = dataGb * (1 + effectiveOverhead);

  return (
    <section className="table-section">
      <h2>Table B — Comparison: AWS Backup vs S3 Versioning</h2>
      <div className="table-wrapper">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Effective Stored (GB)</th>
              <th>Price source</th>
              <th>Resolved Rate(s) ($/GB-month)</th>
              <th>Monthly Cost ($)</th>
              <th>Delta vs AWS Backup ($)</th>
              <th>Delta vs AWS Backup (%)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>AWS Backup (base)</td>
              <td>{dataGb.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
              <td>AWS Backup</td>
              <td>{loading ? "…" : rateLabel(awbRate)}</td>
              <td>{loading ? "…" : fmtUsd(awbTotal)}</td>
              <td>—</td>
              <td>—</td>
            </tr>
            {numCopyAddons > 0 || flatAddonUsd > 0 ? (
              <tr>
                <td>AWS Backup (with add-ons)</td>
                <td>{dataGb.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                <td>AWS Backup × {copyMult.toFixed(1)}{flatAddonUsd > 0 ? ` + $${flatAddonUsd}/mo` : ""}</td>
                <td>{rateLabel(awbRate)}</td>
                <td>{fmtUsd(awbTotal)}</td>
                <td>—</td>
                <td>—</td>
              </tr>
            ) : null}
            {s3Tiers.length > 0 && (
              <>
                <tr>
                  <td>S3 Versioning (base)</td>
                  <td>{versionedGb.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                  <td>Amazon S3 — {s3Class}</td>
                  <td>{loading ? "…" : s3RateLabel(s3Tiers)}</td>
                  <td>{loading ? "…" : fmtUsd(s3Total)}</td>
                  <td>{s3DeltaUsd != null ? fmtUsd(s3DeltaUsd) : "N/A"}</td>
                  <td>{s3DeltaPct != null ? `${s3DeltaPct.toFixed(1)}%` : "N/A"}</td>
                </tr>
                {(numCopyAddons > 0 || flatAddonUsd > 0) && (
                  <tr>
                    <td>S3 Versioning (with add-ons)</td>
                    <td>{versionedGb.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                    <td>Amazon S3 — {s3Class} × {copyMult.toFixed(1)}{flatAddonUsd > 0 ? ` + $${flatAddonUsd}/mo` : ""}</td>
                    <td>{s3RateLabel(s3Tiers)}</td>
                    <td>{fmtUsd(s3Total)}</td>
                    <td>{s3DeltaUsd != null ? fmtUsd(s3DeltaUsd) : "N/A"}</td>
                    <td>{s3DeltaPct != null ? `${s3DeltaPct.toFixed(1)}%` : "N/A"}</td>
                  </tr>
                )}
              </>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
