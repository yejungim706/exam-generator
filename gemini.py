import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import os
import tempfile
import time

st.set_page_config(
    page_title="AI 전 과목 시험지 & 답안지 생성기",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

API_KEY = st.secrets["API_KEY"]
MODEL_NAME = "google/gemini-2.5-flash"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    }
    
    .stApp {
        background-color: #0F172A;
    }
    
    .main-title {
        font-size: 2.25rem;
        font-weight: 800;
        color: #F8FAFC;
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: -0.025em;
    }
    
    .sub-title {
        font-size: 1.05rem;
        font-weight: 400;
        color: #94A3B8;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .warning-banner {
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 1rem 1.25rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2.5rem;
    }
    
    .warning-text {
        color: #F87171 !important;
        font-size: 0.95rem;
        font-weight: 600;
        margin: 0;
        line-height: 1.5;
    }
    
    .stForm, .result-container, .timer-card {
        background: #1E293B !important;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        border: 1px solid #334155;
    }
    
    .result-container {
        text-align: center;
        margin-top: 2rem;
    }
    
    .timer-card {
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .stForm label, p, span, div[data-baseweb="select"] span, label[data-baseweb="checkbox"] {
        color: #F8FAFC !important;
    }
    
    input, div[data-baseweb="select"] > div {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border-color: #334155 !important;
    }
    
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.65rem 1rem;
        transition: all 0.2s ease-in-out;
    }
    
    div.stFormSubmitButton > button {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        border: none;
        font-size: 1.05rem;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }
    div.stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

try:
    pdfmetrics.registerFont(UnicodeCIDFont('HYGothic-Medium'))
    FONT_NAME = 'HYGothic-Medium'
except:
    FONT_NAME = 'Helvetica'

st.markdown('<p class="main-title">📚 AI 전 과목 시험지 & 답안지 생성기</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">국어, 영어, 수학, 사회, 과학 등 모든 과목의 평가문항과 상세 해설지를 자동 생성합니다.</p>', unsafe_allow_html=True)

st.markdown("""
    <div class="warning-banner">
        <p class="warning-text">🚨 공지사항: AI 사용료가 비싸 후원이 없으면 서비스가 중단될 수 있습니다!<br>유용하게 쓰셨다면 자발적인 이용료 후원을 부탁드립니다.</p>
    </div>
""", unsafe_allow_html=True)

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

if "generated" not in st.session_state:
    st.session_state.generated = False
    st.session_state.exam_pdf_path = None
    st.session_state.answer_pdf_path = None

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = 0.0
if "elapsed_time" not in st.session_state:
    st.session_state.elapsed_time = 0.0

subjects = ["국어", "영어", "수학", "사회", "역사", "과학", "도덕", "기타"]

def build_pdf_two_column_vertical_order(items, filename, title_text, is_exam=True):
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=35,
        bottomMargin=35
    )
    
    title_style = ParagraphStyle(
        'DocTitle',
        fontName=FONT_NAME,
        fontSize=16,
        leading=20,
        textColor=colors.black
    )
    
    content_style = ParagraphStyle(
        'ContentText',
        fontName=FONT_NAME,
        fontSize=11 if is_exam else 10.5,
        leading=16 if is_exam else 15,
        textColor=colors.black
    )
    
    story = []
    story.append(Paragraph(f"<b>{title_text}</b>", title_style))
    story.append(Spacer(1, 12))
    
    def make_cell(item_text):
        content_elements = []
        lines = item_text.strip().split('\n')
        for line in lines:
            if line.strip():
                content_elements.append(Paragraph(f"<b>{line}</b>", content_style))
                content_elements.append(Spacer(1, 3))
        
        if is_exam:
            content_elements.append(Spacer(1, 6))
            content_elements.append(Paragraph("<b>(풀이)</b>", content_style))
            content_elements.append(Spacer(1, 2))
            for _ in range(7):
                content_elements.append(Spacer(1, 14))
            content_elements.append(Spacer(1, 4))
            content_elements.append(Paragraph("<b>정답 : ________________________</b>", content_style))
        
        cell_table = Table([[content_elements]], colWidths=[col_w])
        cell_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        return cell_table

    col_w = (A4[0] - 60 - 20) / 2
    total_items = len(items)
    half_n = (total_items + 1) // 2
    
    left_items = items[:half_n]
    right_items = items[half_n:]
    
    table_data = []
    max_len = max(len(left_items), len(right_items))
    
    for i in range(max_len):
        left_cell = make_cell(left_items[i]) if i < len(left_items) else ''
        right_cell = make_cell(right_items[i]) if i < len(right_items) else ''
        
        table_data.append([left_cell, '', right_cell])
        table_data.append(['', '', ''])
        
    main_table = Table(table_data, colWidths=[col_w, 20, col_w])
    main_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    
    story.append(main_table)
    doc.build(story)
    return filepath

col_timer, col_main = st.columns([0.9, 2.1])

with col_timer:
    st.markdown("""
        <div class="timer-card">
            <h3 style="color: #F8FAFC; font-size: 1.25rem; font-weight: 700; margin-bottom: 0.5rem;">⏱️ 실전 시험 타이머</h3>
            <p style="color: #94A3B8; font-size: 0.85rem; margin-bottom: 1.5rem;">문제를 풀며 제한 시간을 측정하세요.</p>
    """, unsafe_allow_html=True)
    
    if st.session_state.timer_running:
        current_elapsed = st.session_state.elapsed_time + (time.time() - st.session_state.start_time)
    else:
        current_elapsed = st.session_state.elapsed_time
        
    total_seconds = int(current_elapsed)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    st.markdown(f"<h1 style='color: #38BDF8; font-size: 2.8rem; font-weight: 800; margin: 1rem 0; letter-spacing: -0.05em;'>{time_str}</h1>", unsafe_allow_html=True)
    
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        if st.button("▶ 시작"):
            if not st.session_state.timer_running:
                st.session_state.timer_running = True
                st.session_state.start_time = time.time()
                st.rerun()
    with t_col2:
        if st.button("⏸ 정지"):
            if st.session_state.timer_running:
                st.session_state.elapsed_time += time.time() - st.session_state.start_time
                st.session_state.timer_running = False
                st.rerun()
    with t_col3:
        if st.button("🔄 리셋"):
            st.session_state.timer_running = False
            st.session_state.elapsed_time = 0.0
            st.session_state.start_time = 0.0
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.session_state.timer_running:
        time.sleep(0.1)
        st.rerun()

with col_main:
    with st.form(f"exam_form_{st.session_state.form_key}"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            selected_subject = st.selectbox("📖 과목 선택", subjects)
            exam_scope = st.text_input("📚 학년 / 과정", placeholder="예: 중학교 2학년, 고등학교 1학년")
        with col_f2:
            sub_scope = st.text_input("🎯 상세 단원 및 주제", placeholder="예: 2. 물질의 구성, 조선 시대 경제")
            difficulty = st.selectbox("⚡ 난이도", ["하 (기본)", "중 (응용)", "상 (심화)", "심화 (최고난도 극상)"])
            
        num_questions = st.number_input("📝 문제 수", min_value=1, value=4, step=1)
        
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✨ AI 맞춤 문제 및 답안 생성하기")

if submitted:
    if not exam_scope or not sub_scope:
        st.warning("⚠️ 학년/과정과 상세 단원을 모두 입력해주세요.")
    else:
        with st.spinner("🤖 AI가 과목별 특성에 맞춰 문항을 출제하고 검수 중입니다... 잠시만 기다려주세요."):
            prompt_1 = f"""
너는 최고급 시험지 출제 프로그램이다. 요청된 과목과 조건에 맞춰 적절하고 균형 잡힌 문항을 출제하라.
[조건]
- 과목: {selected_subject}
- 학년/과정: {exam_scope}
- 상세 단원: {sub_scope}
- 선택된 난이도: {difficulty}
- 문제 수: 정확히 {num_questions}문제
- 형식: 모든 문제는 반드시 5지선다형 객관식으로 출제하고, 문제 번호와 본문 아래에 보기 ①, ②, ③, ④, ⑤가 각각 줄바꿈되어 포함되도록 할 것.
- 답안지 형식: 각 문제별로 '문제', '정답', '상세해설'이 모두 포함되도록 상세하게 작성할 것.

[출력 형식]
반드시 아래 형식으로만 출력해줘. 다른 설명은 절대 하지 마.

---문제지---
1. (문제 내용)
① ...
② ...
③ ...
④ ...
⑤ ...

2. (문제 내용)
① ...
② ...
③ ...
④ ...
⑤ ...

---답안지---
1.
문제: 1번 문제 내용
정답: ①
상세해설: ...

2.
문제: 2번 문제 내용
정답: ③
상세해설: ...
"""

            response_1 = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_1}],
                temperature=0.7
            )
            
            raw_result_text = response_1.choices[0].message.content

            prompt_2 = f"""
너는 시험지 전문 검수 및 교정 에이전트이다.
아래에 제공된 1차 시험지 및 답안지 텍스트를 검수하여 다음 사항을 완벽하게 수정해라.

[검수 및 교정 규칙]
1. 문맥과 기호가 깨지지 않도록 매끄럽게 정돈할 것.
2. 문제와 보기(①~⑤), 답안지의 '문제', '정답', '상세해설' 내용이 서로 겹치거나 깨지지 않도록 문맥을 완벽하게 다듬을 것.
3. 오직 정제된 최종 내용만 출력하고 다른 인사말이나 설명은 절대 하지 마.

[수정할 원본 텍스트]
{raw_result_text}
"""

            response_2 = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt_2}],
                temperature=0.3
            )
            
            result_text = response_2.choices[0].message.content
            
            if "---답안지---" in result_text:
                parts = result_text.split("---답안지---")
                exam_raw = parts[0].replace("---문제지---", "").strip()
                answer_raw = parts[1].strip()
            else:
                exam_raw = result_text
                answer_raw = "답안 분리 실패"

            questions = [q.strip() for q in exam_raw.split('\n\n') if q.strip()]
            answers = [a.strip() for a in answer_raw.split('\n\n') if a.strip()]
            
            st.session_state.exam_pdf_path = build_pdf_two_column_vertical_order(questions, "exam.pdf", f"[{selected_subject}] {sub_scope} 평가문제지", is_exam=True)
            st.session_state.answer_pdf_path = build_pdf_two_column_vertical_order(answers, "answer.pdf", f"[{selected_subject}] {sub_scope} 정답 및 해설지", is_exam=False)
            st.session_state.generated = True

if st.session_state.generated:
    st.markdown("""
        <div class="result-container">
            <h3 style="color: #F8FAFC; margin-bottom: 0.5rem; font-weight: 700;">🎉 시험지와 답안지 패키지가 준비되었습니다!</h3>
            <p style="color: #94A3B8; font-size: 0.95rem; margin-bottom: 1.5rem;">원하시는 문서를 다운로드하거나 설정을 초기화하여 새로운 시험지를 만들어보세요.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.exam_pdf_path and os.path.exists(st.session_state.exam_pdf_path):
            with open(st.session_state.exam_pdf_path, "rb") as f:
                st.download_button(
                    label="📥 시험지 PDF 다운로드",
                    data=f,
                    file_name="exam.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
    with col2:
        if st.session_state.answer_pdf_path and os.path.exists(st.session_state.answer_pdf_path):
            with open(st.session_state.answer_pdf_path, "rb") as f:
                st.download_button(
                    label="📥 답안지 PDF 다운로드",
                    data=f,
                    file_name="answer.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
    with col3:
        if st.button("🔄 전체 초기화", use_container_width=True):
            st.session_state.form_key += 1
            st.session_state.generated = False
            st.session_state.exam_pdf_path = None
            st.session_state.answer_pdf_path = None
            st.session_state.timer_running = False
            st.session_state.elapsed_time = 0.0
            st.session_state.start_time = 0.0
            st.rerun()

st.markdown("<br><hr style='border-color: #334155;'>", unsafe_allow_html=True)
col_foot1, col_foot2 = st.columns([2, 1])
with col_foot1:
    st.markdown("<p style='color: #64748B; font-size: 0.85rem;'></p>", unsafe_allow_html=True)
with col_foot2:
    @st.dialog("☕ 개발자에게 커피 사주기")
    def donate_dialog():
        st.markdown("""
            <p style='color: #F8FAFC; text-align: center; margin-bottom: 1.5rem;'>서비스를 유용하게 쓰셨나요?<br>자발적인 후원은 더 좋은 기능을 만드는 데 큰 힘이 됩니다!</p>
            <div style='background-color: #0F172A; padding: 20px; border-radius: 10px; border: 1px solid #334155; text-align: center; margin-bottom: 1rem;'>
                <p style='color: #38BDF8; font-weight: 700; font-size: 1.2rem; margin-bottom: 8px;'>토스뱅크 1002-6694-4531</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("닫기", use_container_width=True):
            st.rerun()

    if st.button("☕ 개발자에게 커피 사주기", use_container_width=True):
        donate_dialog()
