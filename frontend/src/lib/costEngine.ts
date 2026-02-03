/**
 * Client-side cost engine (mirrors backend logic).
 * TB/GB conversion, versioning overhead, copy multiplier, tier math.
 * Port: N/A.
 */

export const TB_BINARY = 1024;
export const TB_DECIMAL = 1000;

export function tbToGb(tb: number, binary: boolean): number {
  return tb * (binary ? TB_BINARY : TB_DECIMAL);
}

export function versionedGb(baseGb: number, overheadPct: number): number {
  return baseGb * (1 + overheadPct);
}

export function copyMultiplier(numCopyAddons: number): number {
  return 1 + Math.max(0, numCopyAddons);
}

export function costFromFlatRate(gb: number, ratePerGbMonth: number): number {
  return gb * ratePerGbMonth;
}

export interface TierBand {
  from_gb: number;
  to_gb: number;
  rate_per_gb_month: number;
}

export function costFromTiers(gb: number, tiers: TierBand[]): number {
  let total = 0;
  let remaining = gb;
  for (const band of tiers) {
    if (remaining <= 0) break;
    const bandSize =
      band.to_gb === Infinity
        ? remaining
        : Math.min(remaining, band.to_gb - band.from_gb);
    if (bandSize > 0) total += bandSize * band.rate_per_gb_month;
    remaining -= bandSize;
  }
  return total;
}

export function awsBackupTotal(
  baseGb: number,
  ratePerGbMonth: number,
  copyMult: number,
  flatAddonUsd = 0
): number {
  return baseGb * ratePerGbMonth * copyMult + flatAddonUsd;
}

export function s3VersioningTotal(
  baseGb: number,
  overheadPct: number,
  tiers: TierBand[],
  copyMult = 1,
  flatAddonUsd = 0
): number {
  const vGb = versionedGb(baseGb, overheadPct);
  return costFromTiers(vGb, tiers) * copyMult + flatAddonUsd;
}

export function deltaUsd(cost: number, reference: number): number {
  return cost - reference;
}

export function deltaPct(cost: number, reference: number): number {
  if (reference === 0) return 0;
  return ((cost - reference) / reference) * 100;
}
