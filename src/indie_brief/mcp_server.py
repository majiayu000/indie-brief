from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from indie_brief.client import fetch_today

mcp = MCPServer("indie-brief")


@mcp.tool()
def today(focus: str = "") -> str:
    """读取今天的独立开发者简报。

    focus 是逗号分隔的关键词，可留空。返回的 JSON 是全部材料。
    不要补充 JSON 里没有的帖子，不要把 context 里的热帖写成产品机会。
    """
    url = os.environ.get("INDIE_BRIEF_API_URL", "http://127.0.0.1:8787")
    api_key = os.environ.get("INDIE_BRIEF_API_KEY", "")
    return fetch_today(focus, url=url, api_key=api_key)


def main() -> None:
    mcp.run(transport="stdio")
