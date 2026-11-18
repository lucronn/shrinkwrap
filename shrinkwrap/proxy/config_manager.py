"""
Config Routing & Rollback Manager for ShrinkWrap.
Discovers supported Codex TOML and JSON MCP configurations and wraps local servers.
"""

import json
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import List, Optional, Tuple

import tomlkit

KNOWN_CONFIG_PATHS = [
    Path.home() / ".gemini" / "config" / "mcp_config.json",
    Path.home() / ".gemini" / "mcp_config.json",
    Path.home() / ".antigravity" / "mcp_config.json",
    Path.home() / ".codex" / "config.toml",
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

    def wrap_config(self, config_path: Path, dry_run: bool = False,
                    server_name: Optional[str] = None) -> Tuple[bool, str]:
        if not config_path.exists():
            return False, f"Config file {config_path} does not exist."

        is_toml = config_path.suffix == ".toml"
        try:
            source = config_path.read_text(encoding="utf-8")
            data = tomlkit.parse(source) if is_toml else json.loads(source)
        except Exception as e:
            return False, f"Failed to parse {config_path}: {e}"

        mcp_servers = data.get("mcp_servers") if is_toml else data.get("mcpServers") or data.get("mcp_servers")
        if not isinstance(mcp_servers, MutableMapping) or not mcp_servers:
            return False, f"No MCP server block found in {config_path}."
        if server_name is not None and server_name not in mcp_servers:
            return False, f"MCP server {server_name} not found in {config_path}."

        modified = False
        for name, server_cfg in mcp_servers.items():
            if server_name is not None and name != server_name:
                continue
            if not isinstance(server_cfg, MutableMapping):
                continue
            command = server_cfg.get("command")
            if not isinstance(command, str) or not command or command == "shrinkwrap":
                continue  # Skip remote/URL servers or already wrapped servers
            args = server_cfg.get("args", [])
            if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
                return False, f"Invalid args for MCP server {name} in {config_path}."
            if list(args[:4]) == ["-m", "shrinkwrap.cli", "wrap-stdio", "--"]:
                continue

            # Use the current Python executable so GUI clients need no PATH setup.
            new_command = sys.executable
            new_args = ["-m", "shrinkwrap.cli", "wrap-stdio", "--", command] + list(args)
            server_cfg["command"] = new_command
            server_cfg["args"] = new_args
            modified = True

        scope = f"server {server_name}" if server_name is not None else "servers"
        if not modified:
            return True, f"No changes needed for {scope} in {config_path}."

        if dry_run:
            return True, f"Dry-run: Would wrap {scope} in {config_path}."

        serialized = tomlkit.dumps(data) if is_toml else json.dumps(data, indent=2) + "\n"
        # Keep a safety backup and replace the config atomically.
        backup_path = config_path.with_suffix(config_path.suffix + ".swbak")
        shutil.copy2(config_path, backup_path)
        fd, tmp_name = tempfile.mkstemp(prefix=config_path.name + ".", suffix=".tmp", dir=config_path.parent)
        try:
            os.chmod(tmp_name, stat.S_IMODE(config_path.stat().st_mode))
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(serialized)
            os.replace(tmp_name, config_path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

        return True, f"Successfully wrapped MCP {scope} in {config_path}. Backup saved to {backup_path.name}."

    def rollback_config(self, config_path: Path) -> Tuple[bool, str]:
        backup_path = config_path.with_suffix(config_path.suffix + ".swbak")
        if not backup_path.exists():
            return False, f"No backup file found at {backup_path}."

        shutil.copy2(backup_path, config_path)
        return True, f"Restored {config_path} from {backup_path.name}."
