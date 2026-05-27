"""WAVES MCP server — stdio tool set for querying VCD waveform files.

Exposes three MCP tools that delegate to the query layer. All descriptions
and parameter docs are consumed by LLM clients via the MCP protocol.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from waves.query import WavesQueryError, get_info, get_transitions, get_value, get_window, list_signals

# FastMCP application instance (stdio transport only).
mcp = FastMCP("WAVES")


def _tool_error(exc: WavesQueryError) -> ToolError:
    # Convert domain exceptions into MCP ToolError so the server returns
    # a clean error message to the LLM client.
    return ToolError(str(exc))


@mcp.tool()
def wave_get_info(
    vcd_path: Annotated[str, Field(description="Explicit path to the VCD file.")],
) -> dict:
    # MCP tool description (sent to LLM client via tools/list)
    """Get basic file-level information from a VCD file.

    Returns timescale, start/end timestamps, and signal count.
    """
    try:
        return get_info(vcd_path=vcd_path)
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


# MCP tool description: visible to LLM via tools/list
@mcp.tool()
def wave_list_signals(
    vcd_path: Annotated[str, Field(description="Explicit path to the VCD file.")],
    filter: Annotated[
        str | None, Field(description="Optional substring filter over full signal names.")
    ] = None,
    limit: Annotated[int, Field(description="Maximum number of records to return.")] = 100,
) -> dict:
    # MCP tool description (sent to LLM client via tools/list)
    """List queryable signals in a VCD file.

    Use this to find exact hierarchical signal names before querying values or transitions.
    """
    try:
        return list_signals(vcd_path=vcd_path, filter=filter, limit=limit)
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


# MCP tool description: visible to LLM via tools/list
@mcp.tool()
def wave_get_value(
    vcd_path: Annotated[str, Field(description="Explicit path to the VCD file.")],
    signal: Annotated[
        str, Field(description="Exact hierarchical signal name returned by wave_list_signals.")
    ],
    time: Annotated[int, Field(description="Raw VCD integer timestamp.")],
) -> dict:
    # MCP tool description (sent to LLM client via tools/list)
    """Get one signal value at a raw VCD timestamp.

    The signal must exactly match a name returned by wave_list_signals.
    """
    try:
        return get_value(vcd_path=vcd_path, signal=signal, time=time)
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


# MCP tool description: visible to LLM via tools/list
@mcp.tool()
def wave_get_transitions(
    vcd_path: Annotated[str, Field(description="Explicit path to the VCD file.")],
    signal: Annotated[
        str, Field(description="Exact hierarchical signal name returned by wave_list_signals.")
    ],
    start_time: Annotated[int, Field(description="Inclusive raw VCD integer start timestamp.")],
    end_time: Annotated[int, Field(description="Inclusive raw VCD integer end timestamp.")],
    limit: Annotated[int, Field(description="Maximum number of records to return.")] = 50,
) -> dict:
    # MCP tool description (sent to LLM client via tools/list)
    """Get recorded signal transitions in an inclusive raw VCD time range.

    Use limit to cap the number of returned transition records.
    """
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


@mcp.tool()
def wave_get_window(
    vcd_path: Annotated[str, Field(description="Explicit path to the VCD file.")],
    signals: Annotated[
        list[str], Field(description="Exact hierarchical signal names returned by wave_list_signals.")
    ],
    start_time: Annotated[int, Field(description="Inclusive raw VCD integer start timestamp.")],
    end_time: Annotated[int, Field(description="Inclusive raw VCD integer end timestamp.")],
    limit_per_signal: Annotated[
        int, Field(description="Maximum transition records to return per signal.")
    ] = 50,
) -> dict:
    # MCP tool description (sent to LLM client via tools/list)
    """Get recorded transitions for multiple VCD signals in one inclusive time window.

    Returns waveform facts only; it does not interpret or diagnose the waveform.
    """
    try:
        return get_window(
            vcd_path=vcd_path,
            signals=signals,
            start_time=start_time,
            end_time=end_time,
            limit_per_signal=limit_per_signal,
        )
    except WavesQueryError as exc:
        raise _tool_error(exc) from exc


def main() -> None:
    # Entry point for the `waves` console script (pyproject.toml).
    mcp.run()
