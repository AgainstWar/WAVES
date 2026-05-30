# WAVES Knowledge Base

**Generated:** 2026-05-30
**Commit:** fcdfd9a
**Branch:** master

## OVERVIEW

WAVES (Waveform Access via Explicit Signals) is a local stdio MCP server for querying VCD waveform files. Built with Python 3.10+ and the official MCP Python SDK.

## STRUCTURE

```
waves/
├── pyproject.toml          # Package config, mcp dependency, waves console entry
├── README.md               # English: install, tools, debugging
├── README.zh.md            # Chinese translation
├── src/waves/
│   ├── __init__.py
│   ├── vcd_parser.py       # Minimal VCD parser (scalar + vector)
│   ├── query.py            # Signal lookup, value, transitions, window, find
│   └── server.py           # FastMCP stdio server, 6 tools
├── tests/
│   ├── fixtures/sample.vcd # Test waveform fixture (Icarus Verilog)
│   └── test_smoke.py       # Minimal executable verification
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add VCD format support | `src/waves/vcd_parser.py` | Only scalar/vector now |
| Add query logic | `src/waves/query.py` | filter, limit, range, truncation |
| Add MCP tools | `src/waves/server.py` | 6 tool decorators |
| Fix install/runtime | `pyproject.toml` | entrypoint: `waves = waves.server:main` |

## CODE MAP

| Symbol | Type | File | Role |
|--------|------|------|------|
| `parse_vcd` | function | `vcd_parser.py` | Entry parser, returns `ParsedVCD` |
| `get_info` | function | `query.py` | File-level metadata |
| `list_signals` | function | `query.py` | Filtered signal listing |
| `get_value` | function | `query.py` | At-or-before value lookup |
| `get_transitions` | function | `query.py` | Inclusive range transitions |
| `get_window` | function | `query.py` | Multi-signal window slice |
| `find_transition` | function | `query.py` | Nearest transition before/after time |
| `wave_get_info` | MCP tool | `server.py` | Delegates to `get_info` |
| `wave_list_signals` | MCP tool | `server.py` | Delegates to `list_signals` |
| `wave_get_value` | MCP tool | `server.py` | Delegates to `get_value` |
| `wave_get_transitions` | MCP tool | `server.py` | Delegates to `get_transitions` |
| `wave_get_window` | MCP tool | `server.py` | Delegates to `get_window` |
| `wave_find_transition` | MCP tool | `server.py` | Delegates to `find_transition` |
| `main` | function | `server.py` | Calls `mcp.run()` (stdio) |

## CONVENTIONS

- **src-layout**: `src/waves/` not `./waves/`
- **Timescale**: parsed as metadata only; all time inputs/outputs are raw VCD integer timestamps
- **Value format**: scalars `"0"/"1"/"x"/"z"`; vectors lowercase bit string without `b` prefix
- **Missing value**: returns `null` (Python `None`) — never invent values
- **Signal matching**: exact hierarchical name only; no fuzzy/suffix/regex

## MCP DESCRIPTIONS

When adding or editing `@mcp.tool()` functions:

- **Tool description** goes in the **docstring** — this is sent to LLM clients via `tools/list`. Keep it concise (one sentence what it does, optionally one sentence how it relates to other tools). Do NOT include debugging strategies, RTL analysis workflows, or natural-language summaries.
- **Parameter descriptions** go in **`Annotated[..., Field(description="...")]`** — these become JSON Schema `description` fields and are visible to LLM clients. Be explicit about units, constraints, and references to other tools (e.g. "Exact hierarchical signal name returned by wave_list_signals").
- See existing tools in `src/waves/server.py` for the established pattern.

## ANTI-PATTERNS (THIS PROJECT)

- Never add HTTP/SSE/transportable-http; stdio only
- Never vendor or modify upstream `mcp` SDK
- Never add simulation execution or VCD generation
- Never add RTL/Chisel/FIRRTL mapping
- Never add natural-language summaries or debug conclusions
- Never add persistent session state or caching
- Never expand test framework beyond minimal smoke

## COMMANDS

```bash
python -m pip install -e .     # Editable install
python tests/test_smoke.py    # Run verification
waves                          # Start stdio MCP server
```

## ICARUS VERILOG COMPATIBILITY

Tested with Icarus Verilog generated VCD files (`tests/fixtures/sample.vcd`):

| Feature | Status | Notes |
|---------|--------|-------|
| `$dumpall` | Supported | Outputs parameter initial values before `$dumpvars` |
| `$dumpoff` / `$dumpon` | Ignored | Safe to skip for query-only use |
| Multi-scope shared identifiers | Supported | Same identifier reused across scopes (e.g. `clk` in `tb`, `dut`, `u_fsm_ctrl`) |
| Multi-char identifiers | Supported | Icarus uses `]"`, `"` etc. when signal count > 94 |
| Short vector values | Supported | Values shorter than signal width (e.g. `b0 ]"` for width-10 signal) |
| `$parameter` type | Supported | Treated same as `wire`/`reg` for signal listing |

## DEBUGGING WITH MCP INSPECTOR

```bash
# UI mode
npx @modelcontextprotocol/inspector waves

# CLI mode examples
npx @modelcontextprotocol/inspector --cli waves --method tools/list
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_list_signals \
  --tool-arg "vcd_path=tests/fixtures/sample.vcd"
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_get_value \
  --tool-arg "vcd_path=tests/fixtures/sample.vcd" \
  --tool-arg signal=tb_pmic_fsm.clk \
  --tool-arg time=100000
```

## NOTES

- Fixture contract: `tests/fixtures/sample.vcd` must contain `tb_pmic_fsm.clk`, `tb_pmic_fsm.rst_n`, `tb_pmic_fsm.current_state [3:0]` with exact transitions
- `WavesVCDError` / `WavesQueryError` are the only domain exceptions; server converts to MCP `ToolError`
- `.sisyphus/` contains planning artifacts and evidence (not shipped)
- `.gitignore` excludes `__pycache__/` and `.egg-info/`
- Tests use script-style assertions, not pytest
