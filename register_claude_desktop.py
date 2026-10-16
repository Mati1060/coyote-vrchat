"""Registers the Coyote MCP in the Claude Desktop app (so Claude can see the coyote_* tools).

Usage:
    python register_claude_desktop.py             # writes to claude_desktop_config.json
    python register_claude_desktop.py --print     # only prints the snippet, writes nothing
    python register_claude_desktop.py --config C:\\path\\claude_desktop_config.json

After writing, FULLY QUIT and reopen the Claude app (also quit it from the Windows tray).
"""
import argparse
import json
import sys
from pathlib import Path

from coyote_vrc import mcp_register


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Registers the Coyote MCP in Claude Desktop")
    ap.add_argument("--print", dest="only_print", action="store_true", help="only print the config snippet")
    ap.add_argument("--config", default=None, help="path to claude_desktop_config.json (default: find it automatically)")
    args = ap.parse_args(argv)

    script = Path(__file__).resolve().parent / "coyote_mcp.py"
    python = mcp_register.python_for_mcp()
    if not script.exists():
        print("Could not find coyote_mcp.py next to this file:", script)
        return 1

    if args.only_print:
        print(json.dumps({"mcpServers": {mcp_register.SERVER_NAME: mcp_register.server_entry(python, str(script))}},
                         indent=2, ensure_ascii=False))
        return 0

    results = mcp_register.register_desktop(python, str(script), [args.config] if args.config else None)
    failed = False
    for r in results:
        if r.action == "error":
            failed = True
            print(f"[error]      {r.path}\n             {r.error}")
        else:
            print(f"[{r.action:<10}] {r.path}")
            if r.backup:
                print(f"             backup copy: {r.backup}")
    if failed:
        print("\nIf the file has an error, open the Claude app > Settings > Developer > Edit Config"
              " and use: python register_claude_desktop.py --print  (paste the snippet there).")
        return 1
    print("\nDone. Fully quit the Claude app (including from the tray) and open it again.")
    print("To check: 'coyote' should show up among the app's tools/connectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
