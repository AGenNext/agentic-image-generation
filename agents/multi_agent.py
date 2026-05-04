from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from tools.image_tools import critique_image, generate_image, refine_prompt


@dataclass
class PlannerAgent:
    """Refines user prompts before image generation."""

    style_hint: str = "cinematic, highly detailed"

    def plan(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        refined = refine_prompt(prompt=prompt, style_hint=self.style_hint, context=context)
        return {"refined_prompt": refined, "plan_notes": "Prompt refined by PlannerAgent."}


@dataclass
class GeneratorAgent:
    """Generates images from prompts via image tools."""

    def generate(self, prompt: str) -> Dict[str, Any]:
        image_result = generate_image(prompt)
        return {
            "image": image_result["image"],
            "backend": image_result["backend"],
            "meta": image_result.get("meta", {}),
        }


@dataclass
class CriticAgent:
    """Evaluates generated images and suggests improvements."""

    quality_threshold: float = 0.72

    def critique(self, prompt: str, image: str, iteration: int) -> Dict[str, Any]:
        critique = critique_image(prompt=prompt, image=image, iteration=iteration)
        critique["accept"] = critique["score"] >= self.quality_threshold
        return critique
