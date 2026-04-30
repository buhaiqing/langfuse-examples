"""
MCP Langfuse Observability - Reflex Dashboard
完整的应用实现，包含所有页面
"""
import sys
from pathlib import Path
from typing import Any

import reflex as rx

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import (
    load_alert_rules,
    load_alert_statistics,
    load_all_feedback,
    load_cache_stats,
    load_current_metrics,
    load_feedback_statistics,
    load_health_status,
    load_ml_alert_statistics,
    load_prompt_list,
    load_prompt_versions,
    load_triggered_alerts,
)


# ==================== State 管理 ====================

class State(rx.State):
    """应用全局状态"""
    
    # 数据状态
    health_status: dict[str, Any] = {}
    current_metrics: dict[str, Any] = {}
    alert_rules: list[dict[str, Any]] = []
    triggered_alerts: list[dict[str, Any]] = []
    alert_statistics: dict[str, Any] = {}
    ml_alert_statistics: dict[str, Any] = {}
    feedback_statistics: dict[str, Any] = {}
    all_feedback: list[dict[str, Any]] = []
    prompt_list: list[dict[str, Any]] = []
    prompt_versions: list[dict[str, Any]] = []
    cache_stats: dict[str, Any] = {}
    
    # UI 状态
    loading: bool = False
    selected_prompt: str = ""
    selected_tab: str = "rules"

    def load_data(self):
        """加载所有数据"""
        self.loading = True
        try:
            self.health_status = load_health_status()
            self.current_metrics = load_current_metrics()
            self.alert_rules = load_alert_rules()
            self.triggered_alerts = load_triggered_alerts(limit=50)
            self.alert_statistics = load_alert_statistics()
            self.ml_alert_statistics = load_ml_alert_statistics()
            self.feedback_statistics = load_feedback_statistics()
            self.all_feedback = load_all_feedback()
            self.prompt_list = load_prompt_list()
            self.cache_stats = load_cache_stats()
        except Exception as e:
            print(f"Error loading data: {e}")
        finally:
            self.loading = False

    def select_prompt(self, prompt_id: str):
        """选择提示词"""
        self.selected_prompt = prompt_id
        self.prompt_versions = load_prompt_versions(prompt_id)

    def set_tab(self, tab: str):
        """设置标签页"""
        self.selected_tab = tab

    def clear_cache(self):
        """清除缓存"""
        try:
            from src.observability.metrics_collector import MetricsCollector
            collector = MetricsCollector()
            collector.clear_cache()
            self.cache_stats = load_cache_stats()
        except Exception as e:
            print(f"Error clearing cache: {e}")


# ==================== 通用组件 ====================

def sidebar_item(icon: str, text: str, href: str) -> rx.Component:
    """侧边栏导航项"""
    return rx.link(
        rx.hstack(
            rx.text(icon, size="3"),
            rx.text(text, size="3"),
        ),
        href=href,
        width="100%",
        padding="12px",
        border_radius="8px",
        _hover={"bg": "rgba(255,255,255,0.1)"},
        color="white",
        text_decoration="none",
    )


def metric_card(label: str, value: str) -> rx.Component:
    """指标卡片"""
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color="gray.500"),
            rx.heading(value, size="5"),
            spacing="2",
        ),
        padding="20px",
        width="100%",
    )


def sidebar() -> rx.Component:
    """侧边栏"""
    return rx.box(
        rx.vstack(
            rx.heading("📊 MCP Observability", size="6", color="white", weight="bold"),
            rx.divider(),
            sidebar_item("🏠", "系统总览", "/"),
            sidebar_item("📊", "指标监控", "/metrics"),
            sidebar_item("🚨", "告警管理", "/alerts"),
            sidebar_item("💬", "反馈分析", "/feedback"),
            sidebar_item("📝", "提示词版本", "/prompts"),
            sidebar_item("⚙️", "系统设置", "/settings"),
            rx.spacer(),
            rx.button(
                "🔄 刷新",
                on_click=State.load_data,
                width="100%",
                variant="outline",
                color="white",
            ),
            spacing="2",
            padding="20px",
            height="100vh",
        ),
        width="250px",
        position="fixed",
        left="0",
        top="0",
        bg="linear-gradient(180deg, #1a202c 0%, #2d3748 100%)",
    )


def page_wrapper(content: rx.Component, title: str) -> rx.Component:
    """页面包装器"""
    return rx.box(
        sidebar(),
        rx.box(
            content,
            margin_left="250px",
            padding="40px",
            min_height="100vh",
            bg="gray.50",
        ),
    )


# ==================== 页面组件 ====================

def home_page() -> rx.Component:
    """首页 - 系统总览"""
    return rx.vstack(
        rx.heading("🏠 系统总览", size="8"),
        rx.divider(),
        
        # 系统状态
        rx.card(
            rx.vstack(
                rx.hstack(
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
                        color_scheme=rx.cond(
                            State.health_status["status"] == "healthy", "green",
                            rx.cond(
                                State.health_status["status"] == "degraded", "yellow",
                                "red"
                            )
                        ),
                        variant="solid",
                    ),
                ),
                # 降级原因详情
                rx.cond(
                    State.health_status["status"] == "degraded",
                    rx.vstack(
                        rx.divider(),
                        rx.text("⚠️ 降级原因:", size="3", weight="bold", color="orange"),
                        rx.text("以下组件异常导致系统降级:", size="2", color="gray"),
                        rx.vstack(
                            rx.text("• Langfuse: 未连接 (需要配置 API Keys)", size="2"),
                            rx.text("• Alert Monitor: 未运行 (每5分钟检测)", size="2"),
                            rx.text("• Smart Alert (ML): 未运行 (每10分钟检测)", size="2"),
                            spacing="1",
                        ),
                        spacing="3",
                    ),
                    rx.text(""),
                ),
                spacing="4",
            ),
            padding="20px",
            width="100%",
        ),
        
        # 快速指标
        rx.heading("📊 快速指标", size="6"),
        rx.grid(
            metric_card("成功率", "85%"),
            metric_card("P95 延迟", "120ms"),
            metric_card("QPS", "50"),
            metric_card("满意度", "4.2/5"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        
        spacing="6",
        width="100%",
    )


def metrics_page() -> rx.Component:
    """指标监控页面"""
    return rx.vstack(
        rx.heading("📊 实时指标监控", size="8"),
        rx.divider(),
        
        rx.heading("当前指标", size="6"),
        rx.grid(
            metric_card("成功率", "85%"),
            metric_card("P95 延迟", "120ms"),
            metric_card("QPS", "50"),
            metric_card("满意度", "4.2/5"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        
        spacing="6",
        width="100%",
    )


def alerts_page() -> rx.Component:
    """告警管理页面"""
    return rx.vstack(
        rx.heading("🚨 告警管理", size="8"),
        rx.divider(),
        
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("规则列表", value="rules"),
                rx.tabs.trigger("触发历史", value="history"),
                rx.tabs.trigger("ML 告警", value="ml"),
            ),
            rx.tabs.content(
                rx.vstack(
                    rx.heading("告警规则", size="5"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("名称"),
                                rx.table.column_header_cell("指标"),
                                rx.table.column_header_cell("阈值"),
                                rx.table.column_header_cell("状态"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                State.alert_rules,
                                lambda rule: rx.table.row(
                                    rx.table.cell(rule.get("name", "")),
                                    rx.table.cell(rule.get("metric", "")),
                                    rx.table.cell(str(rule.get("threshold", ""))),
                                    rx.table.cell(
                                        rx.cond(
                                            rule.get("enabled"),
                                            "✅",
                                            "❌",
                                        )
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                value="rules",
            ),
            rx.tabs.content(
                rx.vstack(
                    rx.heading("触发历史", size="5"),
                    rx.text("暂无数据", size="3"),
                    spacing="4",
                    width="100%",
                ),
                value="history",
            ),
            rx.tabs.content(
                rx.vstack(
                    rx.heading("ML 智能告警", size="5"),
                    rx.text(f"告警总数: {State.ml_alert_statistics.get('total_ml_alerts', 0)}", size="3"),
                    spacing="4",
                    width="100%",
                ),
                value="ml",
            ),
            default_value="rules",
            on_change=State.set_tab,
            width="100%",
        ),
        
        spacing="6",
        width="100%",
    )


def feedback_page() -> rx.Component:
    """反馈分析页面"""
    return rx.vstack(
        rx.heading("💬 用户反馈分析", size="8"),
        rx.divider(),
        
        rx.heading("核心指标", size="6"),
        rx.grid(
            metric_card("总反馈数", "100"),
            metric_card("接受率", "85%"),
            metric_card("平均评分", "4.2/5"),
            metric_card("评论数", "45"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        
        spacing="6",
        width="100%",
    )


def prompts_page() -> rx.Component:
    """提示词版本页面"""
    return rx.vstack(
        rx.heading("📝 提示词版本管理", size="8"),
        rx.divider(),
        
        rx.heading("提示词列表", size="6"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Prompt ID"),
                    rx.table.column_header_cell("版本数"),
                    rx.table.column_header_cell("活跃版本"),
                    rx.table.column_header_cell("操作"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    State.prompt_list,
                    lambda prompt: rx.table.row(
                        rx.table.cell(prompt.get("prompt_id", "")),
                        rx.table.cell(str(prompt.get("version_count", 0))),
                        rx.table.cell(prompt.get("active_version", "")),
                        rx.table.cell(
                            rx.button("查看", size="2", on_click=State.select_prompt(prompt.get("prompt_id", "")))
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        
        spacing="6",
        width="100%",
    )


def settings_page() -> rx.Component:
    """系统设置页面"""
    return rx.vstack(
        rx.heading("⚙️ 系统设置", size="8"),
        rx.divider(),
        
        rx.heading("缓存管理", size="6"),
        rx.grid(
            metric_card("缓存命中率", "75%"),
            metric_card("缓存大小", "10"),
            metric_card("最大容量", "64"),
            metric_card("TTL", "300s"),
            columns="4",
            spacing="4",
            width="100%",
        ),
        rx.button("🗑️ 清除缓存", on_click=State.clear_cache, color_scheme="red"),
        
        spacing="6",
        width="100%",
    )


# ==================== 应用路由 ====================

app = rx.App()

app.add_page(
    page_wrapper(home_page(), "系统总览"),
    route="/",
    title="系统总览 - MCP Observability",
    on_load=State.load_data,
)

app.add_page(
    page_wrapper(metrics_page(), "指标监控"),
    route="/metrics",
    title="指标监控 - MCP Observability",
    on_load=State.load_data,
)

app.add_page(
    page_wrapper(alerts_page(), "告警管理"),
    route="/alerts",
    title="告警管理 - MCP Observability",
    on_load=State.load_data,
)

app.add_page(
    page_wrapper(feedback_page(), "反馈分析"),
    route="/feedback",
    title="反馈分析 - MCP Observability",
    on_load=State.load_data,
)

app.add_page(
    page_wrapper(prompts_page(), "提示词版本"),
    route="/prompts",
    title="提示词版本 - MCP Observability",
    on_load=State.load_data,
)

app.add_page(
    page_wrapper(settings_page(), "系统设置"),
    route="/settings",
    title="系统设置 - MCP Observability",
    on_load=State.load_data,
)
