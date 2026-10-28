
import io
import json
import os
import re
import time
import html

import streamlit as st
from pypdf import PdfReader

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


APP_NAME = "Prateek Quiz Hub"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 8% 0%,
    #35205f 0%, #17172f 48%, #0b1220 100%);
    color: #f8fafc;
}
.block-container {
    max-width: 1150px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
.brand {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 20px;
}
.brand-icon {
    background: linear-gradient(135deg,#ec4899,#7c3aed);
    border-radius: 18px;
    width: 58px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
}
.brand-title {
    font-size: 2rem;
    font-weight: 850;
    color: white;
}
.brand-sub {
    color: #c4b5fd;
}
.hero {
    padding: 25px;
    border: 1px solid #8b5cf6;
    border-radius: 24px;
    background: linear-gradient(120deg,#31205b,#18213c);
    margin: 12px 0 22px;
}
.hero h2 {
    color: white;
}
.hero p {
    color: #ddd6fe;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 20px;
    border-color: #5b4b91;
}
div.stButton > button {
    border-radius: 12px;
    border: 1px solid #a78bfa;
    background: linear-gradient(135deg,#7c3aed,#db2777);
    color: white;
    font-weight: 750;
    min-height: 44px;
}
[data-testid="stMetric"] {
    background: #1d2440;
    border: 1px solid #494078;
    padding: 13px;
    border-radius: 14px;
}
.qcard {
    padding: 18px;
    border: 1px solid #6354a5;
    border-radius: 18px;
    background: #191a35;
    margin: 10px 0;
}
.footer {
    text-align: center;
    color: #f9a8d4;
    border-top: 1px solid #453b70;
    margin-top: 28px;
    padding: 16px;
}
</style>
""", unsafe_allow_html=True)


def init_state():
    defaults = {
        "page": "home",
        "quiz": [],
        "answers": {},
        "quiz_title": "PDF Practice Quiz",
        "started": None,
        "limit": 0,
        "index": 0,
        "pdf_text": "",
        "pdf_name": "",
        "language": "हिंदी",
        "quiz_counter": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def header():
    st.markdown(
        f"""
        <div class="brand">
            <div class="brand-icon">🧠</div>
            <div>
                <div class="brand-title">{APP_NAME}</div>
                <div class="brand-sub">
                    Learn smarter · Practice better
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        '<div class="footer">♡ Made by Prateek Senmar 🩷</div>',
        unsafe_allow_html=True,
    )


def get_api_key():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def extract_pdf(uploaded_file):
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
        pages = []
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as exc:
        st.error(f"PDF पढ़ने में समस्या: {exc}")
        return ""


def parse_json(raw):
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def generate_questions(source, count, language, title):
    key = get_api_key()

    if not key:
        st.error(
            "GEMINI_API_KEY नहीं मिली। "
            "Streamlit App की Settings → Secrets में "
            "GEMINI_API_KEY जोड़ें।"
        )
        return []

    if genai is None or types is None:
        st.error(
            "google-genai library नहीं मिली। "
            "requirements.txt में google-genai जोड़ें।"
        )
        return []

    lang = {
        "हिंदी": "Hindi",
        "English": "English",
        "हिंदी + English": "Hindi and English",
    }[language]

    prompt = f"""
Create up to {count} distinct multiple-choice questions
using only the PDF text below.

Quiz title: {title}
Language: {lang}

Return ONLY valid JSON in this format:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer_index": 0,
      "explanation": "Explanation of the correct answer"
    }}
  ]
}}

Rules:
- Exactly four options per question.
- answer_index must be an integer from 0 to 3.
- There must be only one correct answer.
- Explain why the answer is correct.
- Avoid duplicate questions.
- Do not invent facts absent from the source.
- If the PDF cannot support {count} questions, return fewer
  supported questions.
- Return JSON only, without Markdown.

PDF TEXT:
{source[:60000]}
"""

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )
        parsed = parse_json(getattr(response, "text", "") or "")
    except Exception as exc:
        st.error(f"प्रश्न नहीं बन पाए। Error: {exc}")
        return []

    if not isinstance(parsed, dict):
        st.error("AI का response सही JSON format में नहीं मिला।")
        return []

    items = parsed.get("questions", [])
    if not isinstance(items, list):
        st.error("AI ने प्रश्नों की सही सूची नहीं भेजी।")
        return []

    valid = []

    for item in items:
        if not isinstance(item, dict):
            continue

        question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        explanation = str(item.get("explanation", "")).strip()

        try:
            answer_index = int(item.get("answer_index", -1))
        except (ValueError, TypeError):
            continue

        if (
            not question
            or not isinstance(options, list)
            or len(options) != 4
            or answer_index not in range(4)
            or not all(str(option).strip() for option in options)
        ):
            continue

        valid.append({
            "question": question,
            "options": [str(option).strip() for option in options],
            "answer_index": answer_index,
            "explanation": explanation or "व्याख्या उपलब्ध नहीं है।",
        })

    if not valid:
        st.error(
            "कोई valid प्रश्न नहीं बना। "
            "अगर PDF scanned है, तो OCR की ज़रूरत हो सकती है।"
        )
        return []

    if len(valid) < count:
        st.warning(
            f"{count} के बजाय {len(valid)} valid प्रश्न बने।"
        )

    # हर क्विज़ के प्रश्नों की ID अलग रखें
    st.session_state.quiz_counter += 1
    quiz_id = st.session_state.quiz_counter

    for i, question in enumerate(valid[:count]):
        question["id"] = f"quiz{quiz_id}_q{i + 1}"

    return valid[:count]


def start_quiz(questions, title, minutes):
    st.session_state.quiz = questions
    st.session_state.answers = {}
    st.session_state.quiz_title = title
    st.session_state.started = time.time()
    st.session_state.limit = int(minutes) * 60
    st.session_state.index = 0
    st.session_state.page = "quiz"


def remaining_seconds():
    limit = int(st.session_state.limit or 0)
    started = st.session_state.started

    if limit <= 0 or started is None:
        return None

    return max(0, limit - int(time.time() - started))


def calculate_results():
    correct, wrong, skipped = [], [], []

    for question in st.session_state.quiz:
        selected = st.session_state.answers.get(question["id"])

        if selected is None:
            skipped.append(question)
        elif int(selected) == question["answer_index"]:
            correct.append(question)
        else:
            wrong.append(question)

    attempted = len(correct) + len(wrong)
    accuracy = (
        len(correct) * 100 / attempted
        if attempted else 0
    )

    return {
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "attempted": attempted,
        "accuracy": accuracy,
    }


def show_home():
    header()

    st.markdown(
        """
        <div class="hero">
            <h2>आपकी तैयारी, आपका तरीका 🚀</h2>
            <p>
                अपनी PDF से क्विज़ बनाएं और अपनी तैयारी बेहतर करें।
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3, gap="medium")

    with a:
        with st.container(border=True):
            st.markdown("## 📄 PDF to Quiz")
            st.caption("PDF अपलोड करके MCQ क्विज़ बनाएं।")
            st.markdown(
                '<p style="color:#93c5fd">'
                'Upload · Generate · Practice</p>',
                unsafe_allow_html=True,
            )

            if st.button(
                "Open PDF to Quiz →",
                key="open_pdf",
                use_container_width=True,
            ):
                st.session_state.page = "pdf"
                st.rerun()

    with b:
        with st.container(border=True):
            st.markdown("## 📝 PYQ Practice")
            st.caption("पिछले वर्षों के प्रश्नों की प्रैक्टिस।")
            st.markdown(
                '<p style="color:#d8b4fe">'
                'Exam-wise question practice</p>',
                unsafe_allow_html=True,
            )
            st.button(
                "कल उपलब्ध होगा",
                key="pyq_disabled",
                disabled=True,
                use_container_width=True,
            )

    with c:
        with st.container(border=True):
            st.markdown("## 🌈 Quick Access")
            st.caption(
                "एग्ज़ाम के लोगो, चैप्टर और हर टॉपिक की 10 प्रश्नों की क्विज़।"
            )
            st.markdown(
                '<p style="color:#5eead4">'
                'Exam logos · Chapters · 10 questions</p>',
                unsafe_allow_html=True,
            )
            st.button(
                "कल उपलब्ध होगा",
                key="quick_disabled",
                disabled=True,
                use_container_width=True,
            )

    st.info(
        "अभी PDF to Quiz काम करेगा। "
        "PYQ Practice और Quick Access अगले चरण में बनाएंगे।"
    )
    footer()


def show_pdf_page():
    header()

    if st.button("← Home", key="back_home"):
        st.session_state.page = "home"
        st.rerun()

    st.title("📄 PDF to Quiz")
    st.write(
        "PDF अपलोड करें, प्रश्नों की संख्या चुनें और क्विज़ शुरू करें।"
    )

    with st.container(border=True):
        uploaded = st.file_uploader(
            "अपनी PDF फ़ाइल चुनें",
            type=["pdf"],
            key="pdf_uploader",
        )

        if uploaded is not None:
            extracted = extract_pdf(uploaded)

            if extracted:
                st.session_state.pdf_text = extracted
                st.session_state.pdf_name = uploaded.name

                st.success(f"PDF पढ़ ली गई: {uploaded.name}")
                st.caption(f"निकाला गया text: {len(extracted):,} characters")

                with st.expander("PDF का text preview देखें"):
                    st.text(extracted[:4000])
            else:
                st.session_state.pdf_text = ""
                st.warning(
                    "PDF से text नहीं निकला। "
                    "यह scanned PDF हो सकती है।"
                )

        title = st.text_input(
            "Quiz का नाम",
            value="PDF Practice Quiz",
        )

        language = st.selectbox(
            "प्रश्नों की भाषा",
            ["हिंदी", "English", "हिंदी + English"],
        )

        count = st.select_slider(
            "कितने प्रश्न चाहिए?",
            options=[5, 10, 15, 20, 25, 30, 40, 50],
            value=10,
        )

        minutes = st.selectbox(
            "टेस्ट का समय",
            [0, 10, 15, 20, 30, 45, 60, 90],
            index=3,
            format_func=lambda x: (
                "बिना समय सीमा" if x == 0 else f"{x} मिनट"
            ),
        )

        if st.button(
            "✨ Generate Quiz",
            type="primary",
            use_container_width=True,
        ):
            source = st.session_state.pdf_text

            if not source:
                st.error("पहले ऐसी PDF अपलोड करें जिसमें पढ़ने योग्य text हो।")
            else:
                with st.spinner("PDF से प्रश्न तैयार हो रहे हैं…"):
                    questions = generate_questions(
                        source,
                        int(count),
                        language,
                        title.strip() or "PDF Practice Quiz",
                    )

                if questions:
                    start_quiz(
                        questions,
                        title.strip() or "PDF Practice Quiz",
                        minutes,
                    )
                    st.rerun()

    footer()


def show_quiz():
    questions = st.session_state.quiz

    if not questions:
        st.warning("Quiz में प्रश्न नहीं हैं।")
        if st.button("Home पर जाएं"):
            st.session_state.page = "home"
            st.rerun()
        return

    seconds = remaining_seconds()

    if seconds is not None and seconds <= 0:
        st.session_state.page = "results"
        st.rerun()
        return

    header()
    st.title(st.session_state.quiz_title)

    if seconds is None:
        st.caption("⏱️ समय सीमा नहीं है")
    else:
        st.warning(
            f"⏱️ समय बचा है: {seconds // 60:02d}:{seconds % 60:02d}"
        )

    total = len(questions)
    index = max(0, min(st.session_state.index, total - 1))
    question = questions[index]

    st.progress((index + 1) / total)
    st.caption(f"प्रश्न {index + 1} / {total}")

    st.markdown(
        f'<div class="qcard"><b>'
        f'{html.escape(question["question"])}'
        f'</b></div>',
        unsafe_allow_html=True,
    )

    previous_answer = st.session_state.answers.get(question["id"])

    selected = st.radio(
        "अपना उत्तर चुनें:",
        range(4),
        format_func=lambda i: (
            f"{chr(65 + i)}. {question['options'][i]}"
        ),
        index=previous_answer if previous_answer is not None else None,
        key=f"radio_{question['id']}",
    )

    if selected is not None:
        st.session_state.answers[question["id"]] = int(selected)

    previous_col, next_col, submit_col = st.columns(3)

    with previous_col:
        if st.button(
            "⬅️ पिछला",
            disabled=index == 0,
            use_container_width=True,
        ):
            st.session_state.index = index - 1
            st.rerun()

    with next_col:
        if st.button(
            "अगला ➡️",
            disabled=index >= total - 1,
            use_container_width=True,
        ):
            st.session_state.index = index + 1
            st.rerun()

    with submit_col:
        if st.button(
            "जमा करें ✓",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.page = "results"
            st.rerun()

    st.caption(
        f"उत्तर दिए: {len(st.session_state.answers)} / {total}"
    )

    if seconds is not None:
        time.sleep(1)
        st.rerun()


def show_results():
    questions = st.session_state.quiz

    if not questions:
        st.warning("कोई रिज़ल्ट उपलब्ध नहीं है।")
        if st.button("Home"):
            st.session_state.page = "home"
            st.rerun()
        return

    header()
    result = calculate_results()

    total = len(questions)
    correct = len(result["correct"])
    wrong = len(result["wrong"])
    skipped = len(result["skipped"])
    score = correct * 100 / total if total else 0

    st.title("📊 Quiz Result")
    st.subheader(st.session_state.quiz_title)

    a, b, c, d = st.columns(4)
    a.metric("कुल प्रश्न", total)
    b.metric("सही", correct)
    c.metric("गलत", wrong)
    d.metric("छोड़े", skipped)

    st.progress(score / 100)
    st.markdown(f"### Score: {correct}/{total} · {score:.1f}%")
    st.caption(
        f"Attempted: {result['attempted']} · "
        f"Accuracy: {result['accuracy']:.1f}%"
    )

    st.divider()
    st.subheader("🧐 Answer Review")

    filter_choice = st.selectbox(
        "कौन से प्रश्न देखें?",
        ["सभी", "गलत उत्तर", "छोड़े गए", "सही उत्तर"],
    )

    groups = {
        "सभी": questions,
        "गलत उत्तर": result["wrong"],
        "छोड़े गए": result["skipped"],
        "सही उत्तर": result["correct"],
    }

    for number, question in enumerate(questions, 1):
        if question not in groups[filter_choice]:
            continue

        picked = st.session_state.answers.get(question["id"])

        with st.container(border=True):
            st.markdown(f"**Q{number}. {question['question']}**")

            for index, option in enumerate(question["options"]):
                if index == question["answer_index"]:
                    st.markdown(
                        f"✅ **{chr(65 + index)}. {option} — सही उत्तर**"
                    )
                elif picked == index:
                    st.markdown(
                        f"❌ **{chr(65 + index)}. {option} — आपका उत्तर**"
                    )
                else:
                    st.write(f"{chr(65 + index)}. {option}")

            if picked is None:
                st.caption("आपने यह प्रश्न छोड़ दिया।")

            st.info(f"व्याख्या: {question['explanation']}")

    left, right = st.columns(2)

    with left:
        if st.button("🔁 नई PDF Quiz", use_container_width=True):
            st.session_state.page = "pdf"
            st.session_state.quiz = []
            st.session_state.answers = {}
            st.session_state.pdf_text = ""
            st.rerun()

    with right:
        if st.button("🏠 Home पर जाएं", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

    footer()


page = st.session_state.page

if page == "home":
    show_home()
elif page == "pdf":
    show_pdf_page()
elif page == "quiz":
    show_quiz()
elif page == "results":
    show_results()
else:
    st.session_state.page = "home"
    st.rerun()

