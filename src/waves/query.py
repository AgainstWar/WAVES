from __future__ import annotations

from waves.vcd_parser import ParsedVCD, SignalInfo, WavesVCDError, parse_vcd


class WavesQueryError(Exception):
    """Raised when a waveform query cannot be completed."""


def _load_vcd(vcd_path: str) -> ParsedVCD:
    try:
        return parse_vcd(vcd_path)
    except WavesVCDError as exc:
        raise WavesQueryError(str(exc)) from exc


def _get_signal(parsed: ParsedVCD, signal: str) -> SignalInfo:
    info = parsed.signals.get(signal)
    if info is None:
        raise WavesQueryError(f"Signal not found: {signal}")
    return info


def list_signals(vcd_path: str, filter: str | None = None, limit: int = 100) -> dict[str, object]:
    """List signals from a VCD file.

    Args:
        vcd_path: Path to the VCD file.
        filter: Optional substring used to match signal names.
        limit: Maximum number of signals to return.

    Returns:
        A dictionary containing the VCD path, timescale, signal count,
        signal summaries, and whether results were truncated.
    """
    if limit <= 0:
        raise WavesQueryError("limit must be greater than 0")

    parsed = _load_vcd(vcd_path)
    matching_signals = [
        (name, info)
        for name, info in parsed.signals.items()
        if filter is None or filter in name
    ]
    signal_count = len(matching_signals)
    limited_signals = matching_signals[:limit]

    return {
        "vcd_path": vcd_path,
        "timescale": parsed.timescale,
        "signal_count": signal_count,
        "signals": [{"name": name, "width": info.width} for name, info in limited_signals],
        "truncated": signal_count > limit,
    }


def get_value(vcd_path: str, signal: str, time: int) -> dict[str, object]:
    """Get the value of a signal at a specific time.

    Args:
        vcd_path: Path to the VCD file.
        signal: Signal name to query.
        time: Query time; must be non-negative.

    Returns:
        A dictionary containing the signal name, query time, and value.
    """
    if time < 0:
        raise WavesQueryError("time must be greater than or equal to 0")

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    value = None
    for transition_time, transition_value in info.transitions:
        if transition_time <= time:
            value = transition_value
        else:
            break

    return {"signal": signal, "time": time, "value": value}


def get_transitions(
    vcd_path: str,
    signal: str,
    start_time: int,
    end_time: int,
    limit: int = 50,
) -> dict[str, object]:
    """Get signal transitions within a time range.

    Args:
        vcd_path: Path to the VCD file.
        signal: Signal name to query.
        start_time: Inclusive range start; must be non-negative.
        end_time: Inclusive range end; must be non-negative.
        limit: Maximum number of transitions to return.

    Returns:
        A dictionary containing the signal name, requested time range,
        transition list, and whether results were truncated.
    """
    if limit <= 0:
        raise WavesQueryError("limit must be greater than 0")
    if start_time < 0:
        raise WavesQueryError("start_time must be greater than or equal to 0")
    if end_time < 0:
        raise WavesQueryError("end_time must be greater than or equal to 0")
    if start_time > end_time:
        raise WavesQueryError("start_time must be less than or equal to end_time")

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    transitions = [
        {"time": transition_time, "value": transition_value}
        for transition_time, transition_value in info.transitions
        if start_time <= transition_time <= end_time
    ]
    transition_count = len(transitions)

    return {
        "signal": signal,
        "start_time": start_time,
        "end_time": end_time,
        "transitions": transitions[:limit],
        "truncated": transition_count > limit,
    }
