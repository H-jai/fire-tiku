import streamlit as st
import json
import random
import time

# ================= 配置区域 =================
PAPER_NAMES = {
    "152890": "中级维保【单选题库】",
    "11455699": "中级维保【判断题库】",
    # 如果有其他ID，继续在这里添加
}
# ===========================================

# --- 1. 手机端界面美化配置 (CSS注入) ---
st.set_page_config(page_title="消防刷题Pro", page_icon="🔥", layout="centered")

st.markdown("""
    <style>
    /* 手机端去除左右留白，利用率最大化 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    /* 题目卡片化 */
    .stAlert {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* 增大选项字体，方便手指点击 */
    .stRadio label, .stCheckbox label {
        font-size: 18px !important;
        padding-top: 10px !important;
        padding-bottom: 10px !important;
    }
    /* 底部按钮浮动优化 */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心函数 ---
@st.cache_data
def load_data():
    try:
        with open('tiku_data_all.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def get_paper_name(paper_id):
    pid = str(paper_id)
    return PAPER_NAMES.get(pid, f"试卷 {pid}")

def identify_question_type(q):
    """
    智能识别题目类型，解决试卷里混杂乱题的问题
    """
    ans = q.get('answer', '').strip()
    q_type = q.get('type', 1)
    
    # 优先用答案长度判断
    if len(ans) > 1:
        return "多选题"
    elif len(q.get('options', [])) == 2:
        return "判断题"
    elif q_type == 2:
        return "多选题"
    else:
        return "单选题"

# --- 3. 初始化状态 ---
if 'stats' not in st.session_state:
    st.session_state.stats = {'correct': 0, 'total': 0}

all_data = load_data()
if not all_data:
    st.error("请先上传 tiku_data_all.json 到 GitHub")
    st.stop()

# 提取所有试卷ID
paper_ids = sorted(list(set([str(q['from_paper_id']) for q in all_data])))

# --- 4. 侧边栏 (设置与计分) ---
with st.sidebar:
    st.header("📊 刷题统计")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("已刷题", f"{st.session_state.stats['total']}")
    with col_b:
        acc = 0
        if st.session_state.stats['total'] > 0:
            acc = (st.session_state.stats['correct'] / st.session_state.stats['total']) * 100
        st.metric("正确率", f"{acc:.1f}%")
    
    if st.button("🗑️ 清空统计数据"):
        st.session_state.stats = {'correct': 0, 'total': 0}
        st.rerun()

    st.divider()
    st.header("⚙️ 题库筛选")
    
    # 试卷选择
    selected_paper = st.selectbox("选择试卷源", paper_ids, format_func=get_paper_name)
    
    # 【核心功能】强制类型过滤
    # 哪怕试卷里混了多选题，这里选了单选，就只给你看单选！
    filter_type = st.radio("只想看哪种题？", ["全部混合", "只看单选题", "只看多选题", "只看判断题"])
    
    mode = st.radio("刷题模式", ["顺序模式", "随机抽题"])

# --- 5. 数据过滤逻辑 ---
# 第一步：按试卷ID过滤
paper_questions = [q for q in all_data if str(q['from_paper_id']) == selected_paper]

# 第二步：按题型强制过滤 (清洗脏数据)
final_questions = []
for q in paper_questions:
    q_real_type = identify_question_type(q)
    if filter_type == "全部混合":
        final_questions.append(q)
    elif filter_type == "只看单选题" and q_real_type == "单选题":
        final_questions.append(q)
    elif filter_type == "只看多选题" and q_real_type == "多选题":
        final_questions.append(q)
    elif filter_type == "只看判断题" and q_real_type == "判断题":
        final_questions.append(q)

if not final_questions:
    st.warning(f"⚠️ 该试卷中没有【{filter_type}】，请切换筛选条件。")
    st.stop()

# --- 6. 题目索引控制 ---
if 'current_paper' not in st.session_state or st.session_state.current_paper != selected_paper:
    st.session_state.current_paper = selected_paper
    st.session_state.q_index = 0
    st.session_state.user_ans = None
    st.session_state.show_res = False

total_q = len(final_questions)
q_now = final_questions[st.session_state.q_index]
q_type_str = identify_question_type(q_now)

# --- 7. 主界面展示 (手机优化版) ---

# 进度条
st.progress((st.session_state.q_index + 1) / total_q)
st.caption(f"📝 {q_type_str} | 进度: {st.session_state.q_index + 1}/{total_q}")

# 题目卡片
st.info(f"**{q_now['content']}**")

# 选项处理
options = q_now.get('options', [])
# 如果没有ABC前缀，自动补全
fmt_options = []
for idx, opt in enumerate(options):
    prefix = chr(65 + idx)
    if not opt.strip().startswith(prefix):
        fmt_options.append(f"{prefix}. {opt}")
    else:
        fmt_options.append(opt)

correct_ans = q_now.get('answer', '').strip()

# --- 8. 答题交互区 ---

# 如果还没有提交答案
if not st.session_state.show_res:
    if q_type_str == "多选题":
        st.write("👇 (多选) 请勾选所有正确项：")
        user_picks = []
        for opt in fmt_options:
            if st.checkbox(opt, key=opt):
                user_picks.append(opt[0])
        
        if st.button("提交答案", type="primary"):
            if not user_picks:
                st.toast("⚠️ 请至少选一个选项！")
            else:
                user_str = "".join(sorted(user_picks))
                st.session_state.user_ans = user_str
                st.session_state.show_res = True
                # 计分
                st.session_state.stats['total'] += 1
                if user_str == correct_ans:
                    st.session_state.stats['correct'] += 1
                st.rerun()
                
    else: # 单选或判断
        st.write("👇 请选择一个选项：")
        # 使用 radio，但在手机上我们要加大间距
        choice = st.radio("选项", fmt_options, index=None, label_visibility="collapsed")
        
        if choice:
            user_char = choice[0]
            st.session_state.user_ans = user_char
            st.session_state.show_res = True
            # 计分
            st.session_state.stats['total'] += 1
            if user_char == correct_ans:
                st.session_state.stats['correct'] += 1
            st.rerun()

# --- 9. 结果展示区 ---
else:
    # 选项回显 (为了美观，这里不重新渲染Radio，直接显示结果)
    is_right = (st.session_state.user_ans == correct_ans)
    
    if is_right:
        st.success(f"✅ 回答正确！")
    else:
        st.error(f"❌ 选错了！你的答案：{st.session_state.user_ans}")
        st.info(f"🔑 正确答案：{correct_ans}")
    
    with st.expander("查看题目解析", expanded=not is_right):
        st.write(q_now.get('analysis', '暂无解析'))

    # 底部控制按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ 上一题"):
            if st.session_state.q_index > 0:
                st.session_state.q_index -= 1
                st.session_state.user_ans = None
                st.session_state.show_res = False
                st.rerun()
    with col2:
        if st.button("下一题 ➡️", type="primary"):
            if mode == "随机抽题":
                st.session_state.q_index = random.randint(0, total_q - 1)
            else:
                if st.session_state.q_index < total_q - 1:
                    st.session_state.q_index += 1
            st.session_state.user_ans = None
            st.session_state.show_res = False
            st.rerun()
