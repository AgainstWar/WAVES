# WAVES smoke test — minimal executable verification for all MCP tools.
#
# Runs the five public query functions against a real Icarus-Verilog-generated
# VCD (tests/fixtures/sample.vcd) and asserts on return shapes, field values,
# and exact error-message text.  This is not a pytest suite; it exits with
# SMOKE_OK or raises AssertionError.

from __future__ import annotations

from typing import Any, cast

import waves.query
import waves.vcd_parser
from waves.query import WavesQueryError, get_info, get_transitions, get_value, get_window, list_signals
from waves.server import main, mcp

# Path to the Icarus Verilog test fixture used for all smoke checks.
VCD_PATH = "tests/fixtures/sample.vcd"


def assert_equal(actual: object, expected: object, message: str) -> None:
    # Raise AssertionError with context if actual != expected.
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def require_dict(value: object, message: str) -> dict[str, Any]:
    # Assert value is a dict and return it casted.
    if not isinstance(value, dict):
        raise AssertionError(message)
    return cast(dict[str, Any], value)


def assert_error_contains(fn: object, expected_substring: str, message: str) -> None:
    # Call fn and assert it raises WavesQueryError containing expected_substring.
    # If no exception is raised, or the message does not contain the substring,
    # raises AssertionError.
    try:
        if callable(fn):
            fn()
        else:
            raise AssertionError(f"{message}: expected callable")
    except WavesQueryError as exc:
        if expected_substring not in str(exc):
            raise AssertionError(
                f"{message}: expected '{expected_substring}' in error message, got '{exc}'"
            ) from exc
    else:
        raise AssertionError(message)


def main_smoke() -> None:
    # ------------------------------------------------------------------
    # Sanity-check module imports and the MCP server instance
    # ------------------------------------------------------------------
    assert mcp is not None
    assert callable(main)
    assert waves.query is not None
    assert waves.vcd_parser is not None

    # ==================================================================
    # wave_get_info
    # ==================================================================
    info = require_dict(get_info(VCD_PATH), "get_info must return a dict")
    assert_equal(info["vcd_path"], VCD_PATH, "info vcd_path mismatch")
    assert_equal(info["timescale"], "1ps", "info timescale mismatch")
    assert_equal(info["start_time"], 0, "info start_time mismatch")
    assert_equal(info["end_time"], 1361000, "info end_time mismatch")
    assert_equal(info["signal_count"], 251, "info signal_count mismatch")

    # ==================================================================
    # wave_list_signals
    # ==================================================================
    signals = require_dict(list_signals(VCD_PATH), "list_signals must return a dict")
    assert_equal(signals["signal_count"], 251, "signal_count mismatch")
    signal_items = signals["signals"]
    if not isinstance(signal_items, list):
        raise AssertionError("signals must be a list")
    first_names = [require_dict(s, "signal entry must be a dict")["name"] for s in signal_items[:3]]
    assert_equal(
        first_names,
        [
            "tb_pmic_fsm.current_state [3:0]",
            "tb_pmic_fsm.current_vg [8:0]",
            "tb_pmic_fsm.fault_latch [4:0]",
        ],
        "first signal names mismatch",
    )

    # Filtered listing with truncation
    filtered = require_dict(
        list_signals(VCD_PATH, filter="clk", limit=5),
        "list_signals filter must return a dict",
    )
    assert_equal(filtered["signal_count"], 10, "filtered signal_count mismatch")
    assert_equal(len(filtered["signals"]), 5, "filtered signals length mismatch")
    assert_equal(filtered["truncated"], True, "filtered truncated mismatch")

    # Parameter error: limit <= 0
    assert_error_contains(
        lambda: list_signals(VCD_PATH, limit=0),
        "Parameter error: limit must be greater than 0",
        "expected Parameter error for invalid limit",
    )

    # ==================================================================
    # wave_get_value
    # ==================================================================
    clk_value = require_dict(
        get_value(VCD_PATH, "tb_pmic_fsm.clk", 100000),
        "get_value must return a dict",
    )
    assert_equal(clk_value["value"], "0", "clk value at 100000 mismatch")

    # Parameter error: negative time
    assert_error_contains(
        lambda: get_value(VCD_PATH, "tb_pmic_fsm.clk", -1),
        "Parameter error: time must be greater than or equal to 0",
        "expected Parameter error for negative time",
    )

    # ==================================================================
    # wave_get_transitions
    # ==================================================================
    transitions = require_dict(
        get_transitions(VCD_PATH, "tb_pmic_fsm.clk", 0, 200000, limit=50),
        "get_transitions must return a dict",
    )
    assert_equal(
        transitions["transitions"][0],
        {"time": 0, "value": "0"},
        "first transition mismatch",
    )
    assert_equal(
        transitions["transitions"][1],
        {"time": 10000, "value": "1"},
        "second transition mismatch",
    )

    # Empty range is normal data, not an error
    empty_range = require_dict(
        get_transitions(VCD_PATH, "tb_pmic_fsm.clk", 5000, 5000, limit=50),
        "get_transitions must return a dict",
    )
    assert_equal(empty_range["transitions"], [], "empty range mismatch")

    # Parameter error: negative start_time
    assert_error_contains(
        lambda: get_transitions(VCD_PATH, "tb_pmic_fsm.clk", -1, 160, limit=50),
        "Parameter error: start_time must be greater than or equal to 0",
        "expected Parameter error for negative start_time",
    )

    # ==================================================================
    # Error model: Signal error
    # ==================================================================
    assert_error_contains(
        lambda: get_value(VCD_PATH, "tb_pmic_fsm.nonexistent", 120),
        "Signal error: signal not found: tb_pmic_fsm.nonexistent",
        "expected Signal error for unknown signal",
    )

    # ==================================================================
    # Error model: VCD file error
    # ==================================================================
    assert_error_contains(
        lambda: get_info("/nonexistent/path/test.vcd"),
        "VCD file error: /nonexistent/path/test.vcd. Reason: file not found",
        "expected VCD file error for missing file",
    )

    # ==================================================================
    # wave_get_window
    # ==================================================================
    window = require_dict(
        get_window(
            VCD_PATH,
            ["tb_pmic_fsm.clk", "tb_pmic_fsm.rst_n", "tb_pmic_fsm.current_state [3:0]"],
            0,
            50000,
            limit_per_signal=50,
        ),
        "get_window must return a dict",
    )
    assert_equal(window["start_time"], 0, "window start_time mismatch")
    assert_equal(window["end_time"], 50000, "window end_time mismatch")
    window_signals = window["signals"]
    if not isinstance(window_signals, list):
        raise AssertionError("window signals must be a list")
    if len(window_signals) != 3:
        raise AssertionError(
            f"window signals length mismatch: expected 3, got {len(window_signals)}"
        )
    assert_equal(window_signals[0]["signal"], "tb_pmic_fsm.clk", "window signal[0] name mismatch")
    assert_equal(window_signals[1]["signal"], "tb_pmic_fsm.rst_n", "window signal[1] name mismatch")
    assert_equal(
        window_signals[2]["signal"],
        "tb_pmic_fsm.current_state [3:0]",
        "window signal[2] name mismatch",
    )
    if not isinstance(window_signals[0]["transitions"], list):
        raise AssertionError("window signal transitions must be a list")
    assert_equal(window_signals[0]["truncated"], False, "window truncated mismatch")

    # Empty transitions inside a window is normal data
    empty_window = require_dict(
        get_window(VCD_PATH, ["tb_pmic_fsm.clk"], 5000, 5000, limit_per_signal=50),
        "get_window must return a dict",
    )
    empty_signals = empty_window["signals"]
    if not isinstance(empty_signals, list) or len(empty_signals) != 1:
        raise AssertionError("empty_window signals mismatch")
    assert_equal(empty_signals[0]["transitions"], [], "empty_window transitions mismatch")
    assert_equal(empty_signals[0]["truncated"], False, "empty_window truncated mismatch")

    # Parameter error: empty signals list
    assert_error_contains(
        lambda: get_window(VCD_PATH, [], 0, 100, limit_per_signal=50),
        "Parameter error: signals must not be empty",
        "expected Parameter error for empty signals",
    )

    # Parameter error: more than 20 signals
    assert_error_contains(
        lambda: get_window(VCD_PATH, ["tb_pmic_fsm.clk"] * 21, 0, 100, limit_per_signal=50),
        "Parameter error: signals must contain at most 20 signals",
        "expected Parameter error for too many signals",
    )

    # Parameter error: limit_per_signal <= 0
    assert_error_contains(
        lambda: get_window(VCD_PATH, ["tb_pmic_fsm.clk"], 0, 100, limit_per_signal=0),
        "Parameter error: limit_per_signal must be greater than 0",
        "expected Parameter error for limit_per_signal=0",
    )

    # Parameter error: duplicate signal names
    assert_error_contains(
        lambda: get_window(
            VCD_PATH, ["tb_pmic_fsm.clk", "tb_pmic_fsm.clk"], 0, 100, limit_per_signal=50
        ),
        "Parameter error: signals contains duplicates: tb_pmic_fsm.clk",
        "expected Parameter error for duplicate signals",
    )

    # Signal error inside wave_get_window
    assert_error_contains(
        lambda: get_window(VCD_PATH, ["tb_pmic_fsm.nonexistent"], 0, 100, limit_per_signal=50),
        "Signal error: signal not found: tb_pmic_fsm.nonexistent",
        "expected Signal error for unknown signal in window",
    )

    print("SMOKE_OK")


if __name__ == "__main__":
    main_smoke()
