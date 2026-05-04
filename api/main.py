from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.langgraph_agent import LangGraphAgent

app = FastAPI(title="Agentic Image Generation API", version="1.0.0")
agent = LangGraphAgent(max_iterations=3)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User prompt for image generation")


class GenerateResponse(BaseModel):
    image: str
    feedback: str
    iterations: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    result = agent.run(prompt=req.prompt)
    return GenerateResponse(
        image=result.get("image", ""),
        feedback=result.get("feedback", "No feedback generated."),
        iterations=result.get("iterations", 0),
    )
