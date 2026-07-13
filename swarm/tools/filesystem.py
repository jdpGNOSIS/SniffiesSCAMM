import os
import json
from datetime import datetime, UTC


class FileSystemTool:
    def __init__(self):
        self._sandbox: str | None = None

    def set_sandbox(self, path: str):
        self._sandbox = path
        os.makedirs(path, exist_ok=True)

    def _resolve(self, name: str) -> str:
        base = self._sandbox or os.path.join(os.getcwd(), ".agent_sandbox")
        os.makedirs(base, exist_ok=True)
        return os.path.normpath(os.path.join(base, name))

    def write(self, name: str, content: str) -> dict:
        path = self._resolve(name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"path": path, "size": len(content)}

    def read(self, name: str) -> dict:
        path = self._resolve(name)
        if not os.path.exists(path):
            return {"error": f"File not found: {name}"}
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"path": path, "content": content[:5000], "size": len(content)}

    def write_json(self, name: str, data: dict) -> dict:
        return self.write(name, json.dumps(data, indent=2, default=str))
