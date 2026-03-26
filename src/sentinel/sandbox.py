import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Union

class SandboxManager:
    """
    Manages macOS native isolation using sandbox-exec (Seatbelt/SBPL).
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
        self.enabled = os.uname().sysname == "Darwin"

    def generate_profile(self, allow_network: bool = False, extra_read_paths: Optional[List[str]] = None) -> str:
        """
        Generates a Restricted Agent Profile in SBPL format.
        """
        read_paths = extra_read_paths or []
        
        profile = [
            "(version 1)",
            "(allow default)", # Start with permissive base for system libraries/services
            
            # Deny Network
            "(deny network-outbound)",
            
            # Deny access to sensitive host directories
            f'(deny file-read* (subpath "{Path.home() / "Documents"}"))',
            f'(deny file-read* (subpath "{Path.home() / "Downloads"}"))',
            '(deny file-read-data (literal "/etc/passwd"))',
            '(deny file-read-data (literal "/etc/shadow"))',
            '(deny file-read-data (literal "/private/etc/passwd"))',
            '(deny file-read-data (literal "/private/etc/shadow"))',
            
            # Deny reading of the primary .env file (Sentinel server reads it, Agent shouldn't)
            f'(deny file-read-data (literal "{os.path.join(self.workspace_root, ".env")}"))',
        ]

        for path in read_paths:
            profile.append(f'(allow file-read* (subpath "{path}"))')

        if allow_network:
            profile.append("(allow network-outbound)")
            profile.append("(allow network-inbound (local ip \"localhost:*\"))")
        
        return "\n".join(profile)

    def wrap_command(self, cmd_args: Union[List[str], str], profile: str) -> List[str]:
        """
        Wraps a command list with sandbox-exec -p <profile>.
        """
        if not self.enabled:
            return cmd_args if isinstance(cmd_args, list) else [cmd_args]

        return ["sandbox-exec", "-p", profile] + (cmd_args if isinstance(cmd_args, list) else [cmd_args])

    def run_sandboxed(self, cmd_args: Union[List[str], str], allow_network: bool = False) -> subprocess.CompletedProcess:
        """
        Convenience method to run a command immediately in the sandbox.
        """
        profile = self.generate_profile(allow_network=allow_network)
        wrapped = self.wrap_command(cmd_args, profile)
        
        # Determine shell usage
        use_shell = isinstance(cmd_args, str)
        
        return subprocess.run(
            wrapped,
            shell=use_shell,
            capture_output=True,
            text=True
        )
