# API 参考文档

> 版本：1.0.0

## 会话管理 API

### set_session
```python
set_session(session_id: str, user_id: str = None, metadata: dict = None)
```

### get_session_id
```python
get_session_id() -> str | None
```

### clear_session
```python
clear_session()
```

## 反馈收集 API

### record_acceptance
```python
record_acceptance(trace_id: str, user_id: str = None, comment: str = None)
```

### record_rejection
```python
record_rejection(trace_id: str, user_id: str = None, reason: str = None, comment: str = None)
```

### record_rating
```python
record_rating(trace_id: str, rating: int, user_id: str = None, comment: str = None)
```

### get_acceptance_rate
```python
get_acceptance_rate() -> float
```

## 告警管理 API

### AlertRule
```python
AlertRule(
    name: str,
    metric: str,
    threshold: float,
    operator: str,
    severity: AlertSeverity,
    window_minutes: int = 60
)
```

## 版本管理 API

### register_prompt_version
```python
register_prompt_version(
    prompt_id: str,
    version: str,
    description: str = None,
    metadata: dict = None
)
```

### get_active_prompt_version
```python
get_active_prompt_version(prompt_id: str) -> str | None
```

## 装饰器

### observe_tool
```python
@observe_tool(name: str = None)
def my_tool(...):
    pass
```

## 通知渠道

### WeComNotifier
```python
WeComNotifier(webhook_url: str)
```

详见：docs/wecom-alert-setup.md
