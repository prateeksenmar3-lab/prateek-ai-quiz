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
    
    # Select Subject Option Added
    selected_subject = st.selectbox("📖 Select Subject (विषय चुनें)", subjects_list, key="pdf_sub")
    
    # Questions Range (10 to 200)
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    
    # Time Slider (10 minutes to 120 minutes / 2 hours)
    time_min = st.slider("⏱️ Select Time (टेस्ट का समय - मिनट में)", min_value=10, max_value=120, value=30, step=5)
    
    difficulty = st.selectbox("कठिनाई स्तर (Difficulty)", ["Easy", "Medium", "Hard"])
    
    if uploaded_file is not None:
        if st.button("🚀 PDF से Quiz जनरेट करें", type="primary", use_container_width=True):
            if not client:
                st.error("Gemini API Key सेट नहीं है! कृपया st.secrets चेक करें।")
            else:
                with st.spinner("PDF से टेक्स्ट निकाला जा रहा है और AI द्वारा उच्च-गुणवत्ता वाले MCQ तैयार हो रहे हैं..."):
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
                        
                        response = client.models.generate_content(
                            model='gemini-3.8-flash',
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
    
    # Select Subject Option Added
    selected_subject = st.selectbox("📖 Select Subject (विषय चुनें)", subjects_list, key="ai_sub")
    
    topic = st.text_input("विशेष टॉपिक दर्ज करें (जैसे: Percentage, Mughal Empire, Articles)")
    
    # Questions Range (10 to 200)
    num_q = st.slider("प्रश्नों की संख्या (10 - 200)", 10, 200, 20, step=5)
    
    # Time Slider (10 minutes to 120 minutes / 2 hours)
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
                    
                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt
                    )
                    
                    clean_res = response.text.strip()
                    if clean_res.startswith("```json"):
                        clean_res = clean_res[7:-3].strip()
                    elif clean_res.startswith("```"):
                        clean_res = clean_res[3:-3].strip()
                        
                    st.session_state.quiz_data = json.loads(clean_
    
