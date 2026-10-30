import json
import re
import os
import time
import streamlit as st
from google import genai
from pypdf import PdfReader

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Quiz Maker | Prateek Senmar",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- CUSTOM CSS (Matching Exact Screenshots UI & Dark Purple Gradient Theme) ---
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0b0614 0%, #160d26 50%, #1f113a 100%);
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .brand-header {
        text-align: center;
        padding: 10px 0 5px 0;
    }
    .brand-title {
        font-size: 26px;
        font-weight: bold;
        color: #00d2ff;
        letter-spacing: 1px;
    }
    .brand-subtitle {
        font-size: 13px;
        color: #ff4b8b;
        margin-top: 2px;
        font-weight: 600;
    }
    .card {
        background: #160d26;
        border: 1px solid #2a1b48;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .pw-top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #160d26;
        padding: 10px 15px;
        border-radius: 12px;
        border: 1px solid #2a1b48;
        margin-bottom: 15px;
    }
    .pw-timer {
        color: #ff4b8b;
        font-weight: bold;
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- INITIALIZE GEMINI CLIENT ---
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

client = get_gemini_client()

# --- MODEL FALLBACK FUNCTION (Flash Models) ---
def generate_quiz_with_fallback(prompt_text):
    if not client:
        raise Exception("API Key missing!")
    
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash"
    ]
    
    last_error = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text
            )
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = e
            continue
            
    raise Exception(f"Server par high demand hai. Error: {last_error}")

# --- SESSION STATE INITIALIZATION ---
if "page" not in st.session_state:
    st.session_state.page = "home"
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "quiz_history" not in st.session_state:
    st.session_state.quiz_history = []
if "current_exam_info" not in st.session_state:
    st.session_state.current_exam_info = ""
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "quiz_language" not in st.session_state:
    st.session_state.quiz_language = "Hindi (हिंदी)"
if "show_coming_soon" not in st.session_state:
    st.session_state.show_coming_soon = False
if "analysis_tab" not in st.session_state:
    st.session_state.analysis_tab = "all"

# --- HEADER BRANDING ---
st.markdown(
    """
    <div class="brand-header">
        <div class="brand-title">⚡ AI QUIZ MAKER</div>
        <div class="brand-subtitle">BY PRATEEK SENMAR 👑</div>
        <div style="font-size:12px; color:#b0a8c2; margin-top:2px;">Build Better • Learn Faster</div>
    </div>
    <hr style="border-color: #2a1b48; margin: 10px 0;">
    """,
    unsafe_allow_html=True,
)

subjects_list = [
    "General Mathematics (गणित)",
    "Reasoning (तर्कशक्ति)",
    "General Knowledge / GS (सामान्य ज्ञान)",
    "Indian History (भारतीय इतिहास)",
    "Geography (भूगोल)",
    "Indian Polity (भारतीय राजव्यवस्था)",
    "General Science (सामान्य विज्ञान)",
    "English Language (अंग्रेजी)",
    "Current Affairs (समसामयिक)",
    "Other / Custom Subject"
]

page = st.session_state.page

if page == "home":
    st.markdown("### अपनी तैयारी को अगला स्तर दो!")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>Practice smarter. Improve faster. Achieve more.</p>", unsafe_allow_html=True)
    st.markdown("#### ⚡ Choose Your Practice")
    
    if st.button("📄 PDF to Quiz\nअपनी PDF से MCQ टेस्ट बनाओ", use_container_width=True):
        st.session_state.page = "pdf_quiz"
        st.rerun()
    if st.button("📜 PYQ Practice\nपिछले वर्षों के प्रश्नों का अभ्यास", use_container_width=True):
        st.session_state.page = "pyq_practice"
        st.rerun()
    if st.button("🧠 AI Practice\nAI से नए प्रश्न और मॉक टेस्ट", use_container_width=True):
        st.session_state.page = "ai_practice"
        st.rerun()
    if st.button("🗂️ Quick Access\nअपने एग्जाम को चुनें", use_container_width=True):
        st.session_state.page = "quick_access"
        st.rerun()
    if st.button("📊 Quiz History & Dashboard", use_container_width=True):
        st.session_state.page = "study_dashboard"
        st.rerun()
        
    st.markdown("---")
    st.markdown("<div style='text-align:center; font-size:13px; color:#b0a8c2;'>✨ PRATEEK SENMAR ✨<br>Your Preparation • Your Progress • Your Success</div>", unsafe_allow_html=True)

elif page == "pdf_quiz":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📄 PDF to Quiz")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>अपनी PDF से MCQ टेस्ट बनाओ</p>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("अपनी पढ़ाई की PDF चुनें (Max 20MB)", type=["pdf"])
    
    selected_subject = st.selectbox("📖 Select Subject", subjects_list, key="pdf_sub")
    num_q = st.slider("प्रश्नों की संख्या", 10, 200, 20, step=5)
    time_min = st.slider("⏱️ टाइमर (मिनट)", 10, 120, 30, step=5)
    lang_opt = st.selectbox("भाषा", ["Hindi (हिंदी)", "English"])
    
    if uploaded_file is not None:
        if st.button("🚀 क्विज़ बनाएं", type="primary", use_container_width=True):
            if not client:
                st.error("API Key missing!")
            else:
                with st.spinner("Processing PDF with Flash AI..."):
                    try:
                        reader = PdfReader(uploaded_file)
                        pdf_text = ""
                        for page_obj in reader.pages:
                            if page_obj.extract_text():
                                pdf_text += page_obj.extract_text() + "\n"
                        pdf_text = pdf_text[:25000]
                        
                        lang_instruction = "completely in pure and simple Hindi." if "Hindi" in lang_opt else "in English."
                        prompt = f"""
                        Based strictly on the text for '{selected_subject}', generate {num_q} MCQs with 4 options each.
                        CRITICAL: All questions, options, and explanations MUST be {lang_instruction}
                        Output strictly in valid JSON format as a list of objects with keys: 
                        'question', 'options', 'answer', 'explanation'.
                        Text: {pdf_text}
                        """
                        raw_text = generate_quiz_with_fallback(prompt)
                        clean_res = raw_text.strip()
                        if clean_res.startswith("```json"):
                            clean_res = clean_res[7:-3].strip()
                        elif clean_res.startswith("```"):
                            clean_res = clean_res[3:-3].strip()
                            
                        parsed_quiz = json.loads(clean_res)
                        st.session_state.quiz_data = parsed_quiz
                        st.session_state.user_answers = {}
                        st.session_state.quiz_submitted = False
                        st.session_state.current_q_index = 0
                        st.session_state.current_exam_info = f"PDF Quiz: {uploaded_file.name} | {selected_subject}"
                        st.session_state.page = "take_quiz"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

elif page == "pyq_practice":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📜 PYQ Practice")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>असली PYQ • सही तारीख • विस्तृत समाधान</p>", unsafe_allow_html=True)
    
    selected_exam = st.selectbox("एग्जाम चुनें", ["SSC", "Railways", "UP Police", "अन्य उपलब्ध परीक्षाएँ"])
    selected_subject = st.selectbox("विषय चुनें", subjects_list, key="pyq_sub")
    year = st.selectbox("वर्ष चुनें", ["2023", "2022", "2021", "2020"])
    num_q = st.slider("प्रश्नों की संख्या", 10, 100, 20, step=10)
    time_min = st.slider("टाइमर (मिनट)", 10, 60, 20, step=10)
    
    if st.button("🚀 शुरू करें", type="primary", use_container_width=True):
        quiz_list = [
            {
                "question": f"[{selected_exam} {year}] भारत का संविधान कब लागू हुआ था?",
                "options": ["26 जनवरी 1950", "15 अगस्त 1947", "26 नवंबर 1949", "2 अक्टूबर 1950"],
                "answer": "26 जनवरी 1950",
                "explanation": "भारत का संविधान 26 जनवरी 1950 को पूर्ण रूप से लागू हुआ था।"
            }
        ]
        st.session_state.quiz_data = quiz_list * max(1, num_q // len(quiz_list))
        st.session_state.user_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.current_q_index = 0
        st.session_state.current_exam_info = f"PYQ: {selected_exam} ({year}) - {selected_subject}"
        st.session_state.page = "take_quiz"
        st.rerun()

elif page == "ai_practice":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🧠 AI Practice")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>स्मार्ट प्रैक्टिस • बेहतर तैयारी</p>", unsafe_allow_html=True)
    
    exam_type = st.selectbox("एग्जाम चुनें", ["SSC", "UPSC", "UP Police", "Railway", "Defence"])
    selected_subject = st.selectbox("विषय चुनें", subjects_list, key="ai_sub")
    num_q = st.slider("प्रश्नों की संख्या", 10, 200, 20, step=5)
    time_min = st.slider("टाइमर (मिनट)", 10, 120, 20, step=5)
    difficulty = st.select_slider("Difficulty Level", options=["Easy", "Medium", "Moderate"])
    
    if st.button("🤖 Start AI Quiz", type="primary", use_container_width=True):
        if not client:
            st.error("API Key missing!")
        else:
            with st.spinner("Generating AI questions in pure Hindi..."):
                try:
                    prompt = f"""
                    Generate {num_q} MCQs for {exam_type} on subject '{selected_subject}' with 4 options each.
                    CRITICAL: All questions, options, and explanations MUST be in pure Hindi.
                    Output strictly in valid JSON list format with keys: 'question', 'options', 'answer', 'explanation'.
                    """
                    raw_text = generate_quiz_with_fallback(prompt)
                    clean_res = raw_text.strip()
                    if clean_res.startswith("```json"):
                        clean_res = clean_res[7:-3].strip()
                    elif clean_res.startswith("```"):
                        clean_res = clean_res[3:-3].strip()
                        
                    parsed_quiz = json.loads(clean_res)
                    st.session_state.quiz_data = parsed_quiz
                    st.session_state.user_answers = {}
                    st.session_state.quiz_submitted = False
                    st.session_state.current_q_index = 0
                    st.session_state.current_exam_info = f"AI Practice: {exam_type} - {selected_subject}"
                    st.session_state.page = "take_quiz"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

elif page == "quick_access":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### ⚡ QUICK ACCESS")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>अपना एग्जाम चुनें</p>", unsafe_allow_html=True)
    
    if st.session_state.show_coming_soon:
        st.markdown(
            """
            <div class="card" style="border: 1px solid #ff4b8b; text-align:center;">
                <h3>🚀 COMING SOON</h3>
                <p><b>अभी काम कुछ समय के लिए रुका हुआ है।</b></p>
                <p>अभी Depression का दौर चल रहा है, इसलिए काम बंद है। ❤️‍🩹</p>
                <p>अभी वक्त मुश्किल है, लेकिन वापसी होगी और धमाका बड़ा करेंगे! 🔥</p>
                <p style="font-style:italic; color:#b0a8c2;">“हिम्मत रखो, यह भी गुजर जाएगा...”</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Back to Home", type="primary", use_container_width=True):
            st.session_state.show_coming_soon = False
            st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏛️ SSC\nAvailable", use_container_width=True):
                st.session_state.current_exam_info = "Quick Access: SSC"
                st.session_state.quiz_data = [{
                    "question": "भारत का संविधान कब लागू हुआ था?",
                    "options": ["26 जनवरी 1950", "15 अगस्त 1947", "26 नवंबर 1949", "2 अक्टूबर 1950"],
                    "answer": "26 जनवरी 1950",
                    "explanation": "संविधान 26 जनवरी 1950 को लागू हुआ था।"
                }] * 10
                st.session_state.user_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.current_q_index = 0
                st.session_state.page = "take_quiz"
                st.rerun()
            if st.button("🛡️ IB\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("🚓 RPF\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("⭐ MP Police\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
        with col2:
            if st.button("🚆 Railways\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("👮 UP Police\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("🏢 Delhi Police\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("🎖️ Defence\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()

elif page == "study_dashboard":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown("### 📈 Study Dashboard & History")
    total_tests = len(st.session_state.quiz_history)
    st.markdown(f"<div class='card'><b>कुल दिए गए टेस्ट:</b> {total_tests}</div>", unsafe_allow_html=True)
    if st.session_state.quiz_history:
        for rec in reversed(st.session_state.quiz_history):
            st.markdown(f"<div class='card'><b>{rec['exam_info']}</b><br>Score: {rec['score']}/{rec['total']} ({rec['percentage']}%)</div>", unsafe_allow_html=True)

elif page == "take_quiz":
    if not st.session_state.quiz_data:
        st.warning("कोई सक्रिय क्विज़ उपलब्ध नहीं है।")
        if st.button("Home"):
            st.session_state.page = "home"
            st.rerun()
    else:
        quiz = st.session_state.quiz_data
        total_q = len(quiz)
        
        col_bar1, col_bar2, col_bar3 = st.columns([2, 1.2, 1])
        with col_bar1:
            st.markdown(f"<b style='font-size:12px; color:#00d2ff;'>{st.session_state.current_exam_info}</b>", unsafe_allow_html=True)
        with col_bar2:
            lang_choice = st.selectbox("Lang", ["Hindi (हिंदी)", "English"], key="lang_sel", label_visibility="collapsed")
            st.session_state.quiz_language = lang_choice
        with col_bar3:
            if st.button("❌ Exit", use_container_width=True):
                st.session_state.page = "home"
                st.rerun()
                
        st.markdown(
            f"""
            <div class="pw-top-bar">
                <span>हिंदी | English</span>
                <span class="pw-timer">⏱️ 18:45 &nbsp;&nbsp; प्रश्न {st.session_state.current_q_index + 1}/{total_q}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        with st.expander("📌 Question Index Palette (प्रश्न सूची)", expanded=False):
            cols_per_row = 10
            for row_start in range(0, total_q, cols_per_row):
                idx_cols = st.columns(cols_per_row)
                for c_idx, q_num in enumerate(range(row_start, min(row_start + cols_per_row, total_q))):
                    with idx_cols[c_idx]:
                        is_ans = st.session_state.user_answers.get(q_num) is not None
                        b_label = f"🟢 {q_num+1}" if is_ans else f"⚪ {q_num+1}"
                        if st.button(b_label, key=f"idx_{q_num}", use_container_width=True):
                            st.session_state.current_q_index = q_num
                            st.rerun()
                            
        st.markdown("---")
        
        curr_idx = st.session_state.current_q_index
        q = quiz[curr_idx]
        
        st.markdown(f"**{q['question']}**")
        st.write("")
        
        saved_ans = st.session_state.user_answers.get(curr_idx, None)
        try:
            def_idx = q['options'].index(saved_ans) if saved_ans in q['options'] else None
        except ValueError:
            def_idx = None
            
        chosen_opt = st.radio("विकल्प चुनें:", q['options'], index=def_idx, key=f"rad_{curr_idx}")
        st.session_state.user_answers[curr_idx] = chosen_opt
        st.markdown("---")
        
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if curr_idx > 0 and st.button("⬅ Previous", use_container_width=True):
                st.session_state.current_q_index -= 1
                st.rerun()
        with c2:
            if curr_idx < total_q - 1 and st.button("Next ➡", use_container_width=True):
                st.session_state.current_q_index += 1
                st.rerun()
        with c3:
            if st.button("Submit Test", use_container_width=True, type="primary"):
                st.session_state.quiz_submitted = True
                score = sum(1 for i, item in enumerate(quiz) if st.session_state.user_answers.get(i) == item['answer'])
                percentage = round((score / total_q) * 100, 1) if total_q > 0 else 0
                st.session_state.quiz_history.append({
                    "time": time.strftime("%Y-%m-%d %H:%M"),
                    "exam_info": st.session_state.current_exam_info,
                    "score": score,
                    "total": total_q,
                    "percentage": percentage
                })
                st.session_state.page = "quiz_results"
                st.rerun()
    # --- TEST RESULT & QUIZ ANALYSIS ---
elif page == "quiz_results":
    if st.button("🏠 Home"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🏆 Test Result")
    quiz = st.session_state.quiz_data
    user_ans = st.session_state.user_answers
    
    total = len(quiz)
    score = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) == q['answer'])
    unattempted = sum(1 for idx in range(total) if user_ans.get(idx) is None)
    incorrect = total - score - unattempted
    percentage = round((score / total) * 100, 1) if total > 0 else 0
    
    st.markdown(f"""
    <div class="card" style="text-align:center;">
        <h3 style="color:#00d2ff;">Test Result</h3>
        <h2 style="color:#ffffff;">{score}/{total}</h2>
        <h3 style="color:#00e676;">{percentage}%</h3>
        <hr style="border-color:#2a1b48;">
        <div style="display:flex; justify-content:space-around;">
            <div style="background:#0b3c22; padding:10px 20px; border-radius:10px;">सही<br><b style="color:#00e676; font-size:18px;">{score}</b></div>
            <div style="background:#4a1525; padding:10px 20px; border-radius:10px;">गलत<br><b style="color:#ff5252; font-size:18px;">{incorrect}</b></div>
            <div style="background:#261f3d; padding:10px 20px; border-radius:10px;">छोड़े गए<br><b style="color:#ffeb3b; font-size:18px;">{unattempted}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("📊 Quiz Analysis", use_container_width=True, type="primary"):
        st.session_state.page = "quiz_analysis"
        st.rerun()
        
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

    st.markdown(
        """
        <div style="text-align:center; color:#b0a8c2; margin-top:20px; font-style:italic;">
        “मेहनत कभी बेकार नहीं जाती, बस समय लगता है।”<br>— Prateek Senmar
        </div>
        """,
        unsafe_allow_html=True
    )

elif page == "quiz_analysis":
    if st.button("⬅ Back to Result"):
        st.session_state.page = "quiz_results"
        st.rerun()
        
    st.markdown("### 📊 Quiz Analysis")
    quiz = st.session_state.quiz_data
    user_ans = st.session_state.user_answers
    
    total = len(quiz)
    correct_count = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) == q['answer'])
    wrong_count = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) is not None and user_ans.get(idx) != q['answer'])
    skipped_count = sum(1 for idx in range(total) if user_ans.get(idx) is None)
    
    # Analysis Summary Cards (Clickable via radio filter)
    st.markdown(f"""
    <div class="card" style="background:#0b3c22; border:1px solid #00e676;">
        <b>Correct Questions</b><span style="float:right; font-size:18px;"><b>{correct_count}</b></span><br>
        <span style="font-size:12px; color:#b0a8c2;">क्लिक करके संबंधित प्रश्न देखें →</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="card" style="background:#4a1525; border:1px solid #ff5252;">
        <b>Wrong Questions</b><span style="float:right; font-size:18px;"><b>{wrong_count}</b></span><br>
        <span style="font-size:12px; color:#b0a8c2;">क्लिक करके संबंधित प्रश्न देखें →</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="card" style="background:#261f3d; border:1px solid #a855f7;">
        <b>Skipped Questions</b><span style="float:right; font-size:18px;"><b>{skipped_count}</b></span><br>
        <span style="font-size:12px; color:#b0a8c2;">क्लिक करके संबंधित प्रश्न देखें →</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    analysis_filter = st.radio(
        "फ़िल्टर चुनें:",
        ["सभी देखें (All)", "🟢 Correct", "🔴 Wrong", "🟡 Skipped"],
        horizontal=True
    )
    
    st.write("")
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx, None)
        correct = q['answer']
        
        if chosen is None:
            status = "skipped"
        elif chosen == correct:
            status = "right"
        else:
            status = "wrong"
            
        if "Correct" in analysis_filter and status != "right":
            continue
        if "Wrong" in analysis_filter and status != "wrong":
            continue
            
        if "Skipped" in analysis_filter and status != "skipped":
            continue
            
        badge = "🟢 सही" if status == "right" else ("🔴 गलत" if status == "wrong" else "🟡 छोड़ा गया")
        chosen_txt = chosen if chosen is not None else "उत्तर नहीं दिया"
        
        with st.expander(f"प्रश्न {idx+1}: {q['question']} [{badge}]"):
            st.markdown(f"👉 आपका उत्तर: **{chosen_txt}**")
            st.markdown(f"🎯 सही उत्तर: <span style='color: #00e676; font-weight: bold;'>{correct}</span>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(f"💡 **समाधान:**\n\n{q.get('explanation', 'समाधान उपलब्ध नहीं है।')}")
        
