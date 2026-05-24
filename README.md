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

## v1 non-goals

WAVES v1 does not:

- run simulations
- generate VCD files
- support HTTP
- support non-VCD waveform formats
- infer bugs or generate fixes
- maintain server-side project state
