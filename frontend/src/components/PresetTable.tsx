/**
 * PresetTable - Table A: 10–90 TB preset AWS Backup monthly cost.
 * v1.0. Port: N/A.
 */

import { tbToGb } from "../lib/costEngine";

type Props = {
  presetTb: number[];
  tbBinary: boolean;
  awbRate: number | null;
  loading: boolean;
};

export function PresetTable({
  presetTb,
  tbBinary,
  awbRate,
  loading,
}: Props) {
  return (
    <section className="table-section">
      <h2>Table A — Preset AWS Backup Monthly Cost</h2>
      <div className="table-wrapper">
        <table className="preset-table">
          <thead>
            <tr>
              <th>Data Size (TB)</th>
              <th>Data Size (GB)</th>
              <th>Resolved AWS Backup Rate ($/GB-month)</th>
              <th>Monthly Cost ($)</th>
            </tr>
          </thead>
          <tbody>
            {presetTb.map((tb) => {
              const gb = tbToGb(tb, tbBinary);
              const cost =
                awbRate != null && !loading ? gb * awbRate : null;
              return (
                <tr key={tb}>
                  <td>{tb}</td>
                  <td>{gb.toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                  <td>
                    {loading
                      ? "…"
                      : awbRate != null
                        ? awbRate.toFixed(6)
                        : "N/A"}
                  </td>
                  <td>
                    {loading
                      ? "…"
                      : cost != null
                        ? cost.toLocaleString("en-US", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })
                        : "N/A"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
