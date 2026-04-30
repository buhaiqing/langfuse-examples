"""
告警管理面板

实现告警规则列表、触发历史、ML 告警统计和新建规则表单。
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import (
    load_alert_rules,
    load_alert_statistics,
    load_ml_alert_statistics,
    load_triggered_alerts,
)
from ui.utils.formatters import format_severity, format_timestamp

st.set_page_config(
    page_title="告警管理 - MCP Observability",
    page_icon="🚨",
    layout="wide",
)

st.title("🚨 告警管理")
st.markdown("---")

# Tab 切换
tab_rules, tab_history, tab_ml, tab_stats = st.tabs([
    "📋 规则列表",
    "📜 触发历史",
    "🤖 ML 告警",
    "📊 统计分析"
])

# ==================== Tab 1: 规则列表 ====================
with tab_rules:
    st.subheader("告警规则")

    rules = load_alert_rules()

    if rules:
        df_rules = pd.DataFrame(rules)
        df_rules["severity"] = df_rules["severity"].apply(format_severity)
        df_rules["enabled"] = df_rules["enabled"].apply(lambda x: "✅ 启用" if x else "❌ 禁用")

        df_rules = df_rules.rename(columns={
            "name": "名称",
            "metric": "指标",
            "threshold": "阈值",
            "operator": "操作符",
            "severity": "严重性",
            "window_minutes": "窗口 (分钟)",
            "enabled": "状态",
        })

        st.dataframe(
            df_rules[["名称", "指标", "阈值", "操作符", "严重性", "窗口 (分钟)", "状态"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("⚠️ 暂无告警规则，请使用下方表单创建")

    st.markdown("---")

    # 新建规则表单
    st.subheader("➕ 新建告警规则")

    with st.form("new_rule_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            rule_name = st.text_input("规则名称", placeholder="例如: success-rate-low")
            metric = st.selectbox(
                "监控指标",
                ["success_rate", "latency_p95_ms", "error_rate", "avg_rating"],
            )

        with col2:
            threshold = st.number_input("阈值", value=0.95, step=0.01, format="%.2f")
            operator = st.selectbox(
                "操作符",
                ["gt", "lt", "gte", "lte", "eq"],
                help="gt: 大于, lt: 小于, gte: 大于等于, lte: 小于等于, eq: 等于",
            )

        with col3:
            severity = st.selectbox(
                "严重性",
                ["info", "warning", "critical"],
            )
            window_minutes = st.number_input("时间窗口 (分钟)", value=60, min_value=5, step=5)
            enabled = st.checkbox("启用", value=True)

        submitted = st.form_submit_button("创建规则")

        if submitted:
            if not rule_name:
                st.error("❌ 规则名称不能为空")
            else:
                try:
                    from src.observability.alerting import (
                        AlertRule,
                        AlertSeverity,
                        get_alert_manager,
                    )

                    manager = get_alert_manager()
                    new_rule = AlertRule(
                        name=rule_name,
                        metric=metric,
                        threshold=threshold,
                        operator=operator,
                        severity=AlertSeverity(severity),
                        window_minutes=window_minutes,
                        enabled=enabled,
                    )
                    manager.register_rule(new_rule)

                    st.success(f"✅ 规则 '{rule_name}' 创建成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 创建规则失败: {e}")

# ==================== Tab 2: 触发历史 ====================
with tab_history:
    st.subheader("已触发告警历史")

    # 筛选器
    col1, col2 = st.columns(2)
    with col1:
        severity_filter = st.selectbox(
            "按严重性筛选",
            ["全部", "info", "warning", "critical"],
            index=0,
        )

    alerts = load_triggered_alerts(limit=100)

    if alerts:
        # 应用筛选
        if severity_filter != "全部":
            alerts = [a for a in alerts if a["severity"] == severity_filter]

        if alerts:
            df_alerts = pd.DataFrame(alerts)
            df_alerts["triggered_at"] = df_alerts["triggered_at"].apply(format_timestamp)
            df_alerts["severity"] = df_alerts["severity"].apply(format_severity)

            df_alerts = df_alerts.rename(columns={
                "triggered_at": "时间",
                "rule_name": "规则",
                "metric": "指标",
                "value": "当前值",
                "threshold": "阈值",
                "severity": "严重性",
                "message": "消息",
            })

            st.dataframe(
                df_alerts[["时间", "规则", "严重性", "指标", "当前值", "阈值", "消息"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("ℹ️ 暂无符合筛选条件的告警")
    else:
        st.info("✅ 暂无触发的告警")

# ==================== Tab 3: ML 告警 ====================
with tab_ml:
    st.subheader("🤖 ML 智能告警统计")

    ml_stats = load_ml_alert_statistics()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "ML 告警总数",
            ml_stats.get("total_ml_alerts", 0),
        )

    with col2:
        last_detection = ml_stats.get("last_detection")
        if last_detection:
            st.metric(
                "最后检测时间",
                format_timestamp(last_detection),
            )
        else:
            st.metric("最后检测时间", "N/A")

    with col3:
        st.metric(
            "检测间隔",
            "10 分钟",
        )

    st.markdown("---")

    # 按类型分布
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 按异常类型分布")
        by_type = ml_stats.get("by_type", {})
        if by_type:
            df_type = pd.DataFrame(
                [{"类型": k, "数量": v} for k, v in by_type.items()]
            )
            st.dataframe(df_type, use_container_width=True, hide_index=True)
        else:
            st.info("暂无 ML 告警数据")

    with col2:
        st.markdown("### 按指标分布")
        by_metric = ml_stats.get("by_metric", {})
        if by_metric:
            df_metric = pd.DataFrame(
                [{"指标": k, "数量": v} for k, v in by_metric.items()]
            )
            st.dataframe(df_metric, use_container_width=True, hide_index=True)
        else:
            st.info("暂无 ML 告警数据")

# ==================== Tab 4: 统计分析 ====================
with tab_stats:
    st.subheader("📊 告警统计分析")

    stats = load_alert_statistics()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "总告警数",
            stats.get("total_alerts", 0),
        )

    with col2:
        by_severity = stats.get("by_severity", {})
        if by_severity:
            severity_text = ", ".join([f"{k}: {v}" for k, v in by_severity.items()])
            st.write(f"**按严重性**: {severity_text}")
        else:
            st.write("**按严重性**: 无数据")

    with col3:
        by_rule = stats.get("by_rule", {})
        if by_rule:
            st.write(f"**告警规则数**: {len(by_rule)}")
        else:
            st.write("**告警规则数**: 0")

    st.markdown("---")

    # 详细分布
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 按严重性分布")
        if by_severity:
            df_severity = pd.DataFrame(
                [{"严重性": format_severity(k), "数量": v} for k, v in by_severity.items()]
            )
            st.dataframe(df_severity, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据")

    with col2:
        st.markdown("### 按规则分布")
        if by_rule:
            df_rule = pd.DataFrame(
                [{"规则": k, "数量": v} for k, v in by_rule.items()]
            )
            st.dataframe(df_rule, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据")

st.markdown("---")
st.caption("数据源: AlertManager + SmartAlertManager | 实时更新")
