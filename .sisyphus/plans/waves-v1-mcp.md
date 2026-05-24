# WAVES v1 MCP Implementation Plan

## TL;DR
> **Summary**: Build WAVES v1 from scratch as a local Python stdio MCP server for querying VCD waveform facts. This repo creates the `waves` package/command; it depends on upstream MCP Python SDK package `mcp`.
> **Deliverables**: Python package scaffold; minimal VCD parser; query layer; three FastMCP tools; minimal executable smoke tests.
> **Effort**: Short
> **Parallel**: YES - 3 waves
> **Critical Path**: Task 1 → Task 2/3 → Task 4 → Task 5

## Context

### Original Request
Read `PLAN.md` and plan how to write the first version of the MCP.

### Interview Summary
- `PLAN.md` defines WAVES as **Waveform Access via Explicit Signals**.
- WAVES v1 is stateless: every call passes `vcd_path`; no server-side project/session state.
- v1 exposes `wave_list_signals`, `wave_get_value`, and `wave_get_transitions`.
- v1 uses Python, official MCP Python SDK, and local stdio transport.
- User selected minimal testing, not a full test suite or CI.
- Clarification: `waves` is our new package/command; `mcp` is only the upstream SDK dependency.

### Metis Review (gaps addressed)
- Time semantics: all `time`, `start_time`, and `end_time` values are raw VCD integer timestamps. `timescale` is parsed and returned only as metadata.
- Range semantics: `wave_get_transitions` includes both `start_time` and `end_time` boundaries.
- Value format: scalar values return `"0"`, `"1"`, `"x"`, or `"z"`; vector values return lowercase bit strings without `b` prefix, e.g. `"1010"`, `"10xz"`.
- Missing value behavior: if a signal exists but has no value at or before a requested time, return `null` for `value` rather than inventing a value.
- Signal matching: exact hierarchical signal name only; no fuzzy, glob, suffix, or regex matching for v1.
- Parser scope: fixture-driven scalar/vector VCD support only; no full VCD compliance goal.

## Work Objectives

### Core Objective
Create a working `waves` Python package that exposes a local stdio MCP server for querying VCD waveform facts.

### Deliverables
- `pyproject.toml` with package metadata, `mcp` dependency, and console script `waves = "waves.server:main"`.
- `README.md` documenting install, stdio use, tools, and v1 non-goals.
- `src/waves/__init__.py`.
- `src/waves/vcd_parser.py` for minimal VCD parsing.
- `src/waves/query.py` for signal lookup, point value lookup, and transition range extraction.
- `src/waves/server.py` for FastMCP tool registration.
- `tests/fixtures/simple.vcd` and minimal smoke tests.

### Definition of Done
- `python -m pip install -e .` succeeds from repo root.
- `python -c "import waves.server; import waves.vcd_parser; import waves.query"` exits 0.
- Minimal smoke test verifies the three v1 tool contracts against `tests/fixtures/simple.vcd`.
- No HTTP server, port binding, simulation runner, diagnosis logic, or persistent session state is added.

### Must Have
- Local stdio MCP server using `FastMCP`.
- Exact schemas from `PLAN.md` for all three tools.
- Stable `ToolError` failures for missing file, invalid VCD, unknown signal, invalid time range, and invalid limits.
- Limit/truncation behavior for list and transition tools.

### Must NOT Have
- No cloning, vendoring, or modifying the upstream MCP SDK.
- No HTTP/network transport.
- No automatic VCD discovery.
- No waveform generation or simulation execution.
- No RTL/Chisel/FIRRTL/source mapping.
- No natural-language waveform summary or debug conclusion.
- No non-VCD formats.
- No CI unless separately requested.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: minimal tests only, per user selection.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy

### Parallel Execution Waves
Wave 1: Task 1 foundation scaffold.
Wave 2: Task 2 after scaffold exists.
Wave 3: Task 3 after parser exists, then Task 4 and Task 5.

### Dependency Matrix
- Task 1 blocks Tasks 2, 3, 4, 5.
- Task 2 blocks Task 3 correctness and Task 4 tool behavior.
- Task 3 blocks Task 4 and Task 5 smoke assertions.
- Task 4 blocks MCP smoke portion of Task 5.
- Task 5 is final implementation verification.

### Agent Dispatch Summary
- Wave 1 → 1 task → quick
- Wave 2 → 1 task → unspecified-low
- Wave 3 → 3 tasks → quick / unspecified-low

### Fixture Contract
`tests/fixtures/simple.vcd` must contain these exact logical signals and transitions:
- `top.clk`, width `1`: `0@0`, `1@5`, `0@10`, `1@15`, `0@20`.
- `top.reset`, width `1`: `1@0`, `0@12`.
- `top.dut.out`, width `8`: `00000000@0`, `00000101@120`, `00000111@140`.

Expected query examples:
- `wave_get_value(signal="top.dut.out", time=120)` returns `{"signal":"top.dut.out","time":120,"value":"00000101"}`.
- `wave_get_value(signal="top.dut.out", time=130)` returns value `"00000101"` because lookup is at-or-before requested time.
- `wave_get_transitions(signal="top.dut.out", start_time=100, end_time=160, limit=50)` returns exactly `[120:"00000101", 140:"00000111"]` in ascending time order.

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. Scaffold the Python package

  **What to do**: Create `pyproject.toml`, `README.md`, `src/waves/__init__.py`, and empty module files for `server.py`, `vcd_parser.py`, and `query.py`. Configure package name `waves`, Python `>=3.10`, dependency `mcp`, and console script `waves = "waves.server:main"`. README must document that WAVES is local stdio only and that `mcp` is an upstream SDK dependency, not the project being implemented.
  **Must NOT do**: Do not clone, vendor, or modify MCP SDK. Do not add HTTP transport, CI, broad test framework, simulation tooling, or non-VCD support.

  **Recommended Agent Profile**:
  - Category: `quick` - Small scaffold and documentation task.
  - Skills: [] - No special skills required.
  - Omitted: [`frontend-ui-ux`, `playwright`] - No browser/UI work.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [2, 3, 4, 5] | Blocked By: []

  **References**:
  - Spec: `PLAN.md:133-167` - Python MCP SDK, recommended structure, local stdio command.
  - Spec: `PLAN.md:169-183` - Docker install expectations.
  - SDK: `https://github.com/modelcontextprotocol/python-sdk` - upstream dependency only.

  **Acceptance Criteria**:
  - [ ] `python -m pip install -e .` exits 0.
  - [ ] `python -c "import waves; import waves.server; import waves.vcd_parser; import waves.query"` exits 0.
  - [ ] `python -c "import tomllib; p=tomllib.load(open('pyproject.toml','rb')); assert p['project']['name']=='waves'; assert p['project']['scripts']['waves']=='waves.server:main'"` exits 0.

  **QA Scenarios**:
  ```
  Scenario: Editable install succeeds
    Tool: Bash
    Steps: Run `python -m pip install -e .` from `/home/username/waves`.
    Expected: Command exits 0 and package `waves` is importable.
    Evidence: .sisyphus/evidence/task-1-scaffold-install.txt

  Scenario: SDK is not vendored
    Tool: Bash
    Steps: Run `python - <<'PY'\nfrom pathlib import Path\nassert not Path('src/mcp').exists()\nassert not Path('mcp').exists()\nPY`.
    Expected: Command exits 0.
    Evidence: .sisyphus/evidence/task-1-no-vendored-sdk.txt
  ```

  **Commit**: NO | Message: `feat(waves): scaffold python package` | Files: [`pyproject.toml`, `README.md`, `src/waves/*`]

- [x] 2. Implement minimal VCD parser

  **What to do**: Implement `src/waves/vcd_parser.py` with a minimal parser that reads a VCD file, parses `$timescale`, `$scope`, `$upscope`, `$var`, `$enddefinitions`, `$dumpvars`, timestamp markers like `#120`, scalar value changes like `1!`, `x!`, `z!`, and vector value changes like `b1010 "`. Build an in-memory representation containing `timescale`, signal definitions with exact hierarchical names and widths, and ordered transition lists per signal. Preserve `x`/`z` bits. Raise a domain error that server code can convert to `ToolError` for missing files, malformed definitions, unsupported value changes, or invalid timestamps.
  **Must NOT do**: Do not implement full VCD compliance, streaming parser, caching, FST/VPD/FSDB, real/string/event types, or source mapping.

  **Recommended Agent Profile**:
  - Category: `unspecified-low` - Small parser with edge cases.
  - Skills: [] - No special skills required.
  - Omitted: [`playwright`] - No browser work.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [3, 4, 5] | Blocked By: [1]

  **References**:
  - Spec: `PLAN.md:30-116` - Required signal/value/transition behavior.
  - Spec: `PLAN.md:118-132` - Explicit parser non-goals.

  **Acceptance Criteria**:
  - [ ] Parser returns `timescale == "1ns"` for `tests/fixtures/simple.vcd`.
  - [ ] Parser exposes exact signal names `top.clk`, `top.reset`, and `top.dut.out` with widths `1`, `1`, and `8`.
  - [ ] Parser records ordered transitions including boundary timestamps used by smoke tests.
  - [ ] Missing file and malformed VCD paths produce stable exceptions, not tracebacks from unrelated internals.

  **QA Scenarios**:
  ```
  Scenario: Parse fixture metadata and signals
    Tool: Bash
    Steps: Run a Python one-liner importing `waves.vcd_parser.parse_vcd('tests/fixtures/simple.vcd')` and asserting timescale plus the three exact signal names and widths.
    Expected: Command exits 0.
    Evidence: .sisyphus/evidence/task-2-parser-fixture.txt

  Scenario: Missing VCD path fails cleanly
    Tool: Bash
    Steps: Run a Python one-liner calling the parser on `/tmp/does-not-exist.vcd` and asserting the expected domain exception class/message.
    Expected: Command exits 0 after catching the expected exception.
    Evidence: .sisyphus/evidence/task-2-parser-missing-file.txt
  ```

  **Commit**: NO | Message: `feat(waves): add minimal vcd parser` | Files: [`src/waves/vcd_parser.py`, `tests/fixtures/simple.vcd`]

- [x] 3. Implement query functions and exact contracts

  **What to do**: Implement `src/waves/query.py` functions for `list_signals`, `get_value`, and `get_transitions`. `list_signals` returns `vcd_path`, `timescale`, `signal_count`, `signals`, and `truncated`; filter is optional substring matching only for listing. `get_value` requires exact signal name and returns value at the greatest transition time `<= time`, or `null` if none exists. `get_transitions` returns transitions with `start_time <= transition.time <= end_time`, sorted ascending, with truncation when more than `limit` results exist. Validate `limit > 0` and `start_time <= end_time`.
  **Must NOT do**: Do not add fuzzy matching, suffix matching, regex, natural language summaries, numeric conversion to hex unless explicitly required later, or batch multi-signal APIs.

  **Recommended Agent Profile**:
  - Category: `quick` - Focused pure-Python query logic.
  - Skills: [] - No special skills required.
  - Omitted: [`playwright`] - No browser work.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [4, 5] | Blocked By: [1, 2]

  **References**:
  - Spec: `PLAN.md:32-116` - Tool input/output schemas.
  - Metis decision: raw timestamp semantics and inclusive range behavior.

  **Acceptance Criteria**:
  - [ ] `list_signals(..., filter='dut', limit=100)` includes only matching signal names and correct `signal_count` for all signals.
  - [ ] `list_signals(..., limit=1)` returns one signal and `truncated: true` when more exist.
  - [ ] `get_value(..., signal='top.dut.out', time=120)` returns `value == "00000101"`.
  - [ ] `get_value(..., signal='top.dut.out', time=130)` returns `value == "00000101"`.
  - [ ] `get_transitions(..., start_time=100, end_time=160, limit=50)` returns exactly `[{"time":120,"value":"00000101"},{"time":140,"value":"00000111"}]`.
  - [ ] Unknown signal, invalid limit, and invalid range produce stable domain exceptions.

  **QA Scenarios**:
  ```
  Scenario: Query happy path
    Tool: Bash
    Steps: Run Python assertions for list, value, and transition queries against `tests/fixtures/simple.vcd` using exact signals `top.clk`, `top.reset`, `top.dut.out`.
    Expected: Command exits 0 and all returned dict fields match expected values.
    Evidence: .sisyphus/evidence/task-3-query-happy.txt

  Scenario: Query validation errors
    Tool: Bash
    Steps: Run Python assertions that unknown signal, `limit=0`, and `start_time > end_time` raise expected domain exceptions.
    Expected: Command exits 0 after catching expected exceptions.
    Evidence: .sisyphus/evidence/task-3-query-errors.txt
  ```

  **Commit**: NO | Message: `feat(waves): add vcd query contracts` | Files: [`src/waves/query.py`]

- [x] 4. Expose the three FastMCP tools over stdio

  **What to do**: Implement `src/waves/server.py` using `from mcp.server.fastmcp import FastMCP`. Create `mcp = FastMCP("WAVES")`. Register exactly three tools with `@mcp.tool()`: `wave_list_signals`, `wave_get_value`, and `wave_get_transitions`. Each tool should delegate to `waves.query`, return plain structured Python dicts matching `PLAN.md`, and convert expected domain exceptions to `ToolError`. Implement `main()` that calls `mcp.run()`; rely on default stdio transport.
  **Must NOT do**: Do not add HTTP/streamable-http/SSE transport, port binding, daemon mode, global cache, auto file discovery, or extra tools.

  **Recommended Agent Profile**:
  - Category: `quick` - Straightforward SDK wiring.
  - Skills: [] - No special skills required.
  - Omitted: [`playwright`, `frontend-ui-ux`] - No UI/browser work.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [5] | Blocked By: [1, 2, 3]

  **References**:
  - Spec: `PLAN.md:30-116` - Exact v1 tool set and schemas.
  - Spec: `PLAN.md:133-167` - Official Python MCP SDK, stdio mode, command name.
  - SDK: `https://github.com/modelcontextprotocol/python-sdk/blob/e8e64842781c66b613872cf394de6e7d6f6925bf/README.md#L221-L279` - FastMCP server pattern.
  - SDK: `https://github.com/modelcontextprotocol/python-sdk/blob/e8e64842781c66b613872cf394de6e7d6f6925bf/src/mcp/server/mcpserver/server.py#L249-L301` - `run()` transport behavior.

  **Acceptance Criteria**:
  - [ ] `python -c "from waves.server import mcp, main; assert callable(main)"` exits 0.
  - [ ] `waves.server` defines exactly the three public MCP tools required by `PLAN.md`; no extra WAVES tools are added.
  - [ ] `main()` calls `mcp.run()` without specifying HTTP/network transport.
  - [ ] Expected query/parser failures are converted to MCP `ToolError` with stable messages.

  **QA Scenarios**:
  ```
  Scenario: Server imports and exposes main
    Tool: Bash
    Steps: Run `python -c "from waves.server import mcp, main; assert callable(main)"` after editable install.
    Expected: Command exits 0.
    Evidence: .sisyphus/evidence/task-4-server-import.txt

  Scenario: No network transport configured
    Tool: Bash
    Steps: Inspect `src/waves/server.py` with a Python script and assert it does not contain `streamable-http`, `sse`, `host=`, `port=`, or `uvicorn`.
    Expected: Command exits 0.
    Evidence: .sisyphus/evidence/task-4-no-network.txt
  ```

  **Commit**: NO | Message: `feat(waves): expose stdio mcp tools` | Files: [`src/waves/server.py`]

- [x] 5. Add minimal smoke verification

  **What to do**: Add the smallest executable verification requested by the user. Prefer a single `tests/test_smoke.py` using pytest and the SDK in-memory client if the installed `mcp` version supports it cleanly. If the SDK client API is awkward, use a minimal Python smoke script under `tests/test_smoke.py` that imports parser/query/server and asserts the three tool contract outputs through query functions plus server import. Fixture path must be `tests/fixtures/simple.vcd`. Do not add CI.
  **Must NOT do**: Do not expand into a broad unit-test suite, property tests, benchmarks, CI, or manual-only test instructions.

  **Recommended Agent Profile**:
  - Category: `unspecified-low` - Small verification with SDK API check.
  - Skills: [] - No special skills required.
  - Omitted: [`playwright`] - No browser work.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [] | Blocked By: [1, 2, 3, 4]

  **References**:
  - User decision: chose minimal testing.
  - Spec: `PLAN.md:143-159` - Proposed fixture/test layout.
  - SDK testing docs: `https://github.com/modelcontextprotocol/python-sdk/blob/e8e64842781c66b613872cf394de6e7d6f6925bf/docs/testing.md#L1-L77` - In-memory client testing option.

  **Acceptance Criteria**:
  - [ ] `python -m pip install -e .` exits 0.
  - [ ] `python -m pytest tests/test_smoke.py` exits 0 if pytest is used.
  - [ ] If pytest is not used, `python tests/test_smoke.py` exits 0 and README documents that smoke command.
  - [ ] Smoke verifies: signal listing includes `top.clk`, `top.reset`, `top.dut.out`; point lookup returns exact expected value; transition query returns exact ordered expected records; server import/main works.
  - [ ] Smoke verifies at least one failure path: unknown signal or invalid time range.

  **QA Scenarios**:
  ```
  Scenario: Minimal smoke test passes
    Tool: Bash
    Steps: Run the chosen smoke command from repo root: either `python -m pytest tests/test_smoke.py` or `python tests/test_smoke.py`.
    Expected: Command exits 0 and verifies all three v1 contracts against `tests/fixtures/simple.vcd`.
    Evidence: .sisyphus/evidence/task-5-smoke-pass.txt

  Scenario: Failure path is covered
    Tool: Bash
    Steps: Run the smoke command and confirm it contains/asserts an unknown-signal or invalid-range error case.
    Expected: Command exits 0 only if the expected error is raised and handled.
    Evidence: .sisyphus/evidence/task-5-smoke-error.txt
  ```

  **Commit**: NO | Message: `test(waves): add minimal smoke coverage` | Files: [`tests/fixtures/simple.vcd`, `tests/test_smoke.py`, `README.md`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [x] F1. Plan Compliance Audit — oracle
- [x] F2. Code Quality Review — unspecified-high
- [x] F3. Real Manual QA — unspecified-high
- [x] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit after all implementation and verification pass.
- Suggested message: `feat(waves): add v1 stdio mcp vcd query server`

## Success Criteria
- The repo installs as a Python package named `waves`.
- Running the `waves` console script starts a local stdio MCP server.
- The three planned tools return structured waveform facts from a fixture VCD.
- Minimal smoke tests pass without user intervention.
