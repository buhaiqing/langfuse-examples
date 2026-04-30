"""
反馈分析面板

实现反馈统计、评分分布、反馈类型饼图和反馈列表。
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import load_all_feedback, load_feedback_statistics
from ui.utils.formatters import format_timestamp

st.set_page_config(
    page_title="反馈分析 - MCP Observability",
    page_icon="💬",
    layout="wide",
)

st.title("💬 用户反馈分析")
st.markdown("---")

# 加载反馈统计
stats = load_feedback_statistics()

# 核心指标卡片
st.subheader("📊 核心指标")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "总反馈数",
        stats.get("total_feedback", 0),
    )

with col2:
    st.metric(
        "接受率",
        f"{stats.get('acceptance_rate', 0):.1f}%",
    )

with col3:
    avg_rating = stats.get("average_rating")
    if avg_rating is not None:
        st.metric(
            "平均评分",
            f"{avg_rating:.1f}/5",
        )
    else:
        st.metric(
            "平均评分",
            "N/A",
        )

with col4:
    st.metric(
        "评论数",
        stats.get("comments_count", 0),
    )

st.markdown("---")

# 图表分析
st.subheader("📈 反馈分析")

col1, col2 = st.columns(2)

# 评分分布柱状图
with col1:
    st.markdown("### 评分分布")

    rating_distribution = stats.get("rating_distribution", {})

    if rating_distribution:
        # 转换为 DataFrame
        df_ratings = pd.DataFrame([
            {"评分": int(k), "数量": v}
            for k, v in rating_distribution.items()
        ])
        df_ratings = df_ratings.sort_values("评分")

        fig = px.bar(
            df_ratings,
            x="评分",
            y="数量",
            title="评分分布 (1-5 星)",
            color="数量",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无评分数据")

# 反馈类型饼图
with col2:
    st.markdown("### 反馈类型分布")

    accepts = stats.get("accepts", 0)
    rejects = stats.get("rejects", 0)
    ratings = stats.get("ratings_count", 0)
    comments = stats.get("comments_count", 0)

    total = accepts + rejects + ratings + comments

    if total > 0:
        df_types = pd.DataFrame({
            "类型": ["接受", "拒绝", "评分", "评论"],
            "数量": [accepts, rejects, ratings, comments],
        })

        fig = px.pie(
            df_types,
            values="数量",
            names="类型",
            title="反馈类型分布",
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无反馈数据")

st.markdown("---")

# 接受率趋势（如果有历史数据）
if accepts + rejects > 0:
    st.subheader("📉 接受/拒绝对比")

    df_comparison = pd.DataFrame({
        "类型": ["接受", "拒绝"],
        "数量": [accepts, rejects],
    })

    fig = px.bar(
        df_comparison,
        x="类型",
        y="数量",
        title="接受 vs 拒绝",
        color="类型",
        color_discrete_map={"接受": "#00C853", "拒绝": "#FF1744"},
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 最新反馈列表
st.subheader("📝 最新反馈")

# 筛选器
col1, col2 = st.columns(2)

with col1:
    feedback_type_filter = st.selectbox(
        "按类型筛选",
        ["全部", "accept", "reject", "rating", "comment"],
        index=0,
    )

with col2:
    show_count = st.slider("显示数量", 10, 100, 20, step=10)

# 加载反馈数据
all_feedback = load_all_feedback()

if all_feedback:
    # 应用筛选
    if feedback_type_filter != "全部":
        all_feedback = [f for f in all_feedback if f["feedback_type"] == feedback_type_filter]

    if all_feedback:
        # 按时间倒序
        all_feedback = sorted(
            all_feedback,
            key=lambda x: x["created_at"],
            reverse=True,
        )

        # 限制显示数量
        all_feedback = all_feedback[:show_count]

        # 转换为 DataFrame
        df_feedback = pd.DataFrame(all_feedback)
        df_feedback["created_at"] = df_feedback["created_at"].apply(format_timestamp)
        df_feedback["feedback_type"] = df_feedback["feedback_type"].map({
            "accept": "✅ 接受",
            "reject": "❌ 拒绝",
            "rating": "⭐ 评分",
            "comment": "💬 评论",
        })

        df_feedback = df_feedback.rename(columns={
            "created_at": "时间",
            "trace_id": "Trace ID",
            "feedback_type": "类型",
            "value": "值",
            "comment": "评论",
            "user_id": "用户 ID",
        })

        st.dataframe(
            df_feedback[["时间", "类型", "值", "评论", "Trace ID", "用户 ID"]],
            use_container_width=True,
            hide_index=True,
        )

        st.caption(f"显示 {len(df_feedback)} 条反馈（共 {len(all_feedback)} 条）")
    else:
        st.info("ℹ️ 暂无符合筛选条件的反馈")
else:
    st.info("✅ 暂无反馈数据")

st.markdown("---")
st.caption("数据源: FeedbackCollector | 实时更新")
