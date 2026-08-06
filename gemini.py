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

API_KEY = st.secrets["OPENROUTER_API_KEY"]
MODEL_NAME = "google/gemini-2.5-flash"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False
if "username" not in st.session_state:
    st.session_state.username = ""

st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif; }
    .stApp { background-color: #0F172A; }
    .main-title { font-size: 2.25rem; font-weight: 800; color: #F8FAFC; text-align: center; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1.05rem; color: #94A3B8; text-align: center; margin-bottom: 2.5rem; }
    .stForm, .result-container, .timer-card, .login-card {
        background: #1E293B !important;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        border: 1px solid #334155;
    }
    .stForm label, p, span, div[data-baseweb="select"] span { color: #F8FAFC !important; }
    input, div[data-baseweb="select"] > div { background-color: #0F172A !important; color: #F8FAFC !important; border-color: #334155 !important; }
    div.stButton > button { width: 100%; border-radius: 10px; font-weight: 600; padding: 0.65rem 1rem; }
    div.stFormSubmitButton > button { background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); color: white; border: none; font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)

try:
    pdfmetrics.registerFont(UnicodeCIDFont('HYGothic-Medium'))
    FONT_NAME = 'HYGothic-Medium'
except:
    FONT_NAME = 'Helvetica'

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""
            <div class="login-card">
                <h2 style="color: #F8FAFC; text-align: center; margin-bottom: 1.5rem;">🔐 로그인 및 이용</h2>
        """, unsafe_allow_html=True)
        username = st.text_input("아이디(닉네임)를 입력하세요")
        if st.button("로그인하기"):
            if username.strip():
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.warning("아이디를 입력해주세요.")
        st.markdown("</div>", unsafe_allow_html=True)

elif not st.session_state.is_subscribed:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown(f"""
            <div class="login-card">
                <h2 style="color: #F8FAFC; text-align: center; margin-bottom: 1rem;">💎 프리미엄 구독 필요</h2>
                <p style="color: #94A3B8; text-align: center; margin-bottom: 1.5rem;">환영합니다, <b>{st.session_state.username}</b>님!<br>서비스를 이용하려면 월 2,000원 구독이 필요합니다.</p>
        """, unsafe_allow_html=True)
        
        if st.button("💳 월 2,000원 결제하기 (토스페이먼츠 연동)"):
            st.info("결제 창이 호출되는 영역입니다.")
            
        if st.button("✅ 결제 완료 확인 (테스트용)"):
            st.session_state.is_subscribed = True
            st.rerun()
            
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown('<p class="main-title">📚 AI 전 과목 시험지 & 답안지 생성기</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-title">환영합니다, <b>{st.session_state.username}</b>님! | <a href="#" target="_self" onclick="window.location.reload();">로그아웃</a></p>', unsafe_allow_html=True)

    if "form_key" not in st.session_state:
        st.session_state.form_key = 0
    if "generated" not in st.session_state:
        st.session_state.generated = False
        st.session_state.exam_pdf_path = None
        st.session_state.answer_pdf_path = None
    if "timer_running" not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.start_time = 0.0
        st.session_state.elapsed_time = 0.0

    subjects = ["국어", "영어", "수학", "사회", "역사", "과학", "도덕", "기타"]

    def build_pdf_two_column_vertical_order(items, filename, title_text, is_exam=True):
        temp_dir = tempfile.mkdtemp()
        filepath = os.path.join(temp_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=35, bottomMargin=35)
        
        title_style = ParagraphStyle('DocTitle', fontName=FONT_NAME, fontSize=16, leading=20, textColor=colors.black)
        content_style = ParagraphStyle('ContentText', fontName=FONT_NAME, fontSize=11 if is_exam else 10.5, leading=16 if is_exam else 15, textColor=colors.black)
        
        story = [Paragraph(f"<b>{title_text}</b>", title_style), Spacer(1, 12)]
        
        def make_cell(item_text):
            content_elements = []
            for line in item_text.strip().split('\n'):
                if line.strip():
                    content_elements.append(Paragraph(f"<b>{line}</b>", content_style))
                    content_elements.append(Spacer(1, 3))
            if is_exam:
                content_elements.extend([Spacer(1, 6), Paragraph("<b>(풀이)</b>", content_style), Spacer(1, 2)])
                for _ in range(7): content_elements.append(Spacer(1, 14))
                content_elements.extend([Spacer(1, 4), Paragraph("<b>정답 : ________________________</b>", content_style)])
            
            cell_table = Table([[content_elements]], colWidths=[col_w])
            cell_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 0)]))
            return cell_table

        col_w = (A4[0] - 60 - 20) / 2
        half_n = (len(items) + 1) // 2
        left_items, right_items = items[:half_n], items[half_n:]
        
        table_data = []
        for i in range(max(len(left_items), len(right_items))):
            left_cell = make_cell(left_items[i]) if i < len(left_items) else ''
            right_cell = make_cell(right_items[i]) if i < len(right_items) else ''
            table_data.append([left_cell, '', right_cell])
            table_data.append(['', '', ''])
            
        main_table = Table(table_data, colWidths=[col_w, 20, col_w])
        main_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 12)]))
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
        
        current_elapsed = st.session_state.elapsed_time + (time.time() - st.session_state.start_time if st.session_state.timer_running else 0)
        total_seconds = int(current_elapsed)
        st.markdown(f"<h1 style='color: #38BDF8; font-size: 2.8rem; font-weight: 800; margin: 1rem 0;'>{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}:{total_seconds % 60:02d}</h1>", unsafe_allow_html=True)
        
        t1, t2, t3 = st.columns(3)
        with t1:
            if st.button("▶ 시작") and not st.session_state.timer_running:
                st.session_state.timer_running, st.session_state.start_time = True, time.time()
                st.rerun()
        with t2:
            if st.button("⏸ 정지") and st.session_state.timer_running:
                st.session_state.elapsed_time += time.time() - st.session_state.start_time
                st.session_state.timer_running = False
                st.rerun()
        with t3:
            if st.button("🔄 리셋"):
                st.session_state.timer_running, st.session_state.elapsed_time, st.session_state.start_time = False, 0.0, 0.0
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        if st.session_state.timer_running:
            time.sleep(0.1)
            st.rerun()

    with col_main:
        with st.form(f"exam_form_{st.session_state.form_key}"):
            cf1, cf2 = st.columns(2)
            with cf1:
                selected_subject = st.selectbox("📖 과목 선택", subjects)
                exam_scope = st.text_input("📚 학년 / 과정", placeholder="예: 중학교 2학년")
            with cf2:
                sub_scope = st.text_input("🎯 상세 단원 및 주제", placeholder="예: 물질의 구성")
                difficulty = st.selectbox("⚡ 난이도", ["하 (기본)", "중 (응용)", "상 (심화)", "심화 (최고난도 극상)"])
            num_questions = st.number_input("📝 문제 수", min_value=1, value=4, step=1)
            submitted = st.form_submit_button("✨ AI 맞춤 문제 및 답안 생성하기")

    if submitted:
        if not exam_scope or not sub_scope:
            st.warning("⚠️ 학년/과정과 상세 단원을 모두 입력해주세요.")
        else:
            with st.spinner("🤖 AI가 문항을 출제하고 검수 중입니다..."):
                prompt_1 = f"과목: {selected_subject}, 학년: {exam_scope}, 단원: {sub_scope}, 난이도: {difficulty}, 문제수: {num_questions}. 5지선다 객관식으로 ---문제지---와 ---답안지--- 형식으로 출력해줘."
                res_1 = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt_1}], temperature=0.7)
                raw_text = res_1.choices[0].message.content
                
                if "---답안지---" in raw_text:
                    parts = raw_text.split("---답안지---")
                    exam_raw, answer_raw = parts[0].replace("---문제지---", "").strip(), parts[1].strip()
                else:
                    exam_raw, answer_raw = raw_text, "답안 분리 실패"

                questions = [q.strip() for q in exam_raw.split('\n\n') if q.strip()]
                answers = [a.strip() for a in answer_raw.split('\n\n') if a.strip()]
                
                st.session_state.exam_pdf_path = build_pdf_two_column_vertical_order(questions, "exam.pdf", f"[{selected_subject}] {sub_scope} 평가문제지", is_exam=True)
                st.session_state.answer_pdf_path = build_pdf_two_column_vertical_order(answers, "answer.pdf", f"[{selected_subject}] {sub_scope} 정답 및 해설지", is_exam=False)
                st.session_state.generated = True

    if st.session_state.generated:
        st.markdown('<div class="result-container"><h3 style="color: #F8FAFC;">🎉 시험지와 답안지 패키지가 준비되었습니다!</h3></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.session_state.exam_pdf_path and os.path.exists(st.session_state.exam_pdf_path):
                with open(st.session_state.exam_pdf_path, "rb") as f:
                    st.download_button("📥 시험지 PDF", f, file_name="exam.pdf", mime="application/pdf", use_container_width=True)
        with c2:
            if st.session_state.answer_pdf_path and os.path.exists(st.session_state.answer_pdf_path):
                with open(st.session_state.answer_pdf_path, "rb") as f:
                    st.download_button("📥 답안지 PDF", f, file_name="answer.pdf", mime="application/pdf", use_container_width=True)
        with c3:
            if st.button("🔄 전체 초기화", use_container_width=True):
                st.session_state.form_key += 1
                st.session_state.generated = False
                st.session_state.timer_running = False
                st.session_state.elapsed_time = 0.0
                st.rerun()
