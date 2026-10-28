
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from pypdf import PdfReader
from google import genai
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
    background: linear-gradient(135deg, #101827, #172033);
    color: #ffffff;
}
h1, h2, h3 {
    color: #f5f7ff !important;
}
.stButton > button {
    border-radius: 10px;
    font-weight: 600;
}
div[data-testid="stMetric"] {
    background: #202b40;
    padding: 12px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("🧠 AI Quiz Maker")
st.caption("Made for learners | PDF Quiz • Real PYQ • AI Practice")

# --------------------------------------------------
# API CONFIGURATION
# --------------------------------------------------

def get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return ""

api_key = get_api_key()

if not api_key:
    st.error(
        "GEMINI_API_KEY नहीं मिली। "
        "Streamlit App Settings → Secrets में अपनी API key सेट करो।"
    )
    st.code('GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"')
    st.stop()

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.5-flash"

# --------------------------------------------------
# PDF HELPERS
# --------------------------------------------------

def extract_pdf(uploaded_file):
    if uploaded_file is None:
        return ""

    reader = PdfReader(uploaded_file)
    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages).strip()


def clean_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_ai(prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    if not response.text:
        raise ValueError("AI से कोई उत्तर नहीं मिला।")

    return clean_json(response.text)


def parse_questions(raw):
    data = json.loads(raw)

    if isinstance(data, dict):
        questions = data.get("questions", [])
    else:
        questions = data

    cleaned = []

    for item in questions:
        question = str(item.get("question", "")).strip()
        options = item.get("options", [])
        answer = str(item.get("answer", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        if not question or not isinstance(options, list):
            continue

        options = [str(option).strip() for option in options]

        if len(options) != 4:
            continue

        if answer not in ["A", "B", "C", "D"]:
            continue

        cleaned.append({
            "question": question,
            "options": options,
            "answer": answer,
            "explanation": explanation
        })

    if not cleaned:
        raise ValueError(
            "वैध प्रश्न नहीं मिले। PDF का टेक्स्ट जाँचो या दोबारा प्रयास करो।"
        )

    return cleaned


# --------------------------------------------------
# QUESTION GENERATION
# --------------------------------------------------

def generate_questions(
    mode,
    count,
    difficulty,
    exam,
    source_text="",
    topic=""
):
    if mode == "PDF Quiz":
        instruction = f"""
दिए गए अध्ययन PDF के आधार पर {count} MCQ बनाओ।
केवल PDF में उपलब्ध जानकारी का उपयोग करो।
कठिनाई: {difficulty}
PDF से बाहर की जानकारी मत जोड़ो।
"""

    elif mode == "Asli PYQ":
        instruction = f"""
यह वास्तविक प्रश्नपत्र से निकाला गया टेक्स्ट है।
इसी में मौजूद प्रश्नों को MCQ में व्यवस्थित करो।
नए प्रश्न मत बनाओ और प्रश्न का अर्थ मत बदलो।
अधिकतम {count} प्रश्न लौटाओ।
यदि किसी प्रश्न के चार विकल्प स्पष्ट नहीं हैं तो उसे छोड़ दो।
उत्तर केवल तभी भरोसे के साथ दो जब प्रश्नपत्र या उपलब्ध स्रोत
से उत्तर समर्थित हो। अनुमान लगाकर आधिकारिक उत्तर मत बताओ।
"""

    else:
        instruction = f"""
परीक्षा: {exam}
विषय/टॉपिक: {topic or "सामान्य अभ्यास"}
कठिनाई: {difficulty}
{count} MCQ बनाओ जो इस परीक्षा के PYQ-पैटर्न जैसे हों।
ये नए AI-generated अभ्यास प्रश्न हैं, वास्तविक PYQ होने का दावा मत करो।
"""

    prompt = f"""
तुम एक सावधान परीक्षा-प्रश्न विशेषज्ञ हो।

{instruction}

नीचे दिया गया स्रोत:
{source_text[:45000] if source_text else "कोई स्रोत PDF नहीं दिया गया।"}

आउटपुट केवल वैध JSON में दो। Markdown या अतिरिक्त टेक्स्ट नहीं।

JSON का प्रारूप:
{{
  "questions": [
    {{
      "question": "प्रश्न",
      "options": [
        "विकल्प 1",
        "विकल्प 2",
        "विकल्प 3",
        "विकल्प 4"
      ],
      "answer": "A",
      "explanation": "उत्तर का संक्षिप्त कारण"
    }}
  ]
}}

नियम:
- answer केवल A, B, C या D हो।
- options में ठीक चार विकल्प हों।
- उत्तर की व्याख्या संक्षिप्त और उपयोगी हो।
- प्रश्नों को दोहराना नहीं।
- उत्तर के बारे में निश्चित न होने पर उस प्रश्न को छोड़ देना।
"""

    raw = call_ai(prompt)
    return parse_questions(raw)


def solve_with_answer_key(questions, answer_key_text):
    if not answer_key_text.strip():
        return questions

    prompt = f"""
तुम्हें MCQ प्रश्न और एक उपलब्ध Answer Key दी गई है।
Answer Key के आधार पर प्रश्नों के सही विकल्प पहचानो।

QUESTIONS:
{json.dumps(questions, ensure_ascii=False)}

ANSWER KEY TEXT:
{answer_key_text[:30000]}

केवल JSON लौटाओ। प्रश्नों और विकल्पों को ज्यों का त्यों रखो।
किसी प्रश्न का उत्तर Answer Key में स्पष्ट रूप से न मिले तो
उसका answer खाली string रखो। अनुमान मत लगाओ।

Format:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "answer": "A",
      "explanation": "..."
    }}
  ]
}}
"""

    raw = call_ai(prompt)
    data = json.loads(raw)
    keyed = data.get("questions", [])

    result = []

    for i, original in enumerate(questions):
        item = dict(original)

        if i < len(keyed):
            answer = str(keyed[i].get("answer", "")).strip().upper()

            if answer in ["A", "B", "C", "D"]:
                item["answer"] = answer
                item["official_key_matched"] = True
            else:
                item["answer"] = ""
                item["official_key_matched"] = False

        result.append(item)

    return result


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

defaults = {
    "quiz": [],
    "answers": {},
    "submitted": False,
    "start_time": None,
    "duration": 1800,
    "quiz_mode": "",
    "quiz_title": "",
    "answer_source": "",
    "quiz_id": 0
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# --------------------------------------------------
# QUIZ SETUP
# --------------------------------------------------

st.sidebar.header("⚙️ Quiz Settings")

mode = st.sidebar.radio(
    "Quiz Mode चुनें",
    [
        "PDF Quiz",
        "Asli PYQ",
        "AI PYQ-style Practice"
    ]
)

exam = st.sidebar.selectbox(
    "Exam",
    [
        "SSC CGL",
        "SSC CHSL",
        "NEET",
        "UP Board Class 10",
        "UP Board Class 12",
        "Railway",
        "UPSC",
        "Other"
    ]
)

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Medium", "Hard"]
)

count = st.sidebar.slider(
    "कितने प्रश्न?",
    min_value=5,
    max_value=50,
    value=10,
    step=5
)

minutes = st.sidebar.selectbox(
    "समय (मिनट)",
    [10, 15, 20, 30, 45, 60],
    index=2
)

source_pdf = None
key_pdf = None
topic = ""

if mode in ["PDF Quiz", "Asli PYQ"]:
    label = (
        "Study PDF अपलोड करो"
        if mode == "PDF Quiz"
        else "Original PYQ Question Paper PDF अपलोड करो"
    )

    source_pdf = st.file_uploader(
        label,
        type=["pdf"],
        key="source_pdf"
    )

    if mode == "Asli PYQ":
        key_pdf = st.file_uploader(
            "Official Answer Key PDF (वैकल्पिक)",
            type=["pdf"],
            key="answer_key_pdf"
        )

else:
    topic = st.text_input(
        "Topic / Chapter",
        placeholder="जैसे: Percentage, भारतीय संविधान, Genetics"
    )

if mode == "Asli PYQ":
    st.info(
        "असली प्रश्नपत्र से उपलब्ध प्रश्न लिए जाएंगे। "
        "AI द्वारा हल किए गए उत्तर आधिकारिक Answer Key नहीं हैं।"
    )

if mode == "AI PYQ-style Practice":
    st.info(
        "यह AI द्वारा बनाए गए अभ्यास प्रश्न हैं, "
        "सत्यापित वास्तविक PYQ नहीं।"
    )


# --------------------------------------------------
# START QUIZ
# --------------------------------------------------

if st.button("🚀 Generate Quiz", type="primary", use_container_width=True):
    source_text = ""
    key_text = ""

    if mode in ["PDF Quiz", "Asli PYQ"]:
        if source_pdf is None:
            st.error("पहले PDF अपलोड करो।")
            st.stop()

        try:
            source_text = extract_pdf(source_pdf)
        except Exception as e:
            st.error(f"PDF पढ़ने में समस्या: {e}")
            st.stop()

        if not source_text:
            st.error(
                "PDF से टेक्स्ट नहीं मिला। संभव है PDF स्कैन की हुई हो। "
                "टेक्स्ट वाली PDF इस्तेमाल करो।"
            )
            st.stop()

        if mode == "Asli PYQ" and key_pdf is not None:
            try:
                key_text = extract_pdf(key_pdf)
            except Exception as e:
                st.error(f"Answer Key PDF पढ़ने में समस्या: {e}")
                st.stop()

    try:
        with st.spinner("प्रश्न तैयार हो रहे हैं..."):
            questions = generate_questions(
                mode=mode,
                count=count,
                difficulty=difficulty,
                exam=exam,
                source_text=source_text,
                topic=topic
            )

            if mode == "Asli PYQ" and key_text:
                questions = solve_with_answer_key(
                    questions,
                    key_text
                )
                answer_source = "Uploaded Answer Key"
            elif mode == "Asli PYQ":
                answer_source = "AI-solved; not officially verified"
            else:
                answer_source = "AI-generated answer"

        st.session_state.quiz = questions
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.session_state.start_time = time.time()
        st.session_state.duration = minutes * 60
        st.session_state.quiz_mode = mode
        st.session_state.quiz_title = f"{exam} | {mode}"
        st.session_state.answer_source = answer_source
        st.session_state.quiz_id += 1

        st.rerun()

    except Exception as e:
        st.error(f"Quiz बनाने में समस्या आई: {e}")


# --------------------------------------------------
# ACTIVE QUIZ
# --------------------------------------------------

quiz = st.session_state.quiz

if quiz:
    st.divider()
    st.subheader(st.session_state.quiz_title)

    if st.session_state.quiz_mode == "AI PYQ-style Practice":
        st.warning("AI-generated practice — verified actual PYQ नहीं।")
    elif st.session_state.quiz_mode == "Asli PYQ":
        st.info(
            "उत्तर स्रोत: " + st.session_state.answer_source
        )

    if not st.session_state.submitted:
        elapsed = int(time.time() - st.session_state.start_time)
        remaining = max(0, st.session_state.duration - elapsed)

        if remaining == 0:
            st.session_state.submitted = True
            st.rerun()

        st_autorefresh(
            interval=1000,
            key=f"timer_{st.session_state.quiz_id}"
        )

        mins, secs = divmod(remaining, 60)
        st.metric("⏳ समय बाकी", f"{mins:02d}:{secs:02d}")

        with st.form(
            key=f"quiz_form_{st.session_state.quiz_id}"
        ):
            for i, q in enumerate(quiz):
                st.markdown(f"### Q{i + 1}. {q['question']}")

                existing = st.session_state.answers.get(i, None)

                selected = st.radio(
                    "अपना उत्तर चुनें",
                    options=["A", "B", "C", "D"],
                    format_func=lambda x, q=q: (
                        f"{x}. {q['options'][ord(x) - ord('A')]}"
                    ),
                    index=(
                        ["A", "B", "C", "D"].index(existing)
                        if existing in ["A", "B", "C", "D"]
                        else None
                    ),
                    key=f"answer_{st.session_state.quiz_id}_{i}",
                    label_visibility="collapsed"
                )

                st.session_state.answers[i] = selected
                st.divider()

            submitted = st.form_submit_button(
                "✅ Submit Quiz",
                use_container_width=True
            )

            if submitted:
                st.session_state.submitted = True
                st.rerun()

    # --------------------------------------------------
    # RESULTS
    # --------------------------------------------------

    if st.session_state.submitted:
        answers = st.session_state.answers
        correct = 0
        wrong = 0
        skipped = 0
        review = []

        for i, q in enumerate(quiz):
            selected = answers.get(i)
            answer = q.get("answer", "")

            if not selected:
                skipped += 1
                status = "Skipped"
            elif answer and selected == answer:
                correct += 1
                status = "Correct"
            elif answer:
                wrong += 1
                status = "Wrong"
            else:
                status = "Unverified"

            review.append({
                "number": i + 1,
                "question": q["question"],
                "options": q["options"],
                "selected": selected or "Not answered",
                "answer": answer or "Not verified",
                "status": status,
                "explanation": q.get("explanation", "")
            })

        total = len(quiz)
        verified_total = correct + wrong
        score = correct
        accuracy = (
            round(correct / verified_total * 100, 2)
            if verified_total else 0
        )

        st.success("Quiz पूरा हो गया!")
        c1, c2, c3 = st.columns(3)
        c1.metric("सही", correct)
        c2.metric("गलत", wrong)
        c3.metric("छोड़े", skipped)

        c4, c5 = st.columns(2)
        c4.metric("Score", f"{score}/{total}")
        c5.metric("Accuracy", f"{accuracy}%")

        if skipped:
            st.caption(f"छोड़े गए प्रश्न: {skipped}")

        if any(not q.get("answer") for q in quiz):
            st.warning(
                "कुछ प्रश्नों के उत्तर सत्यापित नहीं हैं। "
                "उन प्रश्नों को सही/गलत स्कोर में शामिल नहीं किया गया।"
            )

        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 All Questions",
            "✅ Correct",
            "❌ Wrong",
            "⏭️ Skipped"
        ])

        with tab1:
            for item in review:
                with st.expander(
                    f"Q{item['number']}: {item['status']}"
                ):
                    st.write(item["question"])
                    for j, option in enumerate(item["options"]):
                        letter = "ABCD"[j]
                        st.write(f"{letter}. {option}")

                    st.write(f"तुम्हारा उत्तर: {item['selected']}")
                    st.write(f"सही उत्तर: {item['answer']}")

                    if item["explanation"]:
                        st.write(
                            f"व्याख्या: {item['explanation']}"
                        )

        with tab2:
            items = [x for x in review if x["status"] == "Correct"]
            if not items:
                st.write("कोई सही उत्तर नहीं।")
            for item in items:
                st.write(
                    f"**Q{item['number']}.** {item['question']}"
                )

        with tab3:
            items = [x for x in review if x["status"] == "Wrong"]
            if not items:
                st.write("कोई गलत उत्तर नहीं।")
            for item in items:
                st.write(
                    f"**Q{item['number']}.** {item['question']}"
                )
                st.write(f"तुम्हारा उत्तर: {item['selected']}")
                st.write(f"सही उत्तर: {item['answer']}")
                if item["explanation"]:
                    st.caption(item["explanation"])

        with tab4:
            items = [x for x in review if x["status"] == "Skipped"]
            if not items:
                st.write("कोई प्रश्न नहीं छोड़ा।")
            for item in items:
                st.write(
                    f"**Q{item['number']}.** {item['question']}"
                )
                st.write(f"सही उत्तर: {item['answer']}")

        if st.button("🔄 नया Quiz बनाओ", use_container_width=True):
            st.session_state.quiz = []
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.session_state.start_time = None
            st.rerun()

st.sidebar.divider()
st.sidebar.caption("AI Quiz Maker | Prateek Senmar")
    
