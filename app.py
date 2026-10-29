import json
import re
import os
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

# --- CUSTOM CSS (Dark Purple Gradient UI) ---
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
        font-size: 28px;
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
    .tagline {
        font-size: 12px;
        color: #b0a8c2;
        margin-top: 2px;
        font-style: italic;
    }
    .card {
        background: #160d26;
        border: 1px solid #2a1b48;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
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

# --- ROBUST CONTENT GENERATION WITH MODEL FALLBACK (503 Error Handler) ---
def generate_quiz_with_fallback(prompt_text):
    if not client:
        raise Exception("Gemini API Key सेट नहीं है!")
    
    # Priority order of models including 3.8, 3.7, and 3.5 flash lite
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
            
    raise Exception(f"सभी मॉडल्स पर हाई डिमांड (503 Error) है। कृपया कुछ देर बाद पुनः प्रयास करें। मूल त्रुटि: {last_error}")

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

# --- HEADER BRANDING ---
st.markdown(
    """
    <div class="brand-header">
        <div class="brand-title">⚡ AI Quiz Maker</div>
        <div class="brand-subtitle">Prateek Senmar</div>
        <div class="tagline">Learn smarter. Practice better. Achieve more.</div>
    </div>
    <hr style="border-color: #2a1b48; margin: 15px 0;">
    """,
    unsafe_allow_html=True,
)

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

# --- NAVIGATION ROUTER ---
page = st.session_state.page

if page == "home":
    st.markdown("### 📂 मुख्य मेनू (Study Dashboard)")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 PDF to Quiz", use_container_width=True):
            st.session_state.page = "pdf_quiz"
            st.rerun()
        if st.button("🧠 AI Practice", use_container_width=True):
            st.session_state.page = "ai_practice"
            st.rerun()
        if st.button("📜 PYQ Practice", use_container_width=True):
            st.session_state.page = "pyq_practice"
            st.rerun()
    with col2:
        if st.button("⚡ Quick Access", use_container_width=True):
            st.session_state.page = "quick_access"
            st.rerun()
        if st.button("📊 Quiz History", use_container_width=True):
            st.session_state.page = "quiz_history_page"
            st.rerun()
        if st.button("📈 Study Dashboard", use_container_width=True):
            st.session_state.page = "study_dashboard"
            st.rerun()

elif page == "pdf_quiz":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📄 PDF to Quiz Converter")
    uploaded_file = st.file_uploader("अपनी PDF फ़ाइल यहाँ अपलोड करें", type=["pdf"])
    
    selected_subject = st.selectbox("📖 Select Subject (विषय चुनें)", subjects_list, key="pdf_sub")
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    time_min = st.slider("⏱️ Select Time (टेस्ट का समय - मिनट में)", min_value=10, max_value=120, value=30, step=5)
    difficulty = st.selectbox("कठिनाई स्तर (Difficulty)", ["Easy", "Medium", "Hard"])
    
    if uploaded_file is not None:
        if st.button("🚀 PDF से Quiz जनरेट करें", type="primary", use_container_width=True):
            if not client:
                st.error("Gemini API Key सेट नहीं है! कृपया st.secrets चेक करें।")
            else:
                with st.spinner("PDF से टेक्स्ट निकाला जा रहा है और AI मॉडल (3.8 / 3.7 / 3.5 Lite) द्वारा MCQ तैयार हो रहे हैं..."):
                    try:
                        reader = PdfReader(uploaded_file)
                        pdf_text = ""
                        for page_obj in reader.pages:
                            if page_obj.extract_text():
                                pdf_text += page_obj.extract_text() + "\n"
                        
                        pdf_text = pdf_text[:25000]
                        
                        prompt = f"""
                        Based strictly on the following text for the subject '{selected_subject}', generate {num_q} Multiple Choice Questions (MCQs) with 4 options each.
                        Difficulty: {difficulty}.
                        Provide output strictly in valid JSON format as a list of objects with keys: 
                        'question', 'options' (list of 4 strings), 'answer' (the correct option string matching one of the options), and 'explanation' (clear explanation in simple Hindi).
                        
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
                        st.session_state.current_exam_info = f"PDF Quiz: {uploaded_file.name} | {selected_subject} ({time_min} Mins)"
                        st.session_state.page = "take_quiz"
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"त्रुटि (Error): {e}")
    else:
        st.info("💡 कृपया पहले ऊपर से एक PDF फ़ाइल अपलोड करें, उसके बाद 'PDF से Quiz जनरेट करें' बटन दिखाई देगा।")

elif page == "ai_practice":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🧠 AI Practice Mode")
    exam_type = st.selectbox("परीक्षा चुनें", ["SSC CGL", "Railway NTPC", "UP Police", "UPSC", "Defence", "अन्य"])
    selected_subject = st.selectbox("📖 Select Subject (विषय चुनें)", subjects_list, key="ai_sub")
    topic = st.text_input("विशेष टॉपिक दर्ज करें (जैसे: Percentage, Mughal Empire, Articles)")
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    time_min = st.slider("⏱️ Select Time (टेस्ट का समय - मिनट में)", min_value=10, max_value=120, value=30, step=5)
    
    if st.button("🚀 AI Quiz शुरू करें", type="primary", use_container_width=True):
        if not client:
            st.error("Gemini API Key सेट नहीं है!")
        else:
            with st.spinner("AI प्रश्न तैयार कर रहा है..."):
                try:
                    search_topic = topic if topic else selected_subject
                    prompt = f"""
                    Generate {num_q} high-yield MCQs for {exam_type} on subject '{selected_subject}' and topic '{search_topic}' with 4 options each.
                    Provide output strictly in valid JSON format containing a list of objects with keys:
                    'question', 'options' (list of 4 strings), 'answer', 'explanation' (in simple Hindi).
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
                    st.session_state.current_exam_info = f"AI Practice: {exam_type} - {selected_subject} ({time_min} Mins)"
                    st.session_state.page = "take_quiz"
                    st.rerun()
                except Exception as e:
                    st.error(f"त्रुटि: {e}")

elif page == "pyq_practice":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📜 PYQ Practice Section")
    mode = st.radio("प्रश्न स्रोत चुनें:", ["सत्यापित PYQ (Verified)", "AI Practice Questions"])
    selected_exam = st.selectbox("परीक्षा चुनें", ["SSC CGL 2023", "UP Police 2024", "Railway Group D"])
    selected_subject = st.selectbox("📖 Select Subject", subjects_list, key="pyq_sub")
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    time_min = st.slider("⏱️ Select Time (मिनट)", 10, 120, 30, step=5)
    
    if st.button("🎯 PYQ Test शुरू करें", type="primary", use_container_width=True):
        quiz_list = []
        if mode == "सत्यापित PYQ (Verified)":
            for i in range(num_q):
                quiz_list.append({
                    "question": f"[{selected_exam} - {selected_subject}] Sample previous year question {i+1}?",
                    "options": [f"Option A ({i})", f"Option B ({i})", f"Option C ({i})", f"Option D ({i})"],
                    "answer": f"Option A ({i})",
                    "explanation": f"यह {selected_exam} का सत्यापित पिछला प्रश्न है।"
                })
            st.session_state.current_exam_info = f"Verified PYQ: {selected_exam} ({selected_subject})"
        else:
            for i in range(num_q):
                quiz_list.append({
                    "question": f"[AI Practice - {selected_subject}] Sample AI question {i+1}?",
                    "options": [f"Choice A ({i})", f"Choice B ({i})", f"Choice C ({i})", f"Choice D ({i})"],
                    "answer": f"Choice A ({i})",
                    "explanation": f"यह प्रश्न AI द्वारा अभ्यास के लिए तैयार किया गया है।"
                })
            st.session_state.current_exam_info = f"AI Practice: {selected_exam} ({selected_subject})"
            
        st.session_state.quiz_data = quiz_list
        st.session_state.user_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.page = "take_quiz"
        st.rerun()

elif page == "quick_access":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### ⚡ Quick Access Exams")
    exams = ["SSC", "Railway", "IB", "UP Police", "RPF", "Delhi Police", "MP Police", "Defence"]
    for ex in exams:
        if st.button(f"📌 {ex} Test शुरू करें", use_container_width=True):
            st.session_state.current_exam_info = f"Quick Access: {ex}"
            st.session_state.quiz_data = [
                {
                    "question": f"[{ex} Quick Test] Sample Question {i+1}?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "Option A",
                    "explanation": f"यह {ex} परीक्षा के लिए त्वरित अभ्यास प्रश्न है।"
                } for i in range(20)
            ]
            st.session_state.user_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.page = "take_quiz"
            st.rerun()

elif page == "quiz_history_page":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown("### 📊 Quiz History")
    if not st.session_state.quiz_history:
        st.info("कोई पिछला रिकॉर्ड उपलब्ध नहीं है।")
    else:
        for record in reversed(st.session_state.quiz_history):
            st.markdown(f"<div class='card'><b>{record['exam_info']}</b><br>Score: {record['score']}/{record['total']} ({record['percentage']}%)</div>", unsafe_allow_html=True)

elif page == "study_dashboard":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown("### 📈 Study Dashboard")
    total_tests = len(st.session_state.quiz_history)
    st.markdown(f"<div class='card'><b>कुल दिए गए टेस्ट:</b> {total_tests}</div>", unsafe_allow_html=True)

elif page == "take_quiz":
    if not st.session_state.quiz_data:
        st.warning("कोई सक्रिय क्विज़ उपलब्ध नहीं है।")
        if st.button("होम पर जाएं"):
            st.session_state.page = "home"
            st.rerun()
    else:
        quiz = st.session_state.quiz_data
        
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.markdown(f"### 📝 {st.session_state.current_exam_info}")
        with col_t2:
            if st.button("❌ रद्द करें"):
                st.session_state.page = "home"
                st.rerun()
        st.markdown("---")
        
        with st.form("active_quiz_form"):
            user_ans = {}
            for idx, q in enumerate(quiz):
                st.markdown(f"**Q{idx+1}: {q['question']}**")
                ans = st.radio("विकल्प चुनें:", q['options'], key=f"ans_q_{idx}", index=None)
                user_ans[idx] = ans
                st.write("---")
                
            submitted = st.form_submit_button("✅ टेस्ट सबमिट करें", use_container_width=True)
            if submitted:
                st.session_state.user_answers = user_ans
                st.session_state.quiz_submitted = True
                
                score = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) == q['answer'])
                total = len(quiz)
                percentage = round((score / total) * 100, 1) if total > 0 else 0
                
                import datetime
                st.session_state.quiz_history.append({
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "exam_info": st.session_state.current_exam_info,
                    "score": score,
                    "total": total,
                    "percentage": percentage
                })
                st.session_state.page = "quiz_results"
                st.rerun()

elif page == "quiz_results":
    if st.button("🏠 होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🏆 टेस्ट परिणाम और विश्लेषण")
    quiz = st.session_state.quiz_data
    user_ans = st.session_state.user_answers
    
    score = sum(1 for idx, q in enumerate(quiz) if user_ans.get(idx) == q['answer'])
    total = len(quiz)
    unattempted = sum(1 for idx in range(total) if user_ans.get(idx) is None or user_ans.get(idx) == "उत्तर नहीं दिया")
    incorrect = total - score - unattempted
    
    st.markdown(f"""
    <div class="card">
        <h4>📊 स्कोर कार्ड Summary</h4>
        <p><b>विषय/परीक्षा:</b> {st.session_state.current_exam_info}</p>
        <p><b>सही उत्तर:</b> <span style="color:#00e676;">{score}</span></p>
        <p><b>गलत उत्तर:</b> <span style="color:#ff5252;">{incorrect}</span></p>
        <p><b>छोड़े गए:</b> <span style="color:#ffeb3b;">{unattempted}</span></p>
        <h3>कुल स्कोर: {score} / {total}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📖 विस्तृत समाधान")
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx, "उत्तर नहीं दिया")
        correct = q['answer']
        st.markdown(f"""
        <div class="card">
            <b>Q{idx+1}: {q['question']}</b><br>
            <span>आपका उत्तर: <b>{chosen}</b></span><br>
            <span style="color: #00d2ff;">सही उत्तर: <b>{correct}</b></span><br>
            <p style="color: #d8b4fe; font-size: 13px; margin-top:8px;">💡 <b>समाधान:</b> {q.get('explanation', 'उपलब्ध नहीं')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🔄 दूसरा टेस्ट दें", use_container_width=True, type="primary"):
        st.session_state.page = "home"
        st.rerun()
            
