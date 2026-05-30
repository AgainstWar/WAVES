# WAVES — VCD 波形查询 MCP 服务器

**WAVES**（Waveform Access via Explicit Signals）是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 的本地 stdio 工具，用于查询 VCD（Value Change Dump）波形文件中的信号值和时序变化。

> [English](./README.md)

---

## 安装

```bash
git clone https://github.com/AgainstWar/WAVES.git
cd WAVES
pip install .
```

---

## 快速使用

启动 MCP 服务器：

```bash
waves
```

通过 stdio 与 MCP 客户端通信。

WAVES 提供 6 个 MCP 工具，覆盖从浏览信号到查询值和跳变的完整工作流：

| 工具 | 功能 |
|------|------|
| `wave_get_info` | 返回时间尺度、时间范围和信号总数 |
| `wave_list_signals` | 列出信号名和位宽，支持按子字符串过滤 |
| `wave_get_value` | 查询信号在指定时间的值（at-or-before 查找） |
| `wave_get_transitions` | 查询信号在时间段内的所有跳变，支持按边沿或值过滤 |
| `wave_get_window` | 查询多个信号在同一窗口内的变化（结构化或表格输出） |
| `wave_find_transition` | 查找指定时间之前或之后的最近跳变，支持按边沿过滤 |

典型工作流：先用 `wave_list_signals` 发现精确信号名，再用 `wave_get_value`、`wave_get_transitions` 或 `wave_get_window` 查询。

### 示例

使用 `tests/fixtures/sample.vcd`（Icarus Verilog）：

**1. 查看文件信息**

输入：`wave_get_info`，参数 `{"vcd_path": "tests/fixtures/sample.vcd"}`

输出：
```json
{
  "vcd_path": "tests/fixtures/sample.vcd",
  "timescale": "1ps",
  "start_time": 0,
  "end_time": 1361000,
  "signal_count": 251
}
```

**2. 列出信号**

输入：`wave_list_signals`，参数 `{"vcd_path": "tests/fixtures/sample.vcd", "filter": "clk", "limit": 5}`

输出：
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

**3. 查询信号值**

输入：`wave_get_value`，参数 `{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "time": 100000}`

输出：
```json
{
  "signal": "tb_pmic_fsm.clk",
  "time": 100000,
  "value": "0"
}
```

> **at-or-before 语义**：若 `time=100000` 没有确切跳变记录，则返回该时间戳处或之前的最近值。

**4. 查询跳变**

输入：`wave_get_transitions`，参数 `{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "start_time": 0, "end_time": 200000, "limit": 10}`

输出：
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

**5. 按边沿过滤**

输入：`wave_get_transitions`，参数 `{"vcd_path": "tests/fixtures/sample.vcd", "signal": "tb_pmic_fsm.clk", "start_time": 0, "end_time": 200000, "edge": "posedge"}`

输出仅保留 0→1 的跳变：
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

**6. 查询多个信号在同一窗口内**

输入：`wave_get_window`，参数 `{"vcd_path": "tests/fixtures/sample.vcd", "signals": ["tb_pmic_fsm.clk", "tb_pmic_fsm.rst_n"], "start_time": 0, "end_time": 50000, "limit_per_signal": 10}`

输出：
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

> 空的 `transitions` 是正常数据，不是错误。

---

## 调试与开发

```
src/waves/
├── vcd_parser.py   # VCD 解析
├── query.py        # 查询逻辑
└── server.py       # MCP 服务器

tests/
├── fixtures/sample.vcd
└── test_smoke.py   # python tests/test_smoke.py
```

### Web UI 调试

```bash
npx @modelcontextprotocol/inspector waves
```

访问 `http://localhost:6274`。

---

## 许可证

MIT
