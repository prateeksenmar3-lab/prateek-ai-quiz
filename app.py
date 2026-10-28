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

# -----------------------------------------------------------------------------
# Prateek Quiz Hub — single-file Streamlit app
# Dependencies: streamlit, google-genai, pypdf
# Configure GEMINI_API_KEY in Streamlit Secrets or an environment variable.
# Optional: GEMINI_MODEL = "gemini-2.5-flash"
# -----------------------------------------------------------------------------

APP_NAME = "Prateek Quiz Hub"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LANGUAGES = ["हिंदी", "English", "हिंदी + English"]
QUESTION_COUNTS = [10, 15, 20, 25, 30, 40, 50, 75, 100, 125, 150, 175, 200, 250, 300]

st.set_page_config(page_title=APP_NAME, page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

# ------------------------------ Styling --------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root { color-scheme: dark; }
    html, body, [class*="css"] { font-family: Inter, sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 0%, #281044 0, #130a22 42%, #0d0717 100%); color: #f5efff; }
    [data-testid="stHeader"] { background: rgba(13,7,23,0.75); }
    [data-testid="stSidebar"] { background: #170d27; }
    .block-container { max-width: 1120px; padding-top: 1.5rem; padding-bottom: 2rem; }
    .brand-row { display:flex; align-items:center; gap:14px; margin: 0 0 1.2rem 0; }
    .brand-icon { width:56px; height:56px; display:flex; align-items:center; justify-content:center; border-radius:17px; background:linear-gradient(135deg,#a855f7,#6d28d9); box-shadow:0 0 28px #7e22ce55; font-size:29px; }
    .brand-title { font-size: clamp(1.55rem, 4vw, 2.1rem); line-height:1.1; font-weight:800; color:#fff; margin:0; }
    .brand-sub { color:#c4b5fd; margin-top:5px; font-size:.91rem; }
    .hero { border:1px solid #6d28d966; border-radius:24px; padding:28px; margin: 14px 0 22px 0; background:linear-gradient(125deg,#28133f,#1a0e2c 72%); box-shadow:0 15px 45px #00000025; }
    .eyebrow { text-transform:uppercase; letter-spacing:.13em; color:#c084fc; font-size:.76rem; font-weight:700; }
    .hero h1 { color:#fff; font-size:clamp(1.8rem,5vw,2.7rem); margin:.45rem 0 .6rem 0; line-height:1.12; }
    .hero p { color:#ddd0f4; font-size:1rem; margin:0; max-width:760px; }
    .section-label { font-size:1.25rem; font-weight:750; color:#fff; margin:1rem 0 .7rem; }
    .feature-card { background:linear-gradient(140deg,#241238,#1a0e2c); border:1px solid #9333ea; border-radius:20px; padding:22px; min-height:180px; box-shadow:0 0 24px #7e22ce14; }
    .feature-icon { width:50px; height:50px; border-radius:15px; display:flex; align-items:center; justify-content:center; background:#492078; font-size:25px; margin-bottom:13px; }
    .feature-card h3 { margin:0 0 8px 0; color:#fff; font-size:1.12rem; }
    .feature-card p { color:#d1c4e9; margin:0; font-size:.9rem; line-height:1.55; }
    .made-by { color:#f9a8d4; text-align:center; font-weight:650; margin-top:30px; padding:14px; border-top:1px solid #51317e; }
    .soft-panel { border:1px solid #51317e; border-radius:16px; padding:16px; background:#1b102a; }
    .question-box { background:#1d1030; border:1px solid #6d28d9; border-radius:18px; padding:20px; margin:12px 0; }
    .small-muted { color:#c4b5fd; font-size:.88rem; }
    div.stButton > button, div.stFormSubmitButton > button { border-radius:12px; border:1px solid #a855f7; background:linear-gradient(135deg,#7e22ce,#6d28d9); color:white; font-weight:700; min-height:44px; }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover { border-color:#d8b4fe; background:linear-gradient(135deg,#9333ea,#7e22ce); color:white; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea { background:#1b102a !important; }
    [data-testid="stMetric"] { background:#1b102a; border:1px solid #51317e; padding:14px; border-radius:14px; }
    div[data-testid="stExpander"] { border:1px solid #51317e; border-radius:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def header() -> None:
    st.markdown(
        f"""
        <div class="brand-row">
          <div class="brand-icon">🧠</div>
          <div><div class="brand-title">{APP_NAME}</div><div class="brand-sub">Learn smarter. Practice better.</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown('<div class="made-by">♡ Made by Prateek Senmar 🩷</div>', unsafe_allow_html=True)


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


def get_api_key() -> Optional[str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    try:
        key = key or str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        pass
    return key or None


def make_client():
    if genai is None:
        raise RuntimeError("google-genai package missing. Install it with: pip install google-genai")
    key = get_api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY नहीं मिली। Streamlit Secrets या environment variable में API key सेट करें।")
    return genai.Client(api_key=key)


def extract_pdf_text(uploaded_file) -> str:
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i + 1}]\n{text}")
        full_text = "\n\n".join(pages).strip()
        if not full_text:
            raise ValueError("PDF से text नहीं निकला। अगर PDF scanned/image वाली है, तो text-selectable PDF या OCR से निकला text इस्तेमाल करें।")
        return full_text
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"PDF पढ़ने में समस्या हुई: {exc}") from exc


def language_instruction(language: str) -> str:
    if language == "English":
        return "Write every question, option, explanation and title in clear English."
    if language == "हिंदी + English":
        return "Write every question, option and explanation bilingually: Hindi first, followed by a concise English version. Keep technical terms clear."
    return "Write every question, option and explanation in clear Hindi (Devanagari). Keep standard scientific/technical terms where useful, with Hindi explanation."


def call_gemini_json(prompt: str, max_retries: int = 4) -> Dict[str, Any]:
    client = make_client()
    model = DEFAULT_MODEL
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.25,
                ),
            )
            raw = (response.text or "").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
            return json.loads(raw)
        except Exception as exc:
            last_error = exc
            msg = str(exc).lower()
            retryable = any(term in msg for term in ["503", "unavailable", "429", "resource_exhausted", "temporarily", "timeout", "500", "internal"])
            if attempt < max_retries - 1 and retryable:
                time.sleep(min(2 ** attempt, 8) + random.random())
                continue
            break
    raise RuntimeError(
        f"Gemini से response नहीं मिला। Model: {model}. Error: {last_error}. "
        "थोड़ी देर बाद फिर कोशिश करें; API key, quota और model availability भी जाँचें।"
    )


def normalize_question(q: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
    question = str(q.get("question", "")).strip()
    options = q.get("options", [])
    explanation = str(q.get("explanation", q.get("solution", ""))).strip()
    answer = q.get("answer_index", q.get("correct_index", q.get("answer", 0)))
    if not question or not isinstance(options, list) or len(options) < 2:
        return None
    options = [str(x).strip() for x in options[:4]]
    if len(options) < 2:
        return None
    try:
        if isinstance(answer, str):
            answer = answer.strip().upper()
            if answer in ["A", "B", "C", "D"]:
                answer = ord(answer) - ord("A")
            else:
                answer = int(answer)
        answer = int(answer)
    except Exception:
        answer = 0
    answer = max(0, min(answer, len(options) - 1))
    if not explanation:
        explanation = "इस प्रश्न की व्याख्या उपलब्ध नहीं है। स्रोत सामग्री से उत्तर को दोबारा जाँचें।"
    return {"id": f"q{index + 1}", "question": question, "options": options, "answer_index": answer, "explanation": explanation}


def generate_quiz_from_pdf(pdf_text: str, count: int, language: str, difficulty: str, batch_size: int = 10) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    batches = (count + batch_size - 1) // batch_size
    progress = st.progress(0, text="Quiz तैयार हो रही है…")
    for batch_no in range(batches):
        wanted = min(batch_size, count - len(result))
        prompt = f"""
You are an accurate exam-question writer. Use ONLY the source text below for factual content. Create exactly {wanted} distinct multiple-choice questions.
Language instruction: {language_instruction(language)}
Difficulty: {difficulty}.
Return valid JSON only with this exact structure:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer_index":0,"explanation":"Explain the correct answer step by step, including the underlying concept and why it is correct."}}]}}
Rules:
- Every question must have exactly four plausible options and one unambiguously correct answer.
- answer_index is zero-based (0 to 3).
- Explanations should be detailed and educational, not just repeat the answer.
- Do not repeat earlier questions in this batch; focus on different facts/concepts.
- If the source is too short for the requested amount, make as many distinct valid questions as possible; never invent unsupported facts.
- This is batch {batch_no + 1} of {batches}. Avoid repeating these earlier question stems: {json.dumps([x['question'] for x in result[-30:]], ensure_ascii=False)}
SOURCE TEXT:
{pdf_text[:65000]}
"""
        data = call_gemini_json(prompt)
        qs = data.get("questions", []) if isinstance(data, dict) else []
        for q in qs:
            item = normalize_question(q, len(result)) if isinstance(q, dict) else None
            if item:
                result.append(item)
                if len(result) >= count:
                    break
        progress.progress(min((batch_no + 1) / batches, 1.0), text=f"Questions तैयार: {min(len(result), count)} / {count}")
        if not qs:
            break
    progress.empty()
    if not result:
        raise RuntimeError("AI कोई usable प्रश्न नहीं बना पाई। PDF में selectable text है या नहीं, जाँचें।")
    return result[:count]


def generate_pyq_style(count: int, language: str, exam: str, subject: str, difficulty: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    batches = (count + 9) // 10
    progress = st.progress(0, text="Practice questions तैयार हो रहे हैं…")
    for batch_no in range(batches):
        wanted = min(10, count - len(result))
        prompt = f"""
Create exactly {wanted} original exam-style MCQs for practice.
Exam type: {exam}. Subject: {subject}. Difficulty: {difficulty}.
Language: {language_instruction(language)}
IMPORTANT: These are AI-generated PYQ-STYLE practice questions, NOT verified actual previous-year questions. Do not attach fake years, exam dates, or claim they appeared in a real exam.
Return valid JSON only: {{"questions":[{{"question":"...","options":["A text","B text","C text","D text"],"answer_index":0,"explanation":"Detailed correct solution and concept explanation."}}]}}
Rules: exactly four plausible options, one correct answer, zero-based answer_index, detailed explanation, distinct questions.
Avoid repeating these earlier questions: {json.dumps([x['question'] for x in result[-30:]], ensure_ascii=False)}
"""
        data = call_gemini_json(prompt)
        qs = data.get("questions", []) if isinstance(data, dict) else []
        for q in qs:
            item = normalize_question(q, len(result)) if isinstance(q, dict) else None
            if item:
                result.append(item)
                if len(result) >= count:
                    break
        progress.progress(min((batch_no + 1) / batches, 1.0), text=f"Questions तैयार: {min(len(result), count)} / {count}")
        if not qs:
            break
    progress.empty()
    if not result:
        raise RuntimeError("Practice questions नहीं बन पाए। फिर कोशिश करें।")
    return result[:count]


def parse_uploaded_pyq(paper_text: str, key_text: str, language: str, count: int) -> List[Dict[str, Any]]:
    prompt = f"""
Extract multiple-choice questions from the supplied previous-year question paper. Preserve the original wording and all options as closely as possible. Extract up to {count} questions.
Display language: {language_instruction(language)}. If the source is in a different language, translate faithfully while preserving its meaning; do not change numeric values, dates, or named entities.
Answer key source is supplied separately below. If an official answer key gives an answer, use it. If no official key answer is present for a question, solve it yourself and set "answer_basis":"AI-solved; not official". Do not pretend an AI answer is official.
Return valid JSON only:
{{"questions":[{{"question":"...","options":["...","...","...","..."],"answer_index":0,"explanation":"Detailed explanation of the correct answer and concept.","answer_basis":"Official key"}}]}}
Rules: exactly four options for each included MCQ. Skip questions whose options/answer cannot be identified reliably. answer_index is zero-based. Keep explanations educational and detailed. Do not invent missing paper text.
PAPER TEXT:
{paper_text[:65000]}
ANSWER KEY TEXT:
{key_text[:25000] if key_text.strip() else "No answer key uploaded. Solve questions using your knowledge and clearly mark answers as AI-solved, not official."}
"""
    data = call_gemini_json(prompt)
    qs = data.get("questions", []) if isinstance(data, dict) else []
    result = []
    for q in qs:
        item = normalize_question(q, len(result)) if isinstance(q, dict) else None
        if item:
            item["answer_basis"] = str(q.get("answer_basis", "AI-solved; not official"))
            result.append(item)
        if len(result) >= count:
            break
    if not result:
        raise RuntimeError("पेपर से MCQ नहीं निकले। हो सकता है PDF scanned हो या उसमें selectable text न हो।")
    return result


def translate_quiz_questions(questions: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
    """Translate displayed text while preserving answer indexes and question IDs."""
    translated = [dict(q) for q in questions]
    batch_size = 10
    progress = st.progress(0, text="Questions की language बदली जा रही है…")
    for start in range(0, len(questions), batch_size):
        batch = questions[start:start + batch_size]
        payload = [{"id": q["id"], "question": q["question"], "options": q["options"], "explanation": q["explanation"]} for q in batch]
        prompt = f"""
Translate the following quiz content into the requested display language: {language}.
Language instruction: {language_instruction(language)}
Return valid JSON only in this format: {{"questions":[{{"id":"same id","question":"translated question","options":["translated option 1","translated option 2"],"explanation":"translated explanation"}}]}}
Rules: preserve each question's meaning, all facts, numbers, formulas, names and technical terms. Keep the exact same id and option order. Do NOT add, remove or reorder options. Do not include answers or change which option is correct. For Hindi + English, show Hindi first and then English for each field. Translate only; do not solve or rewrite.
INPUT: {json.dumps(payload, ensure_ascii=False)}
"""
        data = call_gemini_json(prompt)
        by_id = {str(q.get("id")): q for q in data.get("questions", []) if isinstance(q, dict)}
        for offset, original in enumerate(batch):
            item = by_id.get(original["id"])
            if not item:
                continue
            target = translated[start + offset]
            if str(item.get("question", "")).strip():
                target["question"] = str(item["question"]).strip()
            options = item.get("options")
            if isinstance(options, list) and len(options) == len(original["options"]):
                target["options"] = [str(x) for x in options]
            if str(item.get("explanation", "")).strip():
                target["explanation"] = str(item["explanation"]).strip()
        progress.progress(min((start + len(batch)) / max(len(questions), 1), 1.0), text=f"Translated {min(start + len(batch), len(questions))} / {len(questions)}")
    progress.empty()
    return translated


def start_quiz(questions: List[Dict[str, Any]], title: str, source: str, minutes: int, mode: str) -> None:
    st.session_state.quiz = questions
    st.session_state.answers = {}
    st.session_state.question_index = 0
    st.session_state.quiz_title = title
    st.session_state.quiz_source = source
    st.session_state.quiz_started_at = time.time()
    st.session_state.time_limit_seconds = max(0, int(minutes * 60))
    st.session_state.quiz_submitted = False
    st.session_state.quiz_mode = mode
    st.session_state.page = "quiz"
    st.rerun()


def remaining_seconds() -> Optional[int]:
    limit = int(st.session_state.get("time_limit_seconds", 0))
    started = st.session_state.get("quiz_started_at")
    if limit <= 0 or not started:
        return None
    return max(0, limit - int(time.time() - started))


def format_time(seconds: Optional[int]) -> str:
    if seconds is None:
        return "No time limit"
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def calculate_results() -> Dict[str, Any]:
    qs = st.session_state.quiz
    answers = st.session_state.answers
    correct, wrong, skipped = [], [], []
    for q in qs:
        selected = answers.get(q["id"])
        if selected is None:
            skipped.append(q)
        elif int(selected) == int(q["answer_index"]):
            correct.append(q)
        else:
            wrong.append(q)
    attempted = len(correct) + len(wrong)
    accuracy = (len(correct) / attempted * 100) if attempted else 0.0
    return {"correct": correct, "wrong": wrong, "skipped": skipped, "attempted": attempted, "accuracy": accuracy}


def show_timer() -> None:
    # Streamlit fragment updates the countdown without needing the learner to click.
    @st.fragment(run_every="1s")
    def _timer_fragment():
        if st.session_state.get("quiz_submitted"):
            return
        seconds = remaining_seconds()
        if seconds is None:
            st.caption("⏱️ No time limit")
        else:
            if 
