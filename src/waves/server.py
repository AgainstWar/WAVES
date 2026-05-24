from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from waves.query import WavesQueryError, get_transitions, get_value, list_signals


mcp = FastMCP("WAVES")


def _tool_error(exc: WavesQueryError) -> ToolError:
    return ToolError(str(exc))


@mcp.tool()
def wave_list_signals(vcd_path: str, filter: str | None = None, limit: int = 100) -> dict:
    """MCP tool that lists signals from a VCD file."""
    try:
        return list_signals(vcd_path=vcd_path, filter=filter, limit=limit)
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def wave_get_value(vcd_path: str, signal: str, time: int) -> dict:
    """MCP tool that returns a signal value at a specific time."""
    try:
        return get_value(vcd_path=vcd_path, signal=signal, time=time)
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


@mcp.tool()
def wave_get_transitions(
    vcd_path: str,
    signal: str,
    start_time: int,
    end_time: int,
    limit: int = 50,
) -> dict:
    """MCP tool that returns signal transitions over a time range."""
    try:
        return get_transitions(
            vcd_path=vcd_path,
            signal=signal,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


def main() -> None:
    mcp.run()
