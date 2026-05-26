# WAVES Knowledge Base

**Generated:** 2026-05-24
**Commit:** 91c421b
**Branch:** master

## OVERVIEW

WAVES (Waveform Access via Explicit Signals) is a local stdio MCP server for querying VCD waveform files. Built with Python 3.10+ and the official MCP Python SDK.

## STRUCTURE

```
waves/
├── pyproject.toml          # Package config, mcp dependency, waves console entry
├── README.md               # Install, tools, non-goals
├── src/waves/
│   ├── __init__.py
│   ├── vcd_parser.py       # Minimal VCD parser (scalar + vector)
│   ├── query.py            # Signal lookup, value, transitions
│   └── server.py           # FastMCP stdio server, 3 tools
├── tests/
│   ├── fixtures/simple.vcd # Test waveform fixture
│   └── test_smoke.py       # Minimal executable verification
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add VCD format support | `src/waves/vcd_parser.py` | Only scalar/vector now |
| Add query logic | `src/waves/query.py` | filter, limit, range, truncation |
| Add MCP tools | `src/waves/server.py` | 3 tool decorators |
| Fix install/runtime | `pyproject.toml` | entrypoint: `waves = waves.server:main` |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `parse_vcd` | function | `vcd_parser.py:24` | Entry parser, returns `ParsedVCD` |
| `list_signals` | function | `query.py:24` | Filtered signal listing |
| `get_value` | function | `query.py:57` | At-or-before value lookup |
| `get_transitions` | function | `query.py:84` | Inclusive range transitions |
| `wave_list_signals` | MCP tool | `server.py:17` | Delegates to `list_signals` |
| `wave_get_value` | MCP tool | `server.py:26` | Delegates to `get_value` |
| `wave_get_transitions` | MCP tool | `server.py:35` | Delegates to `get_transitions` |
| `main` | function | `server.py:55` | Calls `mcp.run()` (stdio) |

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

Tested with Icarus Verilog generated VCD files (`sample/sample.vcd`):

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
  --tool-arg vcd_path=sample/sample.vcd
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_get_value \
  --tool-arg vcd_path=sample/sample.vcd \
  --tool-arg signal=tb_pmic_fsm.clk \
  --tool-arg time=100000
```

## NOTES

- Fixture contract: `tests/fixtures/simple.vcd` must contain `top.clk`, `top.reset`, `top.dut.out` with exact transitions
- `WavesVCDError` / `WavesQueryError` are the only domain exceptions; server converts to MCP `ToolError`
- `.sisyphus/` contains planning artifacts and evidence (not shipped)
- `.gitignore` excludes `__pycache__/` and `.egg-info/`
- Tests use script-style assertions, not pytest
