import json
import re
import time
import uuid
from datetime import datetime, timezone

import streamlit as st
from pypdf import PdfReader
from google import genai
from supabase import create_client

# =========================================================
# AI QUIZ MAKER | PRATEEK SENMAR
# Streamlit Secrets:
# SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY
# Optional: GEMINI_MODEL
# =========================================================

st.set_page_config(
    page_title="AI Quiz Maker | Prateek Senmar",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

.stApp {
 background:
 radial-gradient(circle at 10% 0%,rgba(124,58,237,.24),transparent 32%),
 radial-gradient(circle at 95% 20%,rgba(168,85,247,.13),transparent 28%),
 linear-gradient(145deg,#090611 0%,#120b22 48%,#080610 100%);
 color:#f7f3ff;
 font-family:Inter,sans-serif;
}
.block-container {max-width:850px;padding-top:1.2rem;padding-bottom:3rem}
.hero {
 padding:25px 18px;
 border:1px solid rgba(196,181,253,.25);
 border-radius:24px;
 text-align:center;
 background:linear-gradient(135deg,rgba(109,40,217,.34),rgba(30,20,50,.65));
 box-shadow:0 14px 50px rgba(0,0,0,.25);
 margin-bottom:18px;
}
.brand {font-size:clamp(1.9rem,6vw,3rem);font-weight:900}
.sub {color:#d8c8ff}
.eyebrow {color:#c4b5fd;font-size:.72rem;letter-spacing:2px;font-weight:800}
div.stButton>button,div.stFormSubmitButton>button {
 width:100%;min-height:48px;border-radius:14px;
 border:1px solid rgba(196,181,253,.24);
 background:linear-gradient(135deg,#6d28d9,#4c1d95);
 color:white;font-weight:800;
}
div.stButton>button:hover,div.stFormSubmitButton>button:hover {
 border-color:#c4b5fd;color:white;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea {
 background:#171126;color:#fff;border:1px solid #49356c;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"]>div {
 background:#171126;border-color:#49356c;color:white;
}
.card {
 border:1px solid rgba(196,181,253,.22);
 border-radius:18px;
 background:linear-gradient(145deg,rgba(35,22,59,.94),rgba(16,11,28,.94));
 padding:17px;margin:7px 0;
}
.small-muted {color:#c4b5fd;font-size:.86rem}
.exam-card {
 border:1px solid rgba(196,181,253,.28);
 border-radius:16px;
 background:linear-gradient(135deg,rgba(109,40,217,.42),rgba(31,20,49,.92));
 padding:16px;text-align:center;min-height:78px;font-weight:800;
}
.metric {
 padding:12px;border:1px solid rgba(196,181,253,.2);
 border-radius:14px;background:rgba(109,40,217,.12);text-align:center;
}
hr {border-color:rgba(196,181,253,.17)}
footer {visibility:hidden}
</style>
""", unsafe_allow_html=True)


# ---------------- CONFIGURATION ----------------

def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


@st.cache_resource
def get_clients():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    gkey = get_secret("GEMINI_API_KEY")

    if not url or not key:
        return None, None, "SUPABASE_URL या SUPABASE_KEY missing है।"

    if not gkey:
        return None, None, "GEMINI_API_KEY missing है।"

    try:
        return (
            create_client(url, key),
            genai.Client(api_key=gkey),
            None,
        )
    except Exception as exc:
        return None, None, str(exc)


supabase, gemini, config_error = get_clients()
MODEL = get_secret("GEMINI_MODEL", "gemini-3.8-flash")


def init_state():
    defaults = {
        "page": "home",
        "user": None,
        "quiz": [],
        "answers": {},
        "q_index": 0,
        "quiz_title": "",
        "quiz_mode": "",
        "quiz_language": "Hindi",
        "quiz_started": False,
        "quiz_submitted": False,
        "quiz_started_at": None,
        "quiz_seconds": 1800,
        "history_id": None,
        "review_index": 0,
        "last_saved": False,
        "quick_exam": "SSC",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def set_page(page):
    st.session_state.page = page
    st.rerun()


def header():
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">SMART PRACTICE • BETTER PREPARATION</div>
      <div class="brand">🧠 AI Quiz Maker</div>
      <div class="sub">Learn smarter. Practice better. Achieve more.</div>
      <div style="margin-top:10px;font-weight:800;color:#e9ddff">
        ✨ PRATEEK SENMAR ✨
      </div>
    </div>
    """, unsafe_allow_html=True)


def get_user_id():
    user = st.session_state.get("user")
    if isinstance(user, dict):
        return user.get("id")
    return getattr(user, "id", None)


def get_user_email():
    user = st.session_state.get("user")
    if isinstance(user, dict):
        return user.get("email", "")
    return getattr(user, "email", "")


def logout():
    try:
        if supabase:
            supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.user = None
    st.session_state.page = "home"
    st.session_state.quiz = []
    st.session_state.answers = {}
    st.session_state.quiz_started = False
    st.session_state.quiz_submitted = False
    st.rerun()


def go_home():
    if st.button("← Home", key=f"home_{st.session_state.page}"):
        set_page("home")


# ---------------- PDF AND AI GENERATION ----------------

def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []

    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pass

    text = "\n".join(pages).strip()

    if not text:
        raise ValueError(
            "PDF से text नहीं मिला। Text-based PDF अपलोड करें।"
        )

    return text[:80000]


def language_instruction(language):
    if language == "Hindi":
        return "सभी प्रश्न, विकल्प और समाधान सरल हिंदी में देवनागरी लिपि में लिखें।"
    return "Write all questions, options and explanations in clear English."


def parse_json_response(raw):
    raw = (raw or "").strip()
    raw = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw,
        flags=re.I,
    )

    start = raw.find("{")
    end = raw.rfind("}")

    if start >= 0 and end > start:
        raw = raw[start:end + 1]

    return json.loads(raw)


def generate_questions(
    source_text,
    count,
    difficulty,
    topic,
    language,
    source_name,
):
    if not gemini:
        raise RuntimeError(config_error or "Gemini API configured नहीं है।")

    prompt = f"""
Create exactly {count} exam-quality multiple-choice questions.

Difficulty: {difficulty}
Subject/topic: {topic or 'infer from source'}
Language: {language_instruction(language)}

Return ONLY valid JSON in this format:
{{
 "questions": [
  {{
   "question": "Question text",
   "options": ["Option A","Option B","Option C","Option D"],
   "answer": 0,
   "explanation": "Concise helpful explanation"
  }}
 ]
}}

Rules:
- Exactly four distinct options for every question.
- answer must be integer 0, 1, 2 or 3.
- Explanation should clearly explain the answer without unnecessary length.
- Avoid duplicate questions.
- Never label AI-generated questions as real PYQs.
- Never invent a previous-year date or exam year.
- Use only reliable, standard facts where the material is not sufficient.

Source: {source_name}

MATERIAL:
{source_text[:60000]}
"""

    
    
    model_candidates = [
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash-lite",
    ]

    response = None
    last_error = None

    for candidate in model_candidates:
        try:
            response = gemini.models.generate_content(
                model=candidate,
                contents=prompt,
                config={
                    "temperature": 0.25,
                    "response_mime_type": "application/json",
                },
            )
            break
        except Exception as exc:
            last_error = exc
            continue

    if response is None:
        raise RuntimeError(
            f"Gemini ke sabhi models fail hue: {last_error}"
        )
        
            

    data = parse_json_response(response.text)
    questions = data.get("questions", [])
    clean = []

    for question in questions:
        options = question.get("options", [])

        try:
            answer = int(question.get("answer", 0))
        except Exception:
            continue

        if not isinstance(question.get("question"), str):
            continue

        if len(options) != 4 or answer not in range(4):
            continue

        clean.append({
            "question": question["question"].strip(),
            "options": [str(x) for x in options],
            "answer": answer,
            "explanation": str(
                question.get("explanation", "")
            ).strip(),
            "source_date": None,
            "origin": "AI-generated",
        })

    if not clean:
        raise ValueError(
            "AI से valid questions नहीं मिले। Topic या PDF बदलकर कोशिश करें।"
        )

    return clean[:count]


# ---------------- QUIZ ENGINE ----------------

def start_quiz(questions, title, mode, language, minutes):
    if not questions:
        st.error("कोई question उपलब्ध नहीं है।")
        return

    st.session_state.quiz = questions
    st.session_state.quiz_title = title
    st.session_state.quiz_mode = mode
    st.session_state.quiz_language = language
    st.session_state.answers = {}
    st.session_state.q_index = 0
    st.session_state.quiz_started = True
    st.session_state.quiz_submitted = False
    st.session_state.quiz_started_at = time.time()
    st.session_state.quiz_seconds = max(60, int(minutes * 60))
    st.session_state.history_id = str(uuid.uuid4())
    st.session_state.last_saved = False

    set_page("test")


def remaining_seconds():
    start = st.session_state.quiz_started_at

    if not start:
        return st.session_state.quiz_seconds

    elapsed = int(time.time() - start)
    return max(0, st.session_state.quiz_seconds - elapsed)


def calculate_results():
    questions = st.session_state.quiz
    answers = st.session_state.answers

    correct = 0
    wrong = 0
    skipped = 0

    for index, question in enumerate(questions):
        selected = answers.get(index)

        if selected is None:
            skipped += 1
        elif int(selected) == int(question["answer"]):
            correct += 1
        else:
            wrong += 1

    total = len(questions)

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "score": correct,
        "percentage": round(correct / total * 100, 1) if total else 0,
    }


def save_history():
    if st.session_state.last_saved:
        return True

    if not supabase or not get_user_id():
        return False

    result = calculate_results()

    record = {
        "id": st.session_state.history_id or str(uuid.uuid4()),
        "user_id": get_user_id(),
        "title": st.session_state.quiz_title,
        "mode": st.session_state.quiz_mode,
        "language": st.session_state.quiz_language,
        "total": result["total"],
        "correct": result["correct"],
        "wrong": result["wrong"],
        "skipped": result["skipped"],
        "percentage": result["percentage"],
        "quiz_json": json.dumps(
            st.session_state.quiz,
            ensure_ascii=False,
        ),
        "answers_json": json.dumps(
            st.session_state.answers,
            ensure_ascii=False,
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        supabase.table("quiz_history").insert(record).execute()
        st.session_state.last_saved = True
        return True
    except Exception as exc:
        st.session_state.history_save_error = str(exc)
        return False


def submit_quiz():
    st.session_state.quiz_submitted = True
    st.session_state.quiz_started = False
    save_history()
    set_page("results")


# ---------------- AUTHENTICATION ----------------

def auth_page():
    header()
    st.subheader("🔐 Login / Sign Up")

    if not supabase:
        st.error(
            "Supabase configuration missing है। "
            "Streamlit Secrets में SUPABASE_URL और SUPABASE_KEY डालें।"
        )
        return

    mode = st.radio(
        "Account",
        ["Login", "Sign Up"],
        horizontal=True,
        key="auth_mode_radio",
    )

    with st.form("auth_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        confirm = None
        if mode == "Sign Up":
            confirm = st.text_input("Confirm password", type="password")

        submitted = st.form_submit_button(
            "Login" if mode == "Login" else "Create Account"
        )

    if not submitted:
        return

    if not email.strip() or not password:
        st.error("Email और password भरें।")
        return

    if mode == "Sign Up" and password != confirm:
        st.error("दोनों password एक जैसे नहीं हैं।")
        return

    try:
        with st.spinner("Account check हो रहा है..."):
            if mode == "Login":
                result = supabase.auth.sign_in_with_password({
                    "email": email.strip(),
                    "password": password,
                })
            else:
                result = supabase.auth.sign_up({
                    "email": email.strip(),
                    "password": password,
                })

        user = getattr(result, "user", None)
        session = getattr(result, "session", None)

        if user and session:
            st.session_state.user = {
                "id": user.id,
                "email": user.email,
            }
            set_page("home")

        elif user and mode == "Sign Up":
            st.success(
                "Account बन गया। Email confirmation चालू है तो "
                "पहले email verify करें, फिर login करें।"
            )

        else:
            st.error(
                "Login पूरा नहीं हुआ। Email, password और Supabase Auth settings जाँचें।"
            )

    except Exception as exc:
        st.error(f"Authentication error: {exc}")


# ---------------- HOME ----------------

def home_page():
    header()

    if st.session_state.user:
        st.markdown(
            f'<div class="small-muted">👋 Welcome, {get_user_email()}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Quiz History को account से save करने के लिए Login करें।")

    st.markdown("### अपना practice mode चुनें")

    left, right = st.columns(2)

    with left:
        if st.button("📄 PDF TO QUIZ\nअपने PDF से MCQ बनाएं", key="home_pdf"):
            set_page("pdf")

        if st.button("📚 PYQ PRACTICE\nReal previous-year questions", key="home_pyq"):
            set_page("pyq")

    with right:
        if st.button("🤖 AI PRACTICE\nTopic से नए MCQ", key="home_ai"):
            set_page("ai")

        if st.button("⚡ QUICK ACCESS\nExam-wise practice", key="home_quick"):
            set_page("quick")

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        if st.button("📊 Quiz History", key="home_history"):
            set_page("history")

    with right:
        if st.session_state.user:
            if st.button("🚪 Logout", key="home_logout"):
                logout()
        else:
            if st.button("🔐 Login / Sign Up", key="home_login"):
                set_page("auth")

    st.markdown("""
    <div class="card">
      <b>✨ Your Study Dashboard</b><br>
      <span class="small-muted">
      PDF-based practice • AI-generated MCQs • Real PYQs
      • Timed tests • Results • Quiz Analysis • Saved History
      </span>
    </div>
    """, unsafe_allow_html=True)


# ---------------- PDF QUIZ ----------------

def pdf_page():
    go_home()
    st.title("📄 PDF to Quiz")
    st.caption("PDF upload करें और उसी material से MCQ बनाएं।")

    file = st.file_uploader(
        "अपनी PDF चुनें",
        type=["pdf"],
        key="pdf_upload",
    )

    left, right = st.columns(2)

    with left:
        count = st.selectbox(
            "Questions",
            [10, 25, 50, 100, 200],
            key="pdf_count",
        )
        difficulty = st.selectbox(
            "Difficulty",
            ["Easy", "Medium", "Moderate"],
            key="pdf_difficulty",
        )
        language = st.selectbox(
            "Language",
            ["Hindi", "English"],
            key="pdf_language",
        )

    with right:
        minutes = st.selectbox(
            "Timer (minutes)",
            [10, 15, 20, 30, 45, 60, 90, 120],
            index=3,
            key="pdf_timer",
        )
        topic = st.text_input(
            "Subject / Topic (optional)",
            key="pdf_topic",
        )

    if st.button("🚀 Generate Quiz", key="pdf_generate"):
        if not file:
            st.warning("पहले PDF upload करें।")
            return

        try:
            with st.spinner("PDF पढ़कर questions बन रहे हैं..."):
                material = extract_pdf_text(file)
                questions = generate_questions(
                    material,
                    count,
                    difficulty,
                    topic,
                    language,
                    file.name,
                )

            start_quiz(
                questions,
                f"PDF: {file.name}",
                "PDF to Quiz",
                language,
                minutes,
            )

        except Exception as exc:
            st.error(f"Quiz नहीं बन पाया: {exc}")
            st.caption(
                "Gemini API key, model, quota और PDF के text-based होने की जाँच करें।"
            )


# ---------------- AI PRACTICE ----------------

def ai_page():
    go_home()
    st.title("🤖 AI Practice")
    st.caption("ये नए AI-generated questions होंगे, real PYQs नहीं।")

    exams = [
        "SSC", "Railways", "IB", "UP Police",
        "RPF", "Delhi Police", "MP Police",
        "Defence", "General",
    ]

    subjects = [
        "General Knowledge", "Reasoning", "Maths", "English",
        "Science", "History", "Geography", "Polity", "Current Affairs",
    ]

    with st.form("ai_practice_form"):
        exam = st.selectbox("Exam", exams)
        subject = st.selectbox("Subject", subjects)
        topic = st.text_input("Specific topic (optional)")

        left, right = st.columns(2)

        with left:
            count = st.selectbox(
                "Questions",
                [10, 25, 50, 100, 200],
            )
            difficulty = st.selectbox(
                "Difficulty",
                ["Easy", "Medium", "Moderate"],
            )

        with right:
            minutes = st.selectbox(
                "Timer (minutes)",
                [10, 15, 20, 30, 45, 60, 90, 120],
                index=3,
            )
            language = st.selectbox(
                "Language",
                ["Hindi", "English"],
            )

        make = st.form_submit_button("✨ Generate AI Practice")

    if make:
        description = (
            f"Create exam-style practice questions for {exam}. "
            f"Subject: {subject}. Topic: {topic or subject}. "
            "Use standard, verifiable facts."
        )

        try:
            with st.spinner("AI questions तैयार कर रहा है..."):
                questions = generate_questions(
                    description,
                    count,
                    difficulty,
                    f"{exam} / {subject} / {topic}",
                    language,
                    "AI Practice",
                )

            start_quiz(
                questions,
                f"{exam} — {subject}",
                "AI Practice",
                language,
                minutes,
            )

        except Exception as exc:
            st.error(f"AI Practice शुरू नहीं हो पाई: {exc}")


# ---------------- PYQ PRACTICE ----------------

def load_pyq_questions(exam, subject, year, count):
    if not supabase:
        raise RuntimeError("Supabase configured नहीं है।")

    query = (
        supabase.table("pyq_questions")
        .select("*")
        .eq("exam", exam)
        .eq("subject", subject)
    )

    if year != "All years":
        query = query.eq("year", int(year))

    response = query.limit(count).execute()
    rows = response.data or []
    output = []

    for row in rows:
        options = row.get("options", [])

        if isinstance(options, str):
            try:
                options = json.loads(options)
            except Exception:
                options = []

        if not isinstance(options, list) or len(options) != 4:
            continue

        try:
            answer = int(row.get("answer", 0))
        except Exception:
            continue

        if answer not in range(4):
            continue

        output.append({
            "question": row.get("question", ""),
            "options": [str(x) for x in options],
            "answer": answer,
            "explanation": row.get("explanation", "") or "",
            "source_date": row.get("year"),
            "origin": "Real PYQ",
        })

    return output


def pyq_page():
    go_home()
    st.title("📚 PYQ Practice")
    st.caption(
        "यहाँ database में मौजूद verified real PYQs ही दिखेंगे। "
        "AI questions को PYQ नहीं कहा जाएगा।"
    )

    exams = [
        "SSC", "Railways", "IB", "UP Police",
        "RPF", "Delhi Police", "MP Police", "Defence",
    ]

    subjects = [
        "General Knowledge", "Reasoning", "Maths", "English",
        "Science", "History", "Geography", "Polity", "Current Affairs",
    ]

    with st.form("pyq_form"):
        left, right = st.columns(2)

        with left:
            exam = st.selectbox("Exam", exams)
            subject = st.selectbox("Subject", subjects)
            year = st.selectbox(
                "Year",
                ["All years"] + list(range(2026, 2009, -1)),
            )

        with right:
            count = st.selectbox(
                "Questions",
                [10, 25, 50, 100, 200],
            )
            minutes = st.selectbox(
                "Timer (minutes)",
                [10, 15, 20, 30, 45, 60, 90, 120],
                index=3,
            )
            language = st.selectbox(
                "Language",
                ["Hindi", "English"],
            )

        search = st.form_submit_button("🔎 Find Real PYQs")

    if search:
        try:
            with st.spinner("Question bank check हो रहा है..."):
                questions = load_pyq_questions(
                    exam,
                    subject,
                    year,
                    count,
                )

            if not questions:
                st.warning(
                    "इस selection के लिए कोई real PYQ नहीं मिला। "
                    "पहले verified questions database में add करें।"
                )
            else:
                start_quiz(
                    questions,
                    f"{exam} — {subject} — PYQ",
                    "PYQ Practice",
                    language,
                    minutes,
                )

        except Exception as exc:
            st.error(f"PYQ database error: {exc}")


# ---------------- QUICK ACCESS ----------------

def quick_page():
    go_home()
    st.title("⚡ Quick Access")
    st.caption("Exam चुनें")

    exams = [
        ("🟣", "SSC"),
        ("🚆", "Railways"),
        ("🕵️", "IB"),
        ("👮", "UP Police"),
        ("🚔", "RPF"),
        ("🏙️", "Delhi Police"),
        ("🛡️", "MP Police"),
        ("✈️", "Defence"),
    ]

    for row in range(4):
        left, right = st.columns(2)

        for col, (icon, name) in zip(
            [left, right],
            exams[row * 2:row * 2 + 2],
        ):
            with col:
                st.markdown(
                    f'<div class="exam-card">{icon}<br>{name}</div>',
                    unsafe_allow_html=True,
                )

                if name == "SSC":
                    if st.button("Open SSC", key="quick_ssc"):
                        st.session_state.quick_exam = "SSC"
                        set_page("ai")
                else:
                    if st.button(
                        f"Open {name}",
                        key=f"quick_{name}",
                    ):
                        st.session_state.quick_exam = name
                        set_page("coming_soon")


def coming_soon_page():
    go_home()
    exam = st.session_state.get("quick_exam", "Exam")

    st.markdown(f"""
    <div class="hero">
      <div class="brand">🚀 COMING SOON</div>
      <div style="font-size:1.08rem;line-height:1.8;margin-top:16px">
      अभी काम कुछ समय के लिए रुका हुआ है।<br>
      अभी Depression का दौर चल रहा है, इसलिए काम बंद है। ❤️‍🩹<br>
      अभी वक्त मुश्किल है, लेकिन वापसी होगी और धमाका बड़ा करेंगे! 🔥
      </div>
      <div class="sub" style="margin-top:14px">{exam}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------- TEST PLAYER ----------------

def test_page():
    if not st.session_state.quiz:
        st.warning("कोई active quiz नहीं है।")
        go_home()
        return

    if st.session_state.quiz_submitted:
        set_page("results")
        return

    questions = st.session_state.quiz
    index = min(
        max(st.session_state.q_index, 0),
        len(questions) - 1,
    )

    remaining = remaining_seconds()

    left, right = st.columns(2)

    with left:
        st.caption(f"🌐 Language: {st.session_state.quiz_language}")

    with right:
        st.markdown(
            f"**⏱️ {remaining // 60:02d}:{remaining % 60:02d}**"
        )

    language = st.selectbox(
        "Display language preference",
        ["Hindi", "English"],
        index=0 if st.session_state.quiz_language == "Hindi" else 1,
        key="test_language_select",
    )

    if language != st.session_state.quiz_language:
        st.session_state.quiz_language = language
        st.info(
            "Language preference बदल गई है। पहले से बने questions "
            "अपनी original generated language में रहेंगे।"
        )

    question = questions[index]

    st.progress((index + 1) / len(questions))
    st.markdown(f"### Question {index + 1} of {len(questions)}")

    if question.get("origin") == "Real PYQ" and question.get("source_date"):
        st.caption(f"Verified PYQ • {question['source_date']}")
    elif question.get("origin") == "AI-generated":
        st.caption("AI-generated practice • Real PYQ नहीं")

    st.markdown(
        f'<div class="card"><b>{question["question"]}</b></div>',
        unsafe_allow_html=True,
    )

    selected = st.session_state.answers.get(index)

    for option_index, option in enumerate(question["options"]):
        label = f"{'🟣' if selected == option_index else '◯'} {chr(65 + option_index)}. {option}"

        if st.button(
            label,
            key=f"option_{index}_{option_index}",
        ):
            st.session_state.answers[index] = option_index
            st.rerun()

    st.caption(
        f"Answered {len(st.session_state.answers)} / {len(questions)}"
    )

    previous, next_col, submit_col = st.columns(3)

    with previous:
        if st.button(
            "← Previous",
            disabled=index == 0,
            key="test_previous",
        ):
            st.session_state.q_index -= 1
            st.rerun()

    with next_col:
        if st.button(
            "Next →",
            disabled=index >= len(questions) - 1,
            key="test_next",
        ):
            st.session_state.q_index += 1
            st.rerun()

    with submit_col:
        if st.button("Submit Test", key="test_submit"):
            submit_quiz()

    if remaining <= 0:
        st.warning("समय पूरा हुआ। Test submit किया जा रहा है।")
        submit_quiz()

    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=1000, key="quiz_timer_refresh")
    except Exception:
        st.caption("Timer अगली interaction पर refresh होगा।")


# ---------------- RESULTS ----------------

def results_page():
    if not st.session_state.quiz:
        st.warning("कोई result नहीं मिला।")
        go_home()
        return

    result = calculate_results()
    st.title("🏁 Test Result")
    st.caption(st.session_state.quiz_title)

    metrics = [
        ("Score", f'{result["score"]}/{result["total"]}'),
        ("Correct", result["correct"]),
        ("Wrong", result["wrong"]),
        ("Skipped", result["skipped"]),
    ]

    columns = st.columns(4)

    for column, (label, value) in zip(columns, metrics):
        with column:
            st.markdown(
                f'<div class="metric"><div class="small-muted">{label}</div>'
                f'<div style="font-size:1.45rem;font-weight:900">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown(f'### Percentage: {result["percentage"]}%')
    st.progress(result["percentage"] / 100)

    st.info(
        "Solutions अपने आप नहीं दिखाई जाएँगी। "
        "नीचे Quiz Analysis खोलकर सही, गलत और skipped questions देखें।"
    )

    if st.session_state.last_saved:
        st.success("Quiz History में result save हो गया।")
    elif st.session_state.user:
        st.warning(
            "History save नहीं हुई हो सकती। Supabase quiz_history table और policies जाँचें।"
        )
        if st.session_state.get("history_save_error"):
            st.caption(st.session_state.history_save_error)
    else:
        st.info("स्थायी Quiz History के लिए Login करें।")

    if st.button("📊 Open Quiz Analysis", key="results_analysis"):
        st.session_state.review_index = 0
        set_page("analysis")

    if st.button("📚 Quiz History", key="results_history"):
        set_page("history")

    if st.button("🏠 Home", key="results_home"):
        st.session_state.quiz = []
        st.session_state.answers = {}
        set_page("home")


# ---------------- QUIZ ANALYSIS ----------------

def analysis_page():
    go_home()

    if not st.session_state.quiz:
        st.warning("Analysis के लिए current quiz उपलब्ध नहीं है।")
        return

    result = calculate_results()

    st.title("📊 Quiz Analysis")
    st.caption(
        f'{st.session_state.quiz_title} • {result["total"]} questions'
    )

    section = st.radio(
        "Question section",
        [
            "All",
            "Correct Questions",
            "Wrong Questions",
            "Skipped Questions",
        ],
        key="analysis_section",
    )

    indices = []

    for index, question in enumerate(st.session_state.quiz):
        selected = st.session_state.answers.get(index)
        correct_answer = int(question["answer"])

        if section == "All":
            indices.append(index)
        elif (
            section == "Correct Questions"
            and selected is not None
            and int(selected) == correct_answer
        ):
            indices.append(index)
        elif (
            section == "Wrong Questions"
            and selected is not None
            and int(selected) != correct_answer
        ):
            indices.append(index)
        elif (
            section == "Skipped Questions"
            and selected is None
        ):
            indices.append(index)

    st.markdown(f"**{section}: {len(indices)}**")

    if not indices:
        st.info("इस section में कोई question नहीं है।")
        return

    position = min(
        max(st.session_state.review_index, 0),
        len(indices) - 1,
    )

    index = indices[position]
    question = st.session_state.quiz[index]
    selected = st.session_state.answers.get(index)

    st.progress((position + 1) / len(indices))
    st.markdown(f"### Question {index + 1}")

    st.markdown(
        f'<div class="card"><b>{question["question"]}</b></div>',
        unsafe_allow_html=True,
    )

    for option_index, option in enumerate(question["options"]):
        if option_index == int(question["answer"]):
            st.success(f"{chr(65 + option_index)}. {option} — Correct Answer")
        elif selected is not None and option_index == int(selected):
            st.error(f"{chr(65 + option_index)}. {option} — Your Answer")
        else:
            st.write(f"{chr(65 + option_index)}. {option}")

    if selected is None:
        st.info("Your answer: Skipped")
    elif int(selected) == int(question["answer"]):
        st.success("Your answer: Correct")
    else:
        st.error("Your answer: Wrong")

    st.markdown("**Solution / Explanation**")
    st.write(
        question.get("explanation")
        or "इस question की explanation उपलब्ध नहीं है।"
    )

    previous, next_col, result_col = st.columns(3)

    with previous:
        if st.button(
            "← Previous",
            disabled=position == 0,
            key="analysis_previous",
        ):
            st.session_state.review_index = position - 1
            st.rerun()

    with next_col:
        if st.button(
            "Next →",
            disabled=position >= len(indices) - 1,
            key="analysis_next",
        ):
            st.session_state.review_index = position + 1
            st.rerun()

    with result_col:
        if st.button("Result", key="analysis_back_result"):
            set_page("results")


# ---------------- QUIZ HISTORY ----------------

def fetch_history():
    if not supabase or not get_user_id():
        return []

    response = (
        supabase.table("quiz_history")
        .select(
            "id,title,mode,language,total,correct,wrong,skipped,"
            "percentage,created_at,quiz_json,answers_json"
        )
        .eq("user_id", get_user_id())
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )

    return response.data or []


def history_page():
    go_home()
    st.title("📚 Quiz History")

    if not st.session_state.user:
        st.warning("History देखने के लिए Login करें।")
        if st.button("Login / Sign Up", key="history_login"):
            set_page("auth")
        return

    try:
        records = fetch_history()
    except Exception as exc:
        st.error(f"History load नहीं हुई: {exc}")
        st.info("Supabase में quiz_history table और policies जाँचें।")
        return

    if not records:
        st.info("अभी कोई saved quiz history नहीं मिली।")
        return

    for record in records:
        created = record.get("created_at", "")

        try:
            created = datetime.fromisoformat(
                created.replace("Z", "+00:00")
            ).astimezone().strftime("%d %b %Y, %I:%M %p")
        except Exception:
            pass

        st.markdown(
            f'<div class="card"><b>{record.get("title", "Quiz")}</b><br>'
            f'<span class="small-muted">{record.get("mode", "")} • {created}</span><br>'
            f'Score: {record.get("correct", 0)}/{record.get("total", 0)}'
            f' • Wrong: {record.get("wrong", 0)}'
            f' • Skipped: {record.get("skipped", 0)}'
            f' • {record.get("percentage", 0)}%</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "Open saved quiz & analysis",
            key=f"history_open_{record.get('id')}",
        ):
            try:
                quiz = json.loads(record.get("quiz_json") or "[]")
                answers = json.loads(record.get("answers_json") or "{}")

                st.session_state.quiz = quiz
                st.session_state.answers = {
                    int(key): value for key, value in answers.items()
                }
                st.session_state.quiz_title = record.get("title", "Saved Quiz")
                st.session_state.quiz_mode = record.get("mode", "")
                st.session_state.quiz_language = record.get("language", "Hindi")
                st.session_state.quiz_submitted = True
                st.session_state.quiz_started = False
                st.session_state.history_id = record.get("id")
                st.session_state.review_index = 0

                set_page("results")

            except Exception as exc:
                st.error(f"Saved quiz open नहीं हुआ: {exc}")


# ---------------- ROUTER ----------------

def main():
    if config_error:
        st.warning("Configuration: " + config_error)

    page = st.session_state.page

    routes = {
        "home": home_page,
        "auth": auth_page,
        "pdf": pdf_page,
        "ai": ai_page,
        "pyq": pyq_page,
        "quick": quick_page,
        "coming_soon": coming_soon_page,
        "test": test_page,
        "results": results_page,
        "analysis": analysis_page,
        "history": history_page,
    }

    routes.get(page, home_page)()


main()
