# MCP With Tracing - 快速参考指南

> **目的**: 提供项目关键信息的快速查阅  
> **适用人群**: 开发者、测试人员、运维人员、技术负责人

---

## 🚀 快速开始

### 1. 环境准备 (5 分钟)
```bash
# 进入项目目录
cd /Users/bohaiqing/opensource/git/langfuse-examples/mcp-with-tracing

# 创建虚拟环境
uv venv
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt
```

### 2. 配置环境变量 (5 分钟)
```bash
# 复制模板
cp .env.example .env

# 编辑配置文件
vim .env
```

**必需配置**:
```env
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

**可选配置** (告警通知):
```env
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

### 3. 验证配置 (2 分钟)
```bash
python scripts/test_langfuse_connection.py
```

### 4. 运行服务器 (1 分钟)
```bash
python src/server.py
```

---

## 📁 项目结构速览

```
mcp-with-tracing/
├── src/                          # 源代码
│   ├── server.py                 # MCP 主服务器
│   ├── observability/            # 可观测性模块
│   │   ├── config.py             # 配置管理
│   │   ├── instrumentation.py    # 初始化工具
│   │   ├── decorators.py         # 追踪装饰器
│   │   ├── langfuse_client.py    # Langfuse 客户端
│   │   ├── session.py            # 会话管理
│   │   ├── prompt_versioning.py  # 提示词版本
│   │   ├── feedback.py           # 反馈收集
│   │   ├── alerting.py           # 告警管理
│   │   └── notifiers.py          # 通知渠道
│   └── tools/                    # MCP 工具
│       └── feedback_tool.py      # 反馈工具
├── tests/                        # 单元测试
├── scripts/                      # 测试和查询脚本
├── docs/                         # 技术文档
├── manuals/                      # 用户手册
└── devs/                         # 开发文档
    ├── EXECUTIVE_SUMMARY.md      # ⭐ 执行摘要
    ├── REQUIREMENT_ALIGNMENT_AND_TASKS.md  # ⭐ 需求对齐
    ├── DETAILED_TASK_BREAKDOWN.md          # ⭐ 子任务拆分
    └── COMPLETION_SUMMARY.md     # 完成总结
```

---

## 🧪 测试命令

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行特定测试文件
```bash
pytest tests/test_instrumentation.py -v
pytest tests/test_session.py -v
pytest tests/test_prompt_versioning.py -v
pytest tests/test_feedback.py -v
```

### 生成覆盖率报告
```bash
pytest tests/ --cov=src/observability --cov-report=html
open htmlcov/index.html
```

### 运行集成测试
```bash
python scripts/test_langfuse_connection.py
python scripts/test_session_tracing.py
python scripts/test_prompt_versioning.py
python scripts/test_alerting.py
```

---

## 🔍 常用查询脚本

### 查询提示词版本效果
```bash
python scripts/query_prompt_versions.py
```

**输出示例**:
```
Prompt Version Comparison
=========================
Version | Success Rate | Avg Latency | P95 Latency | Calls
--------|--------------|-------------|-------------|------
v1.0    | 98.5%        | 320ms       | 450ms       | 1234
v1.1    | 99.2%        | 280ms       | 380ms       | 567
```

### 查询用户反馈
```bash
python scripts/query_feedback.py
```

**输出示例**:
```
Feedback Summary
================
Period: Last 7 days
Acceptance Rate: 87.3%
Average Score: 4.2/5.0
Total Feedback: 456
```

---

## 📊 核心 API 速查

### 初始化 Langfuse
```python
from src.observability.instrumentation import init_observability

# 初始化
client = init_observability()
```

### 使用装饰器追踪工具
```python
from src.observability.decorators import observe_tool, track_session

@observe_tool(name="my_tool")
@track_session(session_id="session_123", user_id="user_456")
def my_tool(param1: str, param2: int) -> dict:
    """我的工具函数"""
    return {"result": "success"}
```

### 记录用户反馈
```python
from src.observability.feedback import FeedbackCollector

collector = FeedbackCollector()

# 记录接受
collector.record_acceptance(trace_id="trace_123")

# 记录拒绝
collector.record_rejection(trace_id="trace_123", reason="不准确")

# 记录评分 (1-5)
collector.record_score(trace_id="trace_123", score=4)

# 添加评论
collector.add_comment(trace_id="trace_123", comment="很好用")
```

### 配置告警
```python
from src.observability.alerting import AlertManager

manager = AlertManager()

# 配置成功率告警
manager.configure_success_rate_alert(
    threshold=0.99,  # 99%
    window_minutes=5
)

# 配置延迟告警
manager.configure_latency_alert(
    p95_threshold_ms=500,
    window_minutes=10
)

# 添加通知渠道
from src.observability.notifiers import WeComNotifier
notifier = WeComNotifier(webhook_url="https://...")
manager.add_notifier(notifier)
```

---

## 🐛 常见问题排查

### 问题 1: Langfuse 连接失败
**症状**: `test_langfuse_connection.py` 失败

**排查步骤**:
```bash
# 1. 检查环境变量
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY

# 2. 检查网络连接
curl https://cloud.langfuse.com/api/public/health

# 3. 验证 API keys
python -c "from langfuse import Langfuse; lf = Langfuse(); print(lf.auth_check())"
```

**解决方案**:
- 确认 `.env` 文件中配置正确
- 确认 API keys 有效且未过期
- 检查网络防火墙设置

---

### 问题 2: 追踪数据未显示
**症状**: 工具调用成功，但 Langfuse 控制台看不到 traces

**排查步骤**:
```bash
# 1. 检查 flush 配置
grep LANGFUSE_FLUSH .env

# 2. 手动刷新
python -c "from src.observability.langfuse_client import get_langfuse_client; get_langfuse_client().flush()"

# 3. 检查错误日志
python src/server.py 2>&1 | grep -i error
```

**解决方案**:
- 增加 `LANGFUSE_FLUSH_INTERVAL` (默认 5 秒)
- 减少 `LANGFUSE_FLUSH_AT` (默认 50 条)
- 检查是否有异常被抑制

---

### 问题 3: Session ID 未传播
**症状**: 多个工具调用的 session_id 不一致

**排查步骤**:
```python
# 检查 contextvars
import asyncio
from src.observability.session import SessionManager

async def test():
    manager = SessionManager()
    session_id = manager.create_session()
    print(f"Session ID: {session_id}")
    
    # 在异步上下文中检查
    retrieved = manager.get_session()
    print(f"Retrieved: {retrieved}")

asyncio.run(test())
```

**解决方案**:
- 确保使用 `@track_session` 装饰器
- 检查是否正确设置 contextvars
- 确认没有手动覆盖 session_id

---

### 问题 4: 告警未触发
**症状**: 成功率低于阈值，但未收到告警

**排查步骤**:
```bash
# 1. 检查告警配置
python -c "from src.observability.alerting import AlertManager; m = AlertManager(); print(m.rules)"

# 2. 测试通知渠道
python -c "from src.observability.notifiers import WeComNotifier; n = WeComNotifier('url'); n.send('test')"

# 3. 模拟告警触发
python scripts/test_alerting.py
```

**解决方案**:
- 确认告警规则已配置
- 确认通知渠道配置正确
- 检查告警去重逻辑

---

## 📖 文档导航

### 快速入门
- **[manuals/快速入门.md](../manuals/快速入门.md)** - 5 分钟上手指南
- **[manuals/用户手册.md](../manuals/用户手册.md)** - 完整用户使用指南
- **[manuals/API 参考.md](../manuals/API%20参考.md)** - API 详细参考

### 技术文档
- **[docs/session-view-guide.md](../docs/session-view-guide.md)** - 会话追踪指南
- **[docs/prompt-effectiveness-dashboard.md](../docs/prompt-effectiveness-dashboard.md)** - 提示词仪表板
- **[docs/satisfaction-dashboard-guide.md](../docs/satisfaction-dashboard-guide.md)** - 满意度仪表板
- **[docs/wecom-alert-setup.md](../docs/wecom-alert-setup.md)** - 企微告警配置
- **[docs/event-response-runbook.md](../docs/event-response-runbook.md)** - 事件响应手册

### 开发文档
- **[devs/EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - ⭐ 执行摘要（管理层）
- **[devs/REQUIREMENT_ALIGNMENT_AND_TASKS.md](REQUIREMENT_ALIGNMENT_AND_TASKS.md)** - ⭐ 需求对齐
- **[devs/DETAILED_TASK_BREAKDOWN.md](DETAILED_TASK_BREAKDOWN.md)** - ⭐ 子任务拆分
- **[devs/COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)** - 完成总结
- **[AGENTS.md](../AGENTS.md)** - 项目总体规范

---

## 🔗 外部资源

### 官方文档
- **Langfuse**: https://langfuse.com/docs
- **Langfuse Python SDK**: https://langfuse.com/docs/sdk/python
- **FastMCP**: https://github.com/anthropics/mcp-server-python
- **MCP Protocol**: https://spec.modelcontextprotocol.io/

### 社区
- **Langfuse Discord**: https://discord.gg/langfuse
- **Langfuse GitHub**: https://github.com/langfuse/langfuse

---

## 💡 最佳实践速查

### 1. 始终使用 Session Context
```python
# ✅ 推荐
@track_session(session_id=session_id, user_id=user_id)
def my_tool():
    pass

# ❌ 避免
def my_tool():
    # 硬编码 session_id
    pass
```

### 2. 附加提示词版本
```python
# ✅ 推荐
@track_prompt_version(prompt_id="my_prompt", version="v1.0")
def generate_response():
    pass

# ❌ 避免
def generate_response():
    # 不追踪版本
    pass
```

### 3. 处理错误
```python
# ✅ 推荐 - 让装饰器自动捕获
@observe_tool(name="my_tool")
def my_tool():
    result = risky_operation()
    return result

# ❌ 避免 - 抑制异常
@observe_tool(name="my_tool")
def my_tool():
    try:
        result = risky_operation()
        return result
    except Exception:
        return {"error": "failed"}  # 隐藏了真实错误
```

### 4. 保护敏感数据
```python
# ✅ 推荐 - 自动脱敏
data = {"phone": "13812345678", "email": "user@example.com"}
# Langfuse 会自动脱敏为: {"phone": "138****5678", "email": "us***@example.com"}

# ❌ 避免 - 明文发送
data = {"password": "secret123"}  # 会被脱敏，但最好在应用层就移除
```

### 5. 平衡粒度与开销
```python
# ✅ 推荐 - 合理的 span 层级
@observe_tool(name="process_request")
def process_request():
    intent = recognize_intent()      # 自动创建 span
    knowledge = retrieve_knowledge() # 自动创建 span
    response = generate_response()   # 自动创建 span
    return response

# ❌ 避免 - 过度嵌套
@observe_tool(name="step1")
def step1():
    with create_span("substep1"):
        with create_span("subsubstep1"):
            # ... 太深了
```

---

## 📞 获取帮助

### 内部支持
- 查看 `docs/event-response-runbook.md` - 常见问题处理
- 查看 `AGENTS.md` - 项目规范和最佳实践
- 联系 Platform Team

### 外部支持
- **Langfuse Discord**: https://discord.gg/langfuse
- **GitHub Issues**: https://github.com/langfuse/langfuse/issues

---

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|---------|
| 2026-04-13 | 1.0.0 | 初始版本，包含所有核心功能 |

---

**最后更新**: 2026-04-13  
**维护者**: Platform Team  
**版本**: 1.0.0