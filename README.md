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

| Tool | Function |
|------|----------|
| `wave_get_info` | Get VCD file basic info (timescale, time range, signal count) |
| `wave_list_signals` | List all signals, with optional name filter |
| `wave_get_value` | Query signal value at a given time (at-or-before) |
| `wave_get_transitions` | Query signal transitions in a time range, with edge/value filter |
| `wave_get_window` | Query multiple signals in the same time window |
| `wave_find_transition` | Find the nearest transition before or after a given time |

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
