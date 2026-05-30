# WAVES query layer — domain functions for VCD waveform queries.
#
# Each public function takes a vcd_path plus query-specific parameters and
# returns a plain dict.  Errors are raised as WavesQueryError in three stable
# categories:
#   - VCD file error  — invalid or unreadable vcd_path
#   - Signal error    — signal name not found in the VCD
#   - Parameter error — invalid numeric arguments (negative time, limit <= 0, etc.)
#
# All functions delegate VCD parsing to _load_vcd; the parsed result is cached
# only for the duration of one function call (no persistent session state).

from __future__ import annotations

from waves.vcd_parser import WavesVCDError, parse_vcd

# Re-export for tests / external use
from waves.vcd_parser import ParsedVCD, SignalInfo  # noqa: F401


class WavesQueryError(Exception):
    """Raised when a waveform query cannot be completed."""


def _load_vcd(vcd_path: str) -> ParsedVCD:
    # Parse the VCD file at vcd_path and return a ParsedVCD.
    # Raises WavesQueryError (VCD file error) on failure.
    try:
        return parse_vcd(vcd_path)
    except WavesVCDError as exc:
        raise WavesQueryError(
            f"VCD file error: {vcd_path}. Reason: {exc}. Please provide a valid VCD file."
        ) from exc


def _get_signal(parsed: ParsedVCD, signal: str) -> SignalInfo:
    # Look up signal in parsed.signals and return its SignalInfo.
    # Raises WavesQueryError (Signal error) if the signal does not exist.
    info = parsed.signals.get(signal)
    if info is None:
        raise WavesQueryError(
            f"Signal error: signal not found: {signal}. Please provide a valid signal name."
        )
    return info


def get_info(vcd_path: str) -> dict[str, object]:
    """Get basic file-level information from a VCD file.

    Returns dict with keys: vcd_path, timescale, start_time, end_time, signal_count.
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

    Uses at-or-before lookup: if no transition exists exactly at time,
    returns the most recent value at or before that timestamp.
    value is None if the signal has no recorded value at or before time.
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


def _match_value(val: str, target: str | None) -> bool:
    # Check if transition value val matches the target filter.
    # None means no filter (match all).
    if target is None:
        return True
    return val == target


def get_transitions(
    vcd_path: str,
    signal: str,
    start_time: int,
    end_time: int,
    limit: int = 50,
    edge: str = "any",
    value: str | None = None,
) -> dict[str, object]:
    """Get recorded signal transitions in an inclusive raw VCD time range.

    Can optionally filter by transition kind and resulting value.
    Use limit to cap the number of returned transition records.
    """
    # Validate parameters
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
    if edge not in ("any", "posedge", "negedge"):
        raise WavesQueryError(
            f"Parameter error: edge must be one of ['any', 'posedge', 'negedge'], got {edge!r}."
        )
    if value is not None and not isinstance(value, str):
        raise WavesQueryError("Parameter error: value must be a string if provided.")

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    # Filter by: time window -> edge -> value -> limit
    filtered: list[dict[str, object]] = []
    prev_val: str | None = None
    for transition_time, transition_value in info.transitions:
        in_window = start_time <= transition_time <= end_time

        if in_window and _matches_edge(prev_val, transition_value, edge) and _match_value(transition_value, value):
            filtered.append({"time": transition_time, "value": transition_value})

        prev_val = transition_value

    transition_count = len(filtered)

    return {
        "signal": signal,
        "start_time": start_time,
        "end_time": end_time,
        "transitions": filtered[:limit],
        "truncated": transition_count > limit,
    }


def _resolve_window(
    start_time: int | None = None,
    end_time: int | None = None,
    center_time: int | None = None,
    before: int | None = None,
    after: int | None = None,
) -> tuple[int, int]:
    # Resolve window boundaries from either explicit or centered parameters.
    # Returns (resolved_start_time, resolved_end_time).
    # Raises WavesQueryError on invalid combinations.
    has_explicit = start_time is not None or end_time is not None
    has_centered = center_time is not None or before is not None or after is not None

    if not has_explicit and not has_centered:
        raise WavesQueryError(
            "Parameter error: provide either start_time/end_time or center_time/before/after."
        )
    if has_explicit and has_centered:
        raise WavesQueryError(
            "Parameter error: start_time/end_time and center_time/before/after are mutually exclusive."
        )

    if has_explicit:
        if start_time is None or end_time is None:
            raise WavesQueryError(
                "Parameter error: start_time and end_time must be provided together."
            )
        return (start_time, end_time)

    # Centered mode
    if center_time is None or before is None or after is None:
        raise WavesQueryError(
            "Parameter error: center_time, before, and after must be provided together."
        )
    if center_time < 0:
        raise WavesQueryError(
            f"Parameter error: center_time must be greater than or equal to 0, got {center_time}."
        )
    if before < 0:
        raise WavesQueryError(
            f"Parameter error: before must be greater than or equal to 0, got {before}."
        )
    if after < 0:
        raise WavesQueryError(
            f"Parameter error: after must be greater than or equal to 0, got {after}."
        )

    resolved_start = center_time - before
    if resolved_start < 0:
        raise WavesQueryError(
            f"Parameter error: centered window start_time must be greater than or equal to 0, got {resolved_start}."
        )
    resolved_end = center_time + after

    return (resolved_start, resolved_end)


def get_window(
    vcd_path: str,
    signals: list[str],
    start_time: int | None = None,
    end_time: int | None = None,
    center_time: int | None = None,
    before: int | None = None,
    after: int | None = None,
    limit_per_signal: int = 50,
) -> dict[str, object]:
    """Get recorded transitions for multiple VCD signals in one time window.

    The window can be specified either by start/end timestamps or by a center
    time with before/after offsets.  Returns waveform facts only; it does not
    interpret or diagnose the waveform.  Empty transitions is normal data.
    """
    # Resolve window from parameters
    resolved_start, resolved_end = _resolve_window(
        start_time, end_time, center_time, before, after
    )

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
    if resolved_start < 0:
        raise WavesQueryError(
            f"Parameter error: start_time must be greater than or equal to 0, got {resolved_start}."
        )
    if resolved_end < 0:
        raise WavesQueryError(
            f"Parameter error: end_time must be greater than or equal to 0, got {resolved_end}."
        )
    if resolved_start > resolved_end:
        raise WavesQueryError(
            f"Parameter error: start_time must be less than or equal to end_time, got start_time={resolved_start}, end_time={resolved_end}."
        )

    # Single VCD parse, then loop over requested signals
    parsed = _load_vcd(vcd_path)
    result_signals = []

    for signal in signals:
        info = _get_signal(parsed, signal)
        transitions = [
            {"time": transition_time, "value": transition_value}
            for transition_time, transition_value in info.transitions
            if resolved_start <= transition_time <= resolved_end
        ]
        transition_count = len(transitions)
        result_signals.append({
            "signal": signal,
            "transitions": transitions[:limit_per_signal],
            "truncated": transition_count > limit_per_signal,
        })

    return {
        "start_time": resolved_start,
        "end_time": resolved_end,
        "signals": result_signals,
    }


def _matches_edge(from_val: str | None, to_val: str, edge: str) -> bool:
    # Check if a transition (from_val -> to_val) matches the given edge kind.
    if edge == "any":
        return True
    # posedge/negedge require single-bit values, a known from value,
    # and the correct 0->1 or 1->0 transition.
    if from_val is None or len(to_val) != 1 or len(from_val) != 1:
        return False
    if edge == "posedge":
        return bool(from_val == "0" and to_val == "1")
    if edge == "negedge":
        return bool(from_val == "1" and to_val == "0")
    return False


def _find_next(
    transitions: list[tuple[int, str]], time: int, edge: str
) -> tuple[int, str | None, str] | None:
    # Find the first transition with t > time that matches edge.
    prev_val: str | None = None
    for t, v in transitions:
        if t > time and _matches_edge(prev_val, v, edge):
            return (t, prev_val, v)
        prev_val = v
    return None


def _find_prev(
    transitions: list[tuple[int, str]], time: int, edge: str
) -> tuple[int, str | None, str] | None:
    # Find the last transition with t < time that matches edge.
    prev_val: str | None = None
    result: tuple[int, str | None, str] | None = None
    for t, v in transitions:
        if t < time and _matches_edge(prev_val, v, edge):
            result = (t, prev_val, v)
        elif t >= time:
            break
        prev_val = v
    return result


def find_transition(
    vcd_path: str,
    signal: str,
    time: int,
    direction: str,
    edge: str = "any",
) -> dict[str, object]:
    """Find the nearest matching transition for one VCD signal.

    direction: "next" (strictly after time) or "prev" (strictly before time).
    edge: "any", "posedge" (0->1 single-bit), or "negedge" (1->0 single-bit).
    Returns found=true with transition details, or found=false on empty result.
    """
    if time < 0:
        raise WavesQueryError(
            f"Parameter error: time must be greater than or equal to 0, got {time}."
        )
    if direction not in ("next", "prev"):
        raise WavesQueryError(
            f"Parameter error: direction must be one of ['next', 'prev'], got {direction!r}."
        )
    if edge not in ("any", "posedge", "negedge"):
        raise WavesQueryError(
            f"Parameter error: edge must be one of ['any', 'posedge', 'negedge'], got {edge!r}."
        )

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    if direction == "next":
        match = _find_next(info.transitions, time, edge)
    else:
        match = _find_prev(info.transitions, time, edge)

    if match is None:
        return {
            "found": False,
            "signal": signal,
            "query_time": time,
            "transition_time": None,
            "from": None,
            "to": None,
            "edge": edge,
        }

    transition_time, from_val, to_val = match
    return {
        "found": True,
        "signal": signal,
        "query_time": time,
        "transition_time": transition_time,
        "from": from_val,
        "to": to_val,
        "edge": edge,
    }
