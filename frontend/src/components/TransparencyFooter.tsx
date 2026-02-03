/**
 * TransparencyFooter - Region, currency, TB method, S3 class, overhead, add-ons, last refreshed, cache TTL.
 * v1.0. Port: N/A.
 */

type Props = {
  region: string;
  currency: string;
  tbBinary: boolean;
  s3Class: string;
  versioningOverheadPct: number;
  addOnsEnabled: boolean;
  copyMultiplier: number;
  lastRefreshed: number | null;
  cacheTtlHours: number;
  onToggleAdvanced: () => void;
  advancedOpen: boolean;
};

export function TransparencyFooter({
  region,
  currency,
  tbBinary,
  s3Class,
  versioningOverheadPct,
  addOnsEnabled,
  copyMultiplier,
  lastRefreshed,
  cacheTtlHours,
  onToggleAdvanced,
  advancedOpen,
}: Props) {
  const lastRefreshedStr =
    lastRefreshed != null
      ? new Date(lastRefreshed).toISOString()
      : "Never";

  return (
    <footer className="transparency-footer">
      <h3>Transparency</h3>
      <ul>
        <li>Region: {region} | Currency: {currency}</li>
        <li>TB conversion: {tbBinary ? "Binary (1 TB = 1024 GB)" : "Decimal (1 TB = 1000 GB)"}</li>
        <li>S3 storage class: {s3Class}</li>
        <li>Versioning overhead: {versioningOverheadPct.toFixed(1)}%</li>
        <li>Add-ons enabled: {addOnsEnabled ? `Yes (copy multiplier: ${copyMultiplier.toFixed(1)})` : "No"}</li>
        <li>Pricing last refreshed: {lastRefreshedStr} | Cache TTL: {cacheTtlHours}h</li>
      </ul>
      <button
        type="button"
        className="accordion-trigger"
        onClick={onToggleAdvanced}
        aria-expanded={advancedOpen}
      >
        {advancedOpen ? "Hide" : "Show"} advanced pricing details (SKU / terms)
      </button>
    </footer>
  );
}
