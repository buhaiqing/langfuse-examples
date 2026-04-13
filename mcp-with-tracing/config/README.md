# 配置文件目录

本目录包含 MCP Langfuse Observability 系统的配置文件。

## 📁 文件说明

### alerts.yaml
**告警规则配置文件**

- **用途**: 定义应用启动时自动加载的告警规则
- **格式**: YAML
- **版本控制**: ✅ 应该提交到 Git（作为模板和默认配置）
- **自定义**: 可以复制为 `alerts-custom.yaml` 并修改

**示例结构**:
```yaml
alerts:
  - name: "success-rate-low"
    metric: "success_rate"
    threshold: 0.95
    operator: "lt"
    severity: "warning"
    channels:
      - "wecom"
      - "slack"
```

**文档**: 详见 [告警规则配置指南](../docs/alert-config-guide.md)

---

## 🔧 使用方式

### 1. 默认配置
服务器启动时会自动加载 `config/alerts.yaml`：

```bash
python -m src.server
```

### 2. 自定义配置路径
通过环境变量指定其他配置文件：

```bash
ALERT_CONFIG_PATH=config/alerts-prod.yaml python -m src.server
```

### 3. 禁用配置文件
如果不想使用配置文件，可以删除或重命名 `alerts.yaml`，服务器会启动但不加载任何规则：

```
⚠️  Alert config file not found: config/alerts.yaml
   No alert rules will be loaded.
```

此时可以通过 API 或脚本动态注册规则。

---

## 📝 配置管理最佳实践

### 开发环境
```bash
# 使用默认配置
cp alerts.yaml alerts-dev.yaml
# 修改阈值等参数以适应开发环境
```

### 生产环境
```bash
# 创建生产专用配置
cp alerts.yaml alerts-prod.yaml
# 调整阈值为更严格的标准
# 启用所有通知渠道
```

### 版本控制
```bash
# 提交基础配置模板
git add alerts.yaml
git commit -m "Add default alert rules configuration"

# 忽略自定义配置（可选）
echo "alerts-custom.yaml" >> .gitignore
```

---

## 🔗 相关文档

- [告警规则配置指南](../docs/alert-config-guide.md) - 完整的配置语法和示例
- [企业微信配置](../docs/wecom-alert-setup.md) - 通知渠道设置
- [事件响应手册](../docs/event-response-runbook.md) - 告警处理流程

---

## ❓ 常见问题

**Q: 修改配置文件后需要重启吗？**  
A: 是的，当前版本需要重启服务器才能加载新配置。未来版本可能支持热重载。

**Q: 可以同时使用配置文件和 API 吗？**  
A: 可以。配置文件在启动时加载，API 可以在运行时动态添加/修改规则。

**Q: 如何验证配置文件是否正确？**  
A: 启动服务器时会显示加载结果。也可以使用 Python 脚本验证：
```python
from src.observability.alert_config_loader import AlertConfigLoader
loader = AlertConfigLoader("config/alerts.yaml")
loader.load_and_register()
```

**Q: 配置文件中的规则优先级如何？**  
A: 所有规则平等，按名称唯一标识。如果名称冲突，后注册的会覆盖先前的。
