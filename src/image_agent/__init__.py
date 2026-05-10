"""Image Agent — generate, edit, upscale, remove bg, describe, and process images."""

__version__ = "0.2.0"


def __getattr__(name: str):
    if name == "ImageAgent":
        from image_agent.agent import ImageAgent
        return ImageAgent
    if name == "create_app":
        from image_agent.api import create_app
        return create_app
    raise AttributeError(name)


__all__ = ["ImageAgent", "create_app"]
