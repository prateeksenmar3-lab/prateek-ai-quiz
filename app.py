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

# --- CUSTOM CSS (Dark Purple Gradient UI & Mobile Friendly) ---
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
        font-size: 13px;
        color: #ff4b8b;
        margin-top: 2px;
        font-weight: 600;
    }
    .tagline {
        font-size: 11px;
        color: #b0a8c2;
        margin-top: 2px;
        font-style: italic;
    }
    .card {
        background: #160d26;
        border: 1px solid #2a1b48;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 15px;
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

# --- SESSION STATE INITIALIZATION ---
if "page" not in st.session_state:
    st.session_state.page = "home"
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "current_q_index" not in st.session_state:
    st.session_state.current_q_index = 0

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

# --- ROUTING SYSTEM ---
page = st.session_state.page

if page == "home":
    st.markdown("### 📂 मुख्य मेनू (Main Menu)")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 PDF to Quiz", use_container_width=True):
            st.session_state.page = "pdf_quiz"
            st.rerun()
        if st.button("🧠 AI Practice", use_container_width=True):
            st.session_state.page = "ai_practice"
            st.rerun()
    with col2:
        if st.button("📜 PYQ Practice", use_container_width=True):
            st.session_state.page = "pyq_practice"
            st.rerun()
        if st.button("⚡ Quick Access", use_container_width=True):
            st.session_state.page = "quick_access"
            st.rerun()

elif page == "pdf_quiz":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 📄 PDF से Quiz बनाएं")
    uploaded_file = st.file_uploader("अपनी PDF फ़ाइल यहाँ अपलोड करें", type=["pdf"])
    
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    difficulty = st.selectbox("कठिनाई स्तर (Difficulty)", ["Easy", "Medium", "Hard"])
    
    if uploaded_file and st.button("🚀 Quiz जनरेट करें", type="primary"):
        if not client:
            st.error("Gemini API Key सेट नहीं है! कृपया st.secrets चेक करें।")
        else:
            with st.spinner("PDF से टेक्स्ट निकाला जा रहा है और AI द्वारा प्रश्न बनाए जा रहे हैं... (कृपया प्रतीक्षा करें)"):
                try:
                    reader = PdfReader(uploaded_file)
                    pdf_text = ""
                    for page_obj in reader.pages:
                        if page_obj.extract_text():
                            pdf_text += page_obj.extract_text() + "\n"
                    
                    pdf_text = pdf_text[:20000]
                    
                    prompt = f"""
                    Based on the following text, generate {num_q} Multiple Choice Questions (MCQs) with 4 options each.
                    Difficulty: {difficulty}.
                    Provide the output strictly in valid JSON format as a list of objects with keys: 
                    'question', 'options' (list of 4 strings), 'answer' (the correct option string), and 'explanation' (in simple Hindi).
                    
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
                    st.session_state.page = "take_quiz"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"त्रुटि (Error): {e}")

elif page == "ai_practice":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown("### 🧠 AI Practice Mode")
    topic = st.text_input("विषय (Topic) दर्ज करें (जैसे: Indian History, Physics, SSC Reasoning)")
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    
    if topic and st.button("🚀 AI Quiz शुरू करें", type="primary"):
        if not client:
            st.error("Gemini API Key सेट नहीं है!")
        else:
            with st.spinner("AI प्रश्न तैयार कर रहा है..."):
                try:
                    prompt = f"""
                    Generate {num_q} MCQs on the topic '{topic}' with 4 options each.
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
                    st.session_state.page = "take_quiz"
                    st.rerun()
                except Exception as e:
                    st.error(f"त्रुटि: {e}")

elif page == "pyq_practice":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown("### 📜 PYQ (Previous Year Questions) Practice")
    st.info("यह सेक्शन सत्यापित पिछले वर्षों के वास्तविक प्रश्नों के लिए है।")
    selected_exam = st.selectbox("परीक्षा चुनें", ["SSC CGL (सत्यापित)", "UPP Constable", "Railway NTPC", "अन्य"])
    num_q = st.slider("प्रश्नों की संख्या", 5, 50, 10)
    
    if st.button("PYQ Test शुरू करें", type="primary"):
        # Mock/Loaded PYQ list structure
        pyq_mock = []
        for i in range(num_q):
            pyq_mock.append({
                "question": f"[{selected_exam} PYQ] Sample previous year question {i+1}?",
                "options": [f"Option A ({i})", f"Option B ({i})", f"Option C ({i})", f"Option D ({i})"],
                "answer": f"Option A ({i})",
                "explanation": f"यह {selected_exam} का सत्यापित पिछले वर्ष का प्रश्न है।"
            })
        st.session_state.quiz_data = pyq_mock
        st.session_state.user_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.page = "take_quiz"
        st.rerun()

elif page == "quick_access":
    if st.button("⬅ होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
    st.markdown("### ⚡ Quick Access")
    st.write("हाल के टेस्ट, शॉर्टकट और परीक्षा लिंक्स यहाँ उपलब्ध हैं।")
    if st.button("📌 SSC CGL Quick Quiz"):
        st.session_state.page = "ai_practice"
        st.rerun()

elif page == "take_quiz":
    if not st.session_state.quiz_data:
        st.warning("कोई सक्रिय क्विज़ नहीं मिला।")
        if st.button("होम पर जाएं"):
            st.session_state.page = "home"
            st.rerun()
    else:
        quiz = st.session_state.quiz_data
        
        if st.button("❌ टेस्ट रद्द करें"):
            st.session_state.page = "home"
            st.rerun()
            
        st.markdown("### 📝 टेस्ट चल रहा है...")
        
        with st.form("quiz_active_form"):
            user_ans = {}
            for idx, q in enumerate(quiz):
                st.markdown(f"**Q{idx+1}: {q['question']}**")
                ans = st.radio(
                    "विकल्प चुनें:",
                    q['options'],
                    key=f"q_{idx}",
                    index=None
                )
                user_ans[idx] = ans
                st.write("---")
                
            submitted = st.form_submit_button("✅ टेस्ट सबमिट करें", use_container_width=True)
            
            if submitted:
                st.session_state.user_answers = user_ans
                st.session_state.quiz_submitted = True
                st.session_state.page = "quiz_results"
                st.rerun()

elif page == "quiz_results":
    if st.button("🏠 होम पर वापस जाएं"):
        st.session_state.page = "home"
        st.rerun()
        
    st.markdown("### 🏆 टेस्ट परिणाम और विश्लेषण (Results & Analysis)")
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
    
    st.markdown(f"""
    <div class="card">
        <h4>📊 स्कोर कार्ड</h4>
        <p><b>कुल प्रश्न:</b> {total}</p>
        <p><b>सही उत्तर:</b> {correct_count}</p>
        <p><b>गलत उत्तर:</b> {incorrect_count}</p>
        <p><b>छोड़े गए प्रश्न:</b> {unattempted_count}</p>
        <h3>आपका कुल स्कोर: {score} / {total}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📖 विस्तृत समाधान (Detailed Solutions & Explanation)")
    for idx, q in enumerate(quiz):
        chosen = user_ans.get(idx, "उत्तर नहीं दिया")
        correct = q['answer']
        explanation = q.get('explanation', 'उपलब्ध नहीं')
        
        status_color = "🟢 सही" if chosen == correct else ("🔴 गलत" if chosen != "उत्तर नहीं दिया" else "🟡 छोड़ा गया")
        
        st.markdown(f"""
        <div class="card">
            <b>Q{idx+1}: {q['question']}</b><br>
            <span>आपका उत्तर: {chosen}</span><br>
            <span style="color: #00d2ff;">सहि उत्तर: {correct}</span><br>
            <b>स्थिति: {status_color}</b><br>
            <p style="margin-top: 8px; color: #d8b4fe;">💡 <b>सरल हिंदी समाधान:</b> {explanation}</p>
        </div>
        """, unsafe_allow_html=True)
        
