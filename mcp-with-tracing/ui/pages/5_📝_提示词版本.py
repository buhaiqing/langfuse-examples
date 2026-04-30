"""
提示词版本管理

实现提示词列表、版本详情、注册新版本功能。
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ui.utils.data_loader import load_prompt_list, load_prompt_versions
from ui.utils.formatters import format_timestamp

st.set_page_config(
    page_title="提示词版本 - MCP Observability",
    page_icon="📝",
    layout="wide",
)

st.title("📝 提示词版本管理")
st.markdown("---")

# 加载提示词列表
prompts = load_prompt_list()

if prompts:
    # 提示词列表
    st.subheader("📋 提示词列表")

    df_prompts = pd.DataFrame(prompts)
    df_prompts["ab_test_enabled"] = df_prompts["ab_test_enabled"].apply(
        lambda x: "✅ 是" if x else "❌ 否"
    )

    df_prompts = df_prompts.rename(columns={
        "prompt_id": "Prompt ID",
        "version_count": "版本数",
        "ab_test_enabled": "A/B 测试",
        "active_version": "活跃版本",
    })

    st.dataframe(
        df_prompts[["Prompt ID", "版本数", "A/B 测试", "活跃版本"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # 选择提示词查看详情
    selected_prompt = st.selectbox(
        "选择提示词查看详情",
        [p["prompt_id"] for p in prompts],
    )

    if selected_prompt:
        st.subheader(f"📖 {selected_prompt} 版本详情")

        versions = load_prompt_versions(selected_prompt)

        if versions:
            df_versions = pd.DataFrame(versions)
            df_versions["created_at"] = df_versions["created_at"].apply(format_timestamp)
            df_versions["description"] = df_versions["description"].fillna("无描述")

            df_versions = df_versions.rename(columns={
                "version": "版本",
                "description": "描述",
                "created_at": "创建时间",
                "metadata": "元数据",
            })

            st.dataframe(
                df_versions[["版本", "描述", "创建时间"]],
                use_container_width=True,
                hide_index=True,
            )

            # 元数据展开
            with st.expander("📋 查看元数据详情"):
                for v in versions:
                    st.write(f"**{v['version']}**: {v.get('metadata', {})}")
        else:
            st.warning("暂无版本数据")

        st.markdown("---")

        # 注册新版本
        st.subheader("➕ 注册新版本")

        with st.form("new_version_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_version = st.text_input(
                    "版本号",
                    placeholder="例如: v3.0",
                )
                description = st.text_area(
                    "版本描述",
                    placeholder="描述此版本的变更...",
                )

            with col2:
                metadata_json = st.text_area(
                    "元数据 (JSON)",
                    placeholder='{"author": "your_name", "changes": "优化了..."}',
                    help="可选，JSON 格式的元数据",
                )

                set_active = st.checkbox("设为活跃版本", value=True)

            submitted = st.form_submit_button("注册版本")

            if submitted:
                if not new_version:
                    st.error("❌ 版本号不能为空")
                else:
                    try:
                        import json

                        from src.observability.prompt_versioning import (
                            get_prompt_version_manager,
                            set_active_prompt_version,
                        )

                        # 解析元数据
                        metadata = {}
                        if metadata_json:
                            try:
                                metadata = json.loads(metadata_json)
                            except json.JSONDecodeError:
                                st.error("❌ 元数据 JSON 格式错误")
                                st.stop()

                        # 注册版本
                        manager = get_prompt_version_manager()
                        manager.register_version(
                            prompt_id=selected_prompt,
                            version=new_version,
                            description=description if description else None,
                            metadata=metadata if metadata else None,
                        )

                        # 设为活跃版本
                        if set_active:
                            set_active_prompt_version(selected_prompt, new_version)

                        st.success(f"✅ 版本 '{new_version}' 注册成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 注册版本失败: {e}")

else:
    st.warning("⚠️ 暂无注册的提示词")

st.markdown("---")
st.caption("数据源: PromptVersionManager | 支持 A/B 测试")
