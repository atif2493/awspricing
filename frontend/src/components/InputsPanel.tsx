/**
 * InputsPanel - Region, currency, TB conversion, preset/custom size, S3 class, overhead, add-ons.
 * v1.0. Port: N/A.
 */

import type { RegionOption } from "../api/client";

const PRESET_TB_OPTIONS = [10, 20, 30, 40, 50, 60, 70, 80, 90];

type Props = {
  region: string;
  setRegion: (r: string) => void;
  currency: string;
  setCurrency: (c: string) => void;
  tbBinary: boolean;
  setTbBinary: (b: boolean) => void;
  presetTb: number;
  setPresetTb: (n: number) => void;
  customSize: string;
  setCustomSize: (s: string) => void;
  customUnit: "GB" | "TB";
  setCustomUnit: (u: "GB" | "TB") => void;
  s3Class: string;
  setS3Class: (c: string) => void;
  overheadPct: number;
  setOverheadPct: (n: number) => void;
  customOverhead: string;
  setCustomOverhead: (s: string) => void;
  addOnLogicalAirGap: boolean;
  setAddOnLogicalAirGap: (b: boolean) => void;
  addOnCrossRegion: boolean;
  setAddOnCrossRegion: (b: boolean) => void;
  addOnSecondaryVault: boolean;
  setAddOnSecondaryVault: (b: boolean) => void;
  flatAddonUsd: number;
  setFlatAddonUsd: (n: number) => void;
  regions: RegionOption[];
  loading: boolean;
  onRefresh: () => void;
};

export function InputsPanel({
  region,
  setRegion,
  currency,
  setCurrency,
  tbBinary,
  setTbBinary,
  presetTb,
  setPresetTb,
  customSize,
  setCustomSize,
  customUnit,
  setCustomUnit,
  s3Class,
  setS3Class,
  overheadPct,
  setOverheadPct,
  customOverhead,
  setCustomOverhead,
  addOnLogicalAirGap,
  setAddOnLogicalAirGap,
  addOnCrossRegion,
  setAddOnCrossRegion,
  addOnSecondaryVault,
  setAddOnSecondaryVault,
  flatAddonUsd,
  setFlatAddonUsd,
  regions,
  loading,
  onRefresh,
}: Props) {
  const s3Classes = [
    "Standard",
    "Standard-IA",
    "Intelligent-Tiering",
    "Glacier Instant Retrieval",
    "Glacier Flexible Retrieval",
    "Glacier Deep Archive",
  ];

  return (
    <div className="inputs-panel-inner">
      <section>
        <h3>Pricing context</h3>
        <label>
          Region
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            disabled={loading}
          >
            {regions.length
              ? regions.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.code} — {r.location}
                  </option>
                ))
              : (
                  <option value={region}>{region}</option>
                )}
          </select>
        </label>
        <label>
          Currency
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            disabled={loading}
          >
            <option value="USD">USD</option>
          </select>
        </label>
        <label className="toggle-row">
          TB conversion
          <span>
            <button
              type="button"
              className={tbBinary ? "active" : ""}
              onClick={() => setTbBinary(true)}
            >
              Binary (1 TB = 1024 GB)
            </button>
            <button
              type="button"
              className={!tbBinary ? "active" : ""}
              onClick={() => setTbBinary(false)}
            >
              Decimal (1 TB = 1000 GB)
            </button>
          </span>
        </label>
        <button
          type="button"
          className="refresh-prices"
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? "Loading…" : "Refresh prices"}
        </button>
      </section>

      <section>
        <h3>Data size</h3>
        <label>
          Preset (TB)
          <select
            value={presetTb}
            onChange={(e) => setPresetTb(Number(e.target.value))}
          >
            {PRESET_TB_OPTIONS.map((tb) => (
              <option key={tb} value={tb}>
                {tb} TB
              </option>
            ))}
          </select>
        </label>
        <label>
          Custom size
          <span className="inline">
            <input
              type="number"
              min={0}
              step="any"
              value={customSize}
              onChange={(e) => setCustomSize(e.target.value)}
              placeholder="e.g. 50"
            />
            <select
              value={customUnit}
              onChange={(e) => setCustomUnit(e.target.value as "GB" | "TB")}
            >
              <option value="GB">GB</option>
              <option value="TB">TB</option>
            </select>
          </span>
        </label>
      </section>

      <section>
        <h3>S3 Versioning comparison</h3>
        <label>
          S3 storage class
          <select
            value={s3Class}
            onChange={(e) => setS3Class(e.target.value)}
            disabled={loading}
          >
            {s3Classes.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label>
          Versioning overhead
          <select
            value={overheadPct}
            onChange={(e) => setOverheadPct(Number(e.target.value))}
          >
            <option value={0}>0%</option>
            <option value={0.1}>10%</option>
            <option value={0.25}>25%</option>
            <option value={0.5}>50%</option>
          </select>
        </label>
        <label>
          Custom overhead (%)
          <input
            type="number"
            min={0}
            max={200}
            step="0.1"
            value={customOverhead}
            onChange={(e) => setCustomOverhead(e.target.value)}
            placeholder="e.g. 15"
          />
        </label>
        <p className="hint">
          Versioning stores additional object versions; storage grows with
          changes + retention.
        </p>
      </section>

      <section>
        <h3>Optional add-ons</h3>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={addOnLogicalAirGap}
            onChange={(e) => setAddOnLogicalAirGap(e.target.checked)}
          />
          Logical air gap (+1 copy)
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={addOnCrossRegion}
            onChange={(e) => setAddOnCrossRegion(e.target.checked)}
          />
          Cross-region copy (+1 copy)
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={addOnSecondaryVault}
            onChange={(e) => setAddOnSecondaryVault(e.target.checked)}
          />
          Secondary vault / immutable copy (+1 copy)
        </label>
        <label>
          Custom flat monthly ($)
          <input
            type="number"
            min={0}
            step="any"
            value={flatAddonUsd || ""}
            onChange={(e) => setFlatAddonUsd(parseFloat(e.target.value) || 0)}
            placeholder="0"
          />
        </label>
      </section>
    </div>
  );
}
