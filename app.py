import streamlit as st
import json
import random
import time

# ================= 配置区域 (请在这里修改试卷名称) =================
# 格式： "试卷ID": "你自己起的名字"
# 如果你的ID不在这个列表里，系统会直接显示ID号
PAPER_NAMES = {
    "152890": "中级维保【单选题】",
    "11455699": "中级维保【判断题】",
    # 你后续如果下载了多选题或综合卷，把ID填在这里，比如：
    # "12345678": "中级维保【多选题】",
}
# ===============================================================

st.set_page_config(page_title="消防刷题Pro版", layout="wide")

# --- 核心函数 ---
@st.cache_data
def load_data():
    try:
        with open('tiku_data_all.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        return []

def get_paper_name(paper_id):
    pid = str(paper_id)
    return PAPER_NAMES.get(pid, f"试卷 ID: {pid}")

# --- 初始化 ---
all_data = load_data()

if not all_data:
    st.error("❌ 未找到题库文件，请检查 GitHub 是否上传了 tiku_data_all.json")
    st.stop()

# 提取所有试卷ID并去重
paper_ids = sorted(list(set([str(q['from_paper_id']) for q in all_data])))

# 初始化 Session State
if 'current_paper_id' not in st.session_state:
    st.session_state.current_paper_id = paper_ids[0]
if 'q_index' not in st.session_state:
    st.session_state.q_index = 0
if 'show_analysis' not in st.session_state:
    st.session_state.show_analysis = False
if 'user_choice' not in st.session_state:
    st.session_state.user_choice = None
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()
if 'mode' not in st.session_state:
    st.session_state.mode = '顺序刷题'

# --- 侧边栏设置 ---
with st.sidebar:
    st.title("⚙️ 刷题设置")
    
    # 1. 选择试卷 (分类功能)
    selected_paper_name = st.selectbox(
        "📂 选择题库/试卷",
        options=paper_ids,
        format_func=lambda x: get_paper_name(x)
    )
    
    # 如果切换了试卷，重置进度
    if selected_paper_name != st.session_state.current_paper_id:
        st.session_state.current_paper_id = selected_paper_name
        st.session_state.q_index = 0
        st.session_state.show_analysis = False
        st.session_state.user_choice = None
        st.session_state.start_time = time.time() # 重置计时
        st.rerun()

    # 筛选当前试卷的题目
    current_questions = [q for q in all_data if str(q['from_paper_id']) == st.session_state.current_paper_id]
    total_q = len(current_questions)
    
    st.divider()

    # 2. 刷题模式
    mode = st.radio("🔄 模式", ["顺序刷题", "随机抽题"])
    if mode != st.session_state.mode:
        st.session_state.mode = mode
        st.rerun()

    # 3. 跳转功能
    if st.session_state.mode == "顺序刷题":
        st.write(f"当前进度: {st.session_state.q_index + 1} / {total_q}")
        new_index = st.number_input("跳转到", min_value=1, max_value=total_q, value=st.session_state.q_index + 1)
        if st.button("Go"):
            st.session_state.q_index = new_index - 1
            st.session_state.show_analysis = False
            st.session_state.user_choice = None
            st.rerun()
    
    st.divider()
    
    # 4. 计时器显示
    elapsed_time = int(time.time() - st.session_state.start_time)
    minutes = elapsed_time // 60
    seconds = elapsed_time % 60
    st.metric("⏱️ 已用时", f"{minutes:02d}:{seconds:02d}")
    if st.button("重置计时"):
        st.session_state.start_time = time.time()
        st.rerun()

# --- 主界面 ---
if not current_questions:
    st.warning("该试卷没有题目")
    st.stop()

q = current_questions[st.session_state.q_index]

# 标题区域
st.markdown(f"### 第 {st.session_state.q_index + 1} 题")
st.progress((st.session_state.q_index + 1) / total_q)

# 题目类型判断
# 通常 type 1=单选/判断, 2=多选 (具体看你的数据，这里做了兼容)
is_multiselect = False
type_label = "【单选/判断】"
if q.get('type') == 2 or len(str(q.get('answer'))) > 1: # 简单判断：如果答案长度大于1或者类型是2，就是多选
    is_multiselect = True
    type_label = "【多选题】"

st.caption(f"{type_label} | 来源: {get_paper_name(q['from_paper_id'])}")
st.markdown(f"**{q['content']}**")

# --- 选项交互区域 ---
options = q.get('options', [])
correct_answer = q.get('answer', '').strip()

# 处理选项显示 (防止选项为空)
if not options:
    st.error("⚠️ 此题数据缺失选项，请查看解析")
else:
    # 构造选项列表 (如果是纯文本，尝试给它加 ABC)
    formatted_options = []
    for idx, opt in enumerate(options):
        # 如果选项本身不包含 "A." 这种前缀，我们手动加上
        prefix = chr(65 + idx) # A, B, C...
        if not opt.strip().startswith(prefix):
             formatted_options.append(f"{prefix}. {opt}")
        else:
             formatted_options.append(opt)

    # === 单选题/判断题 逻辑 ===
    if not is_multiselect:
        # 使用 radio 单选框
        # 注意：Streamlit 的 radio 只有点击时才会触发 value change
        selected_opt = st.radio(
            "请选择答案：", 
            formatted_options, 
            index=None, 
            key=f"radio_{st.session_state.q_index}" # 绑定独立key防止混淆
        )
        
        # 只有当用户做出了选择，并且还没看答案时，自动检查
        if selected_opt:
            user_ans_char = selected_opt[0] # 取首字母 'A'
            if not st.session_state.show_analysis:
                # 自动显示答案（类似刷题APP的效果）
                if user_ans_char == correct_answer:
                    st.success(f"✅ 回答正确！")
                else:
                    st.error(f"❌ 选错了，正确答案是：{correct_answer}")
                st.session_state.show_analysis = True

    # === 多选题 逻辑 ===
    else:
        st.info("💡 这是一个多选题，请勾选所有正确选项后点击“提交”")
        # 多选使用 checkbox
        selected_boxes = []
        for opt in formatted_options:
            if st.checkbox(opt, key=opt):
                selected_boxes.append(opt[0]) # 存入 'A', 'B'
        
        if st.button("提交答案"):
            user_ans_str = "".join(sorted(selected_boxes)) # 变成 "ABC"
            if user_ans_str == correct_answer:
                 st.success("✅ 回答正确！")
            else:
                 st.error(f"❌ 错误，你的选择：{user_ans_str}，正确答案：{correct_answer}")
            st.session_state.show_analysis = True

# --- 按钮与解析 ---
st.write("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("⬅️ 上一题"):
        if st.session_state.q_index > 0:
            st.session_state.q_index -= 1
            st.session_state.show_analysis = False
            st.session_state.user_choice = None
            st.rerun()

with col2:
    if st.button("👁️ 强制看解析"):
        st.session_state.show_analysis = not st.session_state.show_analysis
        st.rerun()

with col3:
    if st.button("下一题 ➡️"):
        if st.session_state.mode == "随机抽题":
             st.session_state.q_index = random.randint(0, total_q - 1)
        else:
            if st.session_state.q_index < total_q - 1:
                st.session_state.q_index += 1
        st.session_state.show_analysis = False
        st.session_state.user_choice = None
        st.rerun()

# 解析显示
if st.session_state.show_analysis:
    with st.expander("查看详细解析", expanded=True):
        st.markdown(f"#### ✅ 正确答案：{correct_answer}")
        st.write(q.get('analysis', '暂无解析'))
