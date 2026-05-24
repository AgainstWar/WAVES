from __future__ import annotations

from typing import Any, cast

import waves.query
import waves.vcd_parser
from waves.query import WavesQueryError, get_transitions, get_value, list_signals
from waves.server import main, mcp


VCD_PATH = "tests/fixtures/simple.vcd"


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def require_dict(value: object, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssertionError(message)
    return cast(dict[str, Any], value)


def main_smoke() -> None:
    assert mcp is not None
    assert callable(main)
    assert waves.query is not None
    assert waves.vcd_parser is not None

    signals = require_dict(list_signals(VCD_PATH), "list_signals must return a dict")
    assert_equal(signals["signal_count"], 3, "signal_count mismatch")
    signal_items = signals["signals"]
    if not isinstance(signal_items, list):
        raise AssertionError("signals must be a list")
    assert_equal(
        [require_dict(signal, "signal entry must be a dict")["name"] for signal in signal_items],
        ["top.clk", "top.reset", "top.dut.out"],
        "signal list mismatch",
    )

    try:
        list_signals(VCD_PATH, limit=0)
    except WavesQueryError:
        pass
    else:
        raise AssertionError("expected WavesQueryError for invalid limit")

    value_at_120 = require_dict(get_value(VCD_PATH, "top.dut.out", 120), "get_value must return a dict")
    assert_equal(value_at_120["value"], "00000101", "value at 120 mismatch")

    value_at_130 = require_dict(get_value(VCD_PATH, "top.dut.out", 130), "get_value must return a dict")
    assert_equal(value_at_130["value"], "00000101", "value at 130 mismatch")

    try:
        get_value(VCD_PATH, "top.dut.out", -1)
    except WavesQueryError:
        pass
    else:
        raise AssertionError("expected WavesQueryError for negative time")

    transitions = require_dict(
        get_transitions(VCD_PATH, "top.dut.out", 100, 160, limit=50),
        "get_transitions must return a dict",
    )
    assert_equal(
        transitions["transitions"],
        [
            {"time": 120, "value": "00000101"},
            {"time": 140, "value": "00000111"},
        ],
        "transitions mismatch",
    )

    empty_range = require_dict(
        get_transitions(VCD_PATH, "top.dut.out", 121, 121, limit=50),
        "get_transitions must return a dict",
    )
    assert_equal(empty_range["transitions"], [], "empty range mismatch")

    try:
        get_transitions(VCD_PATH, "top.dut.out", -1, 160, limit=50)
    except WavesQueryError:
        pass
    else:
        raise AssertionError("expected WavesQueryError for negative start_time")

    try:
        get_value(VCD_PATH, "top.dut.missing", 120)
    except WavesQueryError:
        pass
    else:
        raise AssertionError("expected WavesQueryError for unknown signal")

    print("SMOKE_OK")


if __name__ == "__main__":
    main_smoke()
