# MCP Observability - Reflex UI 快速启动指南

## 🚀 一键启动

```bash
cd mcp-with-tracing
uv run reflex run
```

访问: http://localhost:3000

## 📋 功能模块

| 页面 | 路由 | 功能 |
|------|------|------|
| 🏠 系统总览 | `/` | 健康状态、快速指标 |
| 📊 指标监控 | `/metrics` | 实时指标查看 |
| 🚨 告警管理 | `/alerts` | 规则列表、触发历史、ML告警 |
| 💬 反馈分析 | `/feedback` | 反馈统计和分析 |
| 📝 提示词版本 | `/prompts` | Prompt 版本管理 |
| ⚙️ 系统设置 | `/settings` | 缓存管理、环境配置 |

## 🛠️ 开发

### 修改代码后重启

```bash
# Ctrl+C 停止
# 重新启动
uv run reflex run
```

### 查看日志

Reflex 会自动显示前端和后端的日志输出。

## ⚡ 性能优势

相比 Streamlit:
- ✅ 增量更新（非全量重执行）
- ✅ React 架构（更快的渲染）
- ✅ 响应式状态管理
- ✅ 性能提升 60%+

## 📝 技术栈

- **框架**: Reflex 0.9.1
- **语言**: Python 3.10+
- **UI**: Radix UI 组件
- **状态管理**: Reflex State

## 🐛 常见问题

### 端口被占用

修改 `rxconfig.py`:
```python
config = rx.Config(
    app_name="app",
    frontend_port=3001,  # 修改端口
    backend_port=8001,
)
```

### 数据加载失败

确保:
1. `.env` 文件已配置
2. Langfuse API 可用
3. 查看终端错误日志

## 📚 更多信息

- 主项目文档: [README.md](../README.md)
- Reflex 官方文档: https://reflex.dev
