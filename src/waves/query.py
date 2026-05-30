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


def get_value(vcd_path: str, signal: str, time: int, value_format: str = "raw") -> dict[str, object]:
    """Get one signal value at a raw VCD timestamp.

    Uses at-or-before lookup: if no transition exists exactly at time,
    returns the most recent value at or before that timestamp.
    value is None if the signal has no recorded value at or before time.
    """
    if time < 0:
        raise WavesQueryError(f"Parameter error: time must be greater than or equal to 0, got {time}.")
    _validate_value_format(value_format)

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    # at-or-before scan
    raw_val: str | None = None
    for transition_time, transition_value in info.transitions:
        if transition_time <= time:
            raw_val = transition_value
        else:
            break

    formatted_val, raw_val_out = _format_value(raw_val, info.width, value_format)

    if value_format == "raw":
        return {"signal": signal, "time": time, "value": raw_val}

    return {
        "signal": signal,
        "time": time,
        "value": formatted_val,
        "value_raw": raw_val_out,
        "value_format": value_format,
    }


def _match_value(val: str, target: str | None) -> bool:
    # Check if transition value val matches the target filter.
    # None means no filter (match all).
    if target is None:
        return True
    return val == target


def _format_value(
    raw_value: str | None,
    width: int,
    value_format: str,
) -> tuple[str | None, str | None]:
    # Format a raw VCD value according to value_format.
    # Returns (formatted_value, raw_value).
    if raw_value is None:
        return (None, None)

    if value_format in ("raw", "bin"):
        return (raw_value, raw_value)

    # hex/uint/sint: only convert pure 0/1 strings
    is_pure = all(c in "01" for c in raw_value)

    if value_format == "hex":
        if not is_pure:
            return (raw_value, raw_value)
        padded = raw_value.zfill((len(raw_value) + 3) // 4 * 4)
        return (f"0x{int(padded, 2):x}", raw_value)

    if value_format == "uint":
        if not is_pure:
            return (raw_value, raw_value)
        return (str(int(raw_value, 2)), raw_value)

    if value_format == "sint":
        if not is_pure:
            return (raw_value, raw_value)
        bits = len(raw_value)
        val = int(raw_value, 2)
        if bits > 0 and val >= (1 << (bits - 1)):
            val -= 1 << bits
        return (str(val), raw_value)

    if value_format == "ascii":
        if width < 8 or width % 8 != 0:
            raise WavesQueryError(
                f"Parameter error: ascii format requires bitvector width divisible by 8, got width={width}."
            )
        if not is_pure:
            raise WavesQueryError(
                "Parameter error: ascii format requires values containing only 0 or 1."
            )
        chars: list[str] = []
        for i in range(0, len(raw_value), 8):
            chars.append(chr(int(raw_value[i:i + 8], 2)))
        return ("".join(chars), raw_value)

    # Should not reach here (caller validates value_format)
    return (raw_value, raw_value)


def _validate_value_format(value_format: str) -> None:
    VALID_FORMATS = {"raw", "bin", "hex", "uint", "sint", "ascii"}
    if value_format not in VALID_FORMATS:
        raise WavesQueryError(
            f"Parameter error: value_format must be one of {sorted(VALID_FORMATS)}, got {value_format!r}."
        )


def get_transitions(
    vcd_path: str,
    signal: str,
    start_time: int,
    end_time: int,
    limit: int = 50,
    edge: str = "any",
    value: str | None = None,
    value_format: str = "raw",
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
    _validate_value_format(value_format)

    parsed = _load_vcd(vcd_path)
    info = _get_signal(parsed, signal)

    # Filter by: time window -> edge -> value -> limit
    filtered_raw: list[tuple[int, str]] = []
    prev_val: str | None = None
    for transition_time, transition_value in info.transitions:
        in_window = start_time <= transition_time <= end_time

        if in_window and _matches_edge(prev_val, transition_value, edge) and _match_value(transition_value, value):
            filtered_raw.append((transition_time, transition_value))

        prev_val = transition_value

    transition_count = len(filtered_raw)

    if value_format == "raw":
        transitions = [{"time": t, "value": v} for t, v in filtered_raw[:limit]]
    else:
        transitions = []
        for t, v in filtered_raw[:limit]:
            fmt, _ = _format_value(v, info.width, value_format)
            transitions.append({"time": t, "value": fmt, "value_raw": v})

    return {
        "signal": signal,
        "start_time": start_time,
        "end_time": end_time,
        "transitions": transitions,
        "truncated": transition_count > limit,
        "value_format": value_format,
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


def _build_window_table(
    signal_transitions: list[list[tuple[int, str]]],
    signal_names: list[str],
    resolved_start: int,
    resolved_end: int,
    value_format: str = "raw",
    signal_widths: list[int] | None = None,
) -> str:
    # Build a text table from per-signal transition data.
    #
    # Collects all unique times from all signals, then for each time
    # computes each signal's at-or-before value.  Values with no known
    # prior transition are shown as "null".
    if not signal_transitions:
        return "time\n"

    # Collect all unique times from all signals plus window bounds
    all_times: set[int] = {resolved_start, resolved_end}
    for sig_tr in signal_transitions:
        for t, _ in sig_tr:
            all_times.add(t)
    sorted_times = sorted(all_times)

    # Compute at-or-before value for each signal at each sorted time
    current_values: list[str | None] = [None] * len(signal_names)
    tr_idx: list[int] = [0] * len(signal_names)

    # Pre-format values if value_format != raw
    def val_display(raw: str | None, sig_idx: int) -> str:
        if raw is None:
            return "null"
        if value_format == "raw":
            return raw
        w = signal_widths[sig_idx] if signal_widths else len(raw)
        fmt, _ = _format_value(raw, w, value_format)
        return fmt if fmt is not None else "null"

    str_rows: list[list[str]] = [["time"] + list(signal_names)]
    for t in sorted_times:
        for i, sig_tr in enumerate(signal_transitions):
            while tr_idx[i] < len(sig_tr) and sig_tr[tr_idx[i]][0] <= t:
                current_values[i] = sig_tr[tr_idx[i]][1]
                tr_idx[i] += 1
        row = [str(t)] + [
            val_display(v, i) for i, v in enumerate(current_values)
        ]
        str_rows.append(row)

    # Calculate column widths
    col_count = len(str_rows[0])
    widths = [
        max(len(str_rows[r][c]) for r in range(len(str_rows)))
        for c in range(col_count)
    ]

    # Build formatted string
    sep = " | "
    lines: list[str] = []
    lines.append(sep.join(hdr.ljust(w) for hdr, w in zip(str_rows[0], widths)))
    lines.append("-+-".join("-" * w for w in widths))
    for row in str_rows[1:]:
        lines.append(sep.join(val.ljust(w) for val, w in zip(row, widths)))
    return "\n".join(lines)


def get_window(
    vcd_path: str,
    signals: list[str],
    start_time: int | None = None,
    end_time: int | None = None,
    center_time: int | None = None,
    before: int | None = None,
    after: int | None = None,
    limit_per_signal: int = 50,
    format: str = "structured",
    value_format: str = "raw",
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

    # Validate format parameter
    if format not in ("structured", "table"):
        raise WavesQueryError(
            f"Parameter error: format must be one of ['structured', 'table'], got {format!r}."
        )
    _validate_value_format(value_format)

    # Single VCD parse, then collect transitions per signal
    parsed = _load_vcd(vcd_path)
    all_signal_transitions: list[list[tuple[int, str]]] = []
    signal_names: list[str] = []
    any_truncated = False

    for signal in signals:
        info = _get_signal(parsed, signal)
        window_tr: list[tuple[int, str]] = [
            (transition_time, transition_value)
            for transition_time, transition_value in info.transitions
            if resolved_start <= transition_time <= resolved_end
        ]
        all_signal_transitions.append(window_tr)
        signal_names.append(signal)
        if len(window_tr) > limit_per_signal:
            any_truncated = True

    if format == "structured":
        # Build the standard per-signal result
        result_signals: list[dict[str, object]] = []
        for i, signal in enumerate(signals):
            tr = all_signal_transitions[i]
            limited = tr[:limit_per_signal]
            if value_format == "raw":
                trans_list = [{"time": t, "value": v} for t, v in limited]
            else:
                width = parsed.signals[signal].width
                trans_list = []
                for t, v in limited:
                    fmt, _ = _format_value(v, width, value_format)
                    trans_list.append({"time": t, "value": fmt, "value_raw": v})
            result_signals.append({
                "signal": signal,
                "transitions": trans_list,
                "truncated": len(tr) > limit_per_signal,
            })
        return {
            "start_time": resolved_start,
            "end_time": resolved_end,
            "signals": result_signals,
            "value_format": value_format,
        }

    # format == "table": build table view from all collected transitions
    table_str = _build_window_table(
        all_signal_transitions, signal_names, resolved_start, resolved_end,
        value_format=value_format,
        signal_widths=[parsed.signals[s].width for s in signals],
    )
    return {
        "start_time": resolved_start,
        "end_time": resolved_end,
        "format": "table",
        "table": table_str,
        "truncated": any_truncated,
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
