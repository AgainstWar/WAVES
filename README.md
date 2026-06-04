# WAVES — VCD Waveform Query MCP Server

<p align="center"><img src="logo.png" alt="WAVES Logo" width="376"></p>

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

### Minimal Example

Query `tb_pmic_fsm.clk` in `tests/fixtures/sample.vcd`:

**Input** (`wave_get_value`):
```json
{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "time": 100000}
```

**Output**:
```json
{"signal": "tb_pmic_fsm.clk", "time": 100000, "value": "0"}
```

> `value` uses at-or-before semantics: if no transition exists exactly at `time`, returns the most recent value at or before that timestamp. `null` means no prior value is recorded.

Query transitions in a time range with edge filter:

**Input** (`wave_get_transitions`):
```json
{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "start_time": 0, "end_time": 200000, "edge": "posedge"}
```

**Output**:
```json
{
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "transitions": [{"time": 10000, "value": "1"}],
  "truncated": false
}
```

> Empty `transitions` is normal data, not an error.

---

## Format Support

WAVES natively parses **VCD** files. Additionally, it supports **FST**, **LXT2**, and **VZT** formats via GTKWave's converter tools (`fst2vcd`, `lxt2vcd`, `vzt2vcd`).

```bash
# Install GTKWave for non-VCD format support
apt install gtkwave
```

Usage is transparent — just pass the file path to any tool:

```json
{"vcd_path": "/path/to/design.fst", "signal": "top.clk", "time": 100}
```

> If a GTKWave converter is not installed, you'll see a clear error message directing you to install `gtkwave`.

---

## Debugging & Development

```
src/waves/
├── vcd_parser.py     # VCD parsing
├── gtkwave_parser.py # FST/LXT2/VZT parsing (via GTKWave)
├── query.py          # Query logic
└── server.py         # MCP server

tests/
├── fixtures/
│   ├── sample.vcd    # VCD test fixture
│   ├── des.fst       # FST test fixture
│   └── transaction.fst # FST test fixture
├── test_smoke.py     # python tests/test_smoke.py
└── test_gtkwave.py   # python tests/test_gtkwave.py (requires gtkwave)
```

Source functions use [Google Style docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) — hover in VS Code / PyCharm to see **Args**, **Returns**, and **Example** snippets.

### Web UI Debugging

```bash
npx @modelcontextprotocol/inspector waves
```

Visit `http://localhost:6274`.

---

## License

MIT
