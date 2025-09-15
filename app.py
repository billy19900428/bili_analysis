#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
B站 AI 工作流分析平台 – Streamlit 前端
author: your_name
"""

import streamlit as st
import subprocess
import os
import time
from datetime import datetime
import pandas as pd
import base64

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))  # 退到根目录
os.chdir(ROOT)                      # 把当前工作目录固定到根目录

# ---------- 页面基础配置 ----------
st.set_page_config(
    page_title="B站内容分析工作流",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- 全局 CSS+JS 动效 ----------
st.markdown(
    """
    <style>
    /* 背景渐变 */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
    }
    /* 卡片 */
    div.stButton > button:first-child {
        background: #fff;
        color: #764ba2;
        border: none;
        padding: 0.55rem 1.5rem;
        border-radius: 30px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,.2);
    }
    /* 输入框 */
    .stTextInput > div > div > input {
        border-radius: 30px;
        padding-left: 1.2rem;
    }
    /* 表格 */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
    /* 标题 */
    h1, h2, h3 {
        font-family: 'Segoe UI', sans-serif;
        letter-spacing: 1px;
    }
    </style>

    <script>
    // 打字机动效
    document.addEventListener("DOMContentLoaded", function() {
        const target = document.querySelector("h1");
        if (target) {
            const txt = target.innerText;
            target.innerText = "";
            let i = 0;
            const speed = 90;
            function typeWriter() {
                if (i < txt.length) {
                    target.innerHTML += txt.charAt(i);
                    i++;
                    setTimeout(typeWriter, speed);
                }
            }
            typeWriter();
        }
    });
    </script>
    """,
    unsafe_allow_html=True
)

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("⚙️ 控制面板")
    keyword = st.text_input("请输入搜索关键词：", placeholder="例：AI 工作流")
    deep_btn = st.button("开始深度分析")
    st.markdown("---")
    st.caption("Powered by CrewAI + Streamlit")

# ---------- 主区域 ----------
st.markdown(
    "<h1 style='text-align: center; margin-top: -30px;'>AI 工作流 - B站 内容分析</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; opacity: .8;'>输入关键词，一键生成数据报告与竞品洞察</p>",
    unsafe_allow_html=True
)


# 调用后端逻辑
from .crew import run_crew          # ① 导入函数

if deep_btn:
    if not keyword or keyword.strip() == "":
        st.warning("请先输入关键词！")
        st.stop()

    with st.spinner("🚀 正在抓取 & 分析中，请稍候..."):
        try:
            run_crew(keyword.strip())          # ② 直接跑
        except Exception as e:
            st.error(f"分析过程出错：{e}")
            st.stop()

    # 读取生成的报告
    report1_path = "report1.md"
    report2_path = "report2.md"
    pdf_path = "b站洞察报告.pdf"

    # 展示
    tab1, tab2, tab3 = st.tabs(["📄 报告预览", "📋 数据明细", "⬇️ 下载 PDF"])
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 综合报告")
            if os.path.exists(report1_path):
                with open(report1_path, encoding="utf-8") as f:
                    st.markdown(f.read())
        with col2:
            st.subheader("🎯 竞品洞察")
            if os.path.exists(report2_path):
                with open(report2_path, encoding="utf-8") as f:
                    st.markdown(f.read())
    with tab2:
        st.subheader("📋 明细数据")
        for csv in ["b站列表数据.csv", "b站详情数据.csv", "b站弹幕数据.csv"]:
            if os.path.exists(csv):
                st.markdown(f"**{csv}**")
                st.dataframe(pd.read_csv(csv))
    with tab3:
        st.subheader("⬇️ 下载报告（Markdown）")
        for md_file in ["report1.md", "report2.md"]:
            if os.path.exists(md_file):
                with open(md_file, "r", encoding="utf-8") as f:
                    b64 = base64.b64encode(f.read().encode()).decode()
                    href = f'<a href="data:text/markdown;base64,{b64}" download="{md_file}">点击下载 {md_file}</a>'
                    st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning(f"{md_file} 还未生成")

# ---------- 页脚 ----------
st.markdown(
    """
    <div style='text-align: center; opacity: .6; margin-top: 4rem;'>
    Made with ❤️ by <a href='https://github.com/yourname' style='color: #fff;'>AI提效局</a>
    </div>
    """,
    unsafe_allow_html=True
)