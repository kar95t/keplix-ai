"""Central in-memory @tool registry with per-agent capability permission scoping."""

from collections.abc import Callable
from typing import Any, Optional

from langchain_core.tools import BaseTool


class ToolRegistry:
    """Singleton in-memory registry holding all discoverable LangChain agent tools."""

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._scopes = {}
        return cls._instance

    def register(
        self,
        tool: BaseTool,
        scope: str = "general",
    ) -> BaseTool:
        """Register a LangChain BaseTool under a specific capability scope."""
        self._tools[tool.name] = tool
        self._scopes[tool.name] = scope
        return tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by its name."""
        return self._tools.get(name)

    def get_scoped_tools(self, requested_names: list[str]) -> list[BaseTool]:
        """Return subset of tools explicitly requested in worker's task contract."""
        matched: list[BaseTool] = []
        for name in requested_names:
            if name in self._tools:
                matched.append(self._tools[name])
        return matched

    def list_all_tools(self) -> dict[str, BaseTool]:
        """Return mapping of all registered tools."""
        return dict(self._tools)


def register_tool(name: Optional[str] = None, scope: str = "general") -> Callable[[Any], Any]:
    """Decorator to register a tool into the global Keplix ToolRegistry."""

    def decorator(fn_or_tool: Any) -> Any:
        registry = ToolRegistry()
        if isinstance(fn_or_tool, BaseTool):
            registry.register(fn_or_tool, scope=scope)
            return fn_or_tool

        from langchain_core.tools import tool as lc_tool

        actual_tool = lc_tool(fn_or_tool)
        if name:
            actual_tool.name = name
        registry.register(actual_tool, scope=scope)
        return actual_tool

    return decorator

