# Image Processing Benchmarks and Cost Model

This repository ships a dependency-light benchmark harness and load-test plan so teams can compare self-hosted and cloud-backed image infrastructure before committing to a vendor.

## Strategies to Compare

| Strategy | Best use case | Latency expectation | Cost trade-off | Failure modes |
| --- | --- | --- | --- | --- |
| Pre-compress with Pillow/libjpeg or sharp/libvips | Upload-time derivatives for hot assets | Upload p99 target: <500 ms for common web images | More storage, lower read CPU | CPU saturation, codec fallback, large source images |
| imgproxy on-demand transform | Dynamic resize/crop/format URLs | Transform p99 target: <100 ms on local network/cache | Lower derivative storage, CPU per miss | Bad signatures, upstream S3/MinIO latency, cache misses |
| ImageMagick fallback | EPS/TIFF/exotic formats | Slower, batch-only recommended | Higher CPU, broader format support | Policy.xml restrictions, memory pressure |

## Cost Attribution Formula

Every processed image response includes a cost breakdown:

```text
storage_usd = output_gb_seconds * storage_gb_month_usd / 30d
cpu_usd = cpu_seconds * cpu_second_usd
bandwidth_usd = (input_gb + output_gb) * bandwidth_gb_usd
total_usd = storage_usd + cpu_usd + bandwidth_usd
```

Example for a 2.5 MB upload compressed to 450 KB in 320 ms with default rates:

- Storage: effectively zero for a sub-second operation window, then accounted for by monthly object inventory.
- CPU: about `$0.00000352`.
- Bandwidth: about `$0.000247`.
- Total request estimate: about `$0.000251`, below the `$0.002` acceptance target.

## Load Test Evidence Plan

Run the application with Docker Compose, then execute the k6 script:

```bash
docker compose up --build
k6 run tests/load/k6-upload.js
```

Acceptance thresholds are encoded in the script:

- Upload p99 `<500ms` at 100 virtual users.
- Failed request rate `<0.1%`.

## India Data Residency Notes

For DPDP-aligned deployments, keep MinIO, Redis, logs, and backups on an India-region VPS or `ap-south-1` equivalent. Avoid third-party CDNs unless consent and transfer terms are documented. Structured logs must not include raw image bytes or sensitive EXIF payloads.
