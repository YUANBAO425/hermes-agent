"""
MCP Search backend for hermes-agent.

Connects to an MCP service via SSE and calls the `search` tool.
Set environment variable MCP_SEARCH_URL (default: http://localhost:8001/sse).
"""

import os
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_SEARCH_URL", "http://localhost:8001/sse")


def _mcp_search(query: str, limit: int = 5) -> dict:
    """Call MCP search tool and return hermes-format results."""
    async def _run():
        from fastmcp import Client
        from fastmcp.client.transports import SSETransport
        transport = SSETransport(url=MCP_URL)
        client = Client(transport)
        async with client:
            result = await client.call_tool(
                name="search",
                arguments={"query": query, "sandbox_id": "hermes"}
            )
            return result

    try:
        result = asyncio.run(_run())
        if result and result.content:
            text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {"raw": text}

            if "data" in data and "web" in data.get("data", {}):
                return data

            web_results = []
            if isinstance(data, list):
                for i, item in enumerate(data[:limit]):
                    web_results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "description": item.get("snippet", item.get("description", "")),
                        "position": i + 1,
                    })
            elif isinstance(data, dict) and "results" in data:
                for i, item in enumerate(data["results"][:limit]):
                    web_results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "description": item.get("snippet", item.get("description", "")),
                        "position": i + 1,
                    })
            else:
                return {"success": True, "data": {"web": []}, "raw": data}

            return {"success": True, "data": {"web": web_results}}
        return {"success": False, "error": "MCP returned empty result"}
    except Exception as e:
        logger.error(f"MCP search error: {e}")
        return {"success": False, "error": str(e)}
