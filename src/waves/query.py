"""WAVES query layer — domain functions for VCD waveform queries.

Each public function takes a vcd_path plus query-specific parameters and
returns a plain dict.  Errors are raised as WavesQueryError in three stable
categories:

- VCD file error  — invalid or unreadable vcd_path
- Signal error    — signal name not found in the VCD
- Parameter error — invalid numeric arguments (negative time, limit <= 0, etc.)

All functions delegate VCD parsing to _load_vcd; the parsed result is cached
only for the duration of one function call (no persistent session state).
"""

from __future__ import annotations

from waves.vcd_parser import ParsedVCD, SignalInfo, WavesVCDError, parse_vcd


class WavesQueryError(Exception):
    """Raised when a waveform query cannot be completed."""


def _load_vcd(vcd_path: str) -> ParsedVCD:
    """Parse the VCD file at *vcd_path* and return a ParsedVCD.

    Raises:
        WavesQueryError: VCD file error if the file is missing, unreadable,
            or not a valid VCD.
    """
    try:
        return parse_vcd(vcd_path)
    except WavesVCDError as exc:
        raise WavesQueryError(
            f"VCD file error: {vcd_path}. Reason: {exc}. Please provide a valid VCD file."
        ) from exc


def _get_signal(parsed: ParsedVCD, signal: str) -> SignalInfo:
    """Look up *signal* in *parsed.signals* and return its SignalInfo.

    Raises:
        WavesQueryError: Signal error if the signal does not exist.
    """
    info = parsed.signals.get(signal)
    if info is None:
        raise WavesQueryError(
            f"Signal error: signal not found: {signal}. Please provide a valid signal name."
        )
    return info


def get_info(vcd_path: str) -> dict[str, object]:
    """Get basic file-level information from a VCD file.

    Returns:
        dict with keys: vcd_path, timescale, start_time, end_time, signal_count.
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

    Args:
        vcd_path: Explicit path to the VCD file.
        filter: Optional substring filter over full signal names.
        limit: Maximum number of records to return.

    Returns:
        dict with keys: vcd_path, timescale, signal_count, signals (list of
        {name, width}), truncated.
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
    Uses at-or-before lookup: if no transition exists exactly at *time*,
    returns the most recent value at or before that timestamp.

    Args:
        vcd_path: Explicit path to the VCD file.
        signal: Exact hierarchical signal name returned by wave_list_signals.
        time: Raw VCD integer timestamp.

    Returns:
        dict with keys: signal, time, value.  value is None if the signal
        has no recorded value at or before the requested time.
    """
    if time < 0:
        raise WavesQueryError(f"Parameter error: time must be greater than or equal to 0, got {time}.")

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    # at-or-before scan
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

    Args:
        vcd_path: Explicit path to the VCD file.
        signal: Exact hierarchical signal name returned by wave_list_signals.
        start_time: Inclusive raw VCD integer start timestamp.
        end_time: Inclusive raw VCD integer end timestamp.
        limit: Maximum number of records to return.

    Returns:
        dict with keys: signal, start_time, end_time, transitions (list of
        {time, value}), truncated.
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

    # inclusive filter
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

    Args:
        vcd_path: Explicit path to the VCD file.
        signals: Exact hierarchical signal names returned by wave_list_signals.
            Must be non-empty, contain at most 20 signals, and have no duplicates.
        start_time: Inclusive raw VCD integer start timestamp.
        end_time: Inclusive raw VCD integer end timestamp.
        limit_per_signal: Maximum transition records to return per signal.

    Returns:
        dict with keys: start_time, end_time, signals (list of
        {signal, transitions, truncated}).  Empty transitions is normal data,
        not an error.
    """
    # Validate signals list
    if not signals:
        raise WavesQueryError("Parameter error: signals must not be empty.")
    if len(signals) > 20:
        raise WavesQueryError(
            f"Parameter error: signals must contain at most 20 signals, got {len(signals)}."
        )
    seen = set()
    for signal in signals:
        if signal in seen:
            raise WavesQueryError(
                f"Parameter error: signals contains duplicates: {signal}."
            )
        seen.add(signal)

    # Validate numeric parameters
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

    # Single VCD parse, then loop over requested signals
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
