
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from pypdf import PdfReader
from google import genai
from google.genai import types
import json
import re
import time

st.set_page_config(
    page_title="AI Quiz Maker | Prateek Senmar",
    page_icon="🧠",
    layout="centered"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(145deg,#0b1020,#21143d,#10172d);
    color: #f7f5ff;
}
.block-container {
    max-width: 900px;
    padding-top: 2rem;
}
.hero {
    text-align: center;
    padding: 28px 16px;
    border: 1px solid #6047a8;
    border-radius: 24px;
    background: linear-gradient(135deg,#251749,#171d38);
    box-shadow: 0 10px 35px #0005;
}
.hero h1 {
    font-size: 42px;
    color: #ffffff;
}
.hero p {
    color: #c9baff;
}
.stButton > button {
    width: 100%;
    border-radius: 12px;
    min-height: 48px;
    font-weight: bold;
    background: linear-gradient(90deg,#8b5cf6,#6366f1);
    color: white;
    border: 0;
}
div[data-testid="stFileUploader"] {
    border: 1px dashed #8b5cf6;
    border-radius: 14px;
    padding: 12px;
}
.quiz-card {
    padding: 20px;
    border: 1px solid #57417f;
    border-radius: 18px;
    background: #17172d;
    margin: 10px 0;
}
.small-note {
    text-align: center;
    color: #b9b4d0;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# SESSION STATE
defaults = {
    "quiz": [],
    "answers": {},
    "started": False,
    "finished": False,
    "index": 0,
    "end_time": 0
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_quiz():
    st.session_state.quiz = []
    st.session_state.answers = {}
    st.session_state.started = False
    st.session_state.finished = False
    st.session_state.index = 0
    st.session_state.end_time = 0


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages).strip()


def generate_questions(text, count, difficulty, topic):
    api_key = st.secrets.get("GEMINI_API_KEY", "")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY nahi mili. "
            "Streamlit Settings > Secrets check karo."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
Create exactly {count} multiple-choice quiz questions.
Language: Hindi.
Difficulty: {difficulty}
Topic: {topic or "uploaded study material"}.

Use the source material below.
Each question must have exactly four options
and one correct answer.

Return ONLY valid JSON in this format:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": 0,
      "explanation": "Short explanation"
    }}
  ]
}}

The answer must be an integer from 0 to 3.
Do not include markdown fences.

SOURCE MATERIAL:
{text[:45000]}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json"
        )
    )

    raw = (response.text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    questions = data.get("questions", [])
    valid = []

    for q in questions:
        options = q.get("options", [])
        answer = q.get("answer")

        if (
            isinstance(q.get("question"), str)
            and isinstance(options, list)
            and len(options) == 4
            and all(isinstance(opt, str) for opt in options)
            and isinstance(answer, int)
            and not isinstance(answer, bool)
            and 0 <= answer < 4
        ):
            valid.append({
                "question": q["question"],
                "options": options,
                "answer": answer,
                "explanation": q.get("explanation", "")
            })

    if not valid:
        raise ValueError(
            "AI ne valid questions nahi banaye. Dobara try karo."
        )

    return valid[:count]


def show_timer():
    remaining = max(
        0,
        int(st.session_state.end_time - time.time())
    )

    mins, secs = divmod(remaining, 60)

    st.markdown(
        f"""
        <div class="quiz-card" style="text-align:center">
        ⏳ <b>Time Remaining</b><br>
        <span style="font-size:30px;color:#c4b5fd">
        {mins:02d}:{secs:02d}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if remaining <= 0:
        st.session_state.finished = True


# HEADER
st.markdown("""
<div class="hero">
  <div style="font-size:48px">🧠</div>
  <h1>AI Quiz Maker</h1>
  <p>Learn smarter. Practice better. Achieve more.</p>
  <div style="color:#fff;font-weight:700">
    ✨ PRATEEK SENMAR ✨
  </div>
</div>
""", unsafe_allow_html=True)

st.write("")


# HOME SCREEN
if not st.session_state.started and not st.session_state.finished:

    st.markdown("### 🚀 Apna Quiz Banao")
    st.write(
        "PDF upload karo aur apne notes se MCQ quiz taiyar karo."
    )

    uploaded = st.file_uploader(
        "📚 Study material ki PDF upload karo",
        type=["pdf"],
        key="pdf_upload"
    )

    col1, col2 = st.columns(2)

    with col1:
        count = st.selectbox(
            "📝 Kitne questions?",
            [5, 10, 15, 20],
            index=1
        )

    with col2:
        duration = st.selectbox(
            "⏱️ Timer (minutes)",
            [5, 10, 15, 20, 30],
            index=1
        )

    difficulty = st.selectbox(
        "🎯 Difficulty",
        ["Easy", "Medium", "Hard"]
    )

    topic = st.text_input(
        "📖 Topic (optional)",
        placeholder="Jaise: Biology - Cell"
    )

    if st.button("✨ CREATE QUIZ", use_container_width=True):

        if not uploaded:
            st.warning("Bhai, pehle PDF upload karo.")

        else:
            try:
                with st.spinner(
                    "🤖 AI tumhara quiz bana raha hai..."
                ):
                    pdf_text = extract_pdf_text(uploaded)

                    if len(pdf_text) < 50:
                        st.error(
                            "PDF se text nahi mila. "
                            "Shayad PDF scanned image hai."
                        )

                    else:
                        questions = generate_questions(
                            pdf_text,
                            count,
                            difficulty,
                            topic
                        )

                        # Save quiz before changing screen
                        st.session_state.quiz = questions
                        st.session_state.answers = {}
                        st.session_state.index = 0
                        st.session_state.finished = False
                        st.session_state.end_time = (
                            time.time() + duration * 60
                        )
                        st.session_state.started = True

                        st.rerun()

            except Exception as e:
                st.error(f"Quiz nahi ban saka: {e}")

    st.markdown(
        '<p class="small-note">Made with ❤️ by Prateek Senmar</p>',
        unsafe_allow_html=True
    )


# ACTIVE QUIZ
elif st.session_state.started and not st.session_state.finished:

    questions = st.session_state.quiz

    if not questions:
        st.error("Quiz questions nahi mile. Naya quiz banao.")
        if st.button("🔄 Back to Home"):
            reset_quiz()
            st.rerun()

    else:
        # Refresh the timer using Streamlit, not browser reload.
        st_autorefresh(
            interval=1000,
            key="quiz_timer_refresh"
        )

        idx = st.session_state.index
        idx = max(0, min(idx, len(questions) - 1))
        st.session_state.index = idx

        show_timer()

        if st.session_state.finished:
            st.rerun()

        st.progress((idx + 1) / len(questions))
        st.caption(f"QUESTION {idx + 1} OF {len(questions)}")

        q = questions[idx]

        st.markdown(
            f'<div class="quiz-card"><h3>{q["question"]}</h3></div>',
            unsafe_allow_html=True
        )

        previous_answer = st.session_state.answers.get(idx)

        selected = st.radio(
            "Apna answer chuno:",
            range(4),
            format_func=lambda i: (
                f"{chr(65+i)}. {q['options'][i]}"
            ),
            index=previous_answer,
            key=f"answer_{idx}",
            label_visibility="collapsed"
        )

        st.session_state.answers[idx] = selected

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "⬅️ Previous",
                disabled=(idx == 0)
            ):
                st.session_state.index -= 1
                st.rerun()

        with col2:
            if idx < len(questions) - 1:
                if st.button("Next ➡️"):
                    st.session_state.index += 1
                    st.rerun()
            else:
                if st.button("🏁 Submit Quiz"):
                    st.session_state.finished = True
                    st.rerun()

        if st.button("🛑 Finish Quiz Now"):
            st.session_state.finished = True
            st.rerun()


# RESULTS SCREEN
if st.session_state.finished and st.session_state.quiz:

    questions = st.session_state.quiz
    answers = st.session_state.answers

    score = sum(
        1
        for i, q in enumerate(questions)
        if answers.get(i) == q["answer"]
    )

    total = len(questions)
    percentage = round(score / total * 100) if total else 0

    st.balloons()
    st.markdown("## 🏆 Quiz Result")
    st.metric("Your Score", f"{score} / {total}")
    st.progress(percentage / 100)
    st.write(f"**Accuracy:** {percentage}%")

    if percentage >= 80:
        st.success(
            "Shabash bhai! Bahut badhiya performance 🔥"
        )
    elif percentage >= 50:
        st.info(
            "Achha effort! Thodi aur practice karo 💪"
        )
    else:
        st.warning(
            "Koi baat nahi bhai, explanations revise karke phir try karo."
        )

    st.markdown("### 📋 Answers & Explanations")

    for i, q in enumerate(questions):
        user_answer = answers.get(i)
        correct_answer = q["answer"]
        is_correct = user_answer == correct_answer

        with st.expander(
            f"{'✅' if is_correct else '❌'} Q{i+1}. {q['question']}"
        ):
            if user_answer is None:
                st.write("Tumne answer nahi diya.")
            else:
                st.write(
                    f"Your answer: {q['options'][user_answer]}"
                )

            st.write(
                f"Correct answer: {q['options'][correct_answer]}"
            )
            st.write(
                f"Explanation: {q['explanation']}"
            )

    if st.button("🔄 Create New Quiz"):
        reset_quiz()
        st.rerun()


st.markdown("---")
st.markdown(
    '<p class="small-note">AI Quiz Maker • Designed by Prateek Senmar</p>',
    unsafe_allow_html=True
    )
            
