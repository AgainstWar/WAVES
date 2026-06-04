# WAVES GTKWave converter smoke tests.
#
# Tests FST waveform parsing via GTKWave converters (fst2vcd).
# Uses system-provided FST test fixtures.  These tests require
# gtkwave to be installed (apt install gtkwave).

from __future__ import annotations

from waves.gtkwave_parser import SUPPORTED_EXTS, parse_gtkwave
from waves.query import (
    WavesQueryError,
    get_info,
    get_transitions,
    get_value,
    get_window,
    list_signals,
)
from waves.vcd_parser import WavesVCDError

FST_SIMPLE = "tests/fixtures/transaction.fst"
FST_COMPLEX = "tests/fixtures/des.fst"
LXT2_FILE = "tests/fixtures/sample.lxt2"
VZT_FILE = "tests/fixtures/sample.vzt"


def assert_eq(actual: object, expected: object, msg: str) -> None:
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected!r}, got {actual!r}")


def assert_err(fn, substring: str, msg: str) -> None:
    try:
        fn()
    except (WavesQueryError, WavesVCDError) as exc:
        if substring not in str(exc):
            raise AssertionError(
                f"{msg}: expected '{substring}' in error, got '{exc}'"
            ) from exc
    except Exception as exc:
        raise AssertionError(f"{msg}: unexpected exception: {exc}") from exc
    else:
        raise AssertionError(f"{msg}: no error raised")


# ====================================================================
# Supported extensions
# ====================================================================

assert_eq(
    SUPPORTED_EXTS,
    {".fst", ".lxt", ".lxt2", ".vzt", ".evcd"},
    "supported extensions mismatch",
)

# ====================================================================
# parse_gtkwave: simple FST (single 8-bit signal)
# ====================================================================

parsed = parse_gtkwave(FST_SIMPLE)
assert_eq(parsed.timescale, "1ms", "simple timescale")
assert_eq(parsed.start_time, 0, "simple start_time")
assert_eq(parsed.end_time, 348927, "simple end_time")
assert_eq(len(parsed.signals), 1, "simple signal count")
assert_eq(
    list(parsed.signals.keys()), ["top.val"], "simple signal name"
)
assert_eq(parsed.signals["top.val"].width, 8, "simple signal width")

# ====================================================================
# get_info
# ====================================================================

info = get_info(FST_SIMPLE)
assert_eq(info["timescale"], "1ms", "info timescale")
assert_eq(info["signal_count"], 1, "info signal_count")
assert_eq(info["start_time"], 0, "info start_time")
assert_eq(info["end_time"], 348927, "info end_time")

info2 = get_info(FST_COMPLEX)
assert_eq(info2["signal_count"], 1432, "complex signal_count")
assert_eq(info2["timescale"], "1s", "complex timescale")

# ====================================================================
# list_signals
# ====================================================================

sigs = list_signals(FST_SIMPLE)
assert_eq(sigs["signal_count"], 1, "list signal_count")
assert_eq(sigs["signals"][0]["name"], "top.val", "list signal name")
assert_eq(sigs["signals"][0]["width"], 8, "list signal width")

# ====================================================================
# get_value
# ====================================================================

v = get_value(FST_SIMPLE, "top.val", 100)
assert_eq(v["signal"], "top.val", "value signal name")
assert isinstance(v["value"], str), "value must be string"

v0 = get_value(FST_SIMPLE, "top.val", 0)
assert isinstance(v0["value"], str), "value at t=0 must be string"
assert len(v0["value"]) == 8, "value at t=0 must be 8-bit"

# ====================================================================
# get_transitions
# ====================================================================

tr = get_transitions(FST_SIMPLE, "top.val", 0, 1000, limit=10)
assert isinstance(tr["transitions"], list), "transitions must be list"
assert len(tr["transitions"]) > 0, "must have transitions"
assert_eq(tr["signal"], "top.val", "transitions signal name")
# May be truncated depending on how many transitions in [0, 1000]
assert isinstance(tr["truncated"], bool), "truncated must be bool"

# ====================================================================
# get_window
# ====================================================================

win = get_window(FST_SIMPLE, ["top.val"], 0, 1000, limit_per_signal=10)
assert_eq(win["start_time"], 0, "window start_time")
assert_eq(win["end_time"], 1000, "window end_time")
assert_eq(len(win["signals"]), 1, "window signals count")
assert_eq(win["signals"][0]["signal"], "top.val", "window signal name")

# ====================================================================
# Error: file not found
# ====================================================================

assert_err(
    lambda: parse_gtkwave("/nonexistent/path.fst"),
    "file not found",
    "missing file error",
)

# ====================================================================
# Error: unsupported extension
# ====================================================================

assert_err(
    lambda: parse_gtkwave("tests/fixtures/sample.vcd"),
    "unsupported format",
    "unsupported format error",
)

# ====================================================================
# Verify VCD files still work unchanged
# ====================================================================

vcd_info = get_info("tests/fixtures/sample.vcd")
assert_eq(vcd_info["signal_count"], 251, "VCD still works")

# ====================================================================
# LXT2 format (via lxt2vcd)
# ====================================================================

lxt2_info = get_info(LXT2_FILE)
assert_eq(lxt2_info["signal_count"], 251, "LXT2 signal_count")
assert_eq(lxt2_info["timescale"], "1ps", "LXT2 timescale")

lxt2_sigs = list_signals(LXT2_FILE, limit=5)
assert_eq(len(lxt2_sigs["signals"]), 5, "LXT2 list_signals")
assert isinstance(lxt2_sigs["truncated"], bool)

lxt2_val = get_value(LXT2_FILE, "tb_pmic_fsm.clk", 100000)
assert_eq(lxt2_val["signal"], "tb_pmic_fsm.clk", "LXT2 value signal")

# ====================================================================
# VZT format (via vzt2vcd)
# ====================================================================

vzt_info = get_info(VZT_FILE)
assert_eq(vzt_info["signal_count"], 251, "VZT signal_count")
assert_eq(vzt_info["timescale"], "1ps", "VZT timescale")

vzt_sigs = list_signals(VZT_FILE, filter="clk", limit=5)
assert len(vzt_sigs["signals"]) > 0, "VZT must have clk signals"

vzt_val = get_value(VZT_FILE, "tb_pmic_fsm.clk", 100000)
assert_eq(vzt_val["signal"], "tb_pmic_fsm.clk", "VZT value signal")

print("GTKWAVE_OK")
