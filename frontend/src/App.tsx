/**
 * awspricing - AWS Backup vs S3 Versioning cost calculator.
 * v1.0 — Live AWS pricing, interactive inputs, Table A/B, transparency footer, export.
 * Deps: API client, cost engine. Port: 3000 (UI).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchAwsBackupPricing,
  fetchRegions,
  fetchS3StoragePricing,
  type AwsBackupPricing,
  type RegionOption,
  type S3StoragePricing,
} from "./api/client";
import {
  awsBackupTotal,
  copyMultiplier,
  deltaPct,
  deltaUsd,
  s3VersioningTotal,
  tbToGb,
  type TierBand,
} from "./lib/costEngine";
import {
  InputsPanel,
  PresetTable,
  ComparisonTable,
  TransparencyFooter,
  AdvancedPricingDetails,
} from "./components";
import "./App.css";

const PRESET_TB = [10, 20, 30, 40, 50, 60, 70, 80, 90];

export default function App() {
  const [region, setRegion] = useState("us-east-1");
  const [currency, setCurrency] = useState("USD");
  const [tbBinary, setTbBinary] = useState(true);
  const [presetTb, setPresetTb] = useState<number>(10);
  const [customSize, setCustomSize] = useState("");
  const [customUnit, setCustomUnit] = useState<"GB" | "TB">("TB");
  const [s3Class, setS3Class] = useState("Standard");
  const [overheadPct, setOverheadPct] = useState(0.25);
  const [customOverhead, setCustomOverhead] = useState("");
  const [addOnLogicalAirGap, setAddOnLogicalAirGap] = useState(false);
  const [addOnCrossRegion, setAddOnCrossRegion] = useState(false);
  const [addOnSecondaryVault, setAddOnSecondaryVault] = useState(false);
  const [flatAddonUsd, setFlatAddonUsd] = useState(0);

  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [awsBackupPricing, setAwsBackupPricing] = useState<AwsBackupPricing | null>(null);
  const [s3Pricing, setS3Pricing] = useState<S3StoragePricing | null>(null);
  const [pricingError, setPricingError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<number | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const refreshPricing = useCallback(
    async (bypassCache = false) => {
      setPricingError(null);
      setLoading(true);
      try {
        const [backupRes, s3Res] = await Promise.all([
          fetchAwsBackupPricing(region, currency, bypassCache),
          fetchS3StoragePricing(region, currency, s3Class, bypassCache),
        ]);
        setAwsBackupPricing(backupRes);
        setS3Pricing(s3Res);
        // Prefer S3 error only if Backup succeeded; if both have errors, show Backup first
        if (backupRes.error && s3Res.error) setPricingError(backupRes.error);
        else if (backupRes.error) setPricingError(backupRes.error);
        else if (s3Res.error) setPricingError(s3Res.error);
        else setPricingError(null);
        setLastRefreshed(Date.now());
      } catch (e) {
        setPricingError(e instanceof Error ? e.message : "Pricing unavailable");
        setAwsBackupPricing(null);
        setS3Pricing(null);
      } finally {
        setLoading(false);
      }
    },
    [region, currency, s3Class]
  );

  useEffect(() => {
    fetchRegions().then(setRegions).catch(() => setRegions([]));
  }, []);

  useEffect(() => {
    refreshPricing(false);
  }, [refreshPricing]);

  const numCopyAddons =
    (addOnLogicalAirGap ? 1 : 0) +
    (addOnCrossRegion ? 1 : 0) +
    (addOnSecondaryVault ? 1 : 0);
  const copyMult = copyMultiplier(numCopyAddons);
  const effectiveOverhead =
    customOverhead !== "" ? parseFloat(customOverhead) / 100 : overheadPct;
  const dataTb =
    customSize !== ""
      ? customUnit === "TB"
        ? parseFloat(customSize) || 0
        : (parseFloat(customSize) || 0) / (tbBinary ? 1024 : 1000)
      : presetTb;
  const dataGb = tbToGb(dataTb, tbBinary);

  const awbRate = awsBackupPricing?.rate_per_gb_month ?? null;
  const s3Tiers: TierBand[] = useMemo(() => {
    if (!s3Pricing) return [];
    if (s3Pricing.rate_per_gb_month != null)
      return [
        {
          from_gb: 0,
          to_gb: Infinity,
          rate_per_gb_month: s3Pricing.rate_per_gb_month,
        },
      ];
    return (s3Pricing.tiers ?? []).map((t) => ({
      from_gb: t.from_gb,
      to_gb: t.to_gb >= 1e35 ? Infinity : t.to_gb,
      rate_per_gb_month: t.rate_per_gb_month,
    }));
  }, [s3Pricing]);

  const awbTotal =
    awbRate != null
      ? awsBackupTotal(dataGb, awbRate, copyMult, flatAddonUsd)
      : null;
  const s3Total =
    s3Tiers.length > 0
      ? s3VersioningTotal(dataGb, effectiveOverhead, s3Tiers, copyMult, flatAddonUsd)
      : null;
  const reference = awbTotal ?? 0;
  const s3DeltaUsd = s3Total != null ? deltaUsd(s3Total, reference) : null;
  const s3DeltaPct = s3Total != null ? deltaPct(s3Total, reference) : null;

  return (
    <div className="app">
      <header className="header">
        <h1>awspricing</h1>
        <p className="tagline">AWS Backup vs S3 Versioning — live pricing (same source as AWS Pricing Calculator)</p>
      </header>

      <div className="layout">
        <aside className="inputs-panel">
          <InputsPanel
            region={region}
            setRegion={setRegion}
            currency={currency}
            setCurrency={setCurrency}
            tbBinary={tbBinary}
            setTbBinary={setTbBinary}
            presetTb={presetTb}
            setPresetTb={setPresetTb}
            customSize={customSize}
            setCustomSize={setCustomSize}
            customUnit={customUnit}
            setCustomUnit={setCustomUnit}
            s3Class={s3Class}
            setS3Class={setS3Class}
            overheadPct={overheadPct}
            setOverheadPct={setOverheadPct}
            customOverhead={customOverhead}
            setCustomOverhead={setCustomOverhead}
            addOnLogicalAirGap={addOnLogicalAirGap}
            setAddOnLogicalAirGap={setAddOnLogicalAirGap}
            addOnCrossRegion={addOnCrossRegion}
            setAddOnCrossRegion={setAddOnCrossRegion}
            addOnSecondaryVault={addOnSecondaryVault}
            setAddOnSecondaryVault={setAddOnSecondaryVault}
            flatAddonUsd={flatAddonUsd}
            setFlatAddonUsd={setFlatAddonUsd}
            regions={regions}
            loading={loading}
            onRefresh={() => refreshPricing(true)}
          />
        </aside>

        <main className="results">
          {pricingError && (
            <div className="banner error">
              {pricingError.includes("not in public") || pricingError.includes("public price list") ? (
                <> {pricingError} Use &quot;Refresh prices&quot; to retry. </>
              ) : (
                <>
                  Pricing unavailable: {pricingError}. Check AWS credentials and IAM
                  (pricing:GetProducts). &quot;Refresh prices&quot; to retry.
                </>
              )}
            </div>
          )}

          <PresetTable
            presetTb={PRESET_TB}
            tbBinary={tbBinary}
            awbRate={awbRate}
            loading={loading}
          />

          <ComparisonTable
            dataGb={dataGb}
            effectiveOverhead={effectiveOverhead}
            awbRate={awbRate}
            awbTotal={awbTotal}
            s3Class={s3Class}
            s3Tiers={s3Tiers}
            s3Total={s3Total}
            copyMult={copyMult}
            numCopyAddons={numCopyAddons}
            flatAddonUsd={flatAddonUsd}
            s3DeltaUsd={s3DeltaUsd}
            s3DeltaPct={s3DeltaPct}
            loading={loading}
          />

          <TransparencyFooter
            region={region}
            currency={currency}
            tbBinary={tbBinary}
            s3Class={s3Class}
            versioningOverheadPct={effectiveOverhead * 100}
            addOnsEnabled={numCopyAddons > 0 || flatAddonUsd > 0}
            copyMultiplier={copyMult}
            lastRefreshed={lastRefreshed}
            cacheTtlHours={24}
            onToggleAdvanced={() => setAdvancedOpen((o) => !o)}
            advancedOpen={advancedOpen}
          />

          <div className="export-actions">
            <ExportButtons
              presetTb={PRESET_TB}
              tbBinary={tbBinary}
              awbRate={awbRate}
              dataGb={dataGb}
              awbTotal={awbTotal}
              s3Total={s3Total}
              s3DeltaUsd={s3DeltaUsd}
              s3DeltaPct={s3DeltaPct}
              s3Class={s3Class}
            />
          </div>
        </main>
      </div>

      {advancedOpen && (
        <AdvancedPricingDetails
          awsBackupPricing={awsBackupPricing}
          s3Pricing={s3Pricing}
        />
      )}
    </div>
  );
}

function ExportButtons({
  presetTb,
  tbBinary,
  awbRate,
  dataGb,
  awbTotal,
  s3Total,
  s3DeltaUsd,
  s3DeltaPct,
  s3Class,
}: {
  presetTb: number[];
  tbBinary: boolean;
  awbRate: number | null;
  dataGb: number;
  awbTotal: number | null;
  s3Total: number | null;
  s3DeltaUsd: number | null;
  s3DeltaPct: number | null;
  s3Class: string;
}) {
  const copyTableA = () => {
    const rows = [
      ["Data Size (TB)", "Data Size (GB)", "Resolved AWS Backup Rate ($/GB-month)", "Monthly Cost ($)"],
      ...presetTb.map((tb) => {
        const gb = tb * (tbBinary ? 1024 : 1000);
        const cost = awbRate != null ? gb * awbRate : "";
        return [tb, gb.toFixed(2), awbRate != null ? awbRate.toFixed(6) : "N/A", cost !== "" ? (cost as number).toFixed(2) : "N/A"];
      }),
    ];
    const text = rows.map((r) => r.join("\t")).join("\n");
    navigator.clipboard.writeText(text);
  };

  const copyTableB = () => {
    const rows = [
      ["Scenario", "Effective Stored (GB)", "Price source", "Resolved Rate(s)", "Monthly Cost ($)", "Delta vs AWS Backup ($)", "Delta vs AWS Backup (%)"],
      ["AWS Backup (base)", dataGb.toFixed(2), "AWS Backup", awbRate != null ? `$${awbRate.toFixed(6)}/GB-mo` : "N/A", awbTotal != null ? awbTotal.toFixed(2) : "N/A", "-", "-"],
      ["S3 Versioning (base)", (dataGb * 1.25).toFixed(2), `Amazon S3 ${s3Class}`, "tiered/flat", s3Total != null ? s3Total.toFixed(2) : "N/A", s3DeltaUsd != null ? s3DeltaUsd.toFixed(2) : "N/A", s3DeltaPct != null ? `${s3DeltaPct.toFixed(1)}%` : "N/A"],
    ];
    const text = rows.map((r) => r.join("\t")).join("\n");
    navigator.clipboard.writeText(text);
  };

  const downloadCsv = () => {
    const tableA = [
      "Data Size (TB),Data Size (GB),Resolved AWS Backup Rate ($/GB-month),Monthly Cost ($)",
      ...presetTb.map((tb) => {
        const gb = tb * (tbBinary ? 1024 : 1000);
        const cost = awbRate != null ? gb * awbRate : "";
        return `${tb},${gb.toFixed(2)},${awbRate != null ? awbRate.toFixed(6) : "N/A"},${cost !== "" ? (cost as number).toFixed(2) : "N/A"}`;
      }),
    ].join("\n");
    const tableB = [
      "Scenario,Effective Stored (GB),Price source,Resolved Rate(s),Monthly Cost ($),Delta vs AWS Backup ($),Delta vs AWS Backup (%)",
      `AWS Backup (base),${dataGb.toFixed(2)},AWS Backup,${awbRate != null ? awbRate.toFixed(6) : "N/A"},${awbTotal != null ? awbTotal.toFixed(2) : "N/A"},-,-\nS3 Versioning (base),${(dataGb * 1.25).toFixed(2)},Amazon S3 ${s3Class},tiered/flat,${s3Total != null ? s3Total.toFixed(2) : "N/A"},${s3DeltaUsd != null ? s3DeltaUsd.toFixed(2) : "N/A"},${s3DeltaPct != null ? `${s3DeltaPct.toFixed(1)}%` : "N/A"}`,
    ].join("\n");
    const blob = new Blob([`Table A - Preset AWS Backup\n${tableA}\n\nTable B - Comparison\n${tableB}`], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "awspricing-results.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="export-buttons">
      <button type="button" onClick={copyTableA}>
        Copy Table A
      </button>
      <button type="button" onClick={copyTableB}>
        Copy Table B
      </button>
      <button type="button" onClick={downloadCsv}>
        Download CSV
      </button>
    </div>
  );
}
