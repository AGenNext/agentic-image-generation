from __future__ import annotations

import base64
import hashlib
from typing import Any, Dict, Optional

from tools.comfy_client import ComfyUIClient
from tools.workflows import improve_workflow, txt2img_workflow


def _dummy_image_data(prompt: str) -> str:
    digest = hashlib.sha256(prompt.encode("utf-8")).digest()
    return "data:image/png;base64," + base64.b64encode(digest).decode("utf-8")


def refine_prompt(prompt: str, style_hint: str = "", context: Optional[Dict[str, Any]] = None) -> str:
    context_hint = ""
    if context and context.get("history"):
        context_hint = " coherent composition"
    return f"{prompt.strip()}, {style_hint}{context_hint}".strip(", ")


def generate_image(prompt: str) -> Dict[str, Any]:
    client = ComfyUIClient()
    workflow = txt2img_workflow(prompt)
    if client.healthcheck():
        try:
            result = client.run_workflow(workflow)
            return {
                "image": result["images"][0],
                "backend": "comfyui",
                "meta": {"prompt_id": result["prompt_id"]},
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "image": _dummy_image_data(prompt),
                "backend": "dummy",
                "meta": {"error": f"ComfyUI fallback: {exc}"},
            }

    return {"image": _dummy_image_data(prompt), "backend": "dummy", "meta": {"reason": "ComfyUI unavailable"}}


def improve_image(prompt: str, feedback: str) -> Dict[str, str]:
    improvement = f"{prompt}. Improve based on critique: {feedback}"
    _ = improve_workflow(improvement)
    return {"improved_prompt": improvement}


def critique_image(prompt: str, image: str, iteration: int) -> Dict[str, Any]:
    score_base = 0.62 + (0.12 * iteration)
    score = min(score_base, 0.95)
    if image.startswith("http"):
        feedback = "Image quality is strong; minor enhancement to composition recommended."
    else:
        feedback = "Fallback render detected; refine prompt for clarity and visual fidelity."
    return {"score": score, "feedback": f"{feedback} Prompt: {prompt[:140]}"}
