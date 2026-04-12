# 事件响应手册 (Incident Response Runbook)

本文档提供告警触发后的标准响应流程和最佳实践。

## 告警响应流程

### 一级响应流程 (Severity-Based)

```
┌─────────────┐
│  Alert      │
│ Triggered   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│ Severity =  │────▶│  Route to   │
│ CRITICAL    │     │  Team Lead  │
└──────┬──────┘     └─────────────┘
       │
       ▼ (Severity = WARNING)
┌─────────────┐
│   On-Call   │
│  Engineer   │
└──────┬──────┘
       │
       ▼ (Severity = INFO)
┌─────────────┐
│  Log Only   │
│   + Email   │
└─────────────┘
```

### 响应时间目标 (RTO)

| Severity | 响应时间 | 解决时间 | 升级时间 |
|----------|----------|----------|----------|
| INFO | 4 小时 | 24 小时 | - |
| WARNING | 30 分钟 | 4 小时 | 1 小时未响应 |
| CRITICAL | 5 分钟 | 1 小时 | 15 分钟未响应 |

---

## 常见告警类型及响应

### 1. 成功率低告警 (success-rate-low)

**告警条件**: 成功率 < 95%

**可能原因**:
- Langfuse API 连接问题
- API key 失效或过期
- 网络问题
- 代码逻辑错误

**诊断步骤**:

```bash
# 1. 检查 Langfuse 连接
curl https://cloud.langfuse.com/api/health

# 2. 查看 API keys 配置
cat .env | grep LANGFUSE

# 3. 检查应用日志
journalctl -u mcp-server -n 50

# 4. 检查 Langfuse dashboard
打开 https://cloud.langfuse.com/project/
查看错误日志
```

**修复步骤**:

1. **API 问题**:
   ```bash
   # 重新配置 API keys
   export LANGFUSE_PUBLIC_KEY=pk-xxx
   export LANGFUSE_SECRET_KEY=sk-xxx
   # 重启服务
   ```

2. **网络问题**:
   ```bash
   # 检查网络连通性
   ping cloud.langfuse.com
   # 检查防火墙规则
   ```

3. **代码问题**:
   - 回滚最近部署
   - 查看错误日志
   - 修复代码并重新部署

---

### 2. 高延迟告警 (latency-high)

**告警条件**: P95 延迟 > 500ms

**可能原因**:
- Langfuse API 响应慢
- 本地网络延迟
- 追踪数据量大
- 资源紧张 (CPU/内存)

**诊断步骤**:

```bash
# 1. 检查系统资源
top -bn1 | head -20
free -h

# 2. 测试 API 延迟
time curl -s https://cloud.langfuse.com/api/health

# 3. 查看追踪数据量
python scripts/query_feedback.py

# 4. 检查网络延迟
ping -c 5 cloud.langfuse.com
```

**修复步骤**:

1. **资源扩容**:
   - 增加 CPU/内存
   - 优化代码性能

2. **批量处理**:
   - 调整 flush 频率
   - 使用批量 API

3. **网络优化**:
   - 使用就近区域
   - 配置连接池

---

### 3. Session ID 问题

**告警条件**: Session 丢失或不完整

**可能原因**:
- Session ID 生成失败
- 上下文传播问题
- Langfuse attribute 限制

**诊断步骤**:

```python
from src.observability.session import get_session_id, SessionManager

# 检查 session 状态
session_id = get_session_id()
print(f"Current session: {session_id}")

# 检查是否符合限制 (< 200 chars, ASCII)
import langfuse
assert len(session_id) <= 200
assert session_id.isascii()
```

**修复步骤**:

1. **Session ID 限制**:
   ```python
   # 使用合规的 Session ID
   session_id = f"session-{uuid.uuid4().hex[:16]}"
   ```

2. **上下文传播**:
   ```python
   # 使用正确的 propagate_attributes
   with propagate_attributes(session_id=ctx["session_id"]):
       # ...
   ```

---

## 升级流程

### 升级规则

| 条件 | 升级目标 | 方式 |
|------|----------|------|
| WARNING > 1 小时未响应 | 团队主管 | Slack + 电话 |
| CRITICAL > 15 分钟未响应 | 技术负责人 | PagerDuty + 电话 |
| 影响用户 > 10% | 全团队 | 紧急会议 |

### 联系方式

| 角色 | Slack | 电话 | 备用 |
|------|-------|------|------|
| On-Call | @on-call | 查看 PagerDuty | Email |
| 团队主管 | @team-lead | - | - |
| 技术负责人 | @tech-lead | - | - |

---

## 事后分析 (Post-Mortem)

### 时间线模板

```markdown
## 事件时间线

| 时间 | 事件 |
|------|------|
| HH:MM | 告警首次触发 |
| HH:MM | On-Call 响应 |
| HH:MM | 诊断开始 |
| HH:MM | 根本原因确认 |
| HH:MM | 修复部署 |
| HH:MM | 告警清除 |
| HH:MM | 服务恢复正常 |
```

### 根本原因分析 (RCA)

```markdown
## 根本原因分析

### 问题描述
简短描述问题现象

### 根本原因
深入分析导致问题的根本原因

### 影响范围
- 影响用户数：X
- 持续时间：Y 分钟
- 影响服务：列表

### 修复措施
- 短期：临时修复
- 长期：永久解决方案

### 预防措施
- [ ] 添加监控
- [ ] 改进告警
- [ ] 代码改进
- [ ] 流程改进
```

---

## 监控检查清单

### 日常检查

- [ ] 查看 Langfuse dashboard
- [ ] 检查告警历史
- [ ] 审查异常日志
- [ ] 验证数据完整性

### 周度检查

- [ ] 分析告警趋势
- [ ] 审查告警阈值
- [ ] 更新响应流程
- [ ] 团队演练

---

## 参考文档

- [Langfuse 告警配置](https://langfuse.com/docs/alerting)
- [Langfuse 监控指标](https://langfuse.com/docs/metrics)
- [内部监控仪表板](https://grafana.example.com/mcp-observability)

---

## 联系支持

如需技术支持，请联系:
- Email: ops-team@example.com
- Slack: #mcp-observability
- Jira: 提交 DOPS 工单
