"""The MCP server: creates the FastMCP instance and registers every tool.

Run it on its own over stdio (for Claude Code):
    fastmcp run app/server.py:mcp
"""

from fastmcp import FastMCP

mcp = FastMCP("my-mcp")
