
import os
import io
import json
import time
import random
from typing import Any, Dict, List, Optional

import streamlit as st
from pypdf import PdfReader

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Prateek Quiz Hub
APP_NAME = "Prateek Quiz Hub"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LANGUAGES = ["हिंदी", "English", "हिंदी + English"]
QUESTION_COUNTS = [
    10, 15, 20, 25, 30, 40, 50, 75,
    100, 125, 150, 175, 200, 250, 300
]

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp {
        background: radial-gradient(
            circle at 15% 0%,
            #281044 0,
            #130a22 42%,
            #0d0717 100%
        );
        color: #f5efff;
    }
    [data-testid="stHeader"] {
        background: rgba(13,7,23,0.75);
    }
    [data-testid="stSidebar"] {
        background: #170d27;
    }
    .block-container {
        max-width: 1120px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .brand-row {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 1.2rem;
    }
    .brand-icon {
        width: 56px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 17px;
        background: linear-gradient(135deg,#a855f7,#6d28d9);
        font-size: 29px;
    }
    .brand-title {
        font-size: 2rem;
        font-weight: 800;
        color: white;
        margin: 0;
    }
    .brand-sub {
        color: #c4b5fd;
        margin-top: 5px;
    }
    .hero {
        border: 1px solid #6d28d966;
        border-radius: 24px;
        padding: 28px;
        margin: 14px 0 22px 0;
        background: linear-gradient(125deg,#28133f,#1a0e2c);
    }
    .hero h1 {
        color: white;
        font-size: 2.5rem;
        margin: .45rem 0 .6rem 0;
    }
    .hero p {
        color: #ddd0f4;
        font-size: 1rem;
    }
    .made-by {
        color: #f9a8d4;
        text-align: center;
        font-weight: 650;
        margin-top: 30px;
        padding: 14px;
        border-top: 1px solid #51317e;
    }
    .question-box {
        background: #1d1030;
        border: 1px solid #6d28d9;
        border-radius: 18px;
        padding: 20px;
        margin: 12px 0;
    }
    div.stButton > button,
    div.stFormSubmitButton > button {
        border-radius: 12px;
        border: 1px solid #a855f7;
        background: linear-gradient(135deg,#7e22ce,#6d28d9);
        color: white;
        font-weight: 700;
        min-height: 44px;
    }
    [data-testid="stMetric"] {
        background: #1b102a;
        border: 1px solid #51317e;
        padding: 14px;
        border-radius: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def header() -> None:
    st.markdown(
        f"""
        <div class="brand-row">
            <div class="brand-icon">🧠</div>
            <div>
                <div class="brand-title">{APP_NAME}</div>
                <div class="brand-sub">
                    Learn smarter. Practice better.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        '<div class="made-by">♡ Made by Prateek Senmar 🩷</div>',
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "page": "home",
        "language": "हिंदी",
        "quiz": [],
        "answers": {},
        "quiz_title": "Practice Quiz",
        "quiz_source": "PDF Quiz",
        "quiz_started_at": None,
        "time_limit_seconds": 0,
        "quiz_submitted": False,
        "quiz_mode": "",
        "generation_notice": "",
        "review_filter": "All",
        "question_index": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

def text_for_language(
    hindi: str,
    english: str,
    language: Optional[str] = None,
) -> str:
    lang = language or st.session_state.get("language", "हिंदी")

    if lang == "English":
        return english

    if lang == "हिंदी + English":
        return f"{hindi}\n\n{english}"

    return hindi


def get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()

    if key:
        return key

    try:
        key = str(
            st.secrets.get("GEMINI_API_KEY", "")
        ).strip()
    except Exception:
        key = ""

    return key


def get_gemini_client():
    if genai is None:
        st.error(
            "Gemini library install nahi hai. "
            "requirements.txt check karein."
        )
        return None

    api_key = get_api_key()

    if not api_key:
        st.error(
            "Gemini API key nahi mili. "
            "Streamlit Secrets mein GEMINI_API_KEY add karein."
        )
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception as exc:
        st.error(f"Gemini client error: {exc}")
        return None


def extract_pdf_text(uploaded_file) -> str:
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        pages = []

        for page in reader.pages:
            content = page.extract_text() or ""
            if content.strip():
                pages.append(content.strip())

        return "\n\n".join(pages).strip()

    except Exception as exc:
        st.error(f"PDF read nahi ho payi: {exc}")
        return ""


def call_gemini(prompt: str) -> str:
    client = get_gemini_client()

    if client is None:
        return ""

    try:
        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
            ),
        )

        result = getattr(response, "text", None)

        if not result:
            st.error("Gemini se khaali response mila.")
            return ""

        return result.strip()

    except Exception as exc:
        st.error(
            "Question generate nahi ho paaye. "
            f"Error: {exc}"
        )
        return ""


def parse_json_response(raw: str) -> Any:
    if not raw:
        return None

    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        st.error(
            "AI response JSON format mein nahi hai. "
            "Dobara generate karke dekhein."
        )
        return None


def normalize_question(
    question: Dict[str, Any],
    index: int,
) -> Optional[Dict[str, Any]]:
    if not isinstance(question, dict):
        return None

    prompt = str(
        question.get("question", "")
    ).strip()

    raw_options = question.get("options", [])
    explanation = str(
        question.get("explanation", "")
    ).strip()

    if not prompt or not isinstance(raw_options, list):
        return None

    options = [
        str(option).strip()
        for option in raw_options
        if str(option).strip()
    ]

    if len(options) < 2:
        return None

    try:
        answer_index = int(question.get("answer_index", 0))
    except (TypeError, ValueError):
        return None

    if answer_index < 0 or answer_index >= len(options):
        return None

    return {
        "id": str(question.get("id", f"q{index + 1}")),
        "question": prompt,
        "options": options,
        "answer_index": answer_index,
        "explanation": explanation or "Explanation available nahi hai.",
    }
    
def generate_questions(
    source_text: str,
    count: int,
    language: str,
    title: str,
    generated_by_ai: bool = True,
) -> List[Dict[str, Any]]:
    if not source_text.strip():
        st.error("Pehle PDF ya question paper ka text dein.")
        return []

    language_instruction = {
        "हिंदी": "Write all questions and explanations in Hindi.",
        "English": "Write all questions and explanations in English.",
        "हिंदी + English": (
            "Write every question, option and explanation "
            "in both Hindi and English."
        ),
    }.get(language, "Write in Hindi.")

    prompt = f"""
You are an expert competitive-exam quiz creator.

Create exactly {count} multiple-choice questions using
the source text below.

Quiz title: {title}
Language: {language_instruction}

Rules:
1. Each question must have four options.
2. Exactly one option must be correct.
3. answer_index must be an integer from 0 to 3.
4. Add a clear explanation for every answer.
5. Do not invent facts that contradict the source.
6. Avoid duplicate questions.
7. If the source is insufficient, make fewer questions
   rather than inventing unsupported facts.
8. Return only valid JSON in this format:

{{
  "questions": [
    {{
      "id": "q1",
      "question": "Question text",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "answer_index": 0,
      "explanation": "Explanation"
    }}
  ]
}}

SOURCE TEXT:
{source_text[:60000]}
"""

    raw = call_gemini(prompt)
    parsed = parse_json_response(raw)

    if not isinstance(parsed, dict):
        return []

    raw_questions = parsed.get("questions", [])

    if not isinstance(raw_questions, list):
        st.error("AI response mein questions ki list nahi mili.")
        return []

    questions = []

    for index, item in enumerate(raw_questions):
        normalized = normalize_question(item, index)

        if normalized is not None:
            questions.append(normalized)

    if not questions:
        st.error("Koi valid question generate nahi hua.")
        return []

    if len(questions) < count:
        st.warning(
            f"Requested {count} questions, "
            f"lekin {len(questions)} valid questions mile."
        )

    if generated_by_ai:
        st.session_state.generation_notice = (
            "AI-generated practice questions — "
            "official PYQs hone ki guarantee nahi hai."
        )

    return questions[:count]


def start_quiz(
    questions: List[Dict[str, Any]],
    title: str,
    source: str,
    time_limit_minutes: int = 0,
) -> bool:
    if not questions:
        st.error("Quiz start karne ke liye questions nahi hain.")
        return False

    st.session_state.quiz = questions
    st.session_state.answers = {}
    st.session_state.quiz_title = title
    st.session_state.quiz_source = source
    st.session_state.quiz_started_at = time.time()
    st.session_state.time_limit_seconds = (
        max(0, int(time_limit_minutes)) * 60
    )
    st.session_state.quiz_submitted = False
    st.session_state.question_index = 0
    st.session_state.page = "quiz"

    return True


def remaining_seconds() -> Optional[int]:
    limit = int(
        st.session_state.get("time_limit_seconds", 0)
    )
    started = st.session_state.get("quiz_started_at")

    if limit <= 0 or started is None:
        return None

    elapsed = int(time.time() - started)

    return max(0, limit - elapsed)


def calculate_results() -> Dict[str, Any]:
    questions = st.session_state.quiz
    answers = st.session_state.answers

    correct = []
    wrong = []
    skipped = []

    for question in questions:
        selected = answers.get(question["id"])

        if selected is None:
            skipped.append(question)
        elif int(selected) == int(question["answer_index"]):
            correct.append(question)
        else:
            wrong.append(question)

    attempted = len(correct) + len(wrong)

    accuracy = (
        len(correct) / attempted * 100
        if attempted
        else 0.0
    )

    return {
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "attempted": attempted,
        "accuracy": accuracy,
}
    
def show_timer() -> None:
    seconds = remaining_seconds()

    if seconds is None:
        st.caption("⏱️ No time limit")
        return

    if seconds <= 0:
        st.session_state.quiz_submitted = True
        st.rerun()
        return

    st.caption(
        f"⏱️ Time remaining: "
        f"{seconds // 60:02d}:{seconds % 60:02d}"
    )


def submit_quiz() -> None:
    st.session_state.quiz_submitted = True
    st.session_state.page = "results"


def show_quiz() -> None:
    questions = st.session_state.quiz

    if not questions:
        st.warning("Quiz mein questions nahi hain.")
        if st.button("🏠 Home par jao"):
            st.session_state.page = "home"
            st.rerun()
        return

    if st.session_state.quiz_submitted:
        st.session_state.page = "results"
        st.rerun()
        return

    seconds = remaining_seconds()

    if seconds is not None and seconds <= 0:
        submit_quiz()
        st.rerun()
        return

    st.title(st.session_state.quiz_title)
    st.caption(st.session_state.quiz_source)
    show_timer()

    total = len(questions)
    index = min(
        max(0, st.session_state.question_index),
        total - 1,
    )
    question = questions[index]

    st.progress((index + 1) / total)
    st.write(f"Question {index + 1} of {total}")

    st.markdown(
        f'<div class="question-box">'
        f'<b>{question["question"]}</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

    options = question["options"]
    question_id = question["id"]
    previous_answer = st.session_state.answers.get(question_id)

    choice = st.radio(
        "Apna answer chunein:",
        options=list(range(len(options))),
        format_func=lambda value: (
            f"{chr(65 + value)}. {options[value]}"
        ),
        index=(
            int(previous_answer)
            if previous_answer is not None
            and 0 <= int(previous_answer) < len(options)
            else None
        ),
        key=f"answer_{question_id}",
    )

    if choice is not None:
        st.session_state.answers[question_id] = int(choice)

    st.write("")

    left, middle, right = st.columns(3)

    with left:
        if st.button(
            "⬅️ Previous",
            disabled=(index == 0),
            use_container_width=True,
        ):
            st.session_state.question_index = index - 1
            st.rerun()

    with middle:
        if st.button(
            "Next ➡️",
            disabled=(index == total - 1),
            use_container_width=True,
        ):
            st.session_state.question_index = index + 1
            st.rerun()

    with right:
        if st.button(
            "✅ Submit Quiz",
            use_container_width=True,
        ):
            submit_quiz()
            st.rerun()

    answered = len(st.session_state.answers)

    st.caption(
        f"Answered: {answered}/{total} · "
        f"Unanswered: {total - answered}"
    )
    
def show_results() -> None:
    questions = st.session_state.quiz

    if not questions:
        st.warning("Abhi koi quiz result available nahi hai.")
        if st.button("🏠 Home"):
            st.session_state.page = "home"
            st.rerun()
        return

    result = calculate_results()

    st.title("📊 Quiz Results")
    st.subheader(st.session_state.quiz_title)

    total = len(questions)
    correct_count = len(result["correct"])
    wrong_count = len(result["wrong"])
    skipped_count = len(result["skipped"])

    first, second, third, fourth = st.columns(4)

    first.metric("Total Questions", total)
    second.metric("Correct", correct_count)
    third.metric("Wrong", wrong_count)
    fourth.metric("Skipped", skipped_count)

    percentage = correct_count / total * 100 if total else 0

    st.progress(percentage / 100)
    st.markdown(f"### Score: {correct_count}/{total}")
    st.write(f"**Accuracy:** {result['accuracy']:.1f}%")

    if percentage >= 80:
        st.success("Excellent! Bahut achha performance! 🎉")
    elif percentage >= 50:
        st.info("Achha kiya! Practice jaari rakho. 💪")
    else:
        st.warning("Revision karo aur dobara practice karo. 📚")

    st.divider()
    st.subheader("📝 Answer Review")

    for index, question in enumerate(questions, start=1):
        selected = st.session_state.answers.get(question["id"])
        answer_index = question["answer_index"]

        if selected is None:
            status = "⏭️ Skipped"
        elif int(selected) == int(answer_index):
            status = "✅ Correct"
        else:
            status = "❌ Wrong"

        with st.expander(
            f"{index}. {question['question']} — {status}"
        ):
            options = question["options"]

            if selected is not None:
                st.write(
                    f"**Your answer:** {options[int(selected)]}"
                )
            else:
                st.write("**Your answer:** Not attempted")

            st.write(
                f"**Correct answer:** {options[answer_index]}"
            )

            st.write(
                f"**Explanation:** {question['explanation']}"
            )

    st.divider()

    left, right = st.columns(2)

    with left:
        if st.button("🔄 Retry Quiz", use_container_width=True):
            start_quiz(
                questions=questions,
                title=st.session_state.quiz_title,
                source=st.session_state.quiz_source,
                time_limit_minutes=(
                    st.session_state.time_limit_seconds // 60
                ),
            )
            st.rerun()

    with right:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    
def show_home() -> None:
    header()

    st.markdown(
        """
        <div class="hero">
            <div>🚀 YOUR PERSONAL EXAM PRACTICE SPACE</div>
            <h1>Prateek Quiz Hub</h1>
            <p>
                Upload a PDF, create practice questions,
                test your knowledge and review every answer.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    language = st.selectbox(
        "🌐 Select Language / भाषा चुनें",
        LANGUAGES,
        index=LANGUAGES.index(
            st.session_state.language
        ),
    )
    st.session_state.language = language

    mode = st.radio(
        "Choose Practice Mode",
        [
            "📄 PDF to Quiz",
            "✍️ Topic-based Practice",
        ],
        horizontal=True,
    )

    st.divider()

    with st.form("quiz_setup_form"):
        if mode == "📄 PDF to Quiz":
            uploaded_file = st.file_uploader(
                "Upload your question paper or study PDF",
                type=["pdf"],
                help="Text-based PDF files work best.",
            )
            topic_text = st.text_area(
                "Optional instructions",
                placeholder=(
                    "Example: Make SSC CGL-level questions "
                    "from Chapter 1."
                ),
                height=100,
            )
        else:
            uploaded_file = None
            topic_text = st.text_area(
                "Enter subject, topic or study material",
                placeholder=(
                    "Example: Indian Polity, Regulating Act 1773, "
                    "Class 12 Chemistry — Solutions"
                ),
                height=150,
            )

        quiz_title = st.text_input(
            "Quiz Title",
            value="My Practice Quiz",
        )

        col1, col2 = st.columns(2)

        with col1:
            question_count = st.selectbox(
                "Number of Questions",
                QUESTION_COUNTS,
                index=QUESTION_COUNTS.index(20),
            )

        with col2:
            timer_minutes = st.selectbox(
                "Timer",
                [0, 10, 15, 20, 30, 45, 60, 90, 120],
                index=0,
                format_func=lambda value: (
                    "No time limit" if value == 0
                    else f"{value} minutes"
                ),
            )

        submitted = st.form_submit_button(
            "✨ Generate My Quiz",
            use_container_width=True,
        )

    if submitted:
        source_text = ""

        if uploaded_file is not None:
            with st.spinner("PDF read ho rahi hai..."):
                source_text = extract_pdf_text(uploaded_file)

            if topic_text.strip():
                source_text += (
                    "\n\nAdditional instructions:\n"
                    + topic_text.strip()
                )

        elif topic_text.strip():
            source_text = topic_text.strip()

        if not source_text.strip():
            st.error(
                "PDF upload karo ya topic/study material likho."
            )
        elif not quiz_title.strip():
            st.error("Quiz ka title likhna zaroori hai.")
        else:
            with st.spinner(
                "🤖 AI questions bana raha hai... "
                "Please wait."
            ):
                questions = generate_questions(
                    source_text=source_text,
                    count=int(question_count),
                    language=language,
                    title=quiz_title.strip(),
                )

            if questions:
                source_name = (
                    uploaded_file.name
                    if uploaded_file is not None
                    else "AI-generated topic practice"
                )

                start_quiz(
                    questions=questions,
                    title=quiz_title.strip(),
                    source=source_name,
                    time_limit_minutes=int(timer_minutes),
                )
                st.rerun()

    st.divider()

    st.subheader("✨ Features")
    a, b, c = st.columns(3)

    with a:
        st.markdown("### 📄 PDF Quiz")
        st.caption("Study material se practice questions.")

    with b:
        st.markdown("### ⏱️ Timed Practice")
        st.caption("Timer ke saath exam-style practice.")

    with c:
        st.markdown("### 📊 Detailed Results")
        st.caption("Correct, wrong, skipped aur explanations.")

    st.info(
        "Note: AI-generated questions practice ke liye hain. "
        "Unhe official previous-year questions (PYQs) "
        "na samjhein jab tak original paper se verify na hon."
    )

    footer()


def main() -> None:
    page = st.session_state.get("page", "home")

    if page == "quiz":
        header()
        show_quiz()
        footer()

    elif page == "results":
        header()
        show_results()
        footer()

    else:
        show_home()


if __name__ == "__main__":
    main()
    
