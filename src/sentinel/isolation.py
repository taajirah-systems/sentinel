import platform
import abc
from typing import List, Optional
from .sandbox import SandboxManager

class IsolationAdapter(abc.ABC):
    @abc.abstractmethod
    def wrap_command(self, cmd_args: List[str], workspace_root: str) -> List[str]:
        """Wraps a command list with OS-specific isolation parameters."""
        raise NotImplementedError("Subclasses must implement wrap_command")

class MacOSAdapter(IsolationAdapter):
    def __init__(self):
        self.manager = SandboxManager()

    def wrap_command(self, cmd_args: List[str], workspace_root: str) -> List[str]:
        profile = self.manager.generate_profile(workspace_root)
        return ["sandbox-exec", "-p", profile] + cmd_args

class LinuxAdapter(IsolationAdapter):
    def wrap_command(self, cmd_args: List[str], workspace_root: str) -> List[str]:
        # Placeholder for seccomp-ready implementation
        # For now, we might use a basic 'firejail' or just return the command
        # as a fallback until the seccomp profile is defined.
        return cmd_args

def get_isolation_adapter() -> IsolationAdapter:
    os_name = platform.system()
    if os_name == "Darwin":
        return MacOSAdapter()
    elif os_name == "Linux":
        return LinuxAdapter()
    else:
        # Fallback to no-op adapter
        class NoOpAdapter(IsolationAdapter):
            def wrap_command(self, cmd_args: List[str], workspace_root: str) -> List[str]:
                return cmd_args
        return NoOpAdapter()

# Default instance
isolation_adapter = get_isolation_adapter()
