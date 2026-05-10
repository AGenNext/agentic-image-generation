from __future__ import annotations

import base64
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from image_agent.api import create_app
from image_agent.utils.costs import estimate_operation_cost
from image_agent.utils.hmac_signer import sign_path, verify_path
from image_agent.utils.validators import normalize_formats, validate_public_url


def png_bytes(size=(32, 32), color=(255, 0, 0)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, format="PNG")
    return out.getvalue()


def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("IMAGE_AGENT_API_KEYS", "test-key")
    return TestClient(create_app())


def test_hmac_sign_and_verify_round_trip():
    path = "/300x200/sm/80/webp/s3:bucket:photos/user123.jpg"
    signature = sign_path(path, key="secret", salt="salt")
    assert verify_path(signature, path, key="secret", salt="salt")


def test_hmac_rejects_tampered_path():
    signature = sign_path("/300x200/sm/80/webp/a.jpg", key="secret", salt="salt")
    assert not verify_path(signature, "/300x200/sm/80/webp/b.jpg", key="secret", salt="salt")


def test_cost_calculator_reports_total():
    result = estimate_operation_cost(input_bytes=2_500_000, output_bytes=450_000, processing_time_ms=320)
    assert result["total_usd"] > 0
    assert {"storage_usd", "cpu_usd", "bandwidth_usd", "total_usd"} <= set(result)


def test_format_normalization_defaults():
    assert normalize_formats(None) == ["webp", "avif", "original"]


def test_format_validation_rejects_unknown():
    try:
        normalize_formats(["exe"])
    except ValueError as exc:
        assert "unsupported format" in str(exc)
    else:
        raise AssertionError("expected invalid format")


def test_ssrf_validation_rejects_loopback():
    try:
        validate_public_url("http://127.0.0.1/image.png")
    except ValueError as exc:
        assert "private network" in str(exc)
    else:
        raise AssertionError("expected loopback rejection")


def test_health_includes_dependency_checks(tmp_path, monkeypatch):
    res = client(tmp_path, monkeypatch).get("/health")
    assert res.status_code == 200
    assert res.json()["checks"]["storage"]["status"] == "ok"


def test_metrics_endpoint_exposes_prometheus(tmp_path, monkeypatch):
    res = client(tmp_path, monkeypatch).get("/metrics")
    assert res.status_code == 200
    assert "image_operations_total" in res.text


def test_upload_processes_webp_and_original(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    res = c.post(
        "/v1/images/upload",
        headers={"X-Image-API-Key": "test-key"},
        files={"file": ("sample.png", png_bytes(), "image/png")},
        data={"tenant_id": "acme", "formats": ["webp", "original"], "quality": "80"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["status"] == "ready"
    assert payload["metrics"]["input_bytes"] > payload["metrics"]["output_bytes"] / 10
    assert "webp" in payload["images"]


def test_upload_requires_api_key(tmp_path, monkeypatch):
    res = client(tmp_path, monkeypatch).post(
        "/v1/images/upload",
        files={"file": ("sample.png", png_bytes(), "image/png")},
        data={"tenant_id": "acme"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_analyze_data_url_returns_exif_and_colors(tmp_path, monkeypatch):
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes()).decode()
    res = client(tmp_path, monkeypatch).post(
        "/v1/images/analyze",
        headers={"X-Image-API-Key": "test-key"},
        json={"tenant_id": "acme", "image_url": data_url, "analysis": ["exif", "colors", "objects", "text"]},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["exif"]["width"] == 32
    assert payload["colors"][0]["hex"] == "#FF0000"
    assert payload["objects"] == []


def test_batch_optimize_queues_job(tmp_path, monkeypatch):
    res = client(tmp_path, monkeypatch).post(
        "/v1/images/batch-optimize",
        headers={"X-Image-API-Key": "test-key"},
        json={"tenant_id": "acme", "images": [{"url": "s3://bucket/img1.jpg", "target_format": "webp"}]},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "queued"


def test_transform_rejects_bad_signature(tmp_path, monkeypatch):
    res = client(tmp_path, monkeypatch).get("/image/bad/300x200/sm/80/webp/s3:bucket:path.jpg")
    assert res.status_code == 403
