/**
 * AdvancedPricingDetails - Expandable SKU / term match details.
 * v1.0. Port: N/A.
 */

import type { AwsBackupPricing, S3StoragePricing } from "../api/client";

type Props = {
  awsBackupPricing: AwsBackupPricing | null;
  s3Pricing: S3StoragePricing | null;
};

export function AdvancedPricingDetails({
  awsBackupPricing,
  s3Pricing,
}: Props) {
  return (
    <div className="advanced-pricing">
      <h4>AWS Backup — matched SKU / terms</h4>
      <pre>
        {awsBackupPricing
          ? JSON.stringify(
              {
                sku: awsBackupPricing.sku,
                product_attributes: awsBackupPricing.product_attributes,
                term_code: awsBackupPricing.term_code,
                price_dimension: awsBackupPricing.price_dimension,
                raw_filter: awsBackupPricing.raw_filter,
              },
              null,
              2
            )
          : "No data"}
      </pre>
      <h4>Amazon S3 — matched SKU / terms</h4>
      <pre>
        {s3Pricing
          ? JSON.stringify(
              {
                sku: s3Pricing.sku,
                product_attributes: s3Pricing.product_attributes,
                term_code: s3Pricing.term_code,
                price_dimension: s3Pricing.price_dimension,
                tiers: s3Pricing.tiers,
                raw_filter: s3Pricing.raw_filter,
              },
              null,
              2
            )
          : "No data"}
      </pre>
    </div>
  );
}
