import streamlit as st
from streamlit_autorefresh import st_autorefresh
from pypdf import PdfReader
from google import genai
from supabase import create_client
import json
import re
import time
import random

# =========================
# APP CONFIG
# =========================
st.set_page_config(
    page_title="AI Quiz Maker | Prateek Senmar",
    page_icon="🧠",
    layout="centered"
)

# =========================
# DESIGN
# =========================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(145deg, #100b20, #1c1035, #100b20);
    color: #ffffff;
}
h1, h2, h3, p, label, span {
    color: #ffffff;
}
.main .block-container {
    max-width: 850px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
.hero {
    text-align: center;
    padding: 26px 12px;
    border-radius: 22px;
    background: linear-gradient(135deg, #49218a, #17112d, #7928ca);
    border: 1px solid #7951bd;
    margin-bottom: 22px;
}
.hero h1 {
    font-size: 34px;
    font-weight: 900;
    margin-bottom: 5px;
}
.hero p {
    font-size: 14px;
    color: #e5d8ff;
}
.question {
    font-size: 21px;
    font-weight: 750;
    line-height: 1.65;
    margin: 22px 0;
}
.option-box {
    padding: 12px;
    border: 1px solid #654a8d;
    border-radius: 12px;
    margin-bottom: 8px;
}
div.stButton > button {
    width: 100%;
    border-radius: 12px;
    min-height: 44px;
    font-weight: 700;
    border: 1px solid #7951bd;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #6d28d9, #9333ea);
    color: white;
}
.result-card {
    padding: 15px;
    border-radius: 15px;
    background: #24183c;
    border: 1px solid #62468a;
    text-align: center;
}
.small-note {
    color: #c8b8e7;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🧠 AI Quiz Maker</h1>
    <p>Learn smarter. Practice better. Achieve more.</p>
    <h3>✨ PRATEEK SENMAR ✨</h3>
</div>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
DEFAULTS = {
    "user": None,
    "page": "Home",
    "quiz": [],
    "answers": {},
    "quiz_index": 0,
    "quiz_end": 0,
    "quiz_started": False,
    "quiz_submitted": False,
    "show_solutions": False,
    "quiz_title": "",
    "quiz_source": "",
    "quiz_language": "Hindi",
    "quiz_duration": 15,
    "login_mode": "Login",
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================
# CONNECTIONS
# =========================
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None


def get_ai_client():
    try:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception:
        return None


def get_model_name():
    try:
        return st.secrets["GEMINI_MODEL"]
    except Exception:
        return "gemini-3.8-flash",
               "gemini-3.5-flash",


# =========================
# PDF TEXT EXTRACTION
# =========================
def extract_pdf_text(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        return text.strip()
    except Exception as e:
        st.error(f"PDF पढ़ने में समस्या हुई: {e}")
        return ""


# =========================
# AI QUESTION GENERATION
# =========================
def generate_questions(
    source_text,
    count=10,
    difficulty="Mixed",
    topic="General",
    language="Hindi",
    exam="General"
):
    client = get_ai_client()

    if client is None:
        st.error("Gemini API key नहीं मिली। Streamlit Secrets चेक करो।")
        return []

    language_instruction = (
        "Write questions, options and explanations in simple Hindi using Devanagari script."
        if language == "Hindi"
        else "Write questions, options and explanations in clear English."
    )

    prompt = f"""
You are an expert competitive-exam question setter.

Create exactly {count} multiple-choice questions.

Exam: {exam}
Topic: {topic}
Difficulty: {difficulty}

Language instructions:
{language_instruction}

Source material:
{source_text[:25000]}

Rules:
1. Every question must have exactly four options.
2. Exactly one option must be correct.
3. The answer field must be an integer from 0 to 3.
4. Explanation must be useful, clear and reasonably concise.
5. Do not invent historical exam dates or shifts.
6. Do not claim generated questions are real previous-year questions.
7. If source material is provided, keep questions based on it.
8. Return ONLY a valid JSON array. Do not use Markdown fences.

Required format:
[
  {{
    "question": "Question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": 0,
    "explanation": "Explanation"
  }}
]
"""

    try:
        response = client.models.generate_content(
            model=get_model_name(),
            contents=prompt
        )

        raw = (response.text or "").strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        start = raw.find("[")
        end = raw.rfind("]")

        if start == -1 or end == -1:
            st.error("AI से सही प्रश्न-फॉर्मेट नहीं मिला। दोबारा कोशिश करो।")
            return []

        data = json.loads(raw[start:end + 1])
        questions = []

        for item in data:
            options = item.get("options", [])
            answer = item.get("answer")

            if (
                not item.get("question")
                or not isinstance(options, list)
                or len(options) != 4
                or not isinstance(answer, int)
                or answer not in range(4)
            ):
                continue

            questions.append({
                "question": str(item["question"]),
                "options": [str(x) for x in options],
                "answer": answer,
                "explanation": str(
                    item.get("explanation", "इस प्रश्न का उत्तर दिए गए सही विकल्प पर आधारित है।")
                ),
                "year": None,
                "shift": None,
                "source_url": None,
                "is_pyq": False,
            })

        return questions[:count]

    except Exception as e:
        st.error(f"प्रश्न बनाने में समस्या: {e}")
        st.caption(
            "अगर मॉडल उपलब्ध नहीं है या सर्वर व्यस्त है, तो कुछ समय बाद दोबारा कोशिश करो।"
        )
        return []


# =========================
# QUIZ CONTROLS
# =========================
def start_quiz(questions, title, source, duration, language):
    if not questions:
        st.warning("अभी कोई प्रश्न उपलब्ध नहीं है।")
        return

    st.session_state.quiz = questions
    st.session_state.answers = {}
    st.session_state.quiz_index = 0
    st.session_state.quiz_title = title
    st.session_state.quiz_source = source
    st.session_state.quiz_duration = duration
    st.session_state.quiz_language = language
    st.session_state.quiz_end = time.time() + duration * 60
    st.session_state.quiz_started = True
    st.session_state.quiz_submitted = False
    st.session_state.show_solutions = False
    st.session_state.page = "Quiz"


def submit_quiz():
    st.session_state.quiz_submitted = True
    st.session_state.quiz_started = False
    st.session_state.show_solutions = False
    st.session_state.page = "Results"


def get_results():
    questions = st.session_state.quiz
    answers = st.session_state.answers

    correct = 0
    wrong = 0
    skipped = 0

    for i, question in enumerate(questions):
        selected = answers.get(i)

        if selected is None:
            skipped += 1
        elif selected == question["answer"]:
            correct += 1
        else:
            wrong += 1

    total = len(questions)
    accuracy = round((correct / total) * 100, 1) if total else 0

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "accuracy": accuracy,
    }


# =========================
# LOGIN / SIGNUP
# =========================
def login_screen():
    st.subheader("🔐 Login / Sign Up")
    st.write("अपना अकाउंट खोलो या नया अकाउंट बनाओ।")

    sb = get_supabase()

    if sb is None:
        st.error(
            "Supabase connection नहीं हो पाया। Streamlit Secrets में "
            "SUPABASE_URL और SUPABASE_KEY चेक करो।"
        )
        return

    mode = st.radio(
        "चुनो",
        ["Login", "Sign Up"],
        horizontal=True,
        key="auth_choice"
    )

    email = st.text_input("Email", key="auth_email")
    password = st.text_input(
        "Password",
        type="password",
        key="auth_password"
    )

    if mode == "Sign Up":
        if st.button("नया अकाउंट बनाओ", type="primary"):
            if not email or not password:
                st.warning("Email और password दोनों भरो।")
            else:
                try:
                    result = sb.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    if result.user:
                        st.success(
                            "अकाउंट बन गया। यदि email confirmation माँगा जाए, "
                            "तो अपना email verify करके Login करो।"
                        )
                except Exception as e:
                    st.error(f"Sign Up में समस्या: {e}")

    else:
        if st.button("Login करो", type="primary"):
            if not email or not password:
                st.warning("Email और password दोनों भरो।")
            else:
                try:
                    result = sb.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    if result.user:
                        st.session_state.user = {
                            "email": result.user.email
                        }
                        st.session_state.page = "Home"
                        st.rerun()
                except Exception as e:
                    st.error(f"Login नहीं हुआ: {e}")


# =========================
# QUIZ PLAYER
# =========================
def show_question_player():
    questions = st.session_state.quiz

    if not questions:
        st.warning("Quiz में कोई प्रश्न नहीं है।")
        if st.button("Home पर वापस जाओ"):
            st.session_state.page = "Home"
            st.rerun()
        return

    # Refresh only while a quiz is running.
    st_autorefresh(interval=1000, key="quiz_timer_refresh")

    now = time.time()
    remaining = max(0, int(st.session_state.quiz_end - now))

    if remaining <= 0:
        submit_quiz()
        st.rerun()

    index = st.session_state.quiz_index
    index = max(0, min(index, len(questions) - 1))
    question = questions[index]

    minutes = remaining // 60
    seconds = remaining % 60

    left, right = st.columns(2)
    with left:
        st.markdown(f"**⏱️ समय:** {minutes:02d}:{seconds:02d}")
    with right:
        st.markdown(f"**🌐 भाषा:** {st.session_state.quiz_language}")

    st.progress((index + 1) / len(questions))
    st.caption(
        f"{st.session_state.quiz_title} · प्रश्न {index + 1}/{len(questions)}"
    )

    st.markdown(
        f'<div class="question">{question["question"]}</div>',
        unsafe_allow_html=True
    )

    saved_answer = st.session_state.answers.get(index)

    # One stable key per question preserves answers during navigation.
    selected = st.radio(
        "सही विकल्प चुनो:",
        options=list(range(4)),
        format_func=lambda x: f"{chr(65 + x)}. {question['options'][x]}",
        index=saved_answer,
        key=f"answer_question_{index}",
        label_visibility="collapsed"
    )

    if selected is not None:
        st.session_state.answers[index] = selected

    st.write("")

    nav_left, nav_mid, nav_right = st.columns(3)

    with nav_left:
        if st.button("⬅️ Previous", disabled=(index == 0)):
            st.session_state.quiz_index = index - 1
            st.rerun()

    with nav_mid:
        if st.button("🧹 उत्तर हटाओ"):
            st.session_state.answers.pop(index, None)
            key = f"answer_question_{index}"
            if key in st.session_state:
                del st.session_state[key]
            st.rerun()

    with nav_right:
        if st.button(
            "Next ➡️",
            disabled=(index == len(questions) - 1)
        ):
            st.session_state.quiz_index = index + 1
            st.rerun()

    st.write("")
    if st.button("✅ Test Submit करो", type="primary"):
        submit_quiz()
        st.rerun()

    answered = len(st.session_state.answers)
    st.caption(
        f"उत्तर दिए गए: {answered}/{len(questions)} · "
        f"बचे हुए: {len(questions) - answered}"
    )


# =========================
# RESULTS
# =========================
def show_results():
    stats = get_results()

    st.title("📊 आपका Result")
    st.caption(st.session_state.quiz_title)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("कुल प्रश्न", stats["total"])
        st.metric("✅ सही", stats["correct"])
    with c2:
        st.metric("❌ गलत", stats["wrong"])
        st.metric("⏭️ छोड़े", stats["skipped"])

    st.metric("🎯 Accuracy", f'{stats["accuracy"]}%')

    if stats["total"]:
        st.progress(stats["correct"] / stats["total"])

    st.write("")
    if st.button("📚 Solutions देखें", type="primary"):
        st.session_state.show_solutions = True
        st.rerun()

    if st.session_state.show_solutions:
        st.divider()
        st.subheader("📚 Solutions")

        category = st.radio(
            "किस तरह के प्रश्न देखना चाहते हो?",
            ["गलत उत्तर", "छोड़े गए", "सही उत्तर", "सभी प्रश्न"],
            horizontal=True,
            key="solution_category"
        )

        questions = st.session_state.quiz
        answers = st.session_state.answers

        for i, question in enumerate(questions):
            selected = answers.get(i)
            correct_answer = question["answer"]

            if selected is None:
                status = "छोड़ा गया"
            elif selected == correct_answer:
                status = "सही"
            else:
                status = "गलत"

            if category == "गलत उत्तर" and status != "गलत":
                continue
            if category == "छोड़े गए" and status != "छोड़ा गया":
                continue
            if category == "सही उत्तर" and status != "सही":
                continue

            with st.expander(
                f"प्रश्न {i + 1} · {status}"
            ):
                st.markdown(f"**{question['question']}**")

                for opt_i, option in enumerate(question["options"]):
                    prefix = chr(65 + opt_i)
                    if opt_i == correct_answer:
                        st.success(f"{prefix}. {option} — सही उत्तर")
                    elif opt_i == selected:
                        st.error(f"{prefix}. {option} — आपका उत्तर")
                    else:
                        st.write(f"{prefix}. {option}")

                if selected is None:
                    st.info("आपने इस प्रश्न का उत्तर नहीं दिया।")
                elif selected == correct_answer:
                    st.success("आपका उत्तर सही था।")
                else:
                    st.error(
                        f"आपका उत्तर: {question['options'][selected]}"
                    )

                st.markdown(
                    f"**सही उत्तर:** {chr(65 + correct_answer)}. "
                    f"{question['options'][correct_answer]}"
                )
                st.write("**समाधान:**")
                st.write(question.get("explanation", "समाधान उपलब्ध नहीं है।"))

                if question.get("is_pyq"):
                    if question.get("year"):
                        st.caption(f"वर्ष: {question['year']}")
                    if question.get("shift"):
                        st.caption(f"Shift: {question['shift']}")
                    if question.get("source_url"):
                        st.markdown(
                            f"[स्रोत देखें]({question['source_url']})"
                        )

    st.divider()
    left, right = st.columns(2)

    with left:
        if st.button("🏠 Home पर जाओ"):
            st.session_state.quiz_started = False
            st.session_state.quiz_submitted = False
            st.session_state.page = "Home"
            st.rerun()

    with right:
        if st.button("🔄 फिर से Practice"):
            st.session_state.quiz_started = False
            st.session_state.quiz_submitted = False
            st.session_state.page = "AI Practice"
            st.rerun()


# =========================
# PDF QUIZ
# =========================
def pdf_quiz_page():
    st.title("📄 PDF से Quiz बनाओ")
    st.write("अपनी PDF अपलोड करो और उससे MCQ टेस्ट तैयार करो।")

    uploaded = st.file_uploader(
        "PDF चुनो",
        type=["pdf"],
        key="pdf_upload"
    )

    count = st.slider(
        "कितने प्रश्न चाहिए?",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
        key="pdf_count"
    )

    difficulty = st.selectbox(
        "कठिनाई",
        ["Easy", "Medium", "Hard", "Mixed"],
        key="pdf_difficulty"
    )

    language = st.selectbox(
        "प्रश्नों की भाषा",
        ["Hindi", "English"],
        key="pdf_language"
    )

    duration = st.selectbox(
        "टेस्ट का समय",
        [5, 10, 15, 20, 30, 45, 60],
        index=2,
        format_func=lambda x: f"{x} मिनट",
        key="pdf_duration"
    )

    if st.button("✨ Quiz बनाओ", type="primary"):
        if uploaded is None:
            st.warning("पहले PDF अपलोड करो।")
        else:
            with st.spinner("PDF पढ़कर प्रश्न बनाए जा रहे हैं..."):
                text = extract_pdf_text(uploaded)

                if len(text) < 50:
                    st.error(
                        "PDF से पर्याप्त टेक्स्ट नहीं मिला। "
                        "अगर PDF स्कैन की हुई तस्वीर है, तो टेक्स्ट वाली PDF इस्तेमाल करो।"
                    )
                else:
                    questions = generate_questions(
                        source_text=text,
                        count=count,
                        difficulty=difficulty,
                        topic="Uploaded PDF",
                        language=language,
                        exam="PDF Practice"
                    )

                    if questions:
                        start_quiz(
                            questions,
                            "PDF Quiz",
                            "pdf",
                            duration,
                            language
                        )
                        st.rerun()


# =========================
# PYQ PRACTICE
# =========================
def pyq_page():
    st.title("🏆 PYQ Practice")
    st.write("यहाँ केवल सत्यापित Previous Year Questions दिखाए जाने चाहिए।")

    sb = get_supabase()

    exam = st.selectbox(
        "Exam चुनो",
        [
            "SSC CGL",
            "SSC CHSL",
            "Railway",
            "UP Police",
            "Delhi Police",
            "RPF",
            "IB",
            "Defence",
            "Other"
        ],
        key="pyq_exam"
    )

    subject = st.selectbox(
        "Subject",
        [
            "All Subjects",
            "Maths",
            "Reasoning",
            "General Knowledge",
            "General Science",
            "English",
            "Hindi"
        ],
        key="pyq_subject"
    )

    count = st.selectbox(
        "प्रश्नों की संख्या",
        [10, 20, 30, 50],
        key="pyq_count"
    )

    duration = st.selectbox(
        "टेस्ट का समय",
        [10, 15, 20, 30, 45, 60],
        index=1,
        format_func=lambda x: f"{x} मिनट",
        key="pdf_duration"
    )

    if st.button("✨ Quiz बनाओ", type="primary"):
        if uploaded is None:
            st.warning("पहले PDF अपलोड करो।")
        else:
            with st.spinner("PDF पढ़कर प्रश्न बनाए जा रहे हैं..."):
                text = extract_pdf_text(uploaded)

                if len(text) < 50:
                    st.error(
                        "PDF से पर्याप्त टेक्स्ट नहीं मिला। "
                        "अगर PDF स्कैन की हुई तस्वीर है, तो टेक्स्ट वाली PDF इस्तेमाल करो।"
                    )
                else:
                    questions = generate_questions(
                        source_text=text,
                        count=count,
                        difficulty=difficulty,
                        topic="Uploaded PDF",
                        language=language,
                        exam="PDF Practice"
                    )

                    if questions:
                        start_quiz(
                            questions,
                            "PDF Quiz",
                            "pdf",
                            duration,
                            language
                        )
                        st.rerun()


# =========================
# PYQ PRACTICE
# =========================
def pyq_page():
    st.title("🏆 PYQ Practice")
    st.write("यहाँ केवल सत्यापित Previous Year Questions दिखाए जाने चाहिए।")

    sb = get_supabase()

    exam = st.selectbox(
        "Exam चुनो",
        [
            "SSC CGL",
            "SSC CHSL",
            "Railway",
            "UP Police",
            "Delhi Police",
            "RPF",
            "IB",
            "Defence",
            "Other"
        ],
        key="pyq_exam"
    )

    subject = st.selectbox(
        "Subject",
        [
            "All Subjects",
            "Maths",
            "Reasoning",
            "General Knowledge",
            "General Science",
            "English",
            "Hindi"
        ],
        key="pyq_subject"
    )

    count = st.selectbox(
        "प्रश्नों की संख्या",
        [10, 20, 30, 50],
        key="pyq_count"
    )

    duration = st.selectbox(
        "टेस्ट का समय",
        [10, 15, 20, 30, 45, 60],
        index=1,
        format_func=lambda x: f"{x} मिनट",
        key="pyq_duration"
    )

    language = st.selectbox(
        "भाषा",
        ["Hindi", "English"],
        key="pyq_language"
    )

    if st.button("🚀 PYQ Test शुरू करो", type="primary"):
        if sb is None:
            st.error("Supabase connection नहीं हुआ। Secrets चेक करो।")
            return

        try:
            response = (
                sb.table("pyq_questions")
                .select("*")
                .eq("verified", True)
                .eq("exam", exam)
                .limit(500)
                .execute()
            )

            rows = response.data or []

            # Only verified questions with a real source URL are accepted.
            rows = [
                row for row in rows
                if row.get("source_url")
                and str(row.get("source_url")).startswith(("http://", "https://"))
            ]

            if subject != "All Subjects":
                rows = [
                    row for row in rows
                    if str(row.get("subject", "")).lower()
                    == subject.lower()
                ]

            questions = []

            for row in rows:
                options = row.get("options", [])

                if isinstance(options, str):
                    try:
                        options = json.loads(options)
                    except Exception:
                        continue

                try:
                    answer = int(row.get("answer"))
                except Exception:
                    continue

                if (
                    not row.get("question")
                    or not isinstance(options, list)
                    or len(options) != 4
                    or answer not in range(4)
                ):
                    continue

                questions.append({
                    "question": str(row["question"]),
                    "options": [str(x) for x in options],
                    "answer": answer,
                    "explanation": str(
                        row.get("explanation", "समाधान अभी उपलब्ध नहीं है।")
                    ),
                    "year": row.get("year"),
                    "shift": row.get("shift"),
                    "source_url": row.get("source_url"),
                    "is_pyq": True,
                })

            if not questions:
                st.warning(
                    "इस Exam/Subject के लिए अभी कोई सत्यापित PYQ उपलब्ध नहीं है। "
                    "AI-generated प्रश्नों को असली PYQ बताकर नहीं दिखाया जाएगा।"
                )
            else:
                random.shuffle(questions)
                questions = questions[:count]

                start_quiz(
                    questions,
                    f"{exam} PYQ",
                    "pyq",
                    duration,
                    language
                )
                st.rerun()

        except Exception as e:
            st.error(f"PYQ लोड नहीं हो पाए: {e}")


# =========================
# AI PRACTICE
# =========================
def ai_practice_page():
    st.title("🤖 AI Practice")
    st.write("AI से नए अभ्यास प्रश्न बनाओ। ये असली PYQ नहीं होंगे।")

    exam = st.selectbox(
        "Exam",
        [
            "SSC CGL",
            "SSC CHSL",
            "Railway",
            "UP Police",
            "Delhi Police",
            "RPF",
            "IB",
            "Defence",
            "General Competitive Exam"
        ],
        key="ai_exam"
    )

    subject = st.selectbox(
        "Subject",
        [
            "Maths",
            "Reasoning",
            "General Knowledge",
            "General Science",
            "English",
            "Hindi",
            "Computer"
        ],
        key="ai_subject"
    )

    topic = st.text_input(
        "Topic (वैकल्पिक)",
        placeholder="जैसे प्रतिशत, रक्त संबंध, संविधान",
        key="ai_topic"
    )

    count = st.selectbox(
        "प्रश्नों की संख्या",
        [5, 10, 15, 20, 30],
        index=1,
        key="ai_count"
    )

    difficulty = st.selectbox(
        "कठिनाई",
        ["Easy", "Medium", "Hard", "Mixed"],
        key="ai_difficulty"
    )

    language = st.selectbox(
        "भाषा",
        ["Hindi", "English"],
        key="ai_language"
    )

    duration = st.selectbox(
        "टेस्ट का समय",
        [5, 10, 15, 20, 30, 45, 60],
        index=2,
        format_func=lambda x: f"{x} मिनट",
        key="ai_duration"
    )

    if st.button("⚡ AI प्रश्न बनाओ", type="primary"):
        with st.spinner("AI प्रश्न बना रहा है..."):
            questions = generate_questions(
                source_text=(
                    f"Create practice questions for the topic: "
                    f"{topic or subject}. Subject: {subject}."
                ),
                count=count,
                difficulty=difficulty,
                topic=topic or subject,
                language=language,
                exam=exam
            )

        if questions:
            start_quiz(
                questions,
                f"{exam} · {subject} AI Practice",
                "ai",
                duration,
                language
            )
            st.rerun()


# =========================
# QUICK ACCESS
# =========================
def quick_access_page():
    st.title("🚀 Quick Access")
    st.write("अपने लक्ष्य वाले Exam को चुनो।")

    exams = [
        "SSC",
        "Railways",
        "IB",
        "UP Police",
        "RPF",
        "Delhi Police",
        "MP Police",
        "Defence"
    ]

    for i in range(0, len(exams), 2):
        col1, col2 = st.columns(2)

        with col1:
            exam = exams[i]
            if st.button(f"🎯 {exam}", key=f"quick_{exam}"):
                st.info("COMING SOON — जल्द ही धमाका होगा!")

        if i + 1 < len(exams):
            with col2:
                exam = exams[i + 1]
                if st.button(f"🎯 {exam}", key=f"quick_{exam}"):
                    st.info("COMING SOON — जल्द ही धमाका होगा!")


# =========================
# HOME
# =========================
def home_page():
    st.title("🏠 Welcome to AI Quiz Maker")

    st.write(
        "PDF से टेस्ट बनाओ, PYQ Practice करो और AI से नए प्रश्नों का अभ्यास करो।"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 PDF से Quiz", type="primary"):
            st.session_state.page = "PDF Quiz"
            st.rerun()

        if st.button("🏆 PYQ Practice"):
            st.session_state.page = "PYQ Practice"
            st.rerun()

    with col2:
        if st.button("🤖 AI Practice", type="primary"):
            st.session_state.page = "AI Practice"
            st.rerun()

        if st.button("🚀 Quick Access"):
            st.session_state.page = "Quick Access"
            st.rerun()

    st.divider()
    st.subheader("✨ Features")
    st.markdown("""
    - PDF से MCQ Quiz
    - एक समय में एक प्रश्न
    - Timer और Auto Submit
    - सही, गलत और छोड़े गए प्रश्नों का Result
    - विस्तृत Solutions
    - अलग Real PYQ और AI Practice
    """)


# =========================
# MAIN APP FLOW
# =========================
if st.session_state.user is None:
    login_screen()

else:
    with st.sidebar:
        st.title("🧠 AI Quiz Maker")
        st.caption(st.session_state.user.get("email", ""))

        page_options = [
            "Home",
            "PDF Quiz",
            "PYQ Practice",
            "AI Practice",
            "Quick Access"
        ]

        current_page = st.session_state.page
        if current_page not in page_options:
            current_page = "Home"

        selected_page = st.radio(
            "Menu",
            page_options,
            index=page_options.index(current_page),
            key="main_navigation"
        )

        if selected_page != st.session_state.page:
            st.session_state.page = selected_page
            st.rerun()

        st.divider()

        if st.button("🚪 Logout"):
            try:
                sb = get_supabase()
                if sb:
                    sb.auth.sign_out()
            except Exception:
                pass

            st.session_state.user = None
            st.session_state.quiz = []
            st.session_state.answers = {}
            st.session_state.quiz_started = False
            st.session_state.quiz_submitted = False
            st.session_state.page = "Home"
            st.rerun()

    # Running quiz and results take priority over normal pages.
    if st.session_state.quiz_started:
        show_question_player()

    elif st.session_state.quiz_submitted:
        show_results()

    elif st.session_state.page == "Home":
        home_page()

    elif st.session_state.page == "PDF Quiz":
        pdf_quiz_page()

    elif st.session_state.page == "PYQ Practice":
        pyq_page()

    elif st.session_state.page == "AI Practice":
        ai_practice_page()

    elif st.session_state.page == "Quick Access":
        quick_access_page()
