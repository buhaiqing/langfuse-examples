# MCP Server HTTP 传输模式配置指南

## 📋 概述

MCP Server 支持三种传输模式：

| 模式 | 适用场景 | 端口 | 协议 |
|------|---------|------|------|
| **http** (推荐) | Web 集成、API 调用 | 8001 | Streamable HTTP |
| **sse** | 实时推送场景 | 8001 | Server-Sent Events |
| **stdio** | Claude Desktop、Cursor | N/A | 标准输入/输出 |

## 🚀 快速开始

### 1. 使用 HTTP 模式（推荐）

```bash
# 方式 1: 通过 .env 文件配置
echo "MCP_TRANSPORT=http" >> .env
echo "MCP_PORT=8001" >> .env
make start-all

# 方式 2: 通过环境变量
MCP_TRANSPORT=http MCP_PORT=8001 make start-all

# 方式 3: 直接运行
MCP_TRANSPORT=http MCP_PORT=8001 PYTHONPATH=. python3 run.py
```

**启动后访问：**
- MCP Endpoint: `http://localhost:8001/mcp`
- Reflex UI: `http://localhost:3000`

### 2. 使用 SSE 模式

```bash
MCP_TRANSPORT=sse MCP_PORT=8001 PYTHONPATH=. python3 run.py
```

**端点：** `http://localhost:8001/sse`

### 3. 使用 STDIO 模式（默认）

```bash
# 用于 Claude Desktop、Cursor 等客户端
PYTHONPATH=. python3 run.py
```

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| `MCP_TRANSPORT` | 传输模式 | `http` | `stdio`, `http`, `sse` |
| `MCP_HOST` | 绑定地址 | `0.0.0.0` | 任意 IP |
| `MCP_PORT` | 监听端口 | `8001` | 任意可用端口 |

### .env 配置示例

```bash
# MCP Server Transport Configuration
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8001
```

## 🧪 测试 HTTP 端点

### 使用 curl 测试

```bash
# 1. 初始化连接
curl -s http://localhost:8001/mcp \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0"
      }
    },
    "id": 1
  }'

# 响应示例:
# event: message
# data: {"jsonrpc":"2.0","id":1,"result":{
#   "protocolVersion":"2024-11-05",
#   "capabilities":{"tools":{"listChanged":true}},
#   "serverInfo":{"name":"MCP Langfuse Observability Server","version":"1.26.0"}
# }}

# 2. 列出可用工具
curl -s http://localhost:8001/mcp \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id-from-init>" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 2
  }'

# 3. 调用工具（健康检查）
curl -s http://localhost:8001/mcp \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: <session-id>" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "health_check",
      "arguments": {}
    },
    "id": 3
  }'
```

### 使用 Python 测试

```python
import requests
import json

# MCP Server URL
MCP_URL = "http://localhost:8001/mcp"

# 1. 初始化
response = requests.post(
    MCP_URL,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    },
    json={
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "python-test", "version": "1.0"}
        },
        "id": 1
    }
)

# 获取 Session ID
session_id = response.headers.get("Mcp-Session-Id")
print(f"Session ID: {session_id}")

# 2. 调用健康检查
response = requests.post(
    MCP_URL,
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id
    },
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "health_check",
            "arguments": {}
        },
        "id": 2
    }
)

print(f"Health Check: {response.text}")
```

## 🌐 客户端集成

### Web 前端集成

```javascript
// JavaScript 示例
const MCP_ENDPOINT = 'http://localhost:8001/mcp';

async function callMcpTool(toolName, args) {
  // 1. 初始化（首次）
  const initResponse = await fetch(MCP_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream'
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'web-client', version: '1.0' }
      },
      id: 1
    })
  });

  const sessionId = initResponse.headers.get('Mcp-Session-Id');

  // 2. 调用工具
  const response = await fetch(MCP_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream',
      'Mcp-Session-Id': sessionId
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'tools/call',
      params: { name: toolName, arguments: args },
      id: 2
    })
  });

  const text = await response.text();
  // 解析 SSE 格式响应
  const data = text.split('\n').find(line => line.startsWith('data: '));
  return JSON.parse(data.replace('data: ', ''));
}

// 使用示例
const health = await callMcpTool('health_check', {});
console.log(health);
```

### Claude Desktop 配置（使用 STDIO）

```json
{
  "mcpServers": {
    "langfuse-observability": {
      "command": "python3",
      "args": ["/path/to/mcp-with-tracing/run.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### Cursor / VS Code 配置

在 `.mcp.json` 中配置：

```json
{
  "servers": {
    "langfuse-observability": {
      "command": "python3",
      "args": ["run.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

## 🔍 故障排查

### 问题 1: 端口被占用

```bash
# 检查端口占用
lsof -i :8001

# 停止占用进程
lsof -ti:8001 | xargs kill -9

# 更换端口
MCP_TRANSPORT=http MCP_PORT=8002 python3 run.py
```

### 问题 2: 连接被拒绝

```bash
# 检查服务器是否运行
curl -I http://localhost:8001/mcp

# 查看日志
tail -f /tmp/mcp_server.log

# 检查防火墙
sudo lsof -iTCP -sTCP:LISTEN -P -n | grep 8001
```

### 问题 3: SSE 事件流解析错误

确保客户端正确设置 Accept 头：

```bash
-H "Accept: application/json, text/event-stream"
```

## 📊 性能对比

| 传输模式 | 延迟 | 吞吐量 | 适用场景 |
|---------|------|--------|---------|
| HTTP | ~10ms | 高 | Web API、微服务 |
| SSE | ~15ms | 中 | 实时推送 |
| STDIO | ~5ms | 低 | 本地客户端 |

## 🎯 最佳实践

1. **生产环境使用 HTTP 模式**
   - 支持负载均衡
   - 易于监控和日志
   - 标准 HTTP 工具链

2. **开发环境使用 STDIO 模式**
   - 与 Claude/Cursor 集成
   - 无需端口管理
   - 快速启动

3. **实时通知使用 SSE 模式**
   - 服务器主动推送
   - 减少轮询开销
   - 适合告警通知

## 📚 相关文档

- [FastMCP 官方文档](https://gofastmcp.com)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Streamable HTTP Transport](https://modelcontextprotocol.io/specification/2024-11-05/basic/transports#streamable-http)

---

**最后更新**: 2026-04-30  
**维护者**: 平台团队
