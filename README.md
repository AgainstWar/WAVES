# WAVES — VCD 波形查询 MCP 服务器

**WAVES**（Waveform Access via Explicit Signals）是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 的本地 stdio 工具，用于查询 VCD（Value Change Dump）波形文件中的信号值和时序变化。

> 🔧 **当前版本**：v0.1.1 — 支持信号列表、点值查询、变化记录查询、波形窗口切片和变化导航

---

## 功能概述

WAVES 将 VCD 波形文件封装为 MCP 工具集，让 LLM 客户端（如 Claude、Cursor、OpenCode）能够通过标准协议直接读取仿真波形数据，无需手动解析文件或编写脚本。

### 提供的 MCP 工具

| 工具名 | 功能 | 输入参数 | 返回 |
|--------|------|----------|------|
| `wave_get_info` | 获取 VCD 文件级基础信息 | `vcd_path` | timescale、时间范围、信号总数 |
| `wave_list_signals` | 列出 VCD 中所有信号 | `vcd_path`, `filter?`, `limit?` | 信号名列表、位宽、是否截断 |
| `wave_get_value` | 查询信号在指定时间的值 | `vcd_path`, `signal`, `time` | 信号值（at-or-before 语义） |
| `wave_get_transitions` | 查询信号在时间段内的变化 | `vcd_path`, `signal`, `start_time`, `end_time`, `limit?`, `edge?`, `value?` | 变化记录列表（支持按边沿和值过滤） |
| `wave_get_window` | 查询多个信号在同一窗口内的变化 | `vcd_path`, `signals`, `start_time?`/`end_time?` 或 `center_time?`/`before?`/`after?`, `limit_per_signal?` | 每个信号的变化记录列表（支持两种窗口指定方式） |
| `wave_find_transition` | 查找指定时间之前或之后的最近变化 | `vcd_path`, `signal`, `time`, `direction`, `edge?` | 找到时返回 `found=true` + 变化详情，未找到时返回 `found=false` |

### 核心特性

- **纯本地 stdio**：无 HTTP 服务、无网络端口、无持久状态
- **零配置**：安装后直接运行 `waves` 命令即可接入 MCP 客户端
- **Icarus Verilog 兼容**：完整支持 Icarus 生成的 VCD 文件（含 `$dumpall`、多字符标识符、跨 scope 共享信号等）
- **轻量依赖**：仅依赖官方 `mcp` Python SDK

---

## 安装

### 方式一：直接安装（推荐）

```bash
git clone https://github.com/AgainstWar/WAVES.git
cd WAVES
pip install .
```

### 方式二：开发模式（可编辑安装）

```bash
git clone https://github.com/AgainstWar/WAVES.git
cd WAVES
python -m pip install -e ".[dev]"
```

> 开发模式会安装 `pytest` 等可选依赖，方便本地测试。

### 验证安装

```bash
python tests/test_smoke.py  # 运行冒烟测试（预期输出：SMOKE_OK）
```

---

## 快速使用

### 1. 独立运行 MCP 服务器

```bash
waves
```

服务器通过标准输入输出（stdio）与 MCP 客户端通信。

### 2. 接入 MCP 客户端

#### OpenCode

在 `~/.config/opencode/opencode.json` 中添加：

```json
{
  "mcp": {
    "waves": {
      "type": "local",
      "command": ["/usr/local/bin/waves"],
      "enabled": true
    }
  }
}
```

> 请将路径替换为你本地的 `waves` 安装路径（可通过 `which waves` 查询）。

#### Claude Desktop

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）或对应配置：

```json
{
  "mcpServers": {
    "waves": {
      "command": "/usr/local/bin/waves",
      "args": []
    }
  }
}
```

#### Cursor

编辑 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "waves": {
      "command": "/usr/local/bin/waves"
    }
  }
}
```

---

## 使用示例

假设你有一个 Icarus Verilog 生成的 VCD 文件 `fsm_norm.vcd`，以下是各工具的调用示例。

### 获取文件信息

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd"
}
```

返回：

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "timescale": "1ps",
  "start_time": 0,
  "end_time": 1361000,
  "signal_count": 251
}
```

> `start_time` 和 `end_time` 是原始 VCD 整数时间戳，不做单位换算。如果没有显式时间戳行，`end_time` 为 `null`。

### 列出所有信号

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "limit": 50
}
```

返回：

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "timescale": "1ps",
  "signal_count": 251,
  "signals": [
    {"name": "tb_pmic_fsm.clk", "width": 1},
    {"name": "tb_pmic_fsm.rst_n", "width": 1},
    {"name": "tb_pmic_fsm.current_state [3:0]", "width": 4}
  ],
  "truncated": true
}
```

### 查询信号在指定时间的值

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signal": "tb_pmic_fsm.clk",
  "time": 100000
}
```

返回：

```json
{
  "signal": "tb_pmic_fsm.clk",
  "time": 100000,
  "value": "0"
}
```

> **at-or-before 语义**：如果 `time=100000` 恰好没有变化记录，则返回最近一次变化（`time <= 100000`）的值。

### 查询信号在时间段内的变化

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "limit": 20
}
```

返回：

```json
{
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "transitions": [
    {"time": 0, "value": "0"},
    {"time": 10000, "value": "1"},
    {"time": 20000, "value": "0"},
    ...
  ],
  "truncated": false
}
```

### 查询信号在时间段内的变化（按边沿和值过滤）

支持通过 `edge` 和 `value` 参数过滤变化记录。

**只查上升沿（posedge）：**

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "edge": "posedge"
}
```

返回（只保留 0→1 的上升沿）：

```json
{
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "transitions": [
    {"time": 10000, "value": "1"},
    {"time": 30000, "value": "1"}
  ],
  "truncated": false
}
```

**只查结果值为 "1" 的变化：**

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "value": "1"
}
```

返回（只保留变化后值为 "1" 的记录）：

```json
{
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "transitions": [
    {"time": 10000, "value": "1"},
    {"time": 30000, "value": "1"}
  ],
  "truncated": false
}
```

**同时按边沿和值过滤：**

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signal": "tb_pmic_fsm.clk",
  "start_time": 0,
  "end_time": 200000,
  "edge": "negedge",
  "value": "0"
}
```

> `edge=posedge/negedge` 仅适用于单 bit 0/1 变化。`value` 过滤的是 transition 后的结果值。过滤后无结果时返回 `"transitions": []`，不是错误。

### 查询多个信号在同一窗口内的变化

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signals": [
    "tb_pmic_fsm.clk",
    "tb_pmic_fsm.rst_n",
    "tb_pmic_fsm.current_state"
  ],
  "start_time": 100000,
  "end_time": 160000,
  "limit_per_signal": 50
}
```

返回：

```json
{
  "start_time": 100000,
  "end_time": 160000,
  "signals": [
    {
      "signal": "tb_pmic_fsm.clk",
      "transitions": [
        {"time": 100000, "value": "0"},
        {"time": 110000, "value": "1"}
      ],
      "truncated": false
    },
    {
      "signal": "tb_pmic_fsm.rst_n",
      "transitions": [],
      "truncated": false
    },
    {
      "signal": "tb_pmic_fsm.current_state",
      "transitions": [
        {"time": 120000, "value": "0010"}
      ],
      "truncated": false
    }
  ]
}
```

> `wave_get_window` 只返回结构化波形事实，不解释波形含义、不判断 bug、不生成自然语言摘要。每个 signal 独立标记 `truncated`；空 `transitions` 是正常结果，不是错误。

**另一种窗口指定方式：使用中心时间点：**

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signals": [
    "tb_pmic_fsm.clk",
    "tb_pmic_fsm.rst_n",
    "tb_pmic_fsm.current_state"
  ],
  "center_time": 130000,
  "before": 30000,
  "after": 30000,
  "limit_per_signal": 50
}
```

等同于 `start_time=100000`、`end_time=160000`。中心窗口模式只是一个便利语法糖，内部会转换成 `start_time` 和 `end_time`，返回结果结构不变。

> `center_time`、`before`、`after` 与 `start_time`/`end_time` 互斥，不能混用。`before` 和 `after` 必须 `>= 0`，计算出的 `start_time` 不能小于 `0`。

### 查找信号变化

```json
{
  "vcd_path": "/path/to/fsm_norm.vcd",
  "signal": "tb_pmic_fsm.clk",
  "time": 50000,
  "direction": "next",
  "edge": "posedge"
}
```

返回：

```json
{
  "found": true,
  "signal": "tb_pmic_fsm.clk",
  "query_time": 50000,
  "transition_time": 60000,
  "from": "0",
  "to": "1",
  "edge": "posedge"
}
```

> **严格语义**：`next` 查找 `time` **之后**（`t > time`）的第一个匹配变化；`prev` 查找 `time` **之前**（`t < time`）的最后一个匹配变化。`edge` 可指定 `any`（任意变化）、`posedge`（单 bit 0→1）或 `negedge`（单 bit 1→0）。对 vector 和多 bit 信号，`posedge`/`negedge` 不会匹配。未找到时返回 `found=false`，`transition_time`、`from`、`to` 均为 `null`，**不是错误**。

---

## Error Model

WAVES returns errors in three stable categories. All messages are in English and describe only what input is unavailable — no RTL debugging advice, no waveform interpretation, and no repair suggestions.

| Category | When | Format | Example |
|----------|------|--------|---------|
| **VCD file error** | `vcd_path` does not exist, is not a file, is unreadable, or is not a valid VCD | `VCD file error: <path>. Reason: <reason>.` | `VCD file error: /tmp/wave.vcd. Reason: file not found.` |
| **Signal error** | `signal` does not match any full hierarchical name in the VCD | `Signal error: signal not found: <signal>.` | `Signal error: signal not found: tb.dut.clk.` |
| **Parameter error** | `limit <= 0`, `time < 0`, `start_time < 0`, `end_time < 0`, `start_time > end_time`, `direction` not in `['next', 'prev']`, `edge` not in `['any', 'posedge', 'negedge']` | `Parameter error: <reason>.` | `Parameter error: limit must be greater than 0, got 0.` |

`wave_get_transitions` can produce all three error categories:
- **VCD file error** for invalid `vcd_path`
- **Signal error** for unknown `signal`
- **Parameter error** for invalid `limit`/`start_time`/`end_time`, `edge`, or `value` (must be a string)

`wave_find_transition` can produce all three error categories:
- **VCD file error** for invalid `vcd_path`
- **Signal error** for unknown `signal`
- **Parameter error** for invalid `time`/`direction`/`edge`

`wave_get_info` only produces **VCD file error**; it does not accept signal names or time parameters.

`wave_get_window` can produce all three error categories:
- **VCD file error** for invalid `vcd_path`
- **Signal error** for any unknown signal in `signals`
- **Parameter error** for invalid `start_time`/`end_time`/`limit_per_signal`, missing or mixed window modes, invalid `center_time`/`before`/`after`, or negative computed `start_time` in centered mode

Empty results are **not** errors:
- `wave_get_transitions` returns `"transitions": []` when no value changes exist in the requested range.
- `wave_get_value` returns `"value": null` when the signal has no recorded value at or before the requested time.
- `wave_get_info` returns `"end_time": null` when the VCD contains no explicit timestamp lines (only a `$dumpvars` snapshot at time 0).
- `wave_find_transition` returns `"found": false` when no matching transition exists in the requested direction.

---

## 调试与开发

### 冒烟测试

```bash
python tests/test_smoke.py
# 预期输出：SMOKE_OK
```

### 使用 MCP Inspector 调试

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) 是官方提供的可视化调试工具，支持交互式查看工具列表、测试调用和查看请求历史。

**安装要求**：Node.js ^22.7.5

**UI 模式**（自动打开浏览器）：

```bash
npx @modelcontextprotocol/inspector waves
```

访问 `http://localhost:6274` 即可交互式调试。

**CLI 模式**（命令行）：

```bash
# 列出工具
npx @modelcontextprotocol/inspector --cli waves --method tools/list

# 调用 wave_list_signals
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_list_signals \
  --tool-arg "vcd_path=tests/fixtures/sample.vcd"

# 调用 wave_get_value
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_get_value \
  --tool-arg "vcd_path=tests/fixtures/sample.vcd" \
  --tool-arg signal=tb_pmic_fsm.clk \
  --tool-arg time=100000

# 调用 wave_get_transitions
npx @modelcontextprotocol/inspector --cli waves --method tools/call \
  --tool-name wave_get_transitions \
  --tool-arg "vcd_path=tests/fixtures/sample.vcd" \
  --tool-arg signal=tb_pmic_fsm.clk \
  --tool-arg start_time=0 \
  --tool-arg end_time=200000
```

---

## Icarus Verilog 兼容性

WAVES 已针对 Icarus Verilog 生成的 VCD 文件进行兼容性测试：

| 特性 | 支持状态 | 说明 |
|------|----------|------|
| `$dumpall` | ✅ 支持 | Icarus 在 `$dumpvars` 前输出参数初始值 |
| `$dumpoff` / `$dumpon` | ✅ 忽略 | 查询工具无需追踪 dump 状态 |
| 多 scope 共享标识符 | ✅ 支持 | 同一标识符在不同模块复用（如 `clk`） |
| 多字符标识符 | ✅ 支持 | 信号数 >94 时自动生成（如 `]"`、`A"`） |
| 短 vector 值 | ✅ 支持 | 值长度可小于信号位宽（VCD 隐式扩展） |
| `$parameter` 类型 | ✅ 支持 | 按 `wire`/`reg` 处理，可正常列出和查询 |

> 示例文件：`tests/fixtures/sample.vcd`（251 信号，时间范围 0 ~ 1,361,000 ps）

---

## v1 非目标

WAVES v1 **不**提供以下功能：

- ❌ 运行仿真或生成 VCD 文件
- ❌ 支持非 VCD 格式（FST、VPD、FSDB 等）
- ❌ HTTP / SSE / 其他网络传输
- ❌ 自动诊断 bug 或生成修复建议
- ❌ RTL / Chisel / FIRRTL 源码映射
- ❌ 自然语言波形摘要
- ❌ 服务端持久状态或会话缓存

---

## 技术栈

- **语言**：Python 3.10+
- **MCP SDK**：官方 `mcp` Python 包
- **传输**：stdio（标准输入输出）
- **布局**：src-layout（`src/waves/`）

---

## 许可证

MIT
