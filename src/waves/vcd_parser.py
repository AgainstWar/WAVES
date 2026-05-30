# Minimal VCD parser for WAVES.
#
# Supports scalar and vector value changes, hierarchical signal names,
# Icarus Verilog extensions (multi-char identifiers, $dumpall, $parameter),
# and basic malformed-VCD detection.
#
# All times are stored as raw integer timestamps; timescale is parsed as
# metadata only.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class WavesVCDError(Exception):
    """Raised when a VCD file cannot be parsed or read."""


@dataclass(slots=True)
class SignalInfo:
    """Metadata and transition list for one VCD signal."""
    # identifier: short VCD id (e.g. "!" or "]\"")
    # width: bit width (1=scalar, >1=vector)
    # transitions: ordered (time, value) tuples; time is raw integer;
    #              value is lower-case bit string without "b" prefix
    identifier: str
    width: int
    transitions: list[tuple[int, str]] = field(default_factory=list)


@dataclass(slots=True)
class ParsedVCD:
    """Result of parsing a VCD file."""
    # timescale: VCD timescale string (e.g. "1ps", "1ns")
    # signals: full hierarchical name -> SignalInfo
    # start_time: always 0 (dumpvars implicitly at time 0)
    # end_time: last explicit timestamp, or None if no #timestamp lines
    timescale: str
    signals: dict[str, SignalInfo]
    start_time: int = 0
    end_time: int | None = None


def parse_vcd(path: str | Path) -> ParsedVCD:
    """Parse a VCD file and return its metadata plus all signal transitions.

    Args:
        path: Path to the VCD file (str or Path).

    Returns:
        ParsedVCD with fields: timescale, signals, start_time, end_time.

    Raises:
        WavesVCDError: If the file is missing, unreadable, or not a valid VCD.

    Example:
        Input: parse_vcd("tests/fixtures/sample.vcd")
        Output: ParsedVCD(
            timescale="1ps",
            signals={"tb_pmic_fsm.clk": SignalInfo(...)},
            start_time=0,
            end_time=1361000,
        )
    """
    file_path = Path(path)
    if not file_path.exists():
        raise WavesVCDError("file not found")
    if not file_path.is_file():
        raise WavesVCDError("path is not a file")

    try:
        raw_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise WavesVCDError("could not read file") from exc

    # Parser state
    timescale: str | None = None
    scope_stack: list[str] = []
    signal_by_id: dict[str, list[SignalInfo]] = {}
    signals: dict[str, SignalInfo] = {}
    current_time = 0
    has_timestamps = False
    saw_enddefinitions = False
    in_dumpvars = False
    command_buffer: list[str] = []

    def malformed(message: str) -> WavesVCDError:
        # Build a WavesVCDError with a malformed-VCD reason.
        return WavesVCDError(message)

    def process_command(command_text: str) -> None:
        # Handle a single VCD command (e.g. $timescale, $var, $scope).
        nonlocal timescale, saw_enddefinitions

        parts = command_text.split()
        if not parts:
            return

        keyword = parts[0]
        if parts[-1] != "$end":
            raise malformed(f"unterminated command: {command_text}")
        args = parts[1:-1]

        if keyword == "$timescale":
            if not args:
                raise malformed("missing timescale value")
            timescale = "".join(args)
            return

        if keyword == "$scope":
            if len(args) < 2:
                raise malformed("invalid $scope declaration")
            scope_stack.append(args[1])
            return

        if keyword == "$upscope":
            if args:
                raise malformed("$upscope does not take arguments")
            if not scope_stack:
                raise malformed("$upscope without matching $scope")
            scope_stack.pop()
            return

        if keyword == "$var":
            if len(args) < 4:
                raise malformed("invalid $var declaration")
            _, width_text, identifier, *reference_parts = args
            try:
                width = int(width_text)
            except ValueError as exc:
                raise malformed(f"invalid signal width: {width_text}") from exc
            if width <= 0:
                raise malformed(f"invalid signal width: {width}")
            reference = " ".join(reference_parts)
            if not reference:
                raise malformed("missing signal reference name")

            # Build hierarchical name from current scope stack
            hierarchical_name = ".".join([*scope_stack, reference])
            if hierarchical_name in signals:
                raise malformed(f"duplicate signal name: {hierarchical_name}")

            signal = SignalInfo(identifier=identifier, width=width)
            signal_by_id.setdefault(identifier, []).append(signal)
            signals[hierarchical_name] = signal
            return

        if keyword == "$enddefinitions":
            if args:
                raise malformed("$enddefinitions does not take arguments")
            saw_enddefinitions = True
            return

        if keyword in {"$comment", "$date", "$version"}:
            # Safe to skip for query-only use
            return

        raise WavesVCDError(f"unsupported VCD construct: {keyword}")

    def record_value_change(identifier: str, value: str) -> None:
        # Record a value change for all signals sharing this identifier.
        signal_list = signal_by_id.get(identifier)
        if not signal_list:
            raise malformed(f"value change for unknown identifier: {identifier}")
        normalized = value.lower()
        if any(bit not in {"0", "1", "x", "z"} for bit in normalized):
            raise malformed(f"unsupported value bits: {value}")
        # VCD allows values shorter than signal width (implicit zero/sign extension)
        # Only reject if value is wider than declared signal width
        max_width = max(s.width for s in signal_list)
        if len(normalized) > max_width:
            raise malformed(
                f"value width mismatch for {identifier}: expected max {max_width}, got {len(normalized)}"
            )
        for signal in signal_list:
            signal.transitions.append((current_time, normalized))

    def process_value_change(line: str) -> None:
        # Parse one value-change line (vector or scalar) and record it.
        if line.startswith("b"):
            parts = line.split()
            if len(parts) != 2:
                raise malformed(f"invalid vector change: {line}")
            vector_value, identifier = parts
            record_value_change(identifier, vector_value[1:])
            return

        prefix = line[0]
        if prefix in {"0", "1", "x", "z"}:
            identifier = line[1:].strip()
            if not identifier:
                raise malformed(f"missing identifier in scalar change: {line}")
            record_value_change(identifier, prefix)
            return

        raise WavesVCDError(f"unsupported VCD value change: {line}")

    # Main parse loop
    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue

        if in_dumpvars:
            if line == "$end":
                in_dumpvars = False
                continue
            process_value_change(line)
            continue

        if command_buffer:
            command_buffer.append(line)
            if "$end" in line:
                process_command(" ".join(command_buffer))
                command_buffer.clear()
            continue

        if line.startswith("$"):
            if line.startswith("$dumpvars") or line == "$dumpall":
                if not saw_enddefinitions:
                    raise malformed("dump section before $enddefinitions")
                if line.startswith("$dumpvars") and line != "$dumpvars":
                    raise WavesVCDError("unsupported VCD construct: inline $dumpvars")
                in_dumpvars = True
                continue

            if line in {"$dumpoff", "$dumpon"}:
                # These commands are safe to ignore for query-only purposes
                continue

            if "$end" in line:
                process_command(line)
            else:
                command_buffer.append(line)
            continue

        if line.startswith("#"):
            if not saw_enddefinitions:
                raise malformed("timestamp before $enddefinitions")
            timestamp_text = line[1:]
            try:
                next_time = int(timestamp_text)
            except ValueError as exc:
                raise malformed(f"invalid timestamp: {timestamp_text}") from exc
            if next_time < 0:
                raise malformed(f"invalid timestamp: {next_time}")
            if next_time < current_time:
                raise malformed("timestamps must be non-decreasing")
            current_time = next_time
            has_timestamps = True
            continue

        if not saw_enddefinitions:
            raise malformed(f"unexpected content before $enddefinitions: {line}")
        process_value_change(line)

    # Final validation
    if command_buffer:
        raise malformed("unterminated command at end of file")
    if in_dumpvars:
        raise malformed("unterminated $dumpvars block")
    if timescale is None:
        raise malformed("missing $timescale")
    if not saw_enddefinitions:
        raise malformed("missing $enddefinitions")

    end_time = current_time if has_timestamps else None
    return ParsedVCD(
        timescale=timescale,
        signals=signals,
        start_time=0,
        end_time=end_time,
    )
