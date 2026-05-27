from __future__ import annotations

from waves.vcd_parser import ParsedVCD, SignalInfo, WavesVCDError, parse_vcd


class WavesQueryError(Exception):
    """Raised when a waveform query cannot be completed."""


def _load_vcd(vcd_path: str) -> ParsedVCD:
    try:
        return parse_vcd(vcd_path)
    except WavesVCDError as exc:
        raise WavesQueryError(
            f"VCD file error: {vcd_path}. Reason: {exc}. Please provide a valid VCD file."
        ) from exc


def _get_signal(parsed: ParsedVCD, signal: str) -> SignalInfo:
    info = parsed.signals.get(signal)
    if info is None:
        raise WavesQueryError(
            f"Signal error: signal not found: {signal}. Please provide a valid signal name."
        )
    return info


def get_info(vcd_path: str) -> dict[str, object]:
    """Get basic file-level information from a VCD file.

    Returns timescale, start/end timestamps, and signal count.
    """
    parsed = _load_vcd(vcd_path)
    return {
        "vcd_path": vcd_path,
        "timescale": parsed.timescale,
        "start_time": parsed.start_time,
        "end_time": parsed.end_time,
        "signal_count": len(parsed.signals),
    }


def list_signals(vcd_path: str, filter: str | None = None, limit: int = 100) -> dict[str, object]:
    """List queryable signals in a VCD file.

    Use this to find exact hierarchical signal names before querying values or transitions.
    """
    if limit <= 0:
        raise WavesQueryError(f"Parameter error: limit must be greater than 0, got {limit}.")

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
    """Get one signal value at a raw VCD timestamp.

    The signal must exactly match a name returned by list_signals.
    """
    if time < 0:
        raise WavesQueryError(f"Parameter error: time must be greater than or equal to 0, got {time}.")

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
    """Get recorded signal transitions in an inclusive raw VCD time range.

    Use limit to cap the number of returned transition records.
    """
    if limit <= 0:
        raise WavesQueryError(f"Parameter error: limit must be greater than 0, got {limit}.")
    if start_time < 0:
        raise WavesQueryError(f"Parameter error: start_time must be greater than or equal to 0, got {start_time}.")
    if end_time < 0:
        raise WavesQueryError(f"Parameter error: end_time must be greater than or equal to 0, got {end_time}.")
    if start_time > end_time:
        raise WavesQueryError(
            f"Parameter error: start_time must be less than or equal to end_time, got start_time={start_time}, end_time={end_time}."
        )

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


def get_window(
    vcd_path: str,
    signals: list[str],
    start_time: int,
    end_time: int,
    limit_per_signal: int = 50,
) -> dict[str, object]:
    """Get recorded transitions for multiple VCD signals in one inclusive time window.

    Returns waveform facts only; it does not interpret or diagnose the waveform.
    """
    if not signals:
        raise WavesQueryError("Parameter error: signals must not be empty.")
    if len(signals) > 20:
        raise WavesQueryError(
            f"Parameter error: signals must contain at most 20 signals, got {len(signals)}."
        )
    if limit_per_signal <= 0:
        raise WavesQueryError(
            f"Parameter error: limit_per_signal must be greater than 0, got {limit_per_signal}."
        )
    if start_time < 0:
        raise WavesQueryError(
            f"Parameter error: start_time must be greater than or equal to 0, got {start_time}."
        )
    if end_time < 0:
        raise WavesQueryError(
            f"Parameter error: end_time must be greater than or equal to 0, got {end_time}."
        )
    if start_time > end_time:
        raise WavesQueryError(
            f"Parameter error: start_time must be less than or equal to end_time, got start_time={start_time}, end_time={end_time}."
        )

    parsed = _load_vcd(vcd_path)
    result_signals = []

    for signal in signals:
        info = _get_signal(parsed, signal)
        transitions = [
            {"time": transition_time, "value": transition_value}
            for transition_time, transition_value in info.transitions
            if start_time <= transition_time <= end_time
        ]
        transition_count = len(transitions)
        result_signals.append({
            "signal": signal,
            "transitions": transitions[:limit_per_signal],
            "truncated": transition_count > limit_per_signal,
        })

    return {
        "start_time": start_time,
        "end_time": end_time,
        "signals": result_signals,
    }
