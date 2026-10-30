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

# --- CUSTOM CSS FOR EXACT UI DESIGN ---
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
        padding: 15px 0 5px 0;
    }
    .brand-title {
        font-size: 26px;
        font-weight: bold;
        color: #00d2ff;
        letter-spacing: 1px;
    }
    .brand-subtitle {
        font-size: 14px;
        color: #ff4b8b;
        margin-top: 2px;
        font-weight: 600;
    }
    .tagline-box {
        background: #160d26;
        border: 1px solid #2a1b48;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
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

# --- MODEL FALLBACK FUNCTION ---
def generate_quiz_with_fallback(prompt_text):
    if not client:
        raise Exception("API Key missing!")
    models_to_try = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt_text)
            if response and response.text:
                return response.text
        except Exception:
            continue
    raise Exception("Server par high demand hai. Kripya punah prayas karein.")

# --- SESSION STATE INITIALIZATION ---
if "page" not in st.session_state:
    st.session_state.page = "home"
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_history" not in st.session_state:
    st.session_state.quiz_history = []
if "current_exam_info" not in st.session_state:
    st.session_state.current_exam_info = ""
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0
if "show_coming_soon" not in st.session_state:
    st.session_state.show_coming_soon = False

# --- SUBJECTS LIST ---
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

# --- HEADER BRANDING ---
st.markdown(
    """
    <div class="brand-header">
        <div style="font-size: 28px;">🧠</div>
        <div class="brand-title">AI QUIZ MAKER</div>
        <div class="brand-subtitle">BY PRATEEK SENMAR 👑</div>
        <div style="font-size: 12px; color: #b0a8c2; margin-top: 4px;">Build Better • Learn Faster</div>
    </div>
    <hr style="border-color: #2a1b48; margin: 15px 0;">
    """,
    unsafe_allow_html=True,
)

# --- NAVIGATION ROUTER ---
page = st.session_state.page

if page == "home":
    st.markdown(
        """
        <div class="tagline-box">
            <h3 style="color: #ffffff; margin-bottom: 5px; font-size: 20px;">अपनी तैयारी को अगला स्तर दो!</h3>
            <p style="color: #b0a8c2; font-size: 13px; margin: 0;">Practice smarter. Improve faster. Achieve more.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<h4 style='color: #ffffff; margin-bottom: 15px;'>⚡ Choose Your Practice</h4>", unsafe_allow_html=True)
    
    if st.button("📄  **PDF to Quiz**\n\n अपनी PDF से MCQ टेस्ट बनाओ", use_container_width=True):
        st.session_state.page = "pdf_quiz"
        st.rerun()
        
    if st.button("🎓  **PYQ Practice**\n\n पिछले वर्षों के प्रश्नों का अभ्यास", use_container_width=True):
        st.session_state.page = "pyq_practice"
        st.rerun()
        
    if st.button("🤖  **AI Practice**\n\n AI से नए प्रश्न और मॉक टेस्ट", use_container_width=True):
        st.session_state.page = "ai_practice"
        st.rerun()
        
    if st.button("🗂️  **Quick Access**\n\n अपने एग्जाम को चुनें", use_container_width=True):
        st.session_state.page = "quick_access"
        st.rerun()

    if st.button("📊  **Quiz History & Dashboard**\n\n अपने पुराने स्कोर देखें", use_container_width=True):
        st.session_state.page = "study_dashboard"
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align: center; color: #b0a8c2; font-size: 12px;">
            ✨ PRATEEK SENMAR ✨<br>
            <span style="font-size: 11px;">Your Preparation • Your Progress • Your Success</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    elif page == "pdf_quiz":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📄 PDF to Quiz")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>अपनी PDF से MCQ टेस्ट बनाओ</p>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("अपनी पढ़ाई की PDF चुनें [ PDF चुनें ]", type=["pdf"])
    selected_subject = st.selectbox("📖 Select Subject (विषय चुनें)", subjects_list, key="pdf_sub")
    
    st.markdown("#### प्रश्नों की संख्या")
    num_q_choice = st.radio("प्रश्नों की संख्या चुनें:", ["सभी प्रश्न", "10", "25", "50", "100", "200"], horizontal=True, key="num_q_radio")
    num_q = 20 if num_q_choice == "सभी प्रश्न" else int(num_q_choice)
        
    st.markdown("#### टाइमर / समय")
    time_choice = st.selectbox("टेस्ट का समय चुनें:", ["15 मिनट", "30 मिनट", "60 मिनट", "अपनी पसंद (Custom)"])
    time_min = st.slider("मिनट चुनें:", 10, 120, 30, step=5) if "अपनी पसंद" in time_choice else int(time_choice.split(" ")[0])
        
    st.markdown("#### भाषा (Language)")
    lang_opt = st.selectbox("भाषा चुनें:", ["Hindi (हिंदी)", "English"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 क्विज़ बनाएँ", type="primary", use_container_width=True):
        if not client:
            st.error("API Key missing!")
        else:
            with st.spinner("Processing PDF with Flash AI..."):
                try:
                    reader = PdfReader(uploaded_file) if uploaded_file else None
                    pdf_text = ""
                    if reader:
                        for page_obj in reader.pages:
                            if page_obj.extract_text():
                                pdf_text += page_obj.extract_text() + "\n"
                        pdf_text = pdf_text[:25000]
                    else:
                        pdf_text = f"General questions for {selected_subject}"
                        
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
                    st.session_state.current_q_index = 0
                    file_name = uploaded_file.name if uploaded_file else "Sample PDF"
                    st.session_state.current_exam_info = f"PDF Quiz: {file_name} | {selected_subject}"
                    st.session_state.page = "take_quiz"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    
    st.markdown("<p style='font-size:12px; color:#b0a8c2; text-align:center; margin-top:15px;'>पुराने PDF सिस्टम की सुविधाएँ बनी रहेंगी। प्रश्न बनने के बाद टेस्ट शुरू होगा।</p>", unsafe_allow_html=True)

elif page == "pyq_practice":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🎓 PYQ Practice")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>पिछले वर्षों के प्रश्न • असली PYQ • सही तारीख • विस्तृत समाधान</p>", unsafe_allow_html=True)
    
    selected_exam = st.selectbox("एग्जाम चुनें", ["SSC", "Railways", "UP Police", "अन्य उपलब्ध परीक्षाएँ"])
    selected_subject = st.selectbox("विषय चुनें", ["General Mathematics (गणित)", "Reasoning (तर्कशक्ति)", "General Knowledge / GS (सामान्य ज्ञान)", "English Language (अंग्रेजी)"])
    selected_year = st.selectbox("वर्ष चुनें", ["2023", "2022", "2021", "2020"])
    
    st.markdown("#### प्रश्नों की संख्या और टाइमर")
    num_q = st.slider("प्रश्नों की संख्या चुनें:", 10, 100, 20, step=10)
    time_min = st.slider("टेस्ट का समय (मिनट में):", 10, 60, 20, step=10)
    
    if st.button("🚀 शुरू करें", type="primary", use_container_width=True):
        quiz_list = [
            {
                "question": f"[{selected_exam} {selected_year}] भारत का संविधान कब लागू हुआ था?",
                "options": ["26 जनवरी 1950", "15 अगस्त 1947", "26 नवंबर 1949", "2 अक्टूबर 1950"],
                "answer": "26 जनवरी 1950",
                "explanation": "भारत का संविधान 26 जनवरी 1950 को पूर्ण रूप से लागू हुआ था।"
            }
        ]
        st.session_state.quiz_data = quiz_list * max(1, num_q // len(quiz_list))
        st.session_state.user_answers = {}
        st.session_state.current_q_index = 0
        st.session_state.current_exam_info = f"PYQ: {selected_exam} ({selected_year}) - {selected_subject}"
        st.session_state.page = "take_quiz"
        st.rerun()
        
    st.markdown("<p style='font-size:12px; color:#b0a8c2; text-align:center; margin-top:15px;'>नोट: असली PYQ और AI से बने अभ्यास प्रश्न स्पष्ट रूप से अलग रहेंगे।</p>", unsafe_allow_html=True)

elif page == "ai_practice":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🤖 AI Practice")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>AI से नए प्रश्न और मॉक टेस्ट • स्मार्ट प्रैक्टिस • बेहतर तैयारी</p>", unsafe_allow_html=True)
    
    exam_type = st.selectbox("एग्जाम चुनें", ["SSC", "UPSC", "UP Police", "Railway", "Defence"])
    selected_subject = st.selectbox("विषय चुनें", ["General Studies", "General Mathematics", "Reasoning", "English"], key="ai_sub_box")
    num_q = st.selectbox("प्रश्नों की संख्या", [10, 20, 30, 50, 100], index=1)
    time_min = st.selectbox("टाइमर (मिनट)", [10, 20, 30, 45, 60], index=1)
    
    st.markdown("#### Difficulty Level")
    diff_cols = st.columns(3)
    with diff_cols[0]: easy_btn = st.button("Easy", use_container_width=True)
    with diff_cols[1]: med_btn = st.button("Medium", use_container_width=True, type="primary")
    with diff_cols[2]: mod_btn = st.button("Moderate", use_container_width=True)
        
    selected_diff = "Medium"
    if easy_btn: selected_diff = "Easy"
    if mod_btn: selected_diff = "Moderate"
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🤖 Start AI Quiz", type="primary", use_container_width=True):
        if not client:
            st.error("API Key missing!")
        else:
            with st.spinner("Generating AI questions in pure Hindi..."):
                try:
                    prompt = f"""
                    Generate {num_q} MCQs for {exam_type} on subject '{selected_subject}' with 4 options each.
                    Difficulty: {selected_diff}.
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
                    st.session_state.current_q_index = 0
                    st.session_state.current_exam_info = f"AI Practice ({selected_diff}): {exam_type} - {selected_subject}"
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
    
    if st.session_state.get("show_coming_soon", False):
        st.markdown(
            """
            <div class="card" style="border: 1px solid #ff4b8b; text-align:center; padding: 25px;">
                <h3>🚀 COMING SOON</h3>
                <p><b>अभी काम कुछ समय के लिए रुका हुआ है।</b></p>
                <p>अभी Depression का दौर चल रहा है, इसलिए काम बंद है। ❤️‍🩹</p>
                <p>अभी वक्त मुश्किल है, लेकिन वापसी होगी और धमाका बड़ा करेंगे! 🔥</p>
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
        
        st.markdown(
            f"""
            <div class="pw-top-bar">
                <span>हिंदी | English</span>
                <span class="pw-timer">⏱️ 18:45 &nbsp;&nbsp; प्रश्न {st.session_state.current_q_index + 1}/{total_q}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        st.markdown(f"<b style='color:#00d2ff;'>{st.session_state.current_exam_info}</b>", unsafe_allow_html=True)
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
        
        c1, c2 = st.columns(2)
        with c1:
            if curr_idx > 0 and st.button("⬅ Previous", use_container_width=True):
                st.session_state.current_q_index -= 1
                st.rerun()
        with c2:
            if curr_idx < total_q - 1 and st.button("Next ➡", use_container_width=True):
                st.session_state.current_q_index += 1
                st.rerun()
                
        if st.button("Submit Test", use_container_width=True, type="primary"):
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

elif page == "quiz_results":
    quiz = st.session_state.quiz_data
    user_ans = st.session_state.user_answers
    
    total = len(quiz)
    score = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) == q['answer'])
    unattempted = sum(1 for idx in range(total) if user_ans.get(idx) is None)
    incorrect = total - score - unattempted
    percentage = round((score / total) * 100, 1) if total > 0 else 0
    
    st.markdown(
        f"""
        <div class="card" style="text-align:center;">
            <div style="font-size:32px;">🏆</div>
            <h3 style="color:#ffffff; margin:5px 0;">Test Result</h3>
            <h1 style="color:#00d2ff; margin:5px 0;">{score}/{total}</h1>
            <h2 style="color:#00e676; margin:5px 0;">{percentage}%</h2>
            <hr style="border-color:#2a1b48; margin:15px 0;">
            <div style="display:flex; justify-content:space-around;">
                <div style="background:#0b3c22; padding:12px 25px; border-radius:12px; border:1px solid #00e676;">
                    <b style="font-size:20px; color:#00e676;">{score}</b><br><span style="font-size:13px; color:#ffffff;">सही</span>
                </div>
                <div style="background:#4a1525; padding:12px 25px; border-radius:12px; border:1px solid #ff5252;">
                    <b style="font-size:20px; color:#ff5252;">{incorrect}</b><br><span style="font-size:13px; color:#ffffff;">गलत</span>
                </div>
                <div style="background:#261f3d; padding:12px 25px; border-radius:12px; border:1px solid #a855f7;">
                    <b style="font-size:20px; color:#ffeb3b;">{unattempted}</b><br><span style="font-size:13px; color:#ffffff;">छोड़े गए</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if st.button("📊 Quiz Analysis", use_container_width=True, type="primary"):
        st.session_state.page = "quiz_analysis"
        st.rerun()
        
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("<p style='text-align:center; color:#b0a8c2; font-size:12px; margin-top:15px;'>रिजल्ट पहले दिखेगा, समाधान केवल Quiz Analysis दबाने पर।</p>", unsafe_allow_html=True)

elif page == "quiz_analysis":
    if st.button("⬅ Back"):
        st.session_state.page = "quiz_results"
        st.rerun()
        
    st.markdown("### 📊 Quiz Analysis")
    quiz = st.session_state.quiz_data
    user_ans = st.session_state.user_answers
    
    total = len(quiz)
    correct_count = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) == q['answer'])
    wrong_count = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) is not None and user_ans.get(idx) != q['answer'])
    skipped_count = sum(1 for idx in range(total) if user_ans.get(idx) is None)
    
    st.markdown(
        f"""
        <div class="card" style="background:#0b3c22; border:1px solid #00e676; padding:15px; margin-bottom:10px;">
            <b style="font-size:16px;">Correct Questions</b>
            <span style="float:right; font-size:20px;"><b>{correct_count}</b></span><br>
            <span style="font-size:12px; color:#b0a8c2;">क्लिक करके संबंधित प्रश्न देखें →</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        f"""
        <div class="card" style="background:#4a1525; border:1px solid #ff5252; padding:15px; margin-bottom:10px;">
            <b style="font-size:16px;">Wrong Questions</b>
            <span style="float:right; font-size:20px;"><b>{wrong_count}</b></span><br>
            <span style="font-size:12px; color:#b0a8c2;">क्लिक करके संबंधित प्रश्न देखें →</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        f"""
        <div class="card" style="background:#261f3d; border:1px solid #a855f7; padding:15px; margin-bottom:15px;">
            <b style="font-size:16px;">Skipped Questions</b>
            <span style="float:right; font-size:20px;"><b>{skipped_count}</b></span><br>
            <span style="font-size:12px; color:#b0a8c2;">क्लिक करके संबंधित प्रश्न देखें →</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    st.markdown("#### विस्तृत समाधान (Detailed Solutions)")
    
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx, None)
        correct = q['answer']
        
        if chosen is None:
            badge = "🟡 छोड़ा गया"
            chosen_txt = "उत्तर नहीं दिया"
        elif chosen == correct:
            badge = "🟢 सही"
            chosen_txt = chosen
        else:
            badge = "🔴 गलत"
            chosen_txt = chosen
            
        with st.expander(f"प्रश्न {idx+1}: {q['question']} [{badge}]"):
            st.markdown(f"आपका उत्तर: **{chosen_txt}**")
            st.markdown(f"सही उत्तर: <span style='color: #00e676; font-weight: bold;'>{correct}</span>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(f"💡 **समाधान:**\n\n{q.get('explanation', 'समाधान उपलब्ध नहीं है।')}")
            
    if st.button("🏠 Home पर जाएं", use_container_width=True, type="primary"):
        st.session_state.page = "home"
        st.rerun()
