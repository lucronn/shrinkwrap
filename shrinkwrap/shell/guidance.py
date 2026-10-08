"""
Shell Command Analyzer & Fallback Compactor for ShrinkWrap.
"""

import shutil
import subprocess
from typing import Dict, Any, Tuple
from shrinkwrap.engine.compactor import CompactionEngine

SUPPORTED_RTK_COMMANDS = {"git", "rg", "grep", "read", "cat", "ls", "tree"}

def analyze_shell_command(cmd_str: str) -> Dict[str, Any]:
    parts = cmd_str.strip().split()
    if not parts:
        return {"action": "raw", "cmd": cmd_str}
    
    base_cmd = parts[0]
    has_rtk = shutil.which("rtk") is not None
    
    if has_rtk and base_cmd in SUPPORTED_RTK_COMMANDS:
        return {"action": "rtk_wrapper", "suggested_cmd": f"rtk {cmd_str}"}
    return {"action": "compactor_fallback", "cmd": cmd_str}

class ShellOutputCompactor:
    def __init__(self, compactor: CompactionEngine = None):
        self.compactor = compactor or CompactionEngine()

    def compact_output(self, raw_output: str, cmd_str: str) -> Tuple[Any, str, int, int]:
        return self.compactor.compact(raw_output, source_type="shell")
