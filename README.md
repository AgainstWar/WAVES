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
