# src/tools/registry.py

from typing import Dict, Any, Callable
import inspect

class ToolRegistry:
    """Registry of all available tools."""
    
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
    
    def register(self, name: str, func: Callable, metadata: Dict):
        """Register a new tool."""
        self.tools[name] = {
            "func": func,
            "metadata": metadata
        }
    
    def get(self, name: str) -> Dict:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool["func"](**kwargs)
    
    def list_tools(self) -> Dict:
        """List all tools with metadata."""
        return {
            name: {
                "description": tool["metadata"].get("description", ""),
                "risk": tool["metadata"].get("risk", "low"),
                "requires_approval": tool["metadata"].get("requires_approval", False),
                "reversible": tool["metadata"].get("reversible", True)
            }
            for name, tool in self.tools.items()
        }