
import json
import re
import time
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="AI Quiz Maker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.stApp { background: radial-gradient(ellipse at top, #101b3c 0%, #060b18 48%, #050812 100%); color: #eef3fb; }
.block-container { max-width: 1120px; padding-top: 1rem; padding-bottom: 3rem; }
h1, h2, h3, p, label { color: #eef3fb; }
.hero {
  background: linear-gradient(135deg,rgba(20,31,65,.98),rgba(10,16,34,.98));
  border: 1px solid #3545a0; border-radius: 22px;
  padding: 28px; margin-bottom: 20px; box-shadow: 0 10px 38px rgba(54,64,190,.14);
}
.hero small { color: #a8baff; letter-spacing: 2px; }
.hero h1 { margin: 7px 0; font-size: 2.2rem; }
.hero p { color: #bdcbe0; margin-bottom: 0; }
.brandbar {display:flex; justify-content:space-between; align-items:center; gap:12px; padding:12px 4px 18px; border-bottom:1px solid #1e2a48; margin-bottom:24px;}
.brandname {font-size:1.45rem; font-weight:850; color:#f6f7ff;}
.brandname span {color:#a78bfa;}
.brandsub {font-size:.82rem; color:#b9c6e5;}
.feature-card {background:linear-gradient(145deg,#101b35,#0b1224); border:1px solid #263765; border-radius:15px; padding:16px 10px; text-align:center; min-height:100px;}
.upload-panel {background:linear-gradient(145deg,rgba(13,25,52,.95),rgba(8,15,30,.98)); border:1px solid #3b3d91; border-radius:22px; padding:22px; margin:12px 0 20px;}
.metric-card {
  background: linear-gradient(145deg,#172236,#111a2b); border: 1px solid #2a3b55;
  border-radius: 16px; padding: 18px 12px; text-align: center;
  min-height: 112px;
}
.metric-label { color: #b6c4d8; font-size: .92rem; }
.metric-value { font-size: 2rem; font-weight: 800; margin-top: 3px; }
.correct { color: #5ce0a0; }
.wrong { color: #ff8795; }
.skipped { color: #c6d0df; }
.score-panel {
  background: linear-gradient(135deg,#1a2a43,#182236);
  border: 1px solid #30435f; border-radius: 20px;
  padding: 24px; text-align: center; margin: 14px 0 20px;
}
.score-caption { color: #b6c4d8; font-size: .9rem; letter-spacing: 1px; }
.score-number { font-size: 2.7rem; font-weight: 850; color: #ffffff; }
.score-note { color: #7de5b1; font-weight: 650; }
.question-card {
  background: #141f31; border: 1px solid #2a3b55;
  border-radius: 16px; padding: 18px; margin: 12px 0;
}
.pill {
  display:inline-block; padding:5px 10px; border-radius:999px;
  font-size:.8rem; font-weight:700; margin-bottom:8px;
}
.pill-green { background:#173c32; color:#70e5b1; }
.pill-red { background:#482530; color:#ff9aa7; }
.pill-gray { background:#303b4e; color:#d0d9e6; }
div.stButton > button {
  border-radius: 12px; min-height: 2.8rem; font-weight: 700;
  border: 1px solid #6556e8; background: linear-gradient(100deg,#8b5cf6,#2563eb);
  color: white; transition: all .2s ease;
}
div.stButton > button:hover {border-color:#8b5cf6; color:white; box-shadow:0 0 18px rgba(99,102,241,.32);}
[data-testid="stFileUploader"] {background:#0a1428; border:1px dashed #5368b6; border-radius:15px; padding:12px;}
[data-testid="stMetric"] {
  background:#172236; border:1px solid #2a3b55; padding:14px;
  border-radius:14px;
}
</style>
""", unsafe_allow_html=True)


def reset_quiz():
    for key in [
        "questions", "answers", "submitted", "deadline",
        "duration_minutes", "source_name", "quiz_started",
    ]:
        st.session_state.pop(key, None)

    for key in list(st.session_state.keys()):
        if key.startswith("answer_"):
            st.session_state.pop(key, None)


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages).strip()


def make_quiz(pdf_text, count, language, topic):
    if "GEMINI_API_KEY" not in st.secrets:
        raise RuntimeError(
            "GEMINI_API_KEY Streamlit Cloud ke Secrets mein nahi mila."
        )

    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )

    if language == "हिंदी (देवनागरी)":
        language_rule = (
            "Write every question, option, and explanation in natural Hindi "
            "using Devanagari script only. Do not use Roman Hindi."
        )
    else:
        language_rule = (
            "Write every question, option, and explanation in clear English."
        )

    prompt = f"""
Create exactly {count} educational multiple-choice questions using the
provided study material. {language_rule}

Topic or focus requested by user: {topic if topic else "Cover the important concepts in the material."}

Rules:
- Each question must have exactly four options.
- The answer must be the exact text of one of the four options.
- Include a clear, helpful explanation/solution for EVERY question.
- Do not invent facts not supported by the source unless basic context is needed.
- Return ONLY valid JSON, with this structure:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Exact correct option text",
      "explanation": "Step-by-step explanation"
    }}
  ]
}}

Study material:
{pdf_text[:45000]}
"""

    model_candidates = [
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
    ]

    response = None
    errors = []

    for model_name in model_candidates:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )

                if response and response.text:
                    break

                errors.append(f"{model_name}: empty response")

            except Exception as exc:
                error_text = str(exc)
                errors.append(
                    f"{model_name}: {error_text[:240]}"
                )

                temporary_error_codes = (
                    "503", "429", "UNAVAILABLE",
                    "RESOURCE_EXHAUSTED", "high demand"
                )

                if not any(
                    code in error_text
                    for code in temporary_error_codes
                ):
                    break

                if attempt == 0:
                    time.sleep(1.5)

        if response and response.text:
            break

        response = None

    if response is None or not response.text:
        raise RuntimeError(
            "Google AI ke sabhi try kiye gaye models abhi busy/limit par hain. "
            "1-2 minute baad dobara try karein. Details: "
            + " | ".join(errors[-3:])
        )

    raw = (response.text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    questions = data.get("questions", [])
    clean_questions = []

    for q in questions:
        options = q.get("options", [])
        answer = q.get("answer", "")

        if (
            isinstance(q.get("question"), str)
            and isinstance(options, list)
            and len(options) == 4
            and answer in options
        ):
            clean_questions.append({
                "question": q["question"],
                "options": [str(option) for option in options],
                "answer": str(answer),
                "explanation": str(
                    q.get(
                        "explanation",
                        "इस प्रश्न का समाधान उपलब्ध नहीं है।"
                    )
                ),
            })

    if not clean_questions:
        raise ValueError(
            "AI se valid questions nahi mile. Dobara try karo."
        )

    return clean_questions[:count]


def get_result_counts(questions, answers):
    correct = sum(
        answers.get(i) == q["answer"]
        for i, q in enumerate(questions)
    )

    skipped = sum(
        answers.get(i) is None
        for i in range(len(questions))
    )

    wrong = len(questions) - correct - skipped
    attempted = correct + wrong

    accuracy = (
        correct / attempted * 100
        if attempted else 0
    )

    percentage = (
        correct / len(questions) * 100
        if questions else 0
    )

    return correct, wrong, skipped, accuracy, percentage


# Main navigation
if "section" not in st.session_state:
    st.session_state.section = "Home"

if "selected_exam" not in st.session_state:
    st.session_state.selected_exam = None


# PDF to Quiz header
if st.session_state.section == "PDF to Quiz":
    st.markdown("""
    <div class="brandbar">
      <div>
        <div class="brandname">🧠 AI Quiz <span>Maker</span></div>
        <div class="brandsub">By Prateek Senmar 👑</div>
      </div>
      <div style="text-align:right">
        <div style="font-weight:750;color:#f3f5ff">Prateek Senmar</div>
        <div class="brandsub">Build Better • Learn Faster</div>
      </div>
    </div>

    <div class="hero">
      <small>SMART PRACTICE • BETTER PREPARATION</small>
      <h1>Turn Your Study Material<br>Into
      <span style="color:#a78bfa">AI-Powered</span> Quizzes</h1>
      <p>Upload your PDF, choose your preferences, and get instant practice
      questions with detailed solutions. Study smarter, not harder!</p>
      <p style="margin-top:12px;color:#8fc8ff">
      ⚡ Instant Quiz Generation　　🧠 AI Powered　　📘 Detailed Solutions
     　　🎯 Track Your Progress</p>
    </div>
    """, unsafe_allow_html=True)


# Home screen
if st.session_state.section == "Home":
    st.markdown("""
    <div class="hero">
      <small>YOUR STUDY SPACE</small>
      <h1>Choose Your Practice Folder</h1>
      <p>Apna section kholo aur practice shuru karo.</p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(3)

    cards = [
        ("📄", "PDF to Quiz", "Apni PDF se MCQ aur solutions banao."),
        ("📝", "PYQ Practice", "Previous Year Questions."),
        ("⚡", "Quick Access", "Exam practice library."),
    ]

    for col, (emoji, title, desc) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                  <div style="font-size:2.1rem">{emoji}</div>
                  <h3>{title}</h3>
                  <p>{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "Open Folder →",
                key=f"open_{title}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.section = title
                st.session_state.selected_exam = None
                st.rerun()

    st.stop()


# PYQ Practice: Coming Soon only
elif st.session_state.section == "PYQ Practice":
    if st.button("← Home", key="pyq_home"):
        st.session_state.section = "Home"
        st.rerun()

    st.markdown("""
    <div class="hero" style="text-align:center; padding:55px 24px;">
      <small>PREVIOUS YEAR QUESTIONS</small>
      <h1>📝 PYQ Practice</h1>
      <h2 style="color:#a78bfa; letter-spacing:3px; margin-top:28px;">
        COMING SOON
      </h2>
      <p>Yeh section jald hi available hoga.</p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# Quick Access: Coming Soon only
elif st.session_state.section == "Quick Access":
    if st.button("← Home", key="quick_home"):
        st.session_state.section = "Home"
        st.session_state.selected_exam = None
        st.rerun()

    st.markdown("""
    <div class="hero" style="text-align:center; padding:55px 24px;">
      <small>EXAM LIBRARY</small>
      <h1>⚡ Quick Access</h1>
      <h2 style="color:#a78bfa; letter-spacing:3px; margin-top:28px;">
        COMING SOON
      </h2>
      <p>Yeh section jald hi available hoga.</p>
    </div>
    """, unsafe_allow_html=True)

    st.stop()


# PDF to Quiz section
if st.session_state.section == "PDF to Quiz":
    if st.button("← Home", key="pdf_home"):
        st.session_state.section = "Home"
        st.rerun()


if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "questions" not in st.session_state:
    st.session_state.questions = None


# Upload PDF and generate questions
if st.session_state.questions is None:
    st.markdown(
        '<div class="upload-panel">',
        unsafe_allow_html=True
    )

    st.subheader("📄 Upload Your PDF")
    st.caption(
        "Choose a PDF file — notes, chapters, or study material."
    )

    uploaded_file = st.file_uploader(
        "PDF file select karo",
        type=["pdf"],
        help="Text-based PDF sabse achhe se kaam karta hai.",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        language = st.selectbox(
            "Questions aur solutions ki language",
            ["हिंदी (देवनागरी)", "English"],
        )

        count = st.selectbox(
            "Kitne questions chahiye?",
            [5, 10, 15, 20, 25, 30, 40, 50],
            index=1,
        )

    with c2:
        duration = st.selectbox(
            "Test ka time",
            [5, 10, 15, 20, 30, 45, 60, 90, 120, 180],
            index=2,
            format_func=lambda x: f"{x} minute",
        )

        topic = st.text_input(
            "Topic (optional)",
            placeholder="Jaise: Chapter 1, important concepts",
        )

    if st.button(
        "✨ Quiz Banao",
        type="primary",
        use_container_width=True,
    ):
        if not uploaded_file:
            st.warning("Pehle apni PDF file upload karo.")
        else:
            try:
                with st.spinner(
                    "PDF padhkar questions aur solutions ban rahe hain..."
                ):
                    pdf_text = extract_pdf_text(uploaded_file)

                    if not pdf_text:
                        st.error(
                            "PDF se text nahi mila. Agar PDF scanned images "
                            "wali hai, to text-based PDF try karo."
                        )
                        st.stop()

                    questions = make_quiz(
                        pdf_text,
                        count,
                        language,
                        topic,
                    )

                st.session_state.questions = questions
                st.session_state.answers = {}
                st.session_state.submitted = False
                st.session_state.duration_minutes = duration
                st.session_state.deadline = time.time() + duration * 60
                st.session_state.source_name = uploaded_file.name
                st.session_state.quiz_started = True

                st.rerun()

            except Exception as e:
                st.error(f"Quiz nahi ban paya: {e}")
                st.info(
                    "Agar model busy ho, thodi der baad dobara try karo. "
                    "API key ko kisi ke saath share mat karna."
                )


# Quiz in progress
elif not st.session_state.submitted:
    questions = st.session_state.questions

    deadline = st.session_state.get(
        "deadline",
        time.time() + 600
    )

    remaining = max(0, int(deadline - time.time()))

    if remaining == 0:
        for i in range(len(questions)):
            st.session_state.answers[i] = st.session_state.get(
                f"answer_{i}"
            )

        st.session_state.submitted = True
        st.rerun()

    st_autorefresh(
        interval=1000,
        key="quiz_timer_refresh"
    )

    minutes, seconds = divmod(remaining, 60)

    top1, top2 = st.columns([3, 1])

    with top1:
        st.subheader("📝 Practice Test")
        st.caption(
            f"PDF: {st.session_state.get('source_name', 'Uploaded PDF')}"
        )

    with top2:
        st.metric(
            "⏳ Bacha hua time",
            f"{minutes:02d}:{seconds:02d}"
        )

    st.progress(
        max(
            0.0,
            min(
                1.0,
                1 - remaining /
                (st.session_state.duration_minutes * 60)
            )
        )
    )

    st.caption(
        f"Total questions: {len(questions)} · "
        "Har question ka ek answer select karo."
    )

    with st.form("quiz_answer_form"):
        for i, q in enumerate(questions):
            st.markdown(
                f'<div class="question-card">'
                f'<b>Question {i+1} of {len(questions)}</b><br><br>'
                f'{q["question"]}</div>',
                unsafe_allow_html=True,
            )

            st.radio(
                "Ek answer chuno:",
                options=q["options"],
                index=None,
                key=f"answer_{i}",
                label_visibility="collapsed",
            )

        submitted = st.form_submit_button(
            "✅ Test Submit Karo",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        for i in range(len(questions)):
            st.session_state.answers[i] = st.session_state.get(
                f"answer_{i}"
            )

        st.session_state.submitted = True
        st.rerun()


# Final result and solutions
else:
    questions = st.session_state.questions
    answers = st.session_state.get("answers", {})

    correct, wrong, skipped, accuracy, percentage = get_result_counts(
        questions,
        answers
    )

    st.markdown("""
    <div class="hero">
      <small>TEST COMPLETED</small>
      <h1>📊 Performance Report</h1>
      <p>Apni performance dekho aur solutions ke saath revise karo.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="score-panel">
      <div class="score-caption">YOUR FINAL SCORE</div>
      <div class="score-number">{correct}
      <span style="font-size:1.3rem;color:#b6c4d8">
      / {len(questions)}</span></div>
      <div class="score-note">{percentage:.1f}% marks</div>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">🟢 Correct / सही</div>
          <div class="metric-value correct">{correct}</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">🔴 Wrong / गलत</div>
          <div class="metric-value wrong">{wrong}</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">⚪ Skipped / छोड़े</div>
          <div class="metric-value skipped">{skipped}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    a1, a2 = st.columns(2)
    a1.metric("🎯 Accuracy (attempted)", f"{accuracy:.1f}%")
    a2.metric("📈 Overall percentage", f"{percentage:.1f}%")

    st.progress(
        percentage / 100 if percentage else 0.0
    )

    if percentage >= 80:
        st.success(
            "बहुत बढ़िया! इसी तरह अभ्यास जारी रखो।"
        )
    elif percentage >= 50:
        st.info(
            "अच्छा प्रयास! नीचे दिए गए solutions देखकर गलतियाँ सुधारो।"
        )
    else:
        st.warning(
            "कोई बात नहीं—solutions ध्यान से पढ़ो और फिर से practice करो।"
        )

    st.divider()
    st.subheader("📚 Answer Review & Solutions")
    st.caption(
        "Har question ka status, aapka answer, correct answer aur explanation dekhein."
    )
    st.caption(
        "सही, गलत और छोड़े गए—सभी प्रश्नों के उत्तर और explanations नीचे हैं।"
    )

    for i, q in enumerate(questions):
        chosen = answer.get(i)
        is_skipped = chosen is None
        is_correct = chosen == q["answer"]

        if is_skipped:
            status = "SKIPPED · छोड़ा गया"
            pill_class = "pill-gray"
        elif is_correct:
            status = "CORRECT · सही"
            pill_class = "pill-green"
        else:
            status = "WRONG · गलत"
            pill_class = "pill-red"

        with st.expander(
            f"Question {i+1}: {status}",
            expanded=False
        ):
            st.markdown(f"**प्रश्न:** {q['question']}")

            st.markdown(
                f'<span class="pill {pill_class}">{status}</span>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f"**आपका उत्तर:** "
                f"{chosen if chosen is not None else 'उत्तर नहीं दिया / Skipped'}"
            )

            st.markdown(
                f"**सही उत्तर:** {q['answer']}"
            )

st.markdown("**💡 समाधान / Explanation**")

st.write(
    q.get(
        "explanation",
        "इस प्रश्न का समाधान उपलब्ध नहीं है।"
    )
)

    st.markdown(
        "<div style='text-align:center;color:#9baed2;padding:18px'>"
        "Made with ❤️ by <b>Prateek Senmar</b> · "
        "Your Personal Study Companion</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        if st.button(
            "🔁 Naya Test Banao",
            type="primary",
            use_container_width=True,
        ):
            reset_quiz()
            st.rerun()

    with right:
        if st.button(
            "⬆️ Result ke Top par",
            use_container_width=True,
        ):
            st.rerun()
            
