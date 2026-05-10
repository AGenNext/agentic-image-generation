# LangFlow Agent Skill

This skill provides a LangFlow agent that can:
- Create custom components (Python code files)
- Upload components to LangFlow
- Create flows via API
- Import flow JSONs
- Build/run flows

## Installation

No additional installation required. This skill uses the LangFlow agent module at `/workspace/project/langflow_agent.py`.

## Classes

### LangFlowAgent

Main class for managing LangFlow workflows.

```python
import sys
sys.path.insert(0, '/workspace/project')
from langflow_agent import LangFlowAgent

agent = LangFlowAgent(
    base_url="http://localhost:7860",
    api_key="your-api-key"
)
```

## Methods

### Flow Management

- `list_flows()` - List all flows
- `get_flow(flow_id)` - Get a flow by ID
- `create_flow(name, description, data, project_id)` - Create a new flow
- `update_flow(flow_id, name, description, data)` - Update an existing flow
- `delete_flow(flow_id)` - Delete a flow
- `import_flow_json(file_path, project_id)` - Import a flow from JSON file
- `export_flow(flow_id)` - Export a flow to JSON

### Flow Execution

- `run_flow(flow_id, input_data, tweaks, stream)` - Run/execute a flow
- `run_flow_stream(flow_id, input_data, tweaks)` - Run flow with streaming

### Custom Components

- `create_custom_component(name, description, category, inputs, outputs, code)` - Create component code
- `save_component(code, name, save_dir)` - Save component to file

### Project Management

- `list_projects()` - List all projects
- `create_project(name, description)` - Create a new project
- `delete_project(project_id)` - Delete a project

### File Management

- `list_files(flow_id)` - List uploaded files
- `upload_file(file_path, flow_id)` - Upload a file
- `delete_file(file_id)` - Delete a file

### API Keys

- `list_api_keys()` - List all API keys
- `create_api_key(name, expires_at)` - Create a new API key
- `delete_api_key(api_key_id)` - Delete an API key

## CLI Usage

```bash
# Check connection
python /workspace/project/langflow_agent.py health --url http://localhost:7860 --api-key YOUR_KEY

# List all flows
python /workspace/project/langflow_agent.py list-flows --url http://localhost:7860 --api-key YOUR_KEY

# Create a new flow
python /workspace/project/langflow_agent.py create-flow --name "My Agent" --description "A new agent"

# Import flow from JSON
python /workspace/project/langflow_agent.py import-flow path/to/flow.json --url http://localhost:7860 --api-key YOUR_KEY

# Run a flow
python /workspace/project/langflow_agent.py run-flow FLOW_ID --input '{"input_value": "Hello!"}'

# Create custom component
python /workspace/project/langflow_agent.py create-component --name "MyProcessor" --description "Processes data"

# Create project
python /workspace/project/langflow_agent.py create-project --name "My Project"
```

## Environment Variables

- `LANGFLOW_URL` - LangFlow server URL (default: http://localhost:7860)
- `LANGFLOW_API_KEY` - LangFlow API key for authentication

## API Endpoints Used

The agent uses these LangFlow API endpoints:
- `POST /api/v1/flows` - Create flow
- `GET /api/v1/flows` - List flows
- `GET /api/v1/flows/{flow_id}` - Get flow
- `PATCH /api/v1/flows/{flow_id}` - Update flow
- `DELETE /api/v1/flows/{flow_id}` - Delete flow
- `POST /api/v1/flows/upload` - Import flow from JSON
- `POST /api/v1/run/{flow_id}` - Run/execute flow
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects
- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files` - List files
- `POST /api/v1/api_key` - Create API key
- `GET /api/v1/api_key` - List API keys