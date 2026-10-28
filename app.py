
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
    background: linear-gradient(145deg, #090b18, #17102d, #090b18);
    color: #f8fafc;
}
.block-container {
    max-width: 850px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
.hero {
    background: linear-gradient(135deg, #6d28d9, #9333ea, #4f46e5);
    padding: 28px 20px;
    border-radius: 24px;
    text-align: center;
    margin-bottom: 24px;
    box-shadow: 0 10px 35px #6d28d944;
}
.hero h1 { color: white; margin-bottom: 5px; }
.hero p { color: #ede9fe; margin: 0; }
.quiz-card {
    background: #17172b;
    border: 1px solid #39315a;
    border-radius: 18px;
    padding: 20px;
    margin: 12px 0;
}
.metric-card {
    background: linear-gradient(145deg, #20183b, #15172a);
    border: 1px solid #493576;
    border-radius: 17px;
    padding: 17px 10px;
    text-align: center;
    min-height: 105px;
}
.metric-label { color: #c4b5fd; font-size: 13px; }
.metric-value { color: white; font-size: 27px; font-weight: 800; }
.metric-sub { color: #a5b4fc; font-size: 12px; }
.result-banner {
    background: linear-gradient(135deg, #312e81, #6d28d9, #7e22ce);
    border-radius: 23px;
    padding: 25px 16px;
    text-align: center;
    margin: 15px 0 22px;
}
.result-banner h1 { color: white; font-size: 34px; }
.result-banner p { color: #ede9fe; margin-bottom: 4px; }
div.stButton > button {
    border-radius: 12px;
    min-height: 44px;
    font-weight: 700;
    border: 1px solid #8b5cf6;
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #7c3aed, #6d28d9);
    color: white;
}
[data-testid="stMetric"] {
    background: #17172b;
    padding: 14px;
    border: 1px solid #39315a;
    border-radius: 15px;
}
.stProgress > div > div > div > div {
    background: #a78bfa;
}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# SESSION STATE
defaults = {
    "quiz": [],
    "answers": {},
    "started": False,
    "finished": False,
    "index": 0,
    "end_time": 0,
    "duration": 10,
    "quiz_id": 0
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
    st.session_state.quiz_id += 1


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
            "GEMINI_API_KEY nahi mili. Streamlit Secrets check karo."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
Create exactly {count} multiple-choice quiz questions.

Language: Hindi.
Difficulty: {difficulty}.
Topic: {topic or "uploaded study material"}.

Use the source material.
Every question must have four options and one correct answer.
The answer must be an integer from 0 to 3.
Give a useful explanation in Hindi.

Return only valid JSON:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "answer": 0,
      "explanation": "Explanation in Hindi"
    }}
  ]
}}

Do not use Markdown fences.

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
            "Valid questions nahi ban paye. PDF dobara check karo."
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
            <div style="color:#c4b5fd;font-size:14px">
                ⏳ TIME REMAINING
            </div>
            <div style="font-size:32px;font-weight:800;color:white">
                {mins:02d}:{secs:02d}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if remaining <= 0:
        st.session_state.finished = True


def get_results():
    questions = st.session_state.quiz
    answers = st.session_state.answers

    correct = []
    incorrect = []
    skipped = []

    for i, q in enumerate(questions):
        user_answer = answers.get(i)

        if user_answer is None:
            skipped.append(i)
        elif user_answer == q["answer"]:
            correct.append(i)
        else:
            incorrect.append(i)

    total = len(questions)
    attempted = len(correct) + len(incorrect)

    score_percent = (
        round(len(correct) / total * 100) if total else 0
    )

    accuracy = (
        round(len(correct) / attempted * 100)
        if attempted else 0
    )

    return {
        "correct": correct,
        "incorrect": incorrect,
        "skipped": skipped,
        "total": total,
        "attempted": attempted,
        "score_percent": score_percent,
        "accuracy": accuracy
    }


def show_question_review(index, status):
    q = st.session_state.quiz[index]
    user_answer = st.session_state.answers.get(index)

    if status == "correct":
        color = "#22c55e"
        label = "CORRECT"
    elif status == "incorrect":
        color = "#fb7185"
        label = "INCORRECT"
    else:
        color = "#fbbf24"
        label = "SKIPPED"

    st.markdown(
        f"""
        <div class="quiz-card">
            <div style="color:{color};font-weight:800;font-size:13px">
                {label} · QUESTION {index + 1}
            </div>
            <h4>{q["question"]}</h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    if user_answer is None:
        st.info("Is question ka answer select nahi kiya tha.")
    else:
        st.write("**Tumhara answer:** " + q["options"][user_answer])

    st.success("**Sahi answer:** " + q["options"][q["answer"]])

    if q.get("explanation"):
        st.info("**Explanation:** " + q["explanation"])

    st.divider()


# HEADER
st.markdown("""
<div class="hero">
    <h1>🧠 AI QUIZ MAKER</h1>
    <p>PRATEEK SENMAR · Learn • Practice • Improve</p>
</div>
""", unsafe_allow_html=True)


# HOME SCREEN
if not st.session_state.started and not st.session_state.finished:

    st.markdown("## 🚀 Apna quiz banao")
    st.write("PDF upload karo aur apni preparation test karo.")

    uploaded_file = st.file_uploader(
        "📚 Study material ki PDF upload karo",
        type=["pdf"],
        key=f"pdf_upload_{st.session_state.quiz_id}"
    )

    col1, col2 = st.columns(2)

    with col1:
        count = st.selectbox(
            "Questions ki sankhya",
            [5, 10, 15, 20, 25, 30],
            index=1
        )

    with col2:
        duration = st.selectbox(
            "Time limit (minutes)",
            [5, 10, 15, 20, 30, 45, 60],
            index=1
        )

    difficulty = st.selectbox(
        "Difficulty level",
        ["Easy", "Medium", "Hard"]
    )

    topic = st.text_input(
        "Topic (optional)",
        placeholder="Jaise: Biology, Polity, Physics..."
    )

    if st.button(
        "✨ GENERATE MY QUIZ",
        type="primary",
        use_container_width=True
    ):
        if uploaded_file is None:
            st.warning("Bhai, pehle PDF upload karo.")
        else:
            try:
                with st.spinner("🤖 AI tumhara quiz bana raha hai..."):
                    pdf_text = extract_pdf_text(uploaded_file)

                    if len(pdf_text) < 50:
                        raise ValueError(
                            "PDF se text nahi mil raha. Text wali PDF try karo."
                        )

                    questions = generate_questions(
                        pdf_text, count, difficulty, topic
                    )

                    st.session_state.quiz = questions
                    st.session_state.answers = {
                        i: None for i in range(len(questions))
                    }
                    st.session_state.index = 0
                    st.session_state.duration = duration
                    st.session_state.end_time = time.time() + duration * 60
                    st.session_state.started = True
                    st.session_state.finished = False

                st.rerun()

            except Exception as e:
                st.error(f"Quiz nahi ban saka: {e}")

    st.markdown("""
    <div class="quiz-card">
        <h3>💜 Your personal study partner</h3>
        <p>PDF se MCQs banao, timer ke saath practice karo
        aur end mein score aur accuracy dekho.</p>
    </div>
    """, unsafe_allow_html=True)


# ACTIVE QUIZ
elif st.session_state.started and not st.session_state.finished:

    questions = st.session_state.quiz

    if not questions:
        st.error("Quiz nahi mila. Naya quiz banao.")

        if st.button("Home par jao"):
            reset_quiz()
            st.rerun()

    else:
        st_autorefresh(
            interval=1000,
            key=f"quiz_timer_refresh_{st.session_state.quiz_id}"
        )

        idx = max(
            0,
            min(st.session_state.index, len(questions) - 1)
        )
        st.session_state.index = idx

        show_timer()

        if st.session_state.finished:
            st.rerun()

        st.progress((idx + 1) / len(questions))
        st.caption(f"QUESTION {idx + 1} OF {len(questions)}")

        q = questions[idx]

        st.markdown(
            f"""
            <div class="quiz-card">
                <h3>{q["question"]}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

        # FIXED ANSWER SELECTION
        # Radio se text milta hai, integer nahi.
        # Isliye text ko index mein convert kar rahe hain.
        options_with_placeholder = [
            "— Answer choose karo —"
        ] + [
            f"{chr(65 + i)}. {q['options'][i]}"
            for i in range(4)
        ]

        previous_answer = st.session_state.answers.get(idx)

        radio_index = (
            previous_answer + 1
            if previous_answer is not None
            else 0
        )

        choice = st.radio(
            "Apna answer chuno:",
            options_with_placeholder,
            index=radio_index,
            key=f"answer_{st.session_state.quiz_id}_{idx}",
            label_visibility="collapsed"
        )

        # IMPORTANT FIX: choice - 1 nahi karna,
        # kyunki choice ek string hai.
        if choice == options_with_placeholder[0]:
            st.session_state.answers[idx] = None
        else:
            st.session_state.answers[idx] = (
                options_with_placeholder.index(choice) - 1
            )

        st.caption(
            "Answer select nahi karoge to question Skipped count hoga."
        )

        st.divider()

        prev_col, next_col = st.columns(2)

        with prev_col:
            if st.button(
                "⬅️ Previous",
                disabled=(idx == 0),
                use_container_width=True
            ):
                st.session_state.index -= 1
                st.rerun()

        with next_col:
            if idx < len(questions) - 1:
                if st.button(
                    "Next ➡️",
                    use_container_width=True
                ):
                    st.session_state.index += 1
                    st.rerun()
            else:
                if st.button(
                    "🏁 Finish Quiz",
                    type="primary",
                    use_container_width=True
                ):
                    st.session_state.finished = True
                    st.rerun()

        st.write("")

        if st.button("Submit Quiz Now", use_container_width=True):
            st.session_state.finished = True
            st.rerun()


# RESULTS SCREEN
if st.session_state.finished and st.session_state.quiz:

    result = get_results()

    correct_count = len(result["correct"])
    incorrect_count = len(result["incorrect"])
    skipped_count = len(result["skipped"])
    total = result["total"]

    st.markdown("""
    <div class="result-banner">
        <p>🎉 QUIZ COMPLETED</p>
        <h1>Great Effort!</h1>
        <p>Har test tumhe apne goal ke aur kareeb le jata hai.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 📊 Your Performance")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">🏆 YOUR SCORE</div>
                <div class="metric-value">{correct_count}/{total}</div>
                <div class="metric-sub">
                    {result["score_percent"]}% of total marks
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">🎯 ACCURACY</div>
                <div class="metric-value">{result["accuracy"]}%</div>
                <div class="metric-sub">
                    Correct out of attempted questions
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    a, b, c = st.columns(3)

    with a:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">✅ CORRECT</div>
                <div class="metric-value">{correct_count}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with b:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">❌ INCORRECT</div>
                <div class="metric-value">{incorrect_count}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">⏭️ SKIPPED</div>
                <div class="metric-value">{skipped_count}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    st.progress(result["score_percent"] / 100)

    st.caption(
        f"Attempted: {result['attempted']} / {total} questions"
    )

    if result["score_percent"] >= 80:
        st.success("🔥 Excellent! Bahut badhiya performance, bhai!")
    elif result["score_percent"] >= 50:
        st.info(
            "💪 Good effort! Galat questions revise karke score badhao."
        )
    else:
        st.warning(
            "📚 Koi baat nahi bhai. Explanations padho aur dobara practice karo."
        )

    st.divider()
    st.markdown("## 📝 Question Review")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        "❌ Incorrect",
        "⏭️ Skipped",
        "✅ Correct"
    ])

    with tab1:
        st.markdown("### Performance Summary")
        st.write(f"✅ Correct answers: **{correct_count}**")
        st.write(f"❌ Wrong answers: **{incorrect_count}**")
        st.write(f"⏭️ Skipped questions: **{skipped_count}**")
        st.write(f"🎯 Attempted questions: **{result['attempted']}**")

        st.info(
            "Accuracy = correct answers ÷ attempted questions. "
            "Score percentage = correct answers ÷ total questions."
        )

    with tab2:
        if not result["incorrect"]:
            st.success("🎉 Koi incorrect question nahi hai!")
        else:
            st.write(f"**{incorrect_count} incorrect questions**")
            for i in result["incorrect"]:
                show_question_review(i, "incorrect")

    with tab3:
        if not result["skipped"]:
            st.success("🎉 Koi question skip nahi hua!")
        else:
            st.write(f"**{skipped_count} skipped questions**")
            for i in result["skipped"]:
                show_question_review(i, "skipped")

    with tab4:
        if not result["correct"]:
            st.info("Abhi koi correct answer nahi hai.")
        else:
            for i in result["correct"]:
                show_question_review(i, "correct")

    st.divider()

    if st.button(
        "🔄 Create New Quiz",
        type="primary",
        use_container_width=True
    ):
        reset_quiz()
        st.rerun()

    st.caption("Made with 💜 by PRATEEK SENMAR")

    
