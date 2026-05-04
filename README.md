# Agentic Image Generation System

A production-oriented, modular image-generation stack using a LangGraph-style multi-agent DAG with ComfyUI, FastAPI, and Gradio.

## Architecture

- **PlannerAgent**: refines user prompt.
- **GeneratorAgent**: renders image via ComfyUI (or fallback dummy renderer).
- **CriticAgent**: scores output and provides feedback.
- **LangGraphAgent Coordinator**: runs planner → generator → critic → improver transitions as a DAG.

## Project Layout

- `agents/langgraph_agent.py` - DAG coordinator and AgentState.
- `agents/multi_agent.py` - planner, generator, critic role agents.
- `tools/comfy_client.py` - ComfyUI API client.
- `tools/workflows.py` - workflow template builders.
- `tools/image_tools.py` - generation, critique, prompt refinement, and fallback logic.
- `api/main.py` - FastAPI service endpoint.
- `ui/app.py` - Gradio live UI.

## Prerequisites

- Python 3.10+
- Optional: running ComfyUI server at `http://127.0.0.1:8188`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run ComfyUI (Optional but Recommended)

1. Install ComfyUI from its official repository.
2. Start ComfyUI so the API is available at `http://127.0.0.1:8188`.
3. Verify endpoint health:

```bash
curl http://127.0.0.1:8188/system_stats
```

If ComfyUI is unavailable, the system auto-falls back to a deterministic dummy image output.

## Start API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Usage

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A futuristic city at sunset"}'
```

Response:

```json
{
  "image": "<url-or-data-uri>",
  "feedback": "...",
  "iterations": 1
}
```

## Launch Gradio UI

```bash
python ui/app.py
```

Then open: `http://127.0.0.1:7860`

## Notes

- The planner/generator/critic/improver flow is modular and extensible.
- ComfyUI workflows can be replaced by custom templates in `tools/workflows.py`.
- The system is intentionally designed for clear separation of concerns and production-friendly structure.
