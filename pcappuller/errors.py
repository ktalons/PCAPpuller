class PCAPPullerError(Exception):
    """Top-level error for controlled exits."""


class ToolNotFoundError(PCAPPullerError):
    """A required Wireshark CLI tool is missing from PATH."""


class ExternalToolError(PCAPPullerError):
    """An external tool exited non-zero or timed out."""

    def __init__(self, tool: str, returncode: int, detail: str = ""):
        self.tool = tool
        self.returncode = returncode
        self.detail = detail
        msg = f"'{tool}' failed with exit code {returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)


class TempSpaceError(PCAPPullerError):
    """Filesystem error while handling temporary or output files."""
