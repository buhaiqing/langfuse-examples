# Reflex UI 开发规范

> **项目**: MCP Langfuse Observability Dashboard  
> **版本**: 1.0.0  
> **最后更新**: 2026-04-30  
> **目的**: 基于 Reflex 迁移和实际开发经验，制定预防性开发规范，避免重复犯错

---

## 目录

1. 项目初始化与依赖管理
2. 环境变量加载规范
3. State 状态管理规范
4. 组件开发规范
5. 数据加载与 API 调用
6. 性能优化与缓存策略
7. 错误处理与降级策略
8. 代码质量与工程规范
9. 开发工作流
10. 常见问题与解决方案

---

## 1. 项目初始化与依赖管理

### 1.1 依赖声明

**强制规则**

**规则 1.1.1**: 所有 Python 依赖必须在 `pyproject.toml` 中声明

```toml
# pyproject.toml
dependencies = [
    "reflex>=0.9.0",
    "langfuse>=2.0.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0.0",
    "apscheduler>=3.10.0",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
]
```

**规则 1.1.2**: 禁止在代码中动态安装依赖

```python
# 错误:在运行时安装依赖
import subprocess
subprocess.run(["pip", "install", "langfuse"])

# 正确:在 pyproject.toml 中声明后执行 uv sync
```

**规则 1.1.3**: 每次添加新依赖后必须执行 `uv sync`

```bash
# 添加依赖后
uv sync
echo "✅ 依赖已同步到 .venv"
```

**检查清单**:
- [ ] 所有依赖是否在 pyproject.toml 中声明?
- [ ] 是否执行了 uv sync 同步依赖?
- [ .venv/bin/python3 -c "import 新模块" 是否成功?

### 1.2 虚拟环境管理

**强制规则**

**规则 1.2.1**: 始终使用 uv 管理虚拟环境

```bash
# 创建/同步环境
uv sync

# 在虚拟环境中运行命令
uv run python3 your_script.py
uv run reflex run
```

**规则 1.2.2**: 禁止直接修改系统 Python 环境

```bash
# 错误:使用系统 pip
pip install reflex

# 正确:使用 uv
uv pip install reflex --venv .venv
```

---

## 2. 环境变量加载规范

### 2.1 .env 文件加载

**背景**: 多次出现服务启动时无法读取 `.env` 文件的问题。

**强制规则**

**规则 2.1.1**: Makefile 必须在开头加载 `.env` 文件

```makefile
# Makefile (第 4-8 行)
# Load environment variables from .env file
ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
endif
```

**规则 2.1.2**: Python 入口文件必须显式调用 `load_dotenv()`

```python
# run.py 或主入口文件
from dotenv import load_dotenv
from pathlib import Path
import os

# 在 main() 函数最开头加载
def main():
    # 必须在所有导入之前加载
    load_dotenv()
    
    # 切换到项目根目录(确保 pydantic-settings 能找到 .env)
    os.chdir(Path(__file__).parent)
    
    # ... 其他代码
```

**规则 2.1.3**: Reflex 后端必须在 `data_loader.py` 中实现懒加载初始化

```python
# ui/utils/data_loader.py
def load_health_status() -> dict[str, Any]:
    """加载系统健康状态。"""
    try:
        # 确保 Langfuse 客户端已初始化(懒加载)
        from src.observability.instrumentation import get_langfuse_client, init_observability
        
        client = get_langfuse_client()
        if client is None:
            # 尝试初始化
            try:
                from src.observability.config import ObservabilityConfig
                config = ObservabilityConfig()
                init_observability(config)
            except Exception as init_error:
                logger.warning(f"Langfuse 初始化失败: {init_error}")
        
        from src.observability.health import get_health_status
        return get_health_status()
    except Exception as e:
        logger.error(f"Failed to load health status: {e}")
        return {"status": "error", "components": {}}
```

**规则 2.1.4**: 禁止在 `rxconfig.py` 中初始化外部客户端

```python
# rxconfig.py - 错误示例
import os
from dotenv import load_dotenv
load_dotenv()
from langfuse import Langfuse  # ❌ 会导致 Reflex 启动失败

config = rx.Config(app_name="app")
```

```python
# rxconfig.py - 正确示例
"""Reflex configuration for MCP Observability Dashboard."""
import reflex as rx

config = rx.Config(
    app_name="app",
    frontend_port=3000,
    backend_port=8000,
)
```

**检查清单**:
- [ ] Makefile 是否加载了 .env 文件?
- [ ] Python 入口是否调用了 load_dotenv()?
- [ ] 是否切换到了项目根目录?
- [ ] rxconfig.py 是否保持简洁(无外部依赖初始化)?
- [ ] data_loader.py 是否实现了懒加载?

---

## 3. State 状态管理规范

### 3.1 State 变量定义

**强制规则**

**规则 3.1.1**: State 变量必须声明明确的类型

```python
import reflex as rx
from typing import Any

class State(rx.State):
    """MCP Observability Dashboard 状态。"""
    
    # 健康状态
    health_status: dict[str, Any] = {}
    
    # 指标数据
    metrics: dict[str, float] = {}
    
    # 会话列表
    sessions: list[dict[str, Any]] = []
    
    # 加载状态
    is_loading: bool = False
```

**规则 3.1.2**: 复杂嵌套字典必须提供默认值

```python
# 正确:提供完整的默认结构
class State(rx.State):
    health_status: dict[str, Any] = {
        "status": "unknown",
        "components": {
            "langfuse": {"status": "disconnected"},
            "alert_monitor": {"is_running": False},
            "smart_alert_manager": {"is_running": False},
        },
    }
```

### 3.2 State 变量访问

**背景**: Reflex 编译器不支持直接调用 Python 方法。

**强制规则**

**规则 3.2.1**: 必须使用字典语法访问 State 变量

```python
# 正确:使用字典语法
State.health_status["status"]
State.health_status["components"]["langfuse"]["status"]

# 错误:使用 .get() 方法
State.health_status.get("status", "unknown")  # ❌ 编译失败
```

**规则 3.2.2**: 字符串方法必须使用 Reflex 转换

```python
# 正确:使用 .to_string() 转换
State.health_status["status"].to_string().upper()

# 错误:直接调用 Python 方法
State.health_status["status"].upper()  # ❌ TypeError
```

**规则 3.2.3**: 必须使用 rx.cond 进行空值检查

```python
# 正确:使用 rx.cond 检查存在性
rx.cond(
    State.health_status["status"],
    State.health_status["status"].to_string().upper(),
    "UNKNOWN"  # 默认值
)

# 错误:直接访问可能为 undefined 的值
State.health_status["status"].to_string().upper()  # ❌ TypeError on undefined
```

**规则 3.2.4**: 禁止在嵌套字典上使用 rx.foreach

```python
# 错误:rx.foreach 不支持嵌套字典
rx.foreach(
    State.health_status["components"].to(dict),
    lambda item: rx.text(item[0])  # ❌ 编译失败
)

# 正确:使用静态列表或简化结构
rx.text("• Langfuse: 未连接", size="2")
rx.text("• Alert Monitor: 未运行", size="2")
```

**检查清单**:
- [ ] 是否使用字典语法而非 .get()?
- [ ] 字符串方法是否使用了 .to_string()?
- [ ] 是否使用 rx.cond 进行空值检查?
- [ ] 是否避免了在嵌套字典上使用 rx.foreach?

---

## 4. 组件开发规范

### 4.1 组件结构

**强制规则**

**规则 4.1.1**: 复杂组件必须拆分为独立函数

```python
# ui/components/health_card.py
def health_status_card() -> rx.Component:
    """系统健康状态卡片。"""
    return rx.card(
        rx.vstack(
            _health_status_header(),
            _health_status_details(),
            spacing="4",
        ),
        padding="20px",
        width="100%",
    )

def _health_status_header() -> rx.Component:
    """健康状态头部(徽章 + 标题)。"""
    return rx.hstack(
        rx.text("系统状态:", size="4", weight="bold"),
        rx.badge(
            rx.text(
                rx.cond(
                    State.health_status["status"],
                    State.health_status["status"].to_string().upper(),
                    "UNKNOWN"
                ),
                size="4",
                weight="bold",
            ),
            color_scheme=_get_status_color(),
            variant="solid",
        ),
    )

def _health_status_details() -> rx.Component:
    """健康状态详情(降级原因等)。"""
    return rx.cond(
        State.health_status["status"] == "degraded",
        _render_degraded_details(),
        rx.text(""),
    )
```

**规则 4.1.2**: 条件渲染必须使用 rx.cond

```python
# 正确:使用 rx.cond
rx.cond(
    State.health_status["status"] == "degraded",
    rx.vstack(
        rx.text("⚠️ 降级原因:", size="3", weight="bold"),
        # ... 详情内容
    ),
    rx.text(""),  # 不满足条件时渲染空内容
)
```

### 4.2 样式与布局

**推荐规则**

**规则 4.2.1**: 使用 rx.vstack 和 rx.hstack 进行布局

```python
# 垂直布局
rx.vstack(
    rx.text("标题"),
    rx.text("内容"),
    spacing="3",
)

# 水平布局
rx.hstack(
    rx.text("标签"),
    rx.badge("值"),
    spacing="2",
)
```

**规则 4.2.2**: 使用 color_scheme 实现语义化颜色

```python
# 根据状态动态设置颜色
rx.badge(
    rx.text("HEALTHY"),
    color_scheme=rx.cond(
        State.health_status["status"] == "healthy", "green",
        rx.cond(
            State.health_status["status"] == "degraded", "yellow",
            "red"
        )
    ),
)
```

---

## 5. 数据加载与 API 调用

### 5.1 数据加载器

**强制规则**

**规则 5.1.1**: 所有数据加载必须在 `ui/utils/data_loader.py` 中实现

```python
# ui/utils/data_loader.py
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

def load_health_status() -> dict[str, Any]:
    """加载系统健康状态。"""
    try:
        # 确保 Langfuse 客户端已初始化
        _ensure_langfuse_initialized()
        
        from src.observability.health import get_health_status
        return get_health_status()
    except Exception as e:
        logger.error(f"Failed to load health status: {e}")
        return {"status": "error", "components": {}}
```

**规则 5.1.2**: 必须提供降级数据

```python
def load_metrics() -> dict[str, float]:
    """加载指标数据。"""
    try:
        # ... 正常加载逻辑
        return metrics
    except Exception as e:
        logger.error(f"Failed to load metrics: {e}")
        return {
            "success_rate": 0.0,
            "latency_p95": 0.0,
            "error_rate": 0.0,
        }
```

### 5.2 State 更新

**强制规则**

**规则 5.2.1**: 使用 @rx.event 装饰器定义事件处理

```python
class State(rx.State):
    """Dashboard 状态。"""
    
    health_status: dict[str, Any] = {}
    
    @rx.event
    def load_health(self):
        """加载健康状态。"""
        from ui.utils.data_loader import load_health_status
        self.health_status = load_health_status()
```

**规则 5.2.2**: 异步操作必须使用 async/await

```python
class State(rx.State):
    """Dashboard 状态。"""
    
    @rx.event
    async def load_all_data(self):
        """加载所有数据。"""
        self.is_loading = True
        yield  # 更新 UI 显示加载状态
        
        try:
            # 并行加载
            self.health_status = load_health_status()
            self.metrics = load_metrics()
            self.sessions = load_sessions()
        finally:
            self.is_loading = False
            yield
```

---

## 6. 性能优化与缓存策略

### 6.1 数据缓存

**推荐规则**

**规则 6.1.1**: 频繁调用的 API 必须缓存

```python
# ui/utils/data_loader.py
from functools import lru_cache
from datetime import datetime, timedelta

_cache = {}
_cache_time = {}

def load_health_status() -> dict[str, Any]:
    """加载系统健康状态(带 5 分钟缓存)。"""
    cache_key = "health_status"
    now = datetime.now()
    
    # 检查缓存是否有效(5 分钟)
    if cache_key in _cache and cache_key in _cache_time:
        if now - _cache_time[cache_key] < timedelta(minutes=5):
            return _cache[cache_key]
    
    # 加载新数据
    data = _fetch_health_status()
    _cache[cache_key] = data
    _cache_time[cache_key] = now
    
    return data
```

### 6.2 按需加载

**推荐规则**

**规则 6.2.1**: 大数据集必须分页或按需加载

```python
class State(rx.State):
    """Dashboard 状态。"""
    
    sessions: list[dict[str, Any]] = []
    page: int = 1
    page_size: int = 20
    
    @rx.event
    def load_sessions_page(self):
        """加载当前页的会话。"""
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        self.sessions = load_sessions()[start:end]
    
    @rx.event
    def next_page(self):
        self.page += 1
        self.load_sessions_page()
    
    @rx.event
    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.load_sessions_page()
```

---

## 7. 错误处理与降级策略

### 7.1 异常捕获

**强制规则**

**规则 7.1.1**: 所有数据加载必须捕获异常

```python
def load_health_status() -> dict[str, Any]:
    """加载系统健康状态。"""
    try:
        from src.observability.health import get_health_status
        return get_health_status()
    except Exception as e:
        logger.error(f"Failed to load health status: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().timestamp(),
            "components": {},
            "error": str(e),
        }
```

### 7.2 UI 降级

**强制规则**

**规则 7.1.2**: 数据加载失败时必须显示友好提示

```python
def health_status_card() -> rx.Component:
    """系统健康状态卡片。"""
    return rx.card(
        rx.vstack(
            rx.cond(
                State.health_status["status"] == "error",
                rx.vstack(
                    rx.text("❌ 系统状态加载失败", size="4", weight="bold"),
                    rx.text(
                        State.health_status.get("error", "未知错误"),
                        size="2",
                        color="red",
                    ),
                    rx.button(
                        "重试",
                        on_click=State.load_health,
                        variant="outline",
                    ),
                ),
                # 正常显示健康状态
                rx.text("✅ 系统正常"),
            ),
        ),
    )
```

---

## 8. 代码质量与工程规范

### 8.1 类型注解

**强制规则**

**规则 8.1.1**: 所有公共函数必须有类型注解

```python
from typing import Any

def load_health_status() -> dict[str, Any]:
    """加载系统健康状态。"""
    pass

def _fetch_metrics(session_id: str | None = None) -> list[dict[str, float]]:
    """获取指标数据。"""
    pass
```

### 8.2 文档字符串

**强制规则**

**规则 8.2.1**: 所有公共函数必须有 Google 风格的文档字符串

```python
def load_health_status() -> dict[str, Any]:
    """
    加载系统健康状态。

    Returns:
        健康状态字典,失败时返回降级数据。
    """
    pass
```

### 8.3 代码格式化

**强制规则**

**规则 8.3.1**: 必须使用 black 和 ruff 格式化代码

```bash
# 格式化代码
uv run ruff check --fix ui/
uv run black ui/

# 检查类型
uv run mypy ui/
```

---

## 9. 开发工作流

### 9.1 启动服务

**标准流程**

```bash
# 1. 确保依赖已安装
uv sync

# 2. 启动所有服务
make start-all

# 3. 验证服务状态
make status

# 4. 查看日志
tail -f /tmp/reflex_ui.log
tail -f /tmp/mcp_server.log
```

### 9.2 停止服务

```bash
# 停止所有服务
make stop

# 或手动清理
pkill -9 -f "reflex run|src/server.py"
lsof -ti:3000,8000,8001 | xargs kill -9
```

### 9.3 调试技巧

**规则 9.3.1**: 使用日志排查问题

```python
import logging

logger = logging.getLogger(__name__)

def load_health_status() -> dict[str, Any]:
    """加载系统健康状态。"""
    logger.debug("Loading health status...")
    try:
        # ... 加载逻辑
        logger.info("Health status loaded successfully")
        return status
    except Exception as e:
        logger.error(f"Failed to load health status: {e}")
        raise
```

**规则 9.3.2**: 检查模块是否可用

```bash
# 检查模块是否在虚拟环境中
.venv/bin/python3 -c "import langfuse; print('✅ langfuse 可用')"

# 或使用 uv run
uv run python3 -c "import langfuse; print('✅ langfuse 可用')"
```

---

## 10. 常见问题与解决方案

### 10.1 Reflex 启动超时

**问题**: `make start-all` 显示 "Reflex UI 启动超时"

**原因**: 
1. 缺少依赖模块
2. rxconfig.py 中初始化外部客户端失败
3. Python 路径不正确

**解决方案**:

```bash
# 1. 同步依赖
uv sync

# 2. 检查日志
tail -100 /tmp/reflex_ui.log | grep -E "ModuleNotFoundError|Error"

# 3. 清理端口并重启
lsof -ti:3000,8000 | xargs kill -9
make start-all
```

### 10.2 TypeError: Cannot read properties of undefined

**问题**: 前端报错 `TypeError: Cannot read properties of undefined (reading 'toUpperCase')`

**原因**: State 变量未初始化或访问方式错误

**解决方案**:

```python
# 错误:直接调用 Python 方法
State.health_status["status"].upper()

# 正确:使用 rx.cond 检查 + .to_string() 转换
rx.cond(
    State.health_status["status"],
    State.health_status["status"].to_string().upper(),
    "UNKNOWN"
)
```

### 10.3 模块导入失败

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**原因**: 依赖未在 pyproject.toml 中声明或未执行 uv sync

**解决方案**:

```bash
# 1. 添加到 pyproject.toml
# dependencies = ["xxx>=1.0.0"]

# 2. 同步依赖
uv sync

# 3. 验证安装
.venv/bin/python3 -c "import xxx; print('✅ 可用')"
```

### 10.4 环境变量未加载

**问题**: 服务启动后无法读取 `.env` 文件中的配置

**原因**: 
1. Makefile 未加载 .env
2. Python 入口未调用 load_dotenv()
3. 工作目录不正确

**解决方案**:

```python
# run.py
from dotenv import load_dotenv
from pathlib import Path
import os

def main():
    load_dotenv()  # 在最前面加载
    os.chdir(Path(__file__).parent)  # 切换到项目根目录
    # ... 其他代码
```

---

## 附录:快速参考卡片

### Reflex State 访问规则

```
✅ State.var["key"]              # 字典访问
✅ State.var["key"].to_string()  # 字符串转换
✅ rx.cond(State.var, true, false)  # 条件渲染
❌ State.var.get("key")          # 不支持 .get()
❌ State.var["key"].upper()      # 不支持直接调用 Python 方法
❌ rx.foreach(嵌套字典, ...)     # 不支持嵌套字典迭代
```

### 环境变量加载顺序

```
1. Makefile 加载 .env → export 变量
2. run.py 调用 load_dotenv() → 确保 Python 能读取
3. os.chdir(项目根目录) → pydantic-settings 能找到 .env
4. data_loader.py 懒加载 → Reflex 后端初始化客户端
```

### 依赖管理流程

```
1. 在 pyproject.toml 中声明依赖
2. 执行 uv sync 同步到 .venv
3. 验证 .venv/bin/python3 -c "import 模块"
4. 重启服务使依赖生效
```

### 组件开发检查清单

```
- [ ] State 变量是否声明了类型?
- [ ] 是否使用字典语法访问 State?
- [ ] 是否使用 rx.cond 进行空值检查?
- [ ] 字符串方法是否使用了 .to_string()?
- [ ] 是否避免了嵌套字典 rx.foreach?
- [ ] 数据加载是否捕获了异常?
- [ ] 是否提供了降级数据?
```

---

**维护者**: 平台团队  
**下次更新**: 发现新陷阱或优化模式时  
**反馈渠道**: GitHub Issues 或团队会议