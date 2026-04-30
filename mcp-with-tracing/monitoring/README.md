# MCP 监控配置

本目录包含 MCP Langfuse Observability Platform 的完整监控配置，支持 Prometheus + Grafana 技术栈。

## 📁 文件说明

| 文件 | 说明 | 用途 |
|------|------|------|
| [prometheus-alerts.yml](prometheus-alerts.yml) | Prometheus 告警规则 | 24 条告警规则，覆盖 7 大类别 |
| [grafana-dashboard.json](grafana-dashboard.json) | Grafana 仪表板 | 20 个可视化面板，开箱即用 |
| [MONITORING_SETUP.md](MONITORING_SETUP.md) | 监控配置指南 | 完整的集成和部署文档 |

## 🚀 快速开始

### 1. Prometheus 集成

```bash
# 在 prometheus.yml 中添加配置
scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

# 加载告警规则
rule_files:
  - "monitoring/prometheus-alerts.yml"
```

### 2. Grafana 仪表板

```bash
# 方式 1: 通过 UI 导入
# Grafana → Dashboard → Import → 上传 grafana-dashboard.json

# 方式 2: 通过 API 导入
curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
  -H "Content-Type: application/json" \
  -d @grafana-dashboard.json
```

### 3. 验证配置

```bash
# 检查 Prometheus 目标
curl http://localhost:9090/api/v1/targets | jq

# 查看告警规则
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].name'

# 查询指标
curl http://localhost:9090/api/v1/query?query=mcp_success_rate
```

## 📊 监控能力

### 告警覆盖

| 类别 | 规则数 | 示例 |
|------|-------|------|
| 可用性 | 3 | 成功率 < 99% |
| 性能 | 8 | P95 延迟 > 1000ms |
| 质量 | 3 | 用户满意度 < 3.5 |
| 会话 | 2 | 活跃会话归零 |
| 错误分析 | 3 | 超时错误率过高 |
| 工具维度 | 2 | 工具成功率 < 95% |
| 基础设施 | 3 | 缓存命中率 < 50% |
| **总计** | **24** | - |

### 仪表板面板

| 区域 | 面板数 | 内容 |
|------|-------|------|
| 系统健康 | 4 | 成功率、会话数、QPS、满意度 |
| 性能趋势 | 2 | 延迟分位数、成功率与 QPS |
| 错误分析 | 2 | 错误类型分布、错误率趋势 |
| 工具监控 | 3 | 调用次数、延迟、成功率 |
| 基础设施 | 4 | 缓存、告警状态、ML 检测 |
| **总计** | **15** | - |

## 📖 详细文档

- [监控配置完整指南](MONITORING_SETUP.md) - 集成、部署、故障排查
- [指标对照表](../docs/metrics-reference.md) - 所有指标的详细说明
- [智能告警指南](../docs/smart-alerting-guide.md) - ML 异常检测配置

## 🔧 自定义配置

### 修改告警阈值

编辑 `prometheus-alerts.yml`，调整 `expr` 表达式：

```yaml
# 修改成功率告警阈值
- alert: MCPSuccessRateLow
  expr: mcp_success_rate < 0.99  # 改为 0.98
  for: 5m
```

### 添加新指标

1. 在 `src/observability/prometheus_exporter.py` 中注册指标
2. 在 `prometheus-alerts.yml` 中添加告警规则
3. 在 `grafana-dashboard.json` 中添加面板

### 调整采集频率

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-server'
    scrape_interval: 30s  # 调整为 15s 或 60s
```

## 🎯 告警级别

| 级别 | 响应时间 | 通知渠道 | 使用场景 |
|------|---------|---------|---------|
| WARNING | 30 分钟 | 企业微信/Slack | 性能下降、早期预警 |
| CRITICAL | 5 分钟 | 企业微信 + 电话 | 服务降级、需要立即处理 |

## 📞 支持

如有问题，请查阅：
- [故障排查指南](MONITORING_SETUP.md#故障排查)
- [项目文档索引](../docs/)
- 联系平台团队

---

**版本**: 1.0.0  
**最后更新**: 2026-04-30  
**维护者**: 平台团队
