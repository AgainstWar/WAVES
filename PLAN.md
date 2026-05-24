# WAVES 规划

WAVES 是 **Waveform Access via Explicit Signals** 的缩写，含义是“通过显式信号访问波形”。

WAVES 是一个本地 stdio 形式的 MCP 风格工具，用于在 RTL 修复实验中查询 VCD 波形。它会安装在实验 Docker 镜像中，由智能体在生成 VCD 文件后调用。

## 范围

WAVES v1 是一个无状态的 VCD 查询工具。每次工具调用都由智能体显式传入 `vcd_path` 和查询参数。工具读取该 VCD 文件，并返回结构化波形数据。

WAVES 不负责生成波形、运行仿真、诊断 bug、追踪 RTL driver、解析 Chisel 或提出补丁建议。这些职责分别由智能体、skills、测试 runner 和未来扩展承担。

## 在研究系统中的角色

预期工作流如下：

1. 智能体先运行正常的失败测试。
2. 波形使用 skill 在需要波形证据时，指导智能体重新运行带 VCD dump 的仿真。
3. 智能体记录生成的 VCD 路径。
4. 智能体用显式 VCD 路径、信号名和时间范围调用 WAVES。
5. WAVES 返回结构化信号值或信号变化记录。
6. 智能体解释波形事实，并决定是否以及如何生成补丁。

职责划分如下：

- Skill：决定什么时候需要波形证据，以及应该如何请求波形证据。
- 智能体：运行仿真、选择信号、解释结果、修改代码。
- WAVES：读取 VCD 文件，并返回被请求的波形数据。

## v1 工具集

### `wave_list_signals`

列出 VCD 文件中可查询的信号。

输入：

```json
{
  "vcd_path": "/path/to/wave.vcd",
  "filter": "optional substring",
  "limit": 100
}
```

输出：

```json
{
  "vcd_path": "/path/to/wave.vcd",
  "timescale": "1ns",
  "signal_count": 42,
  "signals": [
    {"name": "top.clk", "width": 1},
    {"name": "top.reset", "width": 1},
    {"name": "top.dut.out", "width": 8}
  ],
  "truncated": false
}
```

### `wave_get_value`

返回某个信号在指定时间点的值。

输入：

```json
{
  "vcd_path": "/path/to/wave.vcd",
  "signal": "top.dut.out",
  "time": 120
}
```

输出：

```json
{
  "signal": "top.dut.out",
  "time": 120,
  "value": "0x05"
}
```

### `wave_get_transitions`

返回某个信号在指定时间范围内的变化记录。

输入：

```json
{
  "vcd_path": "/path/to/wave.vcd",
  "signal": "top.dut.out",
  "start_time": 100,
  "end_time": 160,
  "limit": 50
}
```

输出：

```json
{
  "signal": "top.dut.out",
  "start_time": 100,
  "end_time": 160,
  "transitions": [
    {"time": 100, "value": "0x00"},
    {"time": 120, "value": "0x05"},
    {"time": 140, "value": "0x07"}
  ],
  "truncated": false
}
```

## v1 非目标

WAVES v1 不实现以下功能：

- 在工作区中自动发现 VCD 文件。
- 生成 VCD 或执行仿真。
- 支持 FST、VPD、FSDB 或其他波形格式。
- 生成自然语言波形摘要。
- 诊断 mismatch。
- 追踪 RTL driver。
- 分析 Verilog/SystemVerilog AST。
- 建立 Chisel 或 FIRRTL 源码映射。
- 生成补丁或修复建议。
- 维护持久 session 或 server 端项目状态。

## 实现形态

WAVES 使用官方 Python MCP SDK 实现：

```text
https://github.com/modelcontextprotocol/python-sdk
```

实现方式采用该 SDK 提供的本地 stdio 通信模式，不实现 HTTP 服务，也不开放网络端口。

推荐包结构：

```text
waves/
  pyproject.toml
  README.md
  src/waves/
    __init__.py
    server.py
    vcd_parser.py
    query.py
  tests/
    fixtures/
      simple.vcd
    test_vcd_parser.py
    test_query.py
```

命令行入口应为本地 stdio 形式：

```text
waves
```

该工具应能在 Docker 内运行，不需要网络服务，也不开放端口。

## Docker 使用方式

在实验镜像中安装：

```bash
pip install .
```

或：

```bash
uv pip install .
```

智能体配置中应调用本地命令，而不是 HTTP endpoint。

## 设计原则

WAVES 返回波形事实，而不是调试结论。

好的输出：

```json
{"time": 120, "value": "0x05"}
```

不好的输出：

```text
The FSM is probably broken because the output is wrong.
```

解释、归因和补丁决策由智能体和 skills 负责。

## 后续扩展

可能的 v2 功能：

- 如果基础文件元数据变得有用，可以增加 `wave_get_metadata`。
- 支持指定时间窗口内的多信号批量查询。
- 支持源代码级信号映射。
- 支持 RTL driver 或源码位置查询。
- 如果未来数据集需要，再支持 FST。
