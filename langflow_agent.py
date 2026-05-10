"""
LangFlow Agent - A Python agent for managing LangFlow workflows

This module provides a LangFlow agent that can:
- Create custom components (Python code files)
- Upload custom components to LangFlow
- Create flows via API
- Upload flow JSONs
- Build flows (run them)

Usage:
    agent = LangFlowAgent(base_url="http://localhost:7860", api_key="your-api-key")
    
    # Create and upload a custom component
    component_code = agent.create_custom_component(...)
    agent.upload_component(component_code)
    
    # Create a new flow
    flow = agent.create_flow(name="My Flow", data={...})
    
    # Import flow from JSON
    flow = agent.import_flow_json("path/to/flow.json")
    
    # Build/run a flow
    result = agent.run_flow(flow_id, input_data={...})
"""

import os
import json
import requests
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class LangFlowAgent:
    """
    LangFlow Agent for managing flows, components, and running workflows.
    
    Attributes:
        base_url: LangFlow server URL
        api_key: LangFlow API key for authentication
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:7860",
        api_key: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize the LangFlow agent.
        
        Args:
            base_url: LangFlow server URL (default: http://localhost:7860)
            api_key: LangFlow API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("LANGFLOW_API_KEY")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-api-key": self.api_key or ""
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an API request to LangFlow.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.RequestException: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        # Update headers with API key if provided
        if self.api_key:
            self.session.headers["x-api-key"] = self.api_key
        
        response = self.session.request(
            method=method,
            url=url,
            timeout=self.timeout,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    
    def check_connection(self) -> bool:
        """
        Check if LangFlow server is reachable.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    # =========================================================================
    # Custom Components Methods
    # =========================================================================
    
    def create_custom_component(
        self,
        name: str,
        description: str = "Custom component",
        category: str = "Custom",
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        code: Optional[str] = None
    ) -> str:
        """
        Create a custom component Python code.
        
        Args:
            name: Component name (e.g., "MyProcessor")
            description: Component description
            category: Component category for organization
            inputs: Input specifications (field name -> type mapping)
            outputs: Output specifications
            
        Returns:
            Python code as string
        """
        inputs = inputs or {}
        outputs = outputs or {}
        
        # Build the component code
        component_code = f'''"""Custom component: {name}"""

from typing import Any, Dict, Optional

from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data, Message


class {name}(Component):
    """
    {description}
    """
    
    display_name = "{name}"
    description = "{description}"
    name = "{name.lower().replace(" ", "_")}"
    icon = "Custom"
    
'''
        
        # Add inputs
        if inputs:
            component_code += "    inputs = [\n"
            for field_name, field_type in inputs.items():
                if field_type == "str":
                    component_code += f'        MessageTextInput(name="{field_name}", display_name="{field_name.replace("_", " ").title()}"),\n'
                # Add other types as needed
            component_code += "    ]\n\n"
        else:
            component_code += "    inputs = []\n\n"
        
        # Add outputs
        if outputs:
            component_code += "    outputs = [\n"
            for output_name, output_type in outputs.items():
                component_code += f'        Output(name="{output_name}", display_name="{output_name.replace("_", " ").title()}", method="{output_name}"),\n'
            component_code += "    ]\n\n"
        else:
            component_code += "    outputs = [\n"
            component_code += '        Output(name="response", display_name="Response", method="response"),\n'
            component_code += "    ]\n\n"
        
        # Add the build method
        custom_code = code or """
    def response(self) -> Message:
        '''Default response method'''
        # TODO: Implement your custom logic here
        return Message(text="Hello from custom component!")
"""
        
        component_code += f'''    def build(self):
        {custom_code}
'''
        
        component_code += """
    def _process_result(self, result: Any) -> Any:
        '''Process the result before returning'''
        return result
"""
        
        return component_code
    
    def save_component(
        self,
        code: str,
        name: str,
        save_dir: str = "./custom_components"
    ) -> str:
        """
        Save a custom component to a Python file.
        
        Args:
            code: Component Python code
            name: Component name
            save_dir: Directory to save the component
            
        Returns:
            Path to the saved file
        """
        # Create directory structure: save_dir/category/__init__.py
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # Save the component file
        file_path = Path(save_dir) / f"{name.lower().replace(' ', '_')}.py"
        file_path.write_text(code)
        
        # Create __init__.py if it doesn't exist
        init_path = Path(save_dir) / "__init__.py"
        if not init_path.exists():
            init_path.write_text(f'"""Custom components for LangFlow"""\n')
        
        return str(file_path)
    
    def get_components_path(self) -> str:
        """
        Get the components path from environment or return default.
        
        Returns:
            Path to custom components directory
        """
        return os.environ.get(
            "LANGFLOW_COMPONENTS_PATH",
            "./custom_components"
        )
    
    # =========================================================================
    # Flow Management Methods
    # =========================================================================
    
    def list_flows(
        self,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all flows.
        
        Args:
            project_id: Filter by project ID
            limit: Maximum number of flows to return
            offset: Offset for pagination
            
        Returns:
            List of flow dictionaries
        """
        params = {"limit": limit, "offset": offset}
        if project_id:
            params["folder_id"] = project_id
        
        return self._request("GET", "/api/v1/flows", params=params)
    
    def get_flow(self, flow_id: str) -> Dict[str, Any]:
        """
        Get a flow by ID.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            Flow data dictionary
        """
        return self._request("GET", f"/api/v1/flows/{flow_id}")
    
    def create_flow(
        self,
        name: str,
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new flow.
        
        Args:
            name: Flow name
            description: Flow description
            data: Flow data (nodes and edges)
            project_id: Target project/folder ID
            
        Returns:
            Created flow data
        """
        flow_data = {
            "name": name,
            "description": description,
            "data": data or {"nodes": [], "edges": []}
        }
        
        if project_id:
            params = {"folder_id": project_id}
            return self._request("POST", "/api/v1/flows", json=flow_data, params=params)
        
        return self._request("POST", "/api/v1/flows", json=flow_data)
    
    def update_flow(
        self,
        flow_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing flow.
        
        Args:
            flow_id: Flow ID
            name: New flow name
            description: New flow description
            data: New flow data
            
        Returns:
            Updated flow data
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if data is not None:
            update_data["data"] = data
        
        return self._request("PATCH", f"/api/v1/flows/{flow_id}", json=update_data)
    
    def delete_flow(self, flow_id: str) -> bool:
        """
        Delete a flow.
        
        Args:
            flow_id: Flow ID to delete
            
        Returns:
            True if deletion was successful
        """
        self._request("DELETE", f"/api/v1/flows/{flow_id}")
        return True
    
    def import_flow_json(
        self,
        file_path: Union[str, Path],
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import a flow from a JSON file.
        
        Args:
            file_path: Path to the flow JSON file
            project_id: Target project/folder ID
            
        Returns:
            Imported flow data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Flow file not found: {file_path}")
        
        with open(file_path, "r") as f:
            flow_data = json.load(f)
        
        files = {
            "file": (file_path.name, f.read(), "application/json")
        }
        
        params = {}
        if project_id:
            params["folder_id"] = project_id
        
        # Use multipart form data for file upload
        url = f"{self.base_url}/api/v1/flows/upload"
        response = self.session.post(
            url,
            files=files,
            data=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def export_flow(self, flow_id: str) -> Dict[str, Any]:
        """
        Export a flow to JSON.
        
        Args:
            flow_id: Flow ID
            
        Returns:
            Flow data as dictionary
        """
        return self._request("GET", f"/api/v1/flows/download", params={"flow_ids": [flow_id]})
    
    # =========================================================================
    # Project Management Methods
    # =========================================================================
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects.
        
        Returns:
            List of project dictionaries
        """
        return self._request("GET", "/api/v1/projects")
    
    def create_project(
        self,
        name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Project description
            
        Returns:
            Created project data
        """
        return self._request(
            "POST",
            "/api/v1/projects",
            json={"name": name, "description": description}
        )
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if deletion was successful
        """
        self._request("DELETE", f"/api/v1/projects/{project_id}")
        return True
    
    # =========================================================================
    # Flow Execution Methods
    # =========================================================================
    
    def run_flow(
        self,
        flow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Run a flow.
        
        Args:
            flow_id: Flow ID to run
            input_data: Input data for the flow (e.g., {"input_value": "Hello"})
            tweaks: Runtime overrides for component inputs
            stream: Whether to enable streaming
            
        Returns:
            Flow execution result
        """
        payload = {
            "input_data": input_data or {},
        }
        
        if tweaks:
            payload["tweaks"] = tweaks
        
        params = {"stream": str(stream).lower()}
        
        return self._request(
            "POST",
            f"/api/v1/run/{flow_id}",
            json=payload,
            params=params
        )
    
    def run_flow_stream(
        self,
        flow_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        tweaks: Optional[Dict[str, Any]] = None
    ):
        """
        Run a flow with streaming responses.
        
        Args:
            flow_id: Flow ID to run
            input_data: Input data for the flow
            tweaks: Runtime overrides
            
        Yields:
            Stream response chunks
        """
        payload = {
            "input_data": input_data or {},
        }
        
        if tweaks:
            payload["tweaks"] = tweaks
        
        url = f"{self.base_url}/api/v1/run/{flow_id}?stream=true"
        
        with self.session.post(
            url,
            json=payload,
            stream=True,
            timeout=self.timeout
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_lines():
                if chunk:
                    yield chunk.decode("utf-8")
    
    # =========================================================================
    # File Management Methods
    # =========================================================================
    
    def list_files(self, flow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List uploaded files.
        
        Args:
            flow_id: Filter by flow ID
            
        Returns:
            List of file dictionaries
        """
        params = {}
        if flow_id:
            params["flow_id"] = flow_id
        
        return self._request("GET", "/api/v1/files", params=params)
    
    def upload_file(
        self,
        file_path: Union[str, Path],
        flow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to LangFlow.
        
        Args:
            file_path: Path to the file to upload
            flow_id: Target flow ID (optional)
            
        Returns:
            Uploaded file data
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "rb") as f:
            files = {
                "file": (file_path.name, f, "application/octet-stream")
            }
            
            params = {}
            if flow_id:
                params["flow_id"] = flow_id
            
            url = f"{self.base_url}/api/v1/files/upload"
            response = self.session.post(
                url,
                files=files,
                data=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file.
        
        Args:
            file_id: File ID
            
        Returns:
            True if deletion was successful
        """
        self._request("DELETE", f"/api/v1/files/{file_id}")
        return True
    
    # =========================================================================
    # API Key Management Methods
    # =========================================================================
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """
        List all API keys.
        
        Returns:
            List of API key dictionaries
        """
        return self._request("GET", "/api/v1/api_key")
    
    def create_api_key(
        self,
        name: str,
        expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new API key.
        
        Args:
            name: API key name
            expires_at: Expiration date (ISO format)
            
        Returns:
            Created API key data (includes the secret)
        """
        data = {"name": name}
        if expires_at:
            data["expires_at"] = expires_at
        
        return self._request("POST", "/api/v1/api_key", json=data)
    
    def delete_api_key(self, api_key_id: str) -> bool:
        """
        Delete an API key.
        
        Args:
            api_key_id: API key ID
            
        Returns:
            True if deletion was successful
        """
        self._request("DELETE", f"/api/v1/api_key/{api_key_id}")
        return True


# =============================================================================
# Chat Interface
# =============================================================================

def run_chat_interface(agent: LangFlowAgent, flow_id: str, system_prompt: str = None, stream: bool = False):
    """
    Interactive chat interface with a flow.
    
    Args:
        agent: LangFlowAgent instance
        flow_id: Flow ID to chat with
        system_prompt: Optional system prompt
        stream: Enable streaming responses
    """
    print(f"{Colors.CYAN}=== LangFlow Chat Interface ==={Colors.NC}")
    print(f"Flow ID: {flow_id}")
    print("Type 'quit' or 'exit' to end the session")
    print("Type 'clear' to clear chat history")
    print("")
    
    # Get flow info
    try:
        flow = agent.get_flow(flow_id)
        print_status(f"Connected to flow: {flow.get('name', flow_id)}", "success")
    except Exception as e:
        print_status(f"Could not get flow info: {e}", "warning")
    
    print("")
    
    chat_history = []
    
    # If system prompt provided, add to history
    if system_prompt:
        chat_history.append({"type": "system", "content": system_prompt})
    
    while True:
        try:
            user_input = input(f"{Colors.GREEN}You:{Colors.NC} ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit"]:
                print_status("Chat session ended", "info")
                break
            
            if user_input.lower() == "clear":
                chat_history = []
                print_status("Chat history cleared", "success")
                continue
            
            # Add user message to history
            chat_history.append({"type": "user", "content": user_input})
            
            # Prepare input for flow
            input_data = {"input_value": user_input, "input_type": "chat", "output_type": "chat"}
            
            print(f"{Colors.BLUE}Assistant:{Colors.NC} ", end="", flush=True)
            
            if stream:
                # Streaming mode
                response_text = ""
                for chunk in agent.run_flow_stream(flow_id, input_data):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                print("")
                response_content = response_text
            else:
                # Non-streaming mode
                result = agent.run_flow(flow_id, input_data)
                
                # Extract response
                if isinstance(result, dict):
                    response_content = result.get("outputs", [{}])[0].get("outputs", [{}])[0].get("message", {}).get("text", "")
                    print(response_content)
                else:
                    response_content = str(result)
                    print(response_content)
            
            # Add assistant response to history
            chat_history.append({"type": "assistant", "content": response_content})
            
        except KeyboardInterrupt:
            print_status("\nChat session ended", "info")
            break
        except Exception as e:
            print_status(f"Error: {str(e)}", "error")


def run_web_chat_ui(agent: LangFlowAgent, host: str = "0.0.0.0", port: int = 8080):
    """
    Run a web-based chat UI for LangFlow.
    
    Args:
        agent: LangFlowAgent instance
        host: Host to bind to
        port: Port to listen on
    """
    try:
        from flask import Flask, request, jsonify, render_template_string
    except ImportError:
        print_status("Flask not installed. Installing...", "info")
        import subprocess
        subprocess.run(["pip", "install", "flask"], check=True)
        from flask import Flask, request, jsonify, render_template_string
    
    app = Flask(__name__)
    
    # Store the agent and flow_id
    app.config["LANGFLOW_AGENT"] = agent
    
    HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LangFlow Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: #16213e;
            padding: 15px 20px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .header h1 { font-size: 1.2rem; color: #00d9ff; }
        .config {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .config input {
            background: #0f3460;
            border: 1px solid #1a1a2e;
            color: #fff;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        .config input::placeholder { color: #888; }
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
        }
        .message.user {
            align-self: flex-end;
            background: #0f3460;
            border-bottom-right-radius: 4px;
        }
        .message.assistant {
            align-self: flex-start;
            background: #16213e;
            border-bottom-left-radius: 4px;
        }
        .message.system {
            align-self: center;
            background: #2d2d44;
            font-size: 0.85rem;
            color: #aaa;
        }
        .input-area {
            background: #16213e;
            padding: 15px 20px;
            border-top: 1px solid #0f3460;
            display: flex;
            gap: 10px;
        }
        .input-area input {
            flex: 1;
            background: #0f3460;
            border: 1px solid #1a1a2e;
            color: #fff;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 1rem;
        }
        .input-area input:focus {
            outline: none;
            border-color: #00d9ff;
        }
        .input-area button {
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .input-area button:hover { background: #00b8d9; }
        .input-area button:disabled { background: #444; cursor: not-allowed; }
        .typing { display: none; align-self: flex-start; background: #16213e; padding: 12px 16px; border-radius: 12px; color: #888; }
        .typing.active { display: block; }
        .error { align-self: center; background: #ff4444; color: #fff; padding: 10px 16px; border-radius: 8px; }
        @media (max-width: 600px) { .config { display: none; } .message { max-width: 95%; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 LangFlow Chat</h1>
        <div class="config">
            <input type="text" id="flowId" placeholder="Flow ID" value="{{ flow_id }}">
            <button id="connectBtn">Connect</button>
        </div>
    </div>
    <div class="chat-container" id="chatContainer">
        <div class="message system">Welcome to LangFlow Chat! Enter a Flow ID and start chatting.</div>
    </div>
    <div class="typing" id="typing">Thinking...</div>
    <div class="input-area">
        <input type="text" id="userInput" placeholder="Type your message..." autofocus>
        <button id="sendBtn">Send</button>
    </div>
    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const typing = document.getElementById('typing');
        const flowIdInput = document.getElementById('flowId');
        
        let currentFlowId = '{{ flow_id }}' || '';
        
        function addMessage(content, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = content;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        function showError(message) {
            const div = document.createElement('div');
            div.className = 'error';
            div.textContent = message;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message || !currentFlowId) return;
            
            userInput.value = '';
            addMessage(message, 'user');
            typing.classList.add('active');
            sendBtn.disabled = true;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flow_id: currentFlowId, message: message })
                });
                
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Request failed');
                
                const reply = data.response || data.outputs?.[0]?.outputs?.[0]?.message?.text || JSON.stringify(data);
                addMessage(reply, 'assistant');
            } catch (error) {
                showError(error.message);
            } finally {
                typing.classList.remove('active');
                sendBtn.disabled = false;
                userInput.focus();
            }
        }
        
        document.getElementById('connectBtn').addEventListener('click', () => {
            currentFlowId = flowIdInput.value.trim();
            if (currentFlowId) { chatContainer.innerHTML = ''; addMessage('Connected to flow: ' + currentFlowId, 'system'); }
        });
        
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
    </script>
</body>
</html>
'''
    
    @app.route("/")
    def index():
        flow_id = request.args.get("flow_id", "")
        return render_template_string(HTML_TEMPLATE, flow_id=flow_id)
    
    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.json
        flow_id = data.get("flow_id")
        message = data.get("message", "")
        
        if not flow_id: return jsonify({"error": "Flow ID required"}), 400
        if not message: return jsonify({"error": "Message required"}), 400
        
        try:
            input_data = {"input_value": message, "input_type": "chat", "output_type": "chat"}
            result = agent.run_flow(flow_id, input_data)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/api/flows")
    def list_flows_api():
        try: return jsonify(agent.list_flows())
        except Exception as e: return jsonify({"error": str(e)}), 500
    
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})
    
    print(f"""


{Colors.CYAN}======================================={Colors.NC}
{Colors.CYAN}   LangFlow Web Chat UI{Colors.NC}
{Colors.CYAN}======================================={Colors.NC}

Chat UI starting at: http://{host}:{port}

Endpoints:
  - Main UI: http://{host}:{port}/
  - API: http://{host}:{port}/api/chat
  - Health: http://{host}:{port}/health

How to use:
  1. Open http://{host}:{port} in your browser
  2. Enter your Flow ID
  3. Start chatting!
""")
    
    app.run(host=host, port=port, debug=False)


# =============================================================================
# CLI Interface
# =============================================================================

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    
    # ANSI colors for CLI
    class Colors:
        RED = '\033[0;31m'
        GREEN = '\033[0;32m'
        YELLOW = '\033[1;33m'
        BLUE = '\033[0;34m'
        CYAN = '\033[0;36m'
        NC = '\033[0m'
    
    def print_status(msg: str, status: str = "info"):
        if status == "success":
            print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")
        elif status == "error":
            print(f"{Colors.RED}✗ {msg}{Colors.NC}")
        elif status == "warning":
            print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")
        elif status == "info":
            print(f"{Colors.BLUE}ℹ {msg}{Colors.NC}")
        else:
            print(msg)
    
    parser = argparse.ArgumentParser(
        description="LangFlow Agent - Manage flows, components, and run workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all flows
  python langflow_agent.py list-flows --url http://localhost:7860 --api-key YOUR_KEY
  
  # Create a new flow
  python langflow_agent.py create-flow --name "My Agent" --description "A new agent"
  
  # Import flow from JSON
  python langflow_agent.py import-flow path/to/flow.json --url http://localhost:7860 --api-key YOUR_KEY
  
  # Create custom component
  python langflow_agent.py create-component --name "MyProcessor" --description "Processes data"
  
  # Save component to file
  python langflow_agent.py create-component --name "TextProcessor" --output ./custom_components
  
  # Run a flow
  python langflow_agent.py run-flow FLOW_ID --input '{"input_value": "Hello!"}'
  
  # Create project
  python langflow_agent.py create-project --name "My Project"
        """
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("LANGFLOW_URL", "http://localhost:7860"),
        help="LangFlow server URL"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LANGFLOW_API_KEY"),
        help="LangFlow API key for authentication"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # -------------------------------------------------------------------------
    # List flows command
    # -------------------------------------------------------------------------
    list_flows_parser = subparsers.add_parser(
        "list-flows",
        help="List all flows"
    )
    list_flows_parser.add_argument(
        "--project-id",
        help="Filter by project/folder ID"
    )
    
    # -------------------------------------------------------------------------
    # Get flow command
    # -------------------------------------------------------------------------
    get_flow_parser = subparsers.add_parser(
        "get-flow",
        help="Get a flow by ID"
    )
    get_flow_parser.add_argument("flow_id", help="Flow ID")
    
    # -------------------------------------------------------------------------
    # Create flow command
    # -------------------------------------------------------------------------
    create_flow_parser = subparsers.add_parser(
        "create-flow",
        help="Create a new flow"
    )
    create_flow_parser.add_argument("--name", required=True, help="Flow name")
    create_flow_parser.add_argument(
        "--description",
        default="",
        help="Flow description"
    )
    create_flow_parser.add_argument(
        "--project-id",
        help="Target project/folder ID"
    )
    
    # -------------------------------------------------------------------------
    # Import flow command
    # -------------------------------------------------------------------------
    import_flow_parser = subparsers.add_parser(
        "import-flow",
        help="Import flow from JSON file"
    )
    import_flow_parser.add_argument(
        "file",
        help="Path to flow JSON file"
    )
    import_flow_parser.add_argument(
        "--project-id",
        help="Target project/folder ID"
    )
    
    # -------------------------------------------------------------------------
    # Update flow command
    # -------------------------------------------------------------------------
    update_flow_parser = subparsers.add_parser(
        "update-flow",
        help="Update an existing flow"
    )
    update_flow_parser.add_argument("flow_id", help="Flow ID")
    update_flow_parser.add_argument("--name", help="New flow name")
    update_flow_parser.add_argument("--description", help="New description")
    update_flow_parser.add_argument(
        "--data",
        help="Path to flow data JSON file"
    )
    
    # -------------------------------------------------------------------------
    # Delete flow command
    # -------------------------------------------------------------------------
    delete_flow_parser = subparsers.add_parser(
        "delete-flow",
        help="Delete a flow"
    )
    delete_flow_parser.add_argument("flow_id", help="Flow ID to delete")
    delete_flow_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation"
    )
    
    # -------------------------------------------------------------------------
    # Run flow command
    # -------------------------------------------------------------------------
    run_flow_parser = subparsers.add_parser(
        "run-flow",
        help="Run/execute a flow"
    )
    run_flow_parser.add_argument("flow_id", help="Flow ID to run")
    run_flow_parser.add_argument(
        "--input",
        default='{}',
        help="Input JSON (e.g., '{\"input_value\": \"Hello\"}')"
    )
    run_flow_parser.add_argument(
        "--tweaks",
        help="Tweaks JSON for component overrides"
    )
    run_flow_parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming output"
    )
    
    # -------------------------------------------------------------------------
    # Create custom component command
    # -------------------------------------------------------------------------
    create_component_parser = subparsers.add_parser(
        "create-component",
        help="Create a custom component"
    )
    create_component_parser.add_argument(
        "--name",
        required=True,
        help="Component name (e.g., MyProcessor)"
    )
    create_component_parser.add_argument(
        "--description",
        default="Custom component",
        help="Component description"
    )
    create_component_parser.add_argument(
        "--category",
        default="Custom",
        help="Component category"
    )
    create_component_parser.add_argument(
        "--output",
        default=".",
        help="Output directory for component file"
    )
    create_component_parser.add_argument(
        "--code",
        help="Custom build method code"
    )
    
    # -------------------------------------------------------------------------
    # Upload custom component command
    # -------------------------------------------------------------------------
    upload_component_parser = subparsers.add_parser(
        "upload-component",
        help="Upload custom component to LangFlow"
    )
    upload_component_parser.add_argument(
        "file",
        help="Path to component Python file"
    )
    
    # -------------------------------------------------------------------------
    # Create project command
    # -------------------------------------------------------------------------
    create_project_parser = subparsers.add_parser(
        "create-project",
        help="Create a new project"
    )
    create_project_parser.add_argument(
        "--name",
        required=True,
        help="Project name"
    )
    create_project_parser.add_argument(
        "--description",
        default="",
        help="Project description"
    )
    
    # -------------------------------------------------------------------------
    # List projects command
    # -------------------------------------------------------------------------
    subparsers.add_parser("list-projects", help="List all projects")
    
    # -------------------------------------------------------------------------
    # List files command
    # -------------------------------------------------------------------------
    list_files_parser = subparsers.add_parser(
        "list-files",
        help="List uploaded files"
    )
    list_files_parser.add_argument(
        "--flow-id",
        help="Filter by flow ID"
    )
    
    # -------------------------------------------------------------------------
    # Upload file command
    # -------------------------------------------------------------------------
    upload_file_parser = subparsers.add_parser(
        "upload-file",
        help="Upload a file to LangFlow"
    )
    upload_file_parser.add_argument(
        "file",
        help="Path to file to upload"
    )
    upload_file_parser.add_argument(
        "--flow-id",
        help="Target flow ID"
    )
    
    # -------------------------------------------------------------------------
    # Health check command
    # -------------------------------------------------------------------------
    subparsers.add_parser("health", help="Check LangFlow connection")
    
    # -------------------------------------------------------------------------
    # List API keys command
    # -------------------------------------------------------------------------
    subparsers.add_parser("list-keys", help="List all API keys")
    
    # -------------------------------------------------------------------------
    # Chat interface command
    # -------------------------------------------------------------------------
    chat_parser = subparsers.add_parser(
        "chat",
        help="Interactive chat with a flow"
    )
    chat_parser.add_argument(
        "flow_id",
        help="Flow ID to chat with"
    )
    chat_parser.add_argument(
        "--system",
        help="System prompt for the chat"
    )
    chat_parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming responses"
    )
    
    # -------------------------------------------------------------------------
    # Serve web UI command
    # -------------------------------------------------------------------------
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start web chat UI server"
    )
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)"
    )
    
    # -------------------------------------------------------------------------
    # Create API key command
    # -------------------------------------------------------------------------
    create_key_parser = subparsers.add_parser(
        "create-key",
        help="Create a new API key"
    )
    create_key_parser.add_argument(
        "--name",
        required=True,
        help="API key name"
    )
    create_key_parser.add_argument(
        "--expires-at",
        help="Expiration date (ISO format)"
    )
    
    args = parser.parse_args()
    
    # Handle health check separately
    if args.command == "health":
        agent = LangFlowAgent(
            base_url=args.url,
            api_key=args.api_key,
            timeout=args.timeout
        )
        if agent.check_connection():
            print_status("LangFlow is reachable", "success")
        else:
            print_status(
                f"Cannot reach LangFlow at {args.url}",
                "error"
            )
            exit(1)
        exit(0)
    
    # Require API key for most commands
    if args.command and args.command not in ["health"]:
        if not args.api_key:
            print_status(
                "API key required. Set with --api-key or LANGFLOW_API_KEY env var",
                "error"
            )
            exit(1)
    
    # Create agent
    agent = LangFlowAgent(
        base_url=args.url,
        api_key=args.api_key,
        timeout=args.timeout
    )
    
    # Execute commands
    try:
        if args.command == "list-flows":
            flows = agent.list_flows(project_id=args.project_id if hasattr(args, 'project_id') else None)
            print(json.dumps(flows, indent=2))
        
        elif args.command == "get-flow":
            flow = agent.get_flow(args.flow_id)
            print(json.dumps(flow, indent=2))
        
        elif args.command == "create-flow":
            flow = agent.create_flow(
                name=args.name,
                description=args.description,
                project_id=args.project_id if hasattr(args, 'project_id') and args.project_id else None
            )
            print_status(f"Flow created: {flow.get('id')}", "success")
            print(json.dumps(flow, indent=2))
        
        elif args.command == "import-flow":
            flow = agent.import_flow_json(
                args.file,
                project_id=args.project_id if hasattr(args, 'project_id') and args.project_id else None
            )
            flow_id = flow.get("id") or flow.get("flow_id")
            print_status(f"Flow imported: {flow_id}", "success")
            print(json.dumps(flow, indent=2))
        
        elif args.command == "update-flow":
            update_data = {}
            if args.name:
                update_data["name"] = args.name
            if args.description:
                update_data["description"] = args.description
            
            if hasattr(args, 'data') and args.data:
                with open(args.data, 'r') as f:
                    update_data["data"] = json.load(f)
            
            flow = agent.update_flow(args.flow_id, **update_data)
            print_status(f"Flow updated: {args.flow_id}", "success")
            print(json.dumps(flow, indent=2))
        
        elif args.command == "delete-flow":
            if not args.force:
                confirm = input(f"Delete flow {args.flow_id}? [y/N]: ")
                if confirm.lower() != 'y':
                    print("Cancelled")
                    exit(0)
            agent.delete_flow(args.flow_id)
            print_status(f"Flow deleted: {args.flow_id}", "success")
        
        elif args.command == "run-flow":
            input_data = json.loads(args.input) if args.input != '{}' else {}
            tweaks = json.loads(args.tweaks) if hasattr(args, 'tweaks') and args.tweaks else None
            
            if args.stream:
                print_status("Running flow with streaming...", "info")
                for chunk in agent.run_flow_stream(args.flow_id, input_data, tweaks):
                    print(chunk, end="")
            else:
                result = agent.run_flow(args.flow_id, input_data, tweaks)
                print(json.dumps(result, indent=2))
        
        elif args.command == "create-component":
            code = agent.create_custom_component(
                name=args.name,
                description=args.description,
                category=args.category,
                code=args.code if hasattr(args, 'code') and args.code else None
            )
            path = agent.save_component(code, args.name, args.output)
            print_status(f"Component saved: {path}", "success")
            print(f"\n{Colors.CYAN}Component code:{Colors.NC}\n{code}")
        
        elif args.command == "upload-component":
            # Read component file and upload
            component_path = Path(args.file)
            if not component_path.exists():
                print_status(f"File not found: {args.file}", "error")
                exit(1)
            
            code = component_path.read_text()
            
            # Note: LangFlow doesn't have a direct API for uploading 
            # custom components. They need to be placed in LANGFLOW_COMPONENTS_PATH
            # or uploaded via the UI
            print_status(
                "Note: LangFlow doesn't have a direct API for custom components",
                "warning"
            )
            print_status(
                "Place component files in LANGFLOW_COMPONENTS_PATH or upload via UI",
                "info"
            )
            
            # Save to default components path
            components_path = agent.get_components_path()
            path = agent.save_component(code, component_path.stem, components_path)
            print_status(f"Component saved to: {path}", "success")
        
        elif args.command == "create-project":
            project = agent.create_project(args.name, args.description)
            print_status(f"Project created: {project.get('id')}", "success")
            print(json.dumps(project, indent=2))
        
        elif args.command == "list-projects":
            projects = agent.list_projects()
            print(json.dumps(projects, indent=2))
        
        elif args.command == "list-files":
            files = agent.list_files(
                flow_id=args.flow_id if hasattr(args, 'flow_id') and args.flow_id else None
            )
            print(json.dumps(files, indent=2))
        
        elif args.command == "upload-file":
            file_info = agent.upload_file(args.file, args.flow_id if hasattr(args, 'flow_id') and args.flow_id else None)
            print_status(f"File uploaded", "success")
            print(json.dumps(file_info, indent=2))
        
        elif args.command == "list-keys":
            keys = agent.list_api_keys()
            print(json.dumps(keys, indent=2))
        
        elif args.command == "create-key":
            key = agent.create_api_key(
                args.name,
                args.expires_at if hasattr(args, 'expires_at') and args.expires_at else None
            )
            print_status(f"API key created", "success")
            print(json.dumps(key, indent=2))
        
        elif args.command == "chat":
            # Interactive chat interface
            run_chat_interface(agent, args.flow_id, args.system, args.stream)
        
        elif args.command == "serve":
            # Web chat UI server
            run_web_chat_ui(agent, args.host, args.port)
        
        else:
            parser.print_help()
    
    except requests.HTTPError as e:
        print_status(f"API error: {e}", "error")
        try:
            error_data = e.response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(e.response.text)
        exit(1)
    
    except Exception as e:
        print_status(f"Error: {str(e)}", "error")
        exit(1)