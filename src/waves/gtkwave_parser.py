# GTKWave converter-based waveform parser for WAVES.
#
# Supports FST, LXT/LXT2, VZT, and EVCD formats by invoking the
# corresponding GTKWave converter tools as subprocesses and piping
# the VCD output to the existing vcd_parser.  GTKWave is an optional
# dependency — only needed for non-VCD files.

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from waves.vcd_parser import ParsedVCD, WavesVCDError, parse_vcd

# File extension -> converter tool mapping.
_CONVERTERS: dict[str, str] = {
    ".fst": "fst2vcd",
    ".lxt": "lxt2vcd",
    ".lxt2": "lxt2vcd",
    ".vzt": "vzt2vcd",
    ".evcd": "evcd2vcd",
}

# All supported extensions for fast lookup.
SUPPORTED_EXTS: frozenset[str] = frozenset(_CONVERTERS.keys())


def _check_converter(converter: str) -> None:
    """Raise WavesVCDError if *converter* is not available on PATH."""
    try:
        subprocess.run(
            [converter, "--help"],
            capture_output=True,
            timeout=5,
        )
    except FileNotFoundError:
        raise WavesVCDError(
            f"{converter} not found.  Install gtkwave to read this file "
            "format: apt install gtkwave"
        )
    except subprocess.TimeoutExpired:
        pass  # tool exists but hung; let the real call handle it


def parse_gtkwave(path: str | Path) -> ParsedVCD:
    """Parse a GTKWave-supported waveform file by converting it to VCD.

    Detects the format from the file extension and runs the appropriate
    converter tool.  Returns a ParsedVCD identical in structure to
    parse_vcd().

    Raises:
        WavesVCDError: if the file is missing, the converter is missing,
            conversion fails, or the format is unsupported.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise WavesVCDError("file not found")
    if not file_path.is_file():
        raise WavesVCDError("path is not a file")

    suffix = file_path.suffix.lower()
    converter = _CONVERTERS.get(suffix)
    if converter is None:
        raise WavesVCDError(
            f"unsupported format: {suffix}.  "
            f"Supported: {', '.join(sorted(_CONVERTERS.keys()))}."
        )

    # Run converter, capture VCD on stdout
    try:
        result = subprocess.run(
            [converter, str(file_path.resolve())],
            capture_output=True,
            timeout=300,
        )
    except FileNotFoundError:
        raise WavesVCDError(
            f"{converter} not found.  Install gtkwave to read this file "
            "format: apt install gtkwave"
        )
    except subprocess.TimeoutExpired:
        raise WavesVCDError(f"{converter} timed out converting {file_path.name}.")

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise WavesVCDError(f"{converter} failed: {stderr}")

    vcd_text = result.stdout.decode("utf-8", errors="replace")

    # Write to temp file and parse with existing vcd parser
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".vcd", delete=False, encoding="utf-8"
    ) as f:
        f.write(vcd_text)
        temp_path = f.name

    try:
        parsed = parse_vcd(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)

    return parsed
