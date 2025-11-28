import streamlit as st
import json
import random

# 页面配置
st.set_page_config(page_title="消防刷题神器", layout="centered")

# 读取题库函数
@st.cache_data
def load_data():
    try:
        with open('tiku_data_all.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

data = load_data()

if not data:
    st.error("❌ 找不到题库文件 tiku_data_all.json，请检查是否上传到 GitHub！")
    st.stop()

st.title(f"🔥 消防题库 (共 {len(data)} 题)")

# 初始化 session_state
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'show_answer' not in st.session_state:
    st.session_state.show_answer = False
if 'mode' not in st.session_state:
    st.session_state.mode = '顺序' # 默认顺序模式

# 侧边栏设置
with st.sidebar:
    st.header("设置")
    mode = st.radio("刷题模式", ["顺序刷题", "随机抽题"])
    if mode != st.session_state.mode:
        st.session_state.mode = mode
        st.rerun()
    
    # 跳转功能
    if st.session_state.mode == "顺序刷题":
        jump_to = st.number_input("跳转到第几题", min_value=1, max_value=len(data), value=st.session_state.current_index + 1)
        if st.button("跳转"):
            st.session_state.current_index = jump_to - 1
            st.session_state.show_answer = False
            st.rerun()

# 获取当前题目
q = data[st.session_state.current_index]

# --- 显示题目区域 ---
st.markdown(f"### 第 {st.session_state.current_index + 1} 题")

# 题目类型标签
q_type = "单选" if q.get('type') == 1 else "多选/判断"
st.caption(f"[{q_type}] 来源试卷ID: {q.get('from_paper_id')}")

# 题目内容
st.info(q['content'])

# 显示选项
if q.get('options'):
    for opt in q['options']:
        st.write(opt)

# --- 按钮区域 ---
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("⬅️ 上一题"):
        if st.session_state.current_index > 0:
            st.session_state.current_index -= 1
            st.session_state.show_answer = False
            st.rerun()

with col2:
    if st.button("👁️ 看答案"):
        st.session_state.show_answer = not st.session_state.show_answer
        st.rerun()

with col3:
    if st.button("下一题 ➡️"):
        if st.session_state.mode == "随机抽题":
            st.session_state.current_index = random.randint(0, len(data)-1)
        else:
            if st.session_state.current_index < len(data) - 1:
                st.session_state.current_index += 1
        st.session_state.show_answer = False
        st.rerun()

# --- 答案解析区域 ---
if st.session_state.show_answer:
    st.success(f"✅ 正确答案：{q.get('answer')}")
    with st.expander("查看解析", expanded=True):
        st.write(q.get('analysis', '暂无解析'))