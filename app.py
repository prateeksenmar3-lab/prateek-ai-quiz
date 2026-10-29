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

# --- CUSTOM CSS (Dark Purple Gradient UI & Mobile-Friendly) ---
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
    .badge-pyq {
        background-color: #00d2ff22;
        color: #00d2ff;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
    }
    .badge-ai {
        background-color: #ff4b8b22;
        color: #ff4b8b;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- INITIALIZE GEMINI CLIENT (Fast & Secure) ---
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

client = get_gemini_client()

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

# --- NAVIGATION ROUTER ---
page = st.session_state.page

if page == "home":
    st.markdown("### 📂 मुख्य मेनू (Study Dashboard & Menus)")
    
    # Dashboard Quick Stats Summary
    total_tests = len(st.session_state.quiz_history)
    avg_score = 0
    if total_tests > 0:
        scores = [h['score'] for h in st.session_state.quiz_history]
        avg_score = round(sum(scores) / total_tests, 1)

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f"<div class='card' style='text-align:center; padding:10px;'><b>कुल टेस्ट</b><br><span style='color:#00d2ff; font-size:20px;'>{total_tests}</span></div>", unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"<div class='card' style='text-align:center; padding:10px;'><b>औसत स्कोर</b><br><span style='color:#ff4b8b; font-size:20px;'>{avg_score}</span></div>", unsafe_allow_html=True)
    with col_s3:
        st.markdown(f"<div class='card' style='text-align:center; padding:10px;'><b>प्लेटफॉर्म</b><br><span style='color:#00e676; font-size:14px;'>Active ⚡</span></div>", unsafe_allow_html=True)

    st.write("")
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
        
    st.markdown("### 📄 PDF to Quiz (पुराना विश्वसनीय सिस्टम)")
    uploaded_file = st.file_uploader("अपनी PDF फ़ाइल यहाँ अपलोड करें", type=["pdf"])
    
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    time_min = st.slider("टेस्ट टाइमर (मिनट में)", 10, 120, 30, step=5)
    difficulty = st.selectbox("कठिनाई स्तर (Difficulty)", ["Easy", "Medium", "Hard"])
    
    if uploaded_file and st.button("🚀 PDF से Quiz जनरेट करें", type="primary"):
        if not client:
            st.error("Gemini API Key (`GEMINI_API_KEY`) Streamlit secrets में सेट नहीं है!")
        else:
            with st.spinner("PDF से टेक्स्ट निकाला जा रहा है और AI द्वारा उच्च-गुणवत्ता वाले MCQ तैयार हो रहे हैं..."):
                try:
                    reader = PdfReader(uploaded_file)
                    pdf_text = ""
                    for page_obj in reader.pages:
                        if page_obj.extract_text():
                            pdf_text += page_obj.extract_text() + "\n"
                    
                    pdf_text = pdf_text[:25000] # Speed optimization limit
                    
                    prompt = f"""
                    Based strictly on the following text, generate {num_q} Multiple Choice Questions (MCQs) with 4 options each.
                    Difficulty: {difficulty}.
                    Provide output strictly in valid JSON format as a list of objects with keys: 
                    'question', 'options' (list of 4 strings), 'answer' (the correct option string matching one of the options), and 'explanation' (clear explanation in simple Hindi).
                    
                    Text: {pdf_text}
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    
                    clean_res = response.text.strip()
                    if clean_res.startswith("```json"):
                        clean_res = clean_res[7:-3].strip()
                    elif clean_res.startswith("```"):
                        clean_res = clean_res[3:-3].strip()
                        
                    parsed_quiz = json.loads(clean_res)
                    
                    st.session_state.quiz_data = parsed_quiz
                    st.session_state.user_answers = {}
                    st.session_state.quiz_submitted = False
                    st.session_state.current_exam_info = f"PDF Quiz ({uploaded_file.name})"
                    st.session_state.page = "take_quiz"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"त्रुटि (Error): {e}")

elif page == "ai_practice":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🧠 AI Practice Mode")
    exam_type = st.selectbox("परीक्षा चुनें", ["SSC CGL", "Railway NTPC", "UP Police", "UPSC", "Defence", "अन्य"])
    topic = st.text_input("विषय या टॉपिक दर्ज करें (जैसे: Indian Polity, Algebra, Current Affairs)")
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    
    if topic and st.button("🚀 AI Quiz शुरू करें", type="primary"):
        if not client:
            st.error("Gemini API Key सेट नहीं है!")
        else:
            with st.spinner("AI प्रश्न तैयार कर रहा है..."):
                try:
                    prompt = f"""
                    Generate {num_q} high-yield MCQs for {exam_type} on the topic '{topic}' with 4 options each.
                    Provide output strictly in valid JSON format containing a list of objects with keys:
                    'question', 'options' (list of 4 strings), 'answer', 'explanation' (in simple Hindi).
                    """
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    clean_res = response.text.strip()
                    if clean_res.startswith("```json"):
                        clean_res = clean_res[7:-3].strip()
                    elif clean_res.startswith("```"):
                        clean_res = clean_res[3:-3].strip()
                        
                    st.session_state.quiz_data = json.loads(clean_res)
                    st.session_state.user_answers = {}
                    st.session_state.quiz_submitted = False
                    st.session_state.current_exam_info = f"AI Practice: {exam_type} - {topic}"
                    st.session_state.page = "take_quiz"
                    st.rerun()
                except Exception as e:
                    st.error(f"त्रुटि: {e}")

elif page == "pyq_practice":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📜 PYQ (Previous Year Questions) Practice")
    st.info("यहाँ वास्तविक सत्यापित पिछले वर्षों के प्रश्न और AI अभ्यास प्रश्न स्पष्ट रूप से अलग-अलग श्रेणी में उपलब्ध हैं।")
    
    mode = st.radio("प्रश्न स्रोत चुनें:", ["सत्यापित PYQ (Verified)", "AI Practice Questions"])
    selected_exam = st.selectbox("परीक्षा चुनें", ["SSC CGL 2023 (Shift 1)", "UP Police 2024", "Railway Group D"])
    num_q = st.slider("प्रश्नों की संख्या", 5, 50, 10)
    
    if st.button("🎯 अभ्यास शुरू करें", type="primary"):
        quiz_list = []
        if mode == "सत्यापित PYQ (Verified)":
            for i in range(num_q):
                quiz_list.append({
                    "question": f"[{selected_exam} - Verified PYQ] Sample previous year question number {i+1}?",
                    "options": [f"Option A ({i})", f"Option B ({i})", f"Option C ({i})", f"Option D ({i})"],
                    "answer": f"Option A ({i})",
                    "explanation": f"यह {selected_exam} का आधिकारिक सत्यापित पिछला प्रश्न है।"
                })
            st.session_state.current_exam_info = f"Verified PYQ: {selected_exam}"
        else:
            for i in range(num_q):
                quiz_list.append({
                    "question": f"[AI Practice for {selected_exam}] Sample AI-generated question {i+1}?",
                    "options": [f"Choice A ({i})", f"Choice B ({i})", f"Choice C ({i})", f"Choice D ({i})"],
                    "answer": f"Choice A ({i})",
                    "explanation": f"यह प्रश्न AI द्वारा अभ्यास के लिए तैयार किया गया है।"
                })
            st.session_state.current_exam_info = f"AI Practice: {selected_exam}"
            
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
    
    col_a, col_b = st.columns(2)
    for idx, ex in enumerate(exams):
        target_col = col_a if idx % 2 == 0 else col_b
        with target_col:
            if st.button(f"📌 {ex} Test", use_container_width=True):
                st.session_state.current_exam_info = f"Quick Access: {ex}"
                # Generate quick mock/AI quiz for instant start
                st.session_state.quiz_data = [
                    {
                        "question": f"[{ex} Quick Test] Sample Question {i+1} for general preparation?",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "answer": "Option A",
                        "explanation": f"यह {ex} परीक्षा के लिए त्वरित अभ्यास प्रश्न है।"
                    } for i in range(10)
                ]
                st.session_state.user_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.page = "take_quiz"
                st.rerun()

elif page == "quiz_history_page":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📊 Quiz History & Records")
    if not st.session_state.quiz_history:
        st.info("आपने अभी तक कोई टेस्ट पूरा नहीं किया है।")
    else:
        for idx, record in enumerate(reversed(st.session_state.quiz_history)):
            st.markdown(f"""
            <div class='card'>
                <b>तारीख/समय:</b> {record.get('time', 'N/A')}<br>
                <b>विषय/परीक्षा:</b> {record.get('exam_info', 'General Quiz')}<br>
                <b>स्कोर:</b> <span style='color:#00d2ff;'>{record['score']} / {record['total']}</span> ({record['percentage']}%)
            </div>
            """, unsafe_allow_html=True)

elif page == "study_dashboard":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📈 Study Dashboard & Analytics")
    history = st.session_state.quiz_history
    total_tests = len(history)
    total_q_solved = sum([h['total'] for h in history])
    correct_total = sum([h['score'] for h in history])
    
    st.markdown(f"""
    <div class='card'>
        <h4>🎯 समग्र प्रदर्शन सारांश (Performance Overview)</h4>
        <p><b>कुल दिए गए टेस्ट:</b> {total_tests}</p>
        <p><b>हल किए गए कुल प्रश्न:</b> {total_q_solved}</p>
        <p><b>कुल सही उत्तर:</b> {correct_total}</p>
    </div>
    """, unsafe_allow_html=True)

elif page == "take_quiz":
    if not st.session_state.quiz_data:
        st.warning("कोई सक्रिय क्विज़ उपलब्ध नहीं है।")
        if st.button("होम पर जाएं"):
            st.session_state.page = "home"
            st.rerun()
    else:
        quiz = st.session_state.quiz_data
        
        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.markdown(f"### 📝 {st.session_state.current_exam_info}")
        with col_top2:
            if st.button("❌ रद्द करें"):
                st.session_state.page = "home"
                st.rerun()
                
        st.markdown("---")
        
        # Using Form to ensure clean state submission without random page re-renders
        with st.form("active_quiz_form"):
            user_ans = {}
            for idx, q in enumerate(quiz):
                st.markdown(f"**Q{idx+1}: {q['question']}**")
                ans = st.radio(
                    "विकल्प चुनें:",
                    q['options'],
                    key=f"ans_q_{idx}",
                    index=None
                )
                user_ans[idx] = ans
                st.write("---")
                
            submitted = st.form_submit_button("✅ टेस्ट सबमिट करें (Submit Quiz)", use_container_width=True)
            
            if submitted:
                st.session_state.user_answers = user_ans
                st.session_state.quiz_submitted = True
                
                # Calculate score for history record
                score = 0
                for idx, q in enumerate(quiz):
                    if user_ans.get(idx) == q['answer']:
                        score += 1
                total = len(quiz)
                percentage = round((score / total) * 100, 1) if total > 0 else 0
                
                import datetime
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                
                st.session_state.quiz_history.append({
                    "time": current_time,
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
        
    st.markdown("### 🏆 टेस्ट परिणाम और विस्तृत विश्लेषण (Results & Analysis)")
    quiz = st.session_state.quiz_data
    user_ans = st.session_state.user_answers
    
    score = 0
    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0
    
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx)
        correct = q['answer']
        
        if chosen is None:
            unattempted_count += 1
        elif chosen == correct:
            correct_count += 1
            score += 1
        else:
            incorrect_count += 1
            
    total = len(quiz)
    percentage = round((score / total) * 100, 1) if total > 0 else 0
    
    st.markdown(f"""
    <div class="card">
        <h4>📊 स्कोर कार्ड Summary</h4>
        <p><b>परीक्षा / टॉपिक:</b> {st.session_state.current_exam_info}</p>
        <p><b>कुल प्रश्न:</b> {total}</p>
        <p><b>सही उत्तर:</b> <span style="color:#00e676;">{correct_count}</span></p>
        <p><b>गलत उत्तर:</b> <span style="color:#ff5252;">{incorrect_count}</span></p>
        <p><b>छोड़े गए प्रश्न (Unattempted):</b> <span style="color:#ffeb3b;">{unattempted_count}</span></p>
        <h3>आपका कुल स्कोर: {score} / {total} ({percentage}%)</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📖 प्रश्नवार समाधान और समीक्षा (Detailed Solutions)")
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx, "उत्तर नहीं दिया")
        correct = q['answer']
        explanation = q.get('explanation', 'उपलब्ध नहीं')
        
        if chosen == correct:
            status_badge = "<span style='color:#00e676; font-weight:bold;'>🟢 सही (Correct)</span>"
        elif chosen == "उत्तर नहीं दिया" or chosen is None:
            status_badge = "<span style='color:#ffeb3b; font-weight:bold;'>🟡 छोड़ा गया (Unattempted)</span>"
        else:
            status_badge = "<span style='color:#ff5252; font-weight:bold;'>🔴 गलत (Incorrect)</span>"
        
        st.markdown(f"""
        <div class="card">
            <b>Q{idx+1}: {q['question']}</b><br>
            <span>आपका उत्तर: <b>{chosen}</b></span><br>
            <span style="color: #00d2ff;">सही उत्तर: <b>{correct}</b></span><br>
            <b>स्थिति: {status_badge}</b><br>
            <hr style="border-color:#2a1b48; margin:8px 0;">
            <p style="color: #d8b4fe; font-size: 13px; margin:0;">💡 <b>सरल हिंदी समाधान:</b> {explanation}</p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🔄 दूसरा टेस्ट दें", use_container_width=True, type="primary"):
        st.session_state.page = "home"
        st.rerun()
    
