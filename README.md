# WAVES — VCD Waveform Query MCP Server

**WAVES** (Waveform Access via Explicit Signals) is a local stdio tool based on the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) for querying signal values and timing changes in VCD (Value Change Dump) waveform files.

> [中文](./README.zh.md)

---

## Installation

```bash
git clone https://github.com/AgainstWar/WAVES.git
cd WAVES
pip install .
```

---

## Quick Start

Start the MCP server:

```bash
waves
```

Communicates with MCP clients via stdio.

WAVES exposes 6 MCP tools covering the workflow from browsing signals to querying values and transitions:

| Tool | Function |
|------|----------|
| `wave_get_info` | Returns timescale, time range, and total signal count |
| `wave_list_signals` | Lists signal names and bit widths, with optional substring filter |
| `wave_get_value` | Queries a signal value at a specific time (at-or-before lookup) |
| `wave_get_transitions` | Queries all transitions of a signal in a time range, with optional edge or value filter |
| `wave_get_window` | Queries multiple signals in the same time window (structured or table output) |
| `wave_find_transition` | Finds the nearest transition before or after a given time, with optional edge filter |

Typical workflow: use `wave_list_signals` to discover exact signal names, then query with `wave_get_value`, `wave_get_transitions`, or `wave_get_window`.

### Example

Using `tests/fixtures/sample.vcd` (Icarus Verilog):  

**1. Inspect the file**

Input: `wave_get_info` with `{"vcd_path": "tests/fixtures/sample.vcd"}`

Output:
```json
{
  "vcd_path": "tests/fixtures/sample.vcd",
  "timescale": "1ps",
  "start_time": 0,
  "end_time": 1361000,
  "signal_count": 251
}
```

**2. List signals**

Input: `wave_list_signals` with `{"vcd_path": "tests/fixtures/sample.vcd", "filter": "clk", "limit": 5}`

Output:
```json
{
  "vcd_path": "tests/fixtures/sample.vcd",
  "signal_count": 10,
  "signals": [
    {"name": "tb_pmic_fsm.clk", "width": 1}
  ],
  "truncated": true
}
```

**3. Query a value**

Input: `wave_get_value` with `{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "time": 100000}`

Output:
```json
{
  "signal": "tb_pmic_fsm.clk",
  "time": 100000,
  "value": "0"
}
```

> **at-or-before semantics**: if no transition exists exactly at `time=100000`, returns the most recent value at or before that timestamp.

**4. Query transitions**

Input: `wave_get_transitions` with `{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "start_time": 0, "end_time": 200000, "limit": 10}`

Output:
```json
{
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "transitions": [
    {"time": 0, "value": "0"},
    {"time": 10000, "value": "1"},
    {"time": 20000, "value": "0"}
  ],
  "truncated": false,
  "value_format": "raw"
}
```

**5. Filter by edge**

Input: `wave_get_transitions` with `{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "start_time": 0, "end_time": 200000, "edge": "posedge"}`

Output retains only 0→1 transitions:
```json
{
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "transitions": [
    {"time": 10000, "value": "1"}
  ],
  "truncated": false
}
```

**6. Query multiple signals in a window**

Input: `wave_get_window` with `{"vcd_path": "tests/fixtures/sample.vcd", "signals": ["tb_pmic_fsm.clk", "tb_pmic_fsm.rst_n"], "start_time": 0, "end_time": 50000, "limit_per_signal": 10}`

Output:
```json
{
  "start_time": 0,
  "end_time": 50000,
  "signals": [
    {
      "signal": "tb_pmic_fsm.clk",
      "transitions": [
        {"time": 0, "value": "0"},
        {"time": 10000, "value": "1"},
        {"time": 20000, "value": "0"}
      ],
      "truncated": false
    },
    {
      "signal": "tb_pmic_fsm.rst_n",
      "transitions": [],
      "truncated": false
    }
  ]
}
```

> Empty `transitions` is normal data, not an error.

---

## Debugging & Development

```
src/waves/
├── vcd_parser.py   # VCD parsing
├── query.py        # Query logic
└── server.py       # MCP server

tests/
├── fixtures/sample.vcd
└── test_smoke.py   # python tests/test_smoke.py
```

### Web UI Debugging

```bash
npx @modelcontextprotocol/inspector waves
```

Visit `http://localhost:6274`.

---

## License

MIT
