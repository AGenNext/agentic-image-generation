# Image Agent

A composable image-generation and image-processing service with FastAPI, pluggable processors, local/S3-shaped storage, imgproxy-compatible signatures, Prometheus metrics, and per-operation cost attribution.

This repository now includes the new **image agent** implemented in PR #2, which can generate images from textual prompts using the `generate_image(prompt, style, width, height)` function. The function supports placeholder API simulation and returns a dictionary with `images` and a `description`.

## Production Goals

- URL/upload → processed images with a p99 target below 500 ms for common web assets.
- No vendor lock-in: local storage for development, MinIO/S3 shape for production, and imgproxy-compatible transform URLs.
- Cost transparency per tenant: input bytes, output bytes, CPU time, bandwidth, and estimated USD per operation.
- Observable API: `/metrics`, structured JSON logs, dependency-aware `/health`.
- India data residency friendly: deploy MinIO/Redis/app/logs on an India VPS or `ap-south-1` equivalent.

## Image Agent Usage

### Example Function Call

```python
from image_agent import generate_image

result = generate_image("A sunset over the mountains", style="photorealistic", width=1024, height=1024)
print(result['description'])
# Access images via result['images']
```

### API Surface

... (existing README content continues)