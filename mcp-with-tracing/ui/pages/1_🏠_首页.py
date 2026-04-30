"""
首页 - 系统总览

展示系统健康状态、组件状态卡片、快速指标概览和最近告警。
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import (
    load_current_metrics,
    load_health_status,
    load_triggered_alerts,
)
from ui.utils.formatters import (
    format_latency,
    format_qps,
    format_severity,
    format_status,
    format_timestamp,
)

st.set_page_config(
    page_title="系统总览 - MCP Observability",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 系统总览")
st.markdown("---")

# 加载健康状态
health = load_health_status()

# 整体状态徽章
status_text = health.get("status", "unknown")
st.markdown(
    f"### 系统状态: <span class='status-{status_text}'>{format_status(status_text)}</span>",
    unsafe_allow_html=True,
)

# 运行时长
uptime = health.get("uptime_seconds", 0)
if uptime > 0:
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    seconds = int(uptime % 60)
    st.caption(f"⏱️ 运行时长: {hours}h {minutes}m {seconds}s")

st.markdown("---")

# 组件状态卡片
st.subheader("📦 组件状态")

components = health.get("components", {})

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    langfuse_status = components.get("langfuse", {})
    st.metric(
        label="Langfuse",
        value=format_status(langfuse_status.get("status", "unknown")),
    )

with col2:
    alert_mgr = components.get("alert_manager", {})
    st.metric(
        label="告警管理器",
        value=f"{alert_mgr.get('rules_loaded', 0)} 条规则",
    )

with col3:
    alert_monitor = components.get("alert_monitor", {})
    st.metric(
        label="告警监控",
        value=format_status(alert_monitor.get("status", "unknown")),
    )

with col4:
    smart_alert = components.get("smart_alert_manager", {})
    st.metric(
        label="智能告警",
        value=format_status(smart_alert.get("status", "unknown")),
    )

with col5:
    metrics_cache = components.get("metrics_cache", {})
    hit_rate = metrics_cache.get("hit_rate", 0)
    st.metric(
        label="缓存命中率",
        value=f"{hit_rate:.1%}",
    )

st.markdown("---")

# 快速指标概览
st.subheader("📊 快速指标")

metrics = load_current_metrics()

col1, col2, col3, col4 = st.columns(4)

with col1:
    success_rate = metrics.get("success_rate", 0)
    st.metric(
        label="成功率",
        value=f"{success_rate:.2%}",
        delta=None,
    )

with col2:
    latency = metrics.get("latency_p95", 0)
    st.metric(
        label="P95 延迟",
        value=format_latency(latency),
        delta=None,
    )

with col3:
    qps = metrics.get("request_rate", 0)
    st.metric(
        label="请求率",
        value=format_qps(qps),
        delta=None,
    )

with col4:
    satisfaction = metrics.get("satisfaction")
    if satisfaction is not None:
        st.metric(
            label="用户满意度",
            value=f"{satisfaction:.1f}/5",
            delta=None,
        )
    else:
        st.metric(
            label="用户满意度",
            value="N/A",
        )

st.markdown("---")

# 最近告警
st.subheader("🚨 最近告警")

recent_alerts = load_triggered_alerts(limit=5)

if recent_alerts:
    # 转换为 DataFrame
    df_alerts = pd.DataFrame(recent_alerts)
    df_alerts["triggered_at"] = df_alerts["triggered_at"].apply(format_timestamp)
    df_alerts["severity"] = df_alerts["severity"].apply(format_severity)

    # 重命名列
    df_alerts = df_alerts.rename(columns={
        "triggered_at": "时间",
        "rule_name": "规则",
        "metric": "指标",
        "value": "当前值",
        "threshold": "阈值",
        "severity": "严重性",
        "message": "消息",
    })

    # 显示表格
    st.dataframe(
        df_alerts[["时间", "规则", "严重性", "当前值", "阈值", "消息"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("✅ 暂无触发的告警")

st.markdown("---")
st.caption("最后更新: 实时数据 | 数据源: Langfuse API + 本地缓存")
