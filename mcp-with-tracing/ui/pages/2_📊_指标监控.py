"""
实时指标监控仪表板

展示 4 个核心指标的趋势图和当前值，支持时间范围选择和自动刷新。
"""

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import load_current_metrics, load_metrics_data
from ui.utils.formatters import format_latency, format_qps

st.set_page_config(
    page_title="指标监控 - MCP Observability",
    page_icon="📊",
    layout="wide",
)

st.title("📊 实时指标监控")
st.markdown("---")

# 控制面板
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    time_range = st.selectbox(
        "时间范围",
        ["1小时", "6小时", "24小时", "7天"],
        index=2,
    )

with col2:
    auto_refresh = st.checkbox("自动刷新", value=True)

with col3:
    if st.button("🔄 手动刷新"):
        st.rerun()

# 时间范围映射
hours_map = {
    "1小时": 1,
    "6小时": 6,
    "24小时": 24,
    "7天": 168,
}
hours = hours_map[time_range]

st.markdown("---")

# 加载当前指标值
st.subheader("当前指标值")
metrics = load_current_metrics()

# 第一行：核心指标
col1, col2, col3, col4 = st.columns(4)

with col1:
    success_rate = metrics.get("success_rate", 0)
    st.metric(
        label="成功率",
        value=f"{success_rate:.2%}",
    )

with col2:
    latency_p95 = metrics.get("latency_p95", 0)
    st.metric(
        label="P95 延迟",
        value=format_latency(latency_p95),
    )

with col3:
    qps = metrics.get("request_rate", 0)
    st.metric(
        label="请求率 (QPS)",
        value=format_qps(qps),
    )

with col4:
    satisfaction = metrics.get("satisfaction")
    if satisfaction is not None:
        st.metric(
            label="用户满意度",
            value=f"{satisfaction:.1f}/5",
        )
    else:
        st.metric(
            label="用户满意度",
            value="N/A",
        )

# 第二行：新增性能指标
st.markdown("### 详细性能指标")
col1, col2, col3, col4 = st.columns(4)

with col1:
    latency_p50 = metrics.get("latency_p50", 0)
    st.metric(
        label="P50 延迟 (中位数)",
        value=format_latency(latency_p50),
    )

with col2:
    latency_p99 = metrics.get("latency_p99", 0)
    st.metric(
        label="P99 延迟 (长尾)",
        value=format_latency(latency_p99),
    )

with col3:
    active_sessions = metrics.get("active_sessions", 0)
    st.metric(
        label="活跃会话数",
        value=f"{active_sessions}",
    )

with col4:
    error_count = metrics.get("error_count", 0)
    st.metric(
        label="错误数",
        value=f"{error_count}",
    )

st.markdown("---")

# 趋势图表
st.subheader("趋势分析")

# 成功率趋势
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 成功率趋势")
    df_success = load_metrics_data("success_rate", hours=hours)

    if df_success is not None and not df_success.empty:
        fig = px.line(
            df_success,
            x="ds",
            y="y",
            title="成功率 (0-1)",
            markers=True,
        )
        fig.update_yaxes(range=[0, 1])
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("暂无成功率数据")

with col2:
    st.markdown("### P95 延迟趋势")
    df_latency = load_metrics_data("latency_p95", hours=hours)

    if df_latency is not None and not df_latency.empty:
        fig = px.line(
            df_latency,
            x="ds",
            y="y",
            title="P95 延迟 (ms)",
            markers=True,
            line_shape="linear",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("暂无延迟数据")

# 请求率和满意度趋势
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 请求率 (QPS) 趋势")
    df_qps = load_metrics_data("request_rate", hours=hours)

    if df_qps is not None and not df_qps.empty:
        fig = px.line(
            df_qps,
            x="ds",
            y="y",
            title="请求率 (requests/second)",
            markers=True,
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("暂无请求率数据")

with col2:
    st.markdown("### 用户满意度趋势")
    df_satisfaction = load_metrics_data("satisfaction", hours=hours)

    if df_satisfaction is not None and not df_satisfaction.empty:
        fig = px.line(
            df_satisfaction,
            x="ds",
            y="y",
            title="平均满意度 (1-5)",
            markers=True,
        )
        fig.update_yaxes(range=[0, 5])
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("暂无满意度数据")

st.markdown("---")

# 错误分类分析
st.subheader("错误分类分析")
error_breakdown = metrics.get("error_breakdown", {})

if error_breakdown:
    col1, col2 = st.columns([2, 1])

    with col1:
        # 柱状图展示错误分类
        import pandas as pd

        error_df = pd.DataFrame([{"错误类型": k, "数量": v} for k, v in error_breakdown.items()])

        fig = px.bar(
            error_df,
            x="错误类型",
            y="数量",
            title="错误类型分布",
            color="数量",
            color_continuous_scale="Reds",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 饼图展示错误占比
        fig = px.pie(
            values=list(error_breakdown.values()),
            names=list(error_breakdown.keys()),
            title="错误占比",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.success("✅ 当前无错误")

st.markdown("---")

# 工具性能监控
st.subheader("工具性能监控")

# 获取工具列表（从指标中推断或手动输入）
tool_names = st.text_input(
    "输入工具名称（逗号分隔）", value="tool_a, tool_b", help="输入要监控的工具名称，用逗号分隔"
)

if tool_names:
    tools = [name.strip() for name in tool_names.split(",") if name.strip()]

    if tools:
        # 加载每个工具的指标
        tool_metrics_list = []
        for tool_name in tools:
            try:
                from src.observability.metrics_collector import MetricsCollector

                collector = MetricsCollector()
                tool_metric = collector.collect_tool_metrics(tool_name)
                tool_metrics_list.append(tool_metric)
            except Exception as e:
                st.warning(f"无法加载工具 {tool_name} 的指标: {e}")

        if tool_metrics_list:
            # 显示工具指标表格
            import pandas as pd

            tool_df = pd.DataFrame(tool_metrics_list)
            tool_df["成功率"] = tool_df["success_rate"].apply(lambda x: f"{x:.2%}")
            tool_df["P50 延迟"] = tool_df["p50_latency_ms"].apply(lambda x: f"{x:.0f}ms")
            tool_df["P95 延迟"] = tool_df["p95_latency_ms"].apply(lambda x: f"{x:.0f}ms")
            tool_df["P99 延迟"] = tool_df["p99_latency_ms"].apply(lambda x: f"{x:.0f}ms")

            display_df = tool_df[
                [
                    "tool_name",
                    "call_count",
                    "成功率",
                    "P50 延迟",
                    "P95 延迟",
                    "P99 延迟",
                    "error_count",
                ]
            ].rename(columns={"tool_name": "工具名称", "call_count": "调用次数", "error_count": "错误数"})

            st.dataframe(display_df, use_container_width=True)

            # 工具调用次数对比图
            fig = px.bar(
                tool_metrics_list,
                x="tool_name",
                y="call_count",
                title="工具调用次数对比",
                color="call_count",
                color_continuous_scale="Blues",
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 数据详情
with st.expander("📋 查看原始数据"):
    st.write("### 成功率数据")
    if df_success is not None and not df_success.empty:
        st.dataframe(df_success, use_container_width=True)
    else:
        st.info("无数据")

    st.write("### P95 延迟数据")
    if df_latency is not None and not df_latency.empty:
        st.dataframe(df_latency, use_container_width=True)
    else:
        st.info("无数据")

st.markdown("---")
st.caption(f"数据时间范围: {time_range} | " f"数据源: Langfuse API (TTL 缓存) | " f"刷新间隔: 60s")
