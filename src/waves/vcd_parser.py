from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class WavesVCDError(Exception):
    """Raised when a VCD file cannot be parsed."""


@dataclass(slots=True)
class SignalInfo:
    identifier: str
    width: int
    transitions: list[tuple[int, str]] = field(default_factory=list)


@dataclass(slots=True)
class ParsedVCD:
    timescale: str
    signals: dict[str, SignalInfo]


def parse_vcd(path: str | Path) -> ParsedVCD:
    file_path = Path(path)
    if not file_path.exists():
        raise WavesVCDError(f"VCD file not found: {file_path}")
    if not file_path.is_file():
        raise WavesVCDError(f"VCD path is not a file: {file_path}")

    try:
        raw_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise WavesVCDError(f"Could not read VCD file: {file_path}") from exc

    timescale: str | None = None
    scope_stack: list[str] = []
    signal_by_id: dict[str, SignalInfo] = {}
    signals: dict[str, SignalInfo] = {}
    current_time = 0
    saw_enddefinitions = False
    in_dumpvars = False
    command_buffer: list[str] = []

    def malformed(message: str) -> WavesVCDError:
        return WavesVCDError(f"Malformed VCD: {message}")

    def process_command(command_text: str) -> None:
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

            hierarchical_name = ".".join([*scope_stack, reference])
            if hierarchical_name in signals:
                raise malformed(f"duplicate signal name: {hierarchical_name}")

            signal = SignalInfo(identifier=identifier, width=width)
            signal_by_id[identifier] = signal
            signals[hierarchical_name] = signal
            return

        if keyword == "$enddefinitions":
            if args:
                raise malformed("$enddefinitions does not take arguments")
            saw_enddefinitions = True
            return

        if keyword in {"$comment", "$date", "$version"}:
            return

        raise WavesVCDError(f"Unsupported VCD construct: {keyword}")

    def record_value_change(identifier: str, value: str) -> None:
        signal = signal_by_id.get(identifier)
        if signal is None:
            raise malformed(f"value change for unknown identifier: {identifier}")
        normalized = value.lower()
        if any(bit not in {"0", "1", "x", "z"} for bit in normalized):
            raise malformed(f"unsupported value bits: {value}")
        if len(normalized) != signal.width:
            raise malformed(
                f"value width mismatch for {identifier}: expected {signal.width}, got {len(normalized)}"
            )
        signal.transitions.append((current_time, normalized))

    def process_value_change(line: str) -> None:
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

        raise WavesVCDError(f"Unsupported VCD value change: {line}")

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
                    raise WavesVCDError("Unsupported VCD construct: inline $dumpvars")
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
            continue

        if not saw_enddefinitions:
            raise malformed(f"unexpected content before $enddefinitions: {line}")
        process_value_change(line)

    if command_buffer:
        raise malformed("unterminated command at end of file")
    if in_dumpvars:
        raise malformed("unterminated $dumpvars block")
    if timescale is None:
        raise malformed("missing $timescale")
    if not saw_enddefinitions:
        raise malformed("missing $enddefinitions")

    return ParsedVCD(timescale=timescale, signals=signals)
