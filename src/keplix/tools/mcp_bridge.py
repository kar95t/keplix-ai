"""MCP (Model Context Protocol) bridge loader using langchain-mcp-adapters."""

from typing import Any, Optional

from langchain_core.tools import BaseTool

from keplix.tools.registry import ToolRegistry


class MCPBridge:
    """Loads external tools from Model Context Protocol (MCP) servers into the Keplix registry."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or ToolRegistry()
        self._connected_servers: dict[str, Any] = {}

    async def connect_stdio_server(
        self,
        server_name: str,
        command: str,
        args: list[str],
        env: Optional[dict[str, str]] = None,
    ) -> list[BaseTool]:
        """Connect to an external MCP server running over stdio and register its exposed tools."""
        try:
            # Dynamically import langchain-mcp-adapters if installed
            from langchain_mcp_adapters.client import MultiServerMCPClient

            client = MultiServerMCPClient()
            await client.connect_to_server(
                server_name,
                transport="stdio",
                command=command,
                args=args,
                env=env,
            )
            tools = await client.get_tools()

            for tool in tools:
                self.registry.register(tool, scope=f"mcp:{server_name}")

            self._connected_servers[server_name] = client
            return tools
        except ImportError:
            # Graceful warning if langchain-mcp-adapters is not yet in workspace
            return []
        except Exception as e:
            from keplix.cli.console import err_console

            err_console.print(f"[yellow]Warning: Could not connect to MCP server {server_name}: {e}[/yellow]")
            return []

    def get_server_names(self) -> list[str]:
        """List active connected MCP servers."""
        return list(self._connected_servers.keys())

