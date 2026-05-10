# Image Agent

A composable image-generation and image-processing service with FastAPI, pluggable processors, local/S3-shaped storage, imgproxy-compatible signatures, Prometheus metrics, and per-operation cost attribution.

The project keeps the original AI image generation endpoints while adding a production-oriented processing API for upload optimization, metadata extraction, asynchronous batch workflows, and transform URL signing.

## Production Goals

- URL/upload → processed images with a p99 target below 500 ms for common web assets.
- No vendor lock-in: local storage for development, MinIO/S3 shape for production, and imgproxy-compatible transform URLs.
- Cost transparency per tenant: input bytes, output bytes, CPU time, bandwidth, and estimated USD per operation.
- Observable API: `/metrics`, structured JSON logs, dependency-aware `/health`.
- India data residency friendly: deploy MinIO/Redis/app/logs on an India VPS or `ap-south-1` equivalent.

## API Surface

### Health and Metrics

```bash
curl http://localhost:8900/health
curl http://localhost:8900/metrics
```

`GET /health` verifies local storage, queue, and imgproxy configuration. `GET /metrics` exports Prometheus counters and histograms for latency, bytes, operations, and cost.

### Upload and Auto-Process

```bash
curl -X POST http://localhost:8900/v1/images/upload \
  -H 'X-Image-API-Key: dev-key' \
  -F tenant_id=acme_corp \
  -F formats=webp \
  -F formats=original \
  -F resize_width=1200 \
  -F quality=80 \
  -F file=@photo.jpg
```

Response includes `job_id`, derivative URLs, compression ratio, processing time, and a cost breakdown. The local processor uses Pillow/libjpeg in this repository and is intentionally shaped so a `sharp`/libvips or ImageMagick backend can be swapped in behind the same processor contract.

### imgproxy-Compatible Transform

```bash
curl http://localhost:8900/image/insecure/300x200/sm/80/webp/s3:bucket:photos/user123.jpg
```

The endpoint validates HMAC-SHA256 signatures unless `insecure` is used for local development. In production, route these URLs directly to the `imgproxy` service from `docker-compose.yml` or use this endpoint to issue/validate pre-signed links.

### Metadata Extraction

```bash
curl -X POST http://localhost:8900/v1/images/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-Image-API-Key: dev-key' \
  -d '{"tenant_id":"acme_corp","image_url":"https://example.com/photo.jpg","analysis":["exif","colors","objects","text"]}'
```

The analyzer extracts width, height, format, basic EXIF fields, dominant colors, and returns empty placeholders for object/text detection until YOLO/OCR backends are configured.

### Batch Optimize

```bash
curl -X POST http://localhost:8900/v1/images/batch-optimize \
  -H 'Content-Type: application/json' \
  -H 'X-Image-API-Key: dev-key' \
  -d '{"tenant_id":"acme_corp","images":[{"url":"s3://bucket/img1.jpg","target_format":"webp"}],"callback_url":"https://webhook.example.com/images-ready"}'
```

The local queue is in-memory for tests and development; production deployments should replace it with BullMQ/Redis or Temporal workers while preserving the response contract.

## Security Guardrails

- API key header: `X-Image-API-Key` for `/v1/images/*` endpoints.
- Max upload size: 100 MB by default (`MAX_UPLOAD_BYTES`).
- Allowed uploads: `image/*`.
- Resize width cap: 2000 px by default (`MAX_RESIZE_WIDTH`).
- Dimension bounds: 10×10 through 8000×8000 px.
- SSRF protection rejects loopback, link-local, and private IP ranges for URL analysis and batch URLs.
- Structured error responses use stable `error.code` values and do not expose stack traces.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
image-agent serve --host 0.0.0.0 --port 8900
```

Or use the reproducible stack:

```bash
cp .env.example .env
docker compose up --build
```

Docker Compose starts:

- `image-agent` on `:8900`
- `imgproxy` on `:8080`
- `minio` on `:9000` and console `:9001`
- `redis` on `:6379`

## Deployment Guide: Coolify + VPS

1. Provision an India-region VPS or an `ap-south-1` equivalent for DPDP-conscious residency.
2. Create a Coolify Docker Compose application using this repository.
3. Store secrets in Coolify, not in Git: `IMAGE_AGENT_API_KEYS`, MinIO credentials, and imgproxy signature key/salt.
4. Put Caddy or Coolify's proxy in front of `image-agent`; keep MinIO and Redis private to the Docker network.
5. Run `imgproxy` with resource limits such as 2 CPU and 2 GB RAM, and scale `image-agent` stateless replicas horizontally.
6. Scrape `/metrics` with Prometheus and dashboard latency, bytes, formats, errors, and `image_cost_usd_total` in Grafana.
7. Configure MinIO lifecycle policies for original → compressed → archive after 30 days, and enable versioning for rollback.

## Benchmarks and Cost Evidence

See [`docs/benchmarks.md`](docs/benchmarks.md) for the latency/cost comparison plan across pre-compression, imgproxy on-demand transforms, and ImageMagick fallback processing.

## Testing

```bash
pytest
```

The test suite covers signing, cost attribution, validation, health/metrics, upload processing, analysis, batch queueing, auth errors, and transform signature failures.

## Legacy Generation Endpoints

The previous AI generation endpoints remain available:

- `POST /generate`
- `POST /edit`
- `POST /upscale`
- `POST /remove-bg`
- `POST /describe`
- `GET /models`

## License

MIT. See [`LICENSE`](LICENSE).
