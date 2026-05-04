from __future__ import annotations

from typing import Any, Dict, Tuple

import gradio as gr
import requests

API_URL = "http://127.0.0.1:8000/generate"


def call_api(prompt: str) -> Tuple[str, str]:
    try:
        response = requests.post(API_URL, json={"prompt": prompt}, timeout=180)
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
        feedback = f"{payload.get('feedback', '')}\nIterations: {payload.get('iterations', 0)}"
        return payload.get("image", ""), feedback
    except Exception as exc:  # noqa: BLE001
        return "", f"API call failed: {exc}"


with gr.Blocks(title="Agentic Image Generation") as demo:
    gr.Markdown("# Agentic Image Generation UI")
    prompt = gr.Textbox(label="Prompt", placeholder="Describe the image you want", lines=3)
    run_btn = gr.Button("Generate")
    image = gr.Image(label="Generated Image")
    feedback = gr.Textbox(label="Critic Feedback", lines=5)

    run_btn.click(fn=call_api, inputs=[prompt], outputs=[image, feedback])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
