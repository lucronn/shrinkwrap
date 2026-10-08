"""
Config Routing & Rollback Manager for ShrinkWrap.
Discovers MCP client configurations (~/.codex/config.json, Claude Desktop, Cursor) and idempotently wraps MCP servers.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List

KNOWN_CONFIG_PATHS = [
    Path.home() / ".codex" / "config.json",
    Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    Path.home() / ".cursor" / "mcp.json",
    Path.home() / ".config" / "claude" / "claude_desktop_config.json",
]

class ConfigManager:
    def discover_configs(self) -> List[Path]:
        found = []
        for p in KNOWN_CONFIG_PATHS:
            if p.exists() and p.is_file():
                found.append(p)
        return found

    def wrap_config(self, config_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
        if not config_path.exists():
            return False, f"Config file {config_path} does not exist."

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, f"Failed to parse {config_path}: {e}"

        mcp_servers = data.get("mcpServers") or data.get("mcp_servers")
        if not mcp_servers or not isinstance(mcp_servers, dict):
            return False, f"No mcpServers block found in {config_path}."

        modified = False
        for server_name, server_cfg in mcp_servers.items():
            command = server_cfg.get("command")
            args = server_cfg.get("args", [])
            if command == "shrinkwrap":
                continue  # Already wrapped

            # Wrap command: shrinkwrap wrap-stdio -- command args...
            new_command = "shrinkwrap"
            new_args = ["wrap-stdio", "--", command] + args
            server_cfg["command"] = new_command
            server_cfg["args"] = new_args
            modified = True

        if not modified:
            return True, f"All servers in {config_path} are already wrapped by ShrinkWrap."

        if dry_run:
            return True, f"Dry-run: Would wrap servers in {config_path}."

        # Create safety backup
        backup_path = config_path.with_suffix(config_path.suffix + ".swbak")
        shutil.copy2(config_path, backup_path)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return True, f"Successfully wrapped MCP servers in {config_path}. Backup saved to {backup_path.name}."

    def rollback_config(self, config_path: Path) -> Tuple[bool, str]:
        backup_path = config_path.with_suffix(config_path.suffix + ".swbak")
        if not backup_path.exists():
            return False, f"No backup file found at {backup_path}."

        shutil.copy2(backup_path, config_path)
        return True, f"Restored {config_path} from {backup_path.name}."
