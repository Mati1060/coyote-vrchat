"""Shortcut to the MCP server (point `claude mcp add` at this file)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coyote_vrc.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
