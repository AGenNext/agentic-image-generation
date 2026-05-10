"""FastAPI server for generation plus production image-processing workflows."""

from __future__ import annotations

import base64
import hashlib
import time
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl

from image_agent.config.env import load_settings
from image_agent.utils.costs import CostRates, estimate_operation_cost
from image_agent.observability.logger import log_event
from image_agent.observability.metrics import image_bytes_total, image_cost_usd_total, image_operation_latency_seconds, image_operations_total, render_metrics
from image_agent.processors.metadata_processor import MetadataProcessor
from image_agent.processors.sharp_processor import ImageProcessor
from image_agent.queue.jobs import InMemoryJobQueue
from image_agent.storage.local import LocalImageStorage
from image_agent.utils.hmac_signer import verify_path
from image_agent.utils.validators import normalize_formats, validate_public_url


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "auto"
    width: int = 1024
    height: int = 1024


class EditRequest(BaseModel):
    prompt: str
    image: str
    mask: str = ""


class AnalyzeRequest(BaseModel):
    image_url: str
    tenant_id: str = Field(..., min_length=1)
    analysis: list[str] = Field(default_factory=lambda: ["exif", "colors"])


class BatchImage(BaseModel):
    url: str
    target_format: str = "webp"


class BatchOptimizeRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    images: list[BatchImage] = Field(..., min_length=1, max_length=1000)
    callback_url: Optional[HttpUrl] = None


def create_app() -> FastAPI:
    settings = load_settings()
    storage = LocalImageStorage(settings.storage_root)
    processor = ImageProcessor()
    metadata = MetadataProcessor()
    queue = InMemoryJobQueue()
    rates = CostRates(settings.storage_gb_month_usd, settings.cpu_second_usd, settings.bandwidth_gb_usd)
    app = FastAPI(title="Image Agent", version="0.2.0", description="Composable image generation and processing API with cost attribution")

    async def require_api_key(x_image_api_key: str | None = Header(default=None)) -> str:
        if x_image_api_key not in settings.api_keys:
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "valid X-Image-API-Key is required"})
        return x_image_api_key or ""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(Exception)
    async def exception_handler(_: Request, exc: Exception):
        log_event("unhandled_error", error=exc.__class__.__name__)
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "request failed"}})

    @app.post("/generate")
    async def generate(req: GenerateRequest):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.generate(req.prompt, req.model, req.width, req.height)

    @app.post("/edit")
    async def edit(req: EditRequest):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.edit(req.image, req.prompt)

    @app.post("/upscale")
    async def upscale(image: str = Form(...), scale: int = Form(2)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.upscale(image, scale)

    @app.post("/remove-bg")
    async def remove_bg(image: str = Form(...)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.remove_bg(image)

    @app.post("/describe")
    async def describe(image: str = Form(...)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.describe(image)

    @app.post("/auto")
    async def auto(prompt: str = Form(...), image: Optional[str] = Form(None)):
        from image_agent.agent import ImageAgent
        agent = ImageAgent()
        return await agent.run(prompt, image_b64=image or "")

    @app.get("/health")
    async def health():
        return {"status": "ok", "checks": {"storage": storage.health(), "redis": queue.health(), "imgproxy": {"status": "configured", "url": settings.imgproxy_url}}}

    @app.get("/metrics")
    async def metrics():
        body, content_type = render_metrics()
        return Response(content=body, media_type=content_type)

    @app.get("/models")
    async def models():
        return {"generation": ["sdxl", "flux", "fal"], "processing": ["pillow/libjpeg", "sharp-compatible", "imgproxy", "imagemagick-fallback"], "storage": ["local", "minio", "s3"]}

    @app.post("/v1/images/upload", dependencies=[Depends(require_api_key)])
    async def upload_image(
        file: UploadFile = File(...),
        tenant_id: str = Form(...),
        formats: list[str] | None = Form(None),
        resize_width: int | None = Form(None),
        quality: int = Form(80),
        webhook_url: str | None = Form(None),
    ):
        started = time.perf_counter()
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_MEDIA_TYPE", "message": "only image/* uploads are allowed"})
        data = await file.read()
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE", "message": "upload exceeds maximum file size"})
        if resize_width and (resize_width < 1 or resize_width > settings.max_resize_width):
            raise HTTPException(status_code=422, detail={"code": "INVALID_RESIZE_WIDTH", "message": f"resize_width must be <= {settings.max_resize_width}"})
        try:
            requested_formats = normalize_formats(formats)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_FORMAT", "message": str(exc)}) from exc
        job = queue.enqueue("upload", {"tenant_id": tenant_id, "webhook_url": webhook_url}, prefix="img")
        variants = processor.process(data, formats=requested_formats, quality=max(1, min(100, quality)), resize_width=resize_width)
        images: dict[str, str] = {}
        output_bytes = 0
        for variant in variants:
            key = f"{tenant_id}/{job.id}/{variant.format}"
            storage.put_bytes(key, variant.bytes)
            output_bytes += len(variant.bytes)
            images[variant.format] = f"/v1/images/{job.id}/{variant.format}"
            image_bytes_total.labels("output", variant.format).inc(len(variant.bytes))
        processing_time_ms = int((time.perf_counter() - started) * 1000)
        costs = estimate_operation_cost(input_bytes=len(data), output_bytes=output_bytes, processing_time_ms=processing_time_ms, rates=rates)
        image_bytes_total.labels("input", file.content_type).inc(len(data))
        image_cost_usd_total.labels(tenant_id).inc(costs["total_usd"])
        image_operations_total.labels("upload", tenant_id, "ready").inc()
        image_operation_latency_seconds.labels("upload").observe(processing_time_ms / 1000)
        log_event("image_processed", tenant_id=tenant_id, job_id=job.id, input_bytes=len(data), output_bytes=output_bytes, cost_usd=costs["total_usd"])
        return {"job_id": job.id, "status": "ready", "images": images, "metrics": {"input_bytes": len(data), "output_bytes": output_bytes, "compression_ratio": round(output_bytes / max(1, len(data)), 4), "processing_time_ms": processing_time_ms, "cost_estimate_usd": costs["total_usd"], "cost_breakdown": costs}}

    @app.get("/v1/images/{job_id}/{fmt}")
    async def get_image(job_id: str, fmt: str):
        matches = [key for key in storage.root.glob(f"*/{job_id}/{fmt}")]
        if not matches:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "image variant not found"})
        data = matches[0].read_bytes()
        etag = hashlib.sha256(data).hexdigest()
        return Response(content=data, media_type="image/webp" if fmt == "webp" else "image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable", "ETag": etag})

    @app.get("/image/{signature}/{resize}/{gravity}/{quality}/{fmt}/{source_path:path}")
    async def transform(signature: str, resize: str, gravity: str, quality: int, fmt: str, source_path: str):
        signed_path = f"/{resize}/{gravity}/{quality}/{fmt}/{source_path}"
        if not verify_path(signature, signed_path, key=settings.imgproxy_signature_key, salt=settings.imgproxy_signature_salt):
            raise HTTPException(status_code=403, detail={"code": "INVALID_SIGNATURE", "message": "imgproxy signature verification failed"})
        return {"status": "proxy", "upstream": f"{settings.imgproxy_url}/image/{signature}{signed_path}", "cache_headers": {"Cache-Control": "public, max-age=31536000", "ETag": "upstream"}}

    async def fetch_image_bytes(url: str) -> bytes:
        validate_public_url(url)
        if url.startswith("data:"):
            return base64.b64decode(url.split(",", 1)[1])
        if url.startswith("s3://"):
            raise HTTPException(status_code=501, detail={"code": "S3_FETCH_NOT_CONFIGURED", "message": "configure MinIO/S3 client for s3:// analysis"})
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    @app.post("/v1/images/analyze", dependencies=[Depends(require_api_key)])
    async def analyze(req: AnalyzeRequest):
        try:
            data = await fetch_image_bytes(req.image_url)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_IMAGE_URL", "message": str(exc)}) from exc
        result = metadata.analyze(data, req.analysis)
        result["image_id"] = f"img_{uuid4().hex[:12]}"
        image_operations_total.labels("analyze", req.tenant_id, "ready").inc()
        image_operation_latency_seconds.labels("analyze").observe(result["processing_time_ms"] / 1000)
        return result

    @app.post("/v1/images/batch-optimize", dependencies=[Depends(require_api_key)])
    async def batch_optimize(req: BatchOptimizeRequest):
        for item in req.images:
            validate_public_url(item.url)
            normalize_formats([item.target_format])
        job = queue.enqueue("batch-optimize", req.model_dump(mode="json"), prefix="batch")
        image_operations_total.labels("batch-optimize", req.tenant_id, "queued").inc()
        return {"batch_id": job.id, "status": "queued", "count": len(req.images)}

    return app
