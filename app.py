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
    .solution-box {
        background: #101826;
        border-left: 4px solid #00e676;
        padding: 12px;
        border-radius: 8px;
        margin-top: 8px;
        font-size: 14px;
        color: #e0e0e0;
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
    models_to_try = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt_text)
            if response and response.text:
                return response.text
        except Exception:
            continue
    raise Exception("Server par high demand hai. Kripya punah prayas karein.")

def parse_json_safely(raw_text):
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
            
    raise Exception("JSON parsing failed. Kripya doosra test try karein.")

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
if "analysis_filter" not in st.session_state:
    st.session_state.analysis_filter = "All"
if "quiz_start_time" not in st.session_state:
    st.session_state.quiz_start_time = 0.0
if "quiz_duration_mins" not in st.session_state:
    st.session_state.quiz_duration_mins = 20
if "ai_diff_level" not in st.session_state:
    st.session_state.ai_diff_level = "Medium"

# --- EXAM WISE SUBJECTS MAPPING ---
exam_subjects_map = {
    "SSC CGL": [
        "Quantitative Aptitude (गणित)",
        "General Intelligence & Reasoning (तर्कशक्ति)",
        "English Comprehension (अंग्रेजी)",
        "General Awareness / GS (सामान्य जागरूकता)",
        "Complete SSC CGL Tier-1 Mock"
    ],
    "SSC GD": [
        "General Intelligence & Reasoning (तर्कशक्ति)",
        "General Knowledge & General Awareness (सामान्य ज्ञान)",
        "Elementary Mathematics (प्रारंभिक गणित)",
        "Hindi / English (हिंदी / अंग्रेजी)",
        "Complete SSC GD Mock Test"
    ],
    "SSC CHSL": [
        "Quantitative Aptitude (गणित)",
        "Reasoning (तर्कशक्ति)",
        "English Language (अंग्रेजी)",
        "General Awareness (सामान्य ज्ञान)"
    ],
    "SSC MTS": [
        "Numerical and Mathematical Ability (गणित)",
        "Reasoning Ability and Problem Solving (तर्कशक्ति)",
        "General Awareness (सामान्य जागरूकता)",
        "English Language and Comprehension (अंग्रेजी)"
    ],
    "SSC CPO": [
        "Quantitative Aptitude (गणित)",
        "General Reasoning (तर्कशक्ति)",
        "English Language (अंग्रेजी)",
        "General Knowledge & General Awareness (सामान्य ज्ञान)"
    ],
    "Railway RRB NTPC": [
        "Mathematics (गणित)",
        "General Intelligence & Reasoning (सामान्य बुद्धि एवं तर्क)",
        "General Awareness & Current Affairs (सामान्य जागरूकता एवं समसामयिक)",
        "Complete RRB NTPC CBT-1 Mock"
    ],
    "Railway RRB Group D": [
        "Mathematics (गणित)",
        "General Intelligence & Reasoning (तर्कशक्ति)",
        "General Science - Physics, Chemistry, Biology (सामान्य विज्ञान)",
        "General Awareness & Current Affairs (सामान्य जागरूकता)"
    ],
    "UPSC Civil Services": [
        "General Studies Paper I (इतिहास, भूगोल, राजव्यवस्था, अर्थव्यवस्था)",
        "CSAT - Quantitative & Reasoning",
        "Environment, Science & Tech (पर्यावरण एवं विज्ञान)",
        "Complete UPSC Prelims GS Mock"
    ],
    "UP Police Constable / SI": [
        "General Hindi (सामान्य हिंदी)",
        "Numerical & Mental Ability (संख्यात्मक एवं मानसिक योग्यता)",
        "Mental Aptitude / IQ / Reasoning (तार्किक क्षमता)",
        "General Knowledge / UP GK (सामान्य ज्ञान एवं यूपी जीके)"
    ],
    "Defence (CDS / NDA / Agniveer)": [
        "Mathematics (गणित)",
        "General English (सामान्य अंग्रेजी)",
        "General Science & Physics (सामान्य विज्ञान एवं भौतिकी)",
        "General Knowledge & Polity (सामान्य ज्ञान)"
    ]
}

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
        
    if st.button("🤖  **AI Practice**\n\n AI से नए प्रश्न और मॉक टेस्ट", use_container_width=True):
        st.session_state.page = "ai_practice"
        st.rerun()
        
    if st.button("🎓  **PYQ Practice**\n\n पिछले वर्षों के प्रश्नों का अभ्यास", use_container_width=True):
        st.session_state.page = "pyq_practice"
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
    all_subjects_flat = [sub for sub_list in exam_subjects_map.values() for sub in sub_list]
    selected_subject = st.selectbox("📖 Select Subject (विषय चुनें)", all_subjects_flat, key="pdf_sub")
    
    st.markdown("#### प्रश्नों की संख्या (Up to 200)")
    num_q_choice = st.radio("प्रश्नों की संख्या चुनें:", ["10", "25", "50", "100", "200"], horizontal=True, key="num_q_radio")
    num_q = int(num_q_choice)
        
    st.markdown("#### टाइमर / समय")
    time_min = st.slider("टेस्ट का समय (मिनट में):", min_value=5, max_value=180, value=30, step=5)
    
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
                        pdf_text = pdf_text[:35000]
                    else:
                        pdf_text = f"General questions for {selected_subject}"
                        
                    lang_instruction = "in pure and simple Hindi language" if "Hindi" in lang_opt else "in English language"
                    prompt = f"""
                    Based strictly on the text for '{selected_subject}', generate {num_q} MCQs with 4 options each.
                    Ensure the 'answer' field matches EXACTLY one of the strings provided in the 'options' list.
                    Provide short, crisp, and clear explanations {lang_instruction}.
                    CRITICAL: EVERY SINGLE question, option, and explanation MUST be strictly generated {lang_instruction}.
                    Output strictly in valid JSON format as a list of objects with keys: 
                    'question', 'options', 'answer', 'explanation'.
                    Text: {pdf_text}
                    """
                    raw_text = generate_quiz_with_fallback(prompt)
                    parsed_quiz = parse_json_safely(raw_text)
                    
                    st.session_state.quiz_data = parsed_quiz
                    st.session_state.user_answers = {}
                    st.session_state.current_q_index = 0
                    st.session_state.quiz_start_time = time.time()
                    st.session_state.quiz_duration_mins = time_min
                    file_name = uploaded_file.name if uploaded_file else "Sample PDF"
                    st.session_state.current_exam_info = f"PDF Quiz: {file_name} | {selected_subject}"
                    st.session_state.page = "take_quiz"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

elif page == "pyq_practice":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🎓 PYQ Practice")
    st.markdown(
        """
        <div class="card" style="border: 1px solid #ff4b8b; text-align:center; padding: 30px; margin-top: 20px;">
            <h3>🚀 COMING SOON</h3>
            <p><b>PYQ Practice पर काम जारी है! 🛠️</b></p>
            <p>बहुत जल्द पिछले वर्षों के सभी प्रश्न और विस्तृत समाधान यहाँ उपलब्ध होंगे।</p>
            <p style="color:#00d2ff; font-style:italic;">“तैयारी मजबूत होगी, थोड़ा इंतज़ार करें!” 🔥</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("🏠 Home पर जाएं", type="primary", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

elif page == "ai_practice":
    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🤖 AI Practice")
    st.markdown("<p style='color:#b0a8c2; font-size:13px;'>AI से नए प्रश्न और मॉक टेस्ट • स्मार्ट प्रैक्टिस • बेहतर तैयारी</p>", unsafe_allow_html=True)
    
    selected_exam = st.selectbox("एग्जाम चुनें", list(exam_subjects_map.keys()), key="ai_exam_sel")
    dynamic_subjects = exam_subjects_map.get(selected_exam, ["General Studies"])
    selected_subject = st.selectbox("विषय चुनें", dynamic_subjects, key="ai_sub_box")
    
    num_q = st.selectbox("प्रश्नों की संख्या (Up to 200)", [10, 20, 30, 50, 100, 150, 200], index=1)
    time_min = st.slider("टेस्ट का समय (मिनट में):", min_value=5, max_value=180, value=30, step=5)
    
    st.markdown("#### भाषा (Language)")
    lang_opt = st.selectbox("भाषा चुनें:", ["Hindi (हिंदी)", "English"], key="ai_lang_sel")
    
    st.markdown("#### Difficulty Level (स्तर चुनें)")
    diff_options = ["Easy", "Medium", "Hard"]
    selected_diff = st.radio("कठिनाई स्तर चुनें:", diff_options, horizontal=True, index=diff_options.index(st.session_state.ai_diff_level))
    st.session_state.ai_diff_level = selected_diff
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🤖 Start AI Quiz", type="primary", use_container_width=True):
        if not client:
            st.error("API Key missing!")
        else:
            with st.spinner(f"Generating AI questions ({selected_diff})..."):
                try:
                    lang_instruction = "in pure and simple Hindi language" if "Hindi" in lang_opt else "in English language"
                    prompt = f"""
                    Generate {num_q} MCQs for {selected_exam} on subject '{selected_subject}' with 4 options each.
                    Difficulty: {selected_diff}.
                    CRITICAL: The 'answer' field MUST match EXACTLY one of the strings given in the 'options' list. 
                    Provide short, concise, and clear explanations {lang_instruction}.
                    CRITICAL: EVERY SINGLE question, option, and explanation MUST be strictly generated {lang_instruction}.
                    Output strictly in valid JSON list format with keys: 'question', 'options', 'answer', 'explanation'.
                    """
                    raw_text = generate_quiz_with_fallback(prompt)
                    parsed_quiz = parse_json_safely(raw_text)
                    
                    st.session_state.quiz_data = parsed_quiz
                    st.session_state.user_answers = {}
                    st.session_state.current_q_index = 0
                    st.session_state.quiz_start_time = time.time()
                    st.session_state.quiz_duration_mins = time_min
                    st.session_state.current_exam_info = f"AI Practice ({selected_diff}): {selected_exam} - {selected_subject}"
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
            if st.button("🏛️ SSC CGL\nAvailable", use_container_width=True):
                st.session_state.current_exam_info = "Quick Access: SSC CGL"
                st.session_state.quiz_data = [{
                    "question": "भारत का संविधान कब लागू हुआ था?",
                    "options": ["26 जनवरी 1950", "15 अगस्त 1947", "26 नवंबर 1949", "2 अक्टूबर 1950"],
                    "answer": "26 जनवरी 1950",
                    "explanation": "संविधान 26 जनवरी 1950 को पूर्ण रूप से लागू हुआ था।"
                }] * 10
                st.session_state.user_answers = {}
                st.session_state.current_q_index = 0
                st.session_state.quiz_start_time = time.time()
                st.session_state.quiz_duration_mins = 20
                st.session_state.page = "take_quiz"
                st.rerun()
            if st.button("🛡️ SSC GD\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("🚆 RRB NTPC\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("⭐ UPSC\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
        with col2:
            if st.button("🚆 RRB Group D\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("👮 UP Police\nComing Soon", use_container_width=True):
                st.session_state.show_coming_soon = True
                st.rerun()
            if st.button("🏢 SSC CHSL\nComing Soon", use_container_width=True):
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
        format_total_q = len(quiz)
        curr_idx = st.session_state.current_q_index
        
        col_tb1, col_tb2, col_tb3 = st.columns([1, 1, 1.2])
        with col_tb1:
            if st.button("⬅ Back", use_container_width=True):
                st.session_state.page = "home"
                st.rerun()
        with col_tb2:
            st.selectbox("Lang", ["Hindi (हिंदी)", "English"], key="active_in_quiz_lang", label_visibility="collapsed")
        with col_tb3:
            elapsed_seconds = int(time.time() - st.session_state.quiz_start_time)
            total_allowed_seconds = st.session_state.quiz_duration_mins * 60
            remaining_seconds = max(0, total_allowed_seconds - elapsed_seconds)
            rem_mins = remaining_seconds // 60
            rem_secs = remaining_seconds % 60
            
            st.markdown(
                f"""
                <div style="text-align: right; padding-top: 5px;">
                    <span style="color: #ff4b8b; font-weight: bold; font-size: 12px; background: #160d26; padding: 4px 6px; border-radius: 8px; border: 1px solid #2a1b48;">
                        ⏱️ {rem_mins:02d}:{rem_secs:02d} | Q {curr_idx + 1}/{format_total_q}
                    </span>
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        st.markdown(f"<b style='color:#00d2ff;'>{st.session_state.current_exam_info}</b>", unsafe_allow_html=True)
        st.markdown("---")
        
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
            if curr_idx < format_total_q - 1 and st.button("Next ➡", use_container_width=True):
                st.session_state.current_q_index += 1
                st.rerun()
                
        if st.button("Submit Test", use_container_width=True, type="primary"):
            score = sum(1 for i, item in enumerate(quiz) if st.session_state.user_answers.get(i) == item['answer'])
            percentage = round((score / format_total_q) * 100, 1) if format_total_q > 0 else 0
            st.session_state.quiz_history.append({
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "exam_info": st.session_state.current_exam_info,
                "score": score,
                "total": format_total_q,
                "percentage": percentage
            })
            st.session_state.page = "quiz_results"
            st.rerun()

        if remaining_seconds <= 0:
            st.warning("समय समाप्त हो गया है! टेस्ट स्वतः सबमिट हो रहा है...")
            time.sleep(2)
            score = sum(1 for i, item in enumerate(quiz) if st.session_state.user_answers.get(i) == item['answer'])
            percentage = round((score / format_total_q) * 100, 1) if format_total_q > 0 else 0
            st.session_state.quiz_history.append({
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "exam_info": st.session_state.current_exam_info,
                "score": score,
                "total": format_total_q,
                "percentage": percentage
            })
            st.session_state.page = "quiz_results"
            st.rerun()
        else:
            time.sleep(1)
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
    
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        if st.button("📊 Quiz Analysis", use_container_width=True, type="primary"):
            st.session_state.analysis_filter = "All"
            st.session_state.page = "quiz_analysis"
            st.rerun()
    with c_res2:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
            
    st.markdown("<p style='text-align:center; color:#b0a8c2; font-size:12px; margin-top:15px;'>रिजल्ट पहले दिखेगा, समाधान केवल Quiz Analysis दबाने पर।</p>", unsafe_allow_html=True)

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
    
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        if st.button(f"🟢 Correct\n\n{correct_count}", use_container_width=True):
            st.session_state.analysis_filter = "Correct"
            st.rerun()
    with col_a2:
        if st.button(f"🔴 Wrong\n\n{wrong_count}", use_container_width=True):
            st.session_state.analysis_filter = "Wrong"
            st.rerun()
    with col_a3:
        if st.button(f"🟡 Skipped\n\n{skipped_count}", use_container_width=True):
            st.session_state.analysis_filter = "Skipped"
            st.rerun()
            
    st.markdown("---")
    
    filter_options = ["All", "Correct", "Wrong", "Skipped"]
    current_default_idx = filter_options.index(st.session_state.analysis_filter) if st.session_state.analysis_filter in filter_options else 0
    
    selected_filter = st.radio(
        "फ़िल्टर चुनें:",
        filter_options,
        index=current_default_idx,
        horizontal=True,
        key="analysis_radio_filter"
    )
    st.session_state.analysis_filter = selected_filter
    
    st.markdown(f"#### वर्तमान फ़िल्टर: <span style='color:#00d2ff;'>{selected_filter} Questions</span>", unsafe_allow_html=True)
    st.write("")
    
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx, None)
        correct = q['answer']
        
        if chosen is None:
            status = "Skipped"
            badge = "🟡 छोड़ा गया"
            chosen_txt = "उत्तर नहीं दिया"
        elif chosen == correct:
            status = "Correct"
            badge = "🟢 सही"
            chosen_txt = chosen
        else:
            status = "Wrong"
            badge = "🔴 गलत"
            chosen_txt = chosen
            
        if st.session_state.analysis_filter != "All" and status != st.session_state.analysis_filter:
            continue
            
        with st.expander(f"Prashn {idx+1}: {q['question']} [{badge}]"):
            st.markdown(f"**Poora Prashn:**\n\n{q['question']}")
            st.markdown(f"Aapka Uttar: **{chosen_txt}**")
            st.markdown(f"Sahi Uttar: <span style='color: #00e676; font-weight: bold;'>{correct}</span>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="solution-box">
                    <b>💡 Saral Samadhan:</b><br>{q.get('explanation', 'Samadhan uplabdh nahi hai.')}
                </div>
                """,
                unsafe_allow_html=True
            )
            
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 Home par jaen", use_container_width=True, type="primary"):
        st.session_state.page = "home"
        st.rerun()
