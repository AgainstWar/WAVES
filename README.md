# WAVES

WAVES is a local, stdio-only MCP tool for querying VCD waveforms.

## Install

```bash
pip install .
```

Development editable install:

```bash
python -m pip install -e .
```

## Runtime model

- Local stdio only
- No HTTP transport
- No network ports
- Uses the upstream official `mcp` Python SDK as a dependency

## CLI

After install, run:

```bash
waves
```

## v1 tools

WAVES v1 exposes three tools:

- `wave_list_signals`
- `wave_get_value`
- `wave_get_transitions`

These tools are intentionally narrow and only cover VCD queries.

## Development

### Testing

Run the minimal smoke test:

```bash
python tests/test_smoke.py
```

Install with dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

### Debugging with MCP Inspector

Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to interactively test and debug WAVES:

```bash
# Install Inspector (requires Node.js ^22.7.5)
npm install -g @modelcontextprotocol/inspector

# Launch Inspector with WAVES
npx @modelcontextprotocol/inspector waves
```

The Inspector UI will open at `http://localhost:6274`. You can:
- Browse available tools (`wave_list_signals`, `wave_get_value`, `wave_get_transitions`)
- Test tool calls with the fixture VCD at `tests/fixtures/simple.vcd`
- View request/response history and errors

CLI mode (no UI):

```bash
# List tools
npx @modelcontextprotocol/inspector --cli waves --method tools/list

# Call wave_list_signals
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_list_signals \
  --tool-arg vcd_path=tests/fixtures/simple.vcd
```

## v1 non-goals

WAVES v1 does not:

- run simulations
- generate VCD files
- support HTTP
- support non-VCD waveform formats
- infer bugs or generate fixes
- maintain server-side project state
