from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["prompt_id"])

    def get_images(self, prompt_id: str, poll_interval: float = 1.0, max_wait: int = 90) -> List[str]:
        waited = 0.0
        while waited < max_wait:
            history_resp = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=self.timeout)
            if history_resp.status_code == 200:
                history_data = history_resp.json()
                outputs = history_data.get(prompt_id, {}).get("outputs", {})
                images: List[str] = []
                for node_output in outputs.values():
                    for img in node_output.get("images", []):
                        filename = img.get("filename")
                        subfolder = img.get("subfolder", "")
                        img_type = img.get("type", "output")
                        if filename:
                            view_url = (
                                f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
                            )
                            images.append(view_url)
                if images:
                    return images
            time.sleep(poll_interval)
            waited += poll_interval
        raise TimeoutError(f"Timed out waiting for ComfyUI prompt_id={prompt_id}")

    def run_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        prompt_id = self.queue_prompt(workflow)
        images = self.get_images(prompt_id)
        return {"prompt_id": prompt_id, "images": images}

    def healthcheck(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/system_stats", timeout=3)
            return response.ok
        except requests.RequestException:
            return False
