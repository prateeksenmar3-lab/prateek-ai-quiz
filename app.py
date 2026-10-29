import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Prateek AI Quiz Hub",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS for Dark Theme & PW Style Look
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0614;
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Header Branding */
    .brand-header {
        text-align: center;
        padding: 15px 0 5px 0;
    }
    .brand-title {
        font-size: 24px;
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

    /* Cards */
    .folder-card {
        background: #160d26;
        border: 1px solid #2a1b48;
        border-radius: 16px;
        padding: 18px 10px;
        text-align: center;
        transition: 0.3s;
    }
    .folder-card:hover {
        border-color: #00d2ff;
    }
    
    .section-title {
        font-size: 16px;
        font-weight: bold;
        letter-spacing: 1px;
        color: #ffffff;
        margin: 20px 0 12px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Session State Initialization
if "page" not in st.session_state:
  st.session_state.page = "home"
if "active_folder" not in st.session_state:
  st.session_state.active_folder = None
if "quiz_data" not in st.session_state:
  st.session_state.quiz_data = None
if "quiz_submitted" not in st.session_state:
  st.session_state.quiz_submitted = False
if "user_answers" not in st.session_state:
  st.session_state.user_answers = {}

# ================= PAGE ROUTING =================

if st.session_state.page == "home":
  # Branding Header
  st.markdown(
      """
        <div class="brand-header">
            <div class="brand-title">🚀 Prateek AI Quiz Hub</div>
            <div class="brand-subtitle">Made by Prateek Senmar ♥️</div>
        </div>
        <hr style="border-color: #2a1b48; margin: 15px 0;">
        """,
      unsafe_allow_html=True,
  )

  st.markdown(
      '<div class="section-title">📂 STUDY FOLDERS</div>', unsafe_allow_html=True
  )

  # 4 Folders Grid (2x2)
  col1, col2 = st.columns(2)

  with col1:
    st.markdown(
        """
            <div class="folder-card">
                <div style="font-size: 28px;">📄</div>
                <div style="font-weight: bold; font-size: 14px; margin-top: 8px;">PDF to Quiz</div>
                <div style="font-size: 11px; color: #a0a0a0; margin-top: 4px;">Convert PDF to Practice Quiz</div>
            </div>
            """,
        unsafe_allow_html=True,
    )
    if st.button("Open PDF to Quiz", key="btn_pdf", use_container_width=True):
      st.session_state.page = "config_screen"
      st.session_state.active_folder = "PDF to Quiz"
      st.rerun()

    st.write("")
    st.markdown(
        """
            <div class="folder-card">
                <div style="font-size: 28px;">🧠</div>
                <div style="font-weight: bold; font-size: 14px; margin-top: 8px;">AI Quiz Maker</div>
                <div style="font-size: 11px; color: #a0a0a0; margin-top: 4px;">Create custom AI Quizzes</div>
            </div>
            """,
        unsafe_allow_html=True,
    )
    if st.button(
        "Open AI Quiz Maker", key="btn_ai_quiz", use_container_width=True
    ):
      st.session_state.page = "config_screen"
      st.session_state.active_folder = "AI Quiz Maker"
      st.rerun()

  with col2:
    st.markdown(
        """
            <div class="folder-card">
                <div style="font-size: 28px;">📜</div>
                <div style="font-weight: bold; font-size: 14px; margin-top: 8px;">PYQ Practice</div>
                <div style="font-size: 11px; color: #a0a0a0; margin-top: 4px;">Actual Previous Year Questions</div>
            </div>
            """,
        unsafe_allow_html=True,
    )
    if st.button("Open PYQ Practice", key="btn_pyq", use_container_width=True):
      st.session_state.page = "config_screen"
      st.session_state.active_folder = "PYQ Practice"
      st.rerun()

    st.write("")
    st.markdown(
        """
            <div class="folder-card">
                <div style="font-size: 28px;">⚡</div>
                <div style="font-weight: bold; font-size: 14px; margin-top: 8px;">Quick Access</div>
                <div style="font-size: 11px; color: #a0a0a0; margin-top: 4px;">Direct Exam Shortcuts</div>
            </div>
            """,
        unsafe_allow_html=True,
    )
    if st.button("Open Quick Access", key="btn_quick", use_container_width=True):
      st.session_state.page = "quick_access_screen"
      st.rerun()


elif st.session_state.page == "quick_access_screen":
  if st.button("⬅ Back to Home"):
    st.session_state.page = "home"
    st.rerun()

  st.markdown("## ⚡ Quick Access Exams")
  exams = ["SSC", "UPP", "DPP", "UPSC", "NEET", "Railway", "Other"]
  for ex in exams:
    if st.button(f"📌 Explore {ex} Batches & Tests", use_container_width=True):
      st.success(f"Opening {ex} section...")


elif st.session_state.page == "config_screen":
  folder = st.session_state.active_folder
  if st.button("⬅ Back to Home"):
    st.session_state.page = "home"
    st.rerun()

  st.markdown(f"## ⚙️ Configure {folder}")
  st.markdown(
      "<p style='font-size: 13px; color: #b0b3c6;'>Apni zaroorat ke hisaab se"
      " details select karein:</p>",
      unsafe_allow_html=True,
  )

  # 1. Select Exam
  exam_list = ["SSC", "UPP", "DPP", "UPSC", "NEET", "Railway", "Other"]
  selected_exam = st.selectbox("🎯 Select Exam", exam_list)

  # 2. Select Subject
  subject_list = [
      "Mathematics",
      "Reasoning",
      "General Science",
      "Indian History",
      "English",
      "Current Affairs",
  ]
  selected_subject = st.selectbox("📖 Select Subject", subject_list)

  # 3. Number of Questions
  num_questions = st.slider("📝 Number of Questions", min_value=2, max_value=20, value=5)

  # 4. Time in Minutes
  time_limit = st.slider("⏱️ Time (Minutes)", min_value=1, max_value=30, value=5)

  if st.button("🚀 Create Quiz", type="primary", use_container_width=True):
    questions = []
    for i in range(num_questions):
      questions.append({
          "q": (
              f"[{selected_exam}] Sample Question {i+1} for"
              f" {selected_subject}?"
          ),
          "options": [
              f"Option A ({i})",
              f"Option B ({i})",
              f"Option C ({i})",
              f"Option D ({i})",
          ],
          "answer": f"Option A ({i})",
      })

    st.session_state.quiz_data = {
        "title": f"{selected_exam} - {selected_subject} ({folder})",
        "time": time_limit,
        "questions": questions,
    }
    st.session_state.quiz_submitted = False
    st.session_state.user_answers = {}
    st.session_state.page = "quiz_screen"
    st.rerun()


elif st.session_state.page == "quiz_screen":
  quiz = st.session_state.quiz_data

  if st.button("⬅ Cancel & Exit"):
    st.session_state.page = "home"
    st.session_state.quiz_data = None
    st.rerun()

  st.markdown(f"## 📝 {quiz['title']}")
  st.markdown(
      f"<p style='color: #00d2ff; font-size: 13px;'>⏱️ Time Limit:"
      f" {quiz['time']} Minutes</p>",
      unsafe_allow_html=True,
  )
  st.markdown("---")

  if not st.session_state.quiz_submitted:
    with st.form("active_quiz_form"):
      ans_dict = {}
      for idx, q in enumerate(quiz["questions"]):
        st.markdown(f"**Q{idx+1}: {q['q']}**")
        ans_dict[idx] = st.radio(
            "Select option:", q["options"], key=f"ans_{idx}", index=None
        )
        st.write("")

      submitted = st.form_submit_button("Submit Quiz", use_container_width=True)
      if submitted:
        st.session_state.user_answers = ans_dict
        st.session_state.quiz_submitted = True
        st.rerun()
  else:
    score = 0
    total = len(quiz["questions"])
    user_ans = st.session_state.user_answers

    for idx, q in enumerate(quiz["questions"]):
      if user_ans.get(idx) == q["answer"]:
        score += 1

    st.balloons()
    st.markdown("### 🏆 Quiz Result Summary")
    st.success(f"🎉 Aapka Score: {score} / {total}")

    for idx, q in enumerate(quiz["questions"]):
      chosen = user_ans.get(idx, "Not Answered")
      correct = q["answer"]
      status = "✅ Correct" if chosen == correct else "❌ Incorrect"
      st.markdown(
          f"""
            <div style="background: #160d26; border: 1px solid #2a1b48; padding: 12px; border-radius: 10px; margin-bottom: 10px;">
                <b>Q{idx+1}: {q['q']}</b><br>
                <span style="font-size:12px; color: #a0a0a0;">Aapka jawab: {chosen}</span><br>
                <span style="font-size:12px; color: #00d2ff;">Sahi jawab: {correct}</span><br>
                <b style="font-size:12px;">{status}</b>
            </div>
            """,
          unsafe_allow_html=True,
      )

    if st.button("🔄 Take Another Quiz", use_container_width=True):
      st.session_state.page = "home"
      st.session_state.quiz_data = None
      st.session_state.quiz_submitted = False
      st.rerun()
      
