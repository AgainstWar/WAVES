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

| 工具 | 功能 |
|------|------|
| `wave_get_info` | 获取 VCD 文件基本信息（timescale、时间范围、信号数） |
| `wave_list_signals` | 列出所有信号，支持按名称过滤 |
| `wave_get_value` | 查询信号在指定时间的值（at-or-before） |
| `wave_get_transitions` | 查询信号在时间段内的变化，支持边沿/值过滤 |
| `wave_get_window` | 查询多个信号在同一窗口内的变化 |
| `wave_find_transition` | 查找指定时间之前或之后的最近变化 |

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
