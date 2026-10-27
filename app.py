
import streamlit as st

st.set_page_config(
    page_title="AI Quiz Maker | Prateek Senmar",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top left,
    #29204d 0%, #10111b 42%, #080910 100%);
    color: white;
}
.block-container {
    max-width: 1050px;
    padding-top: 3rem;
}
.hero {
    padding: 35px 25px;
    border: 1px solid #393052;
    border-radius: 25px;
    background: linear-gradient(135deg,
    rgba(124,58,237,.22), rgba(20,20,35,.85));
    text-align: center;
}
.hero h1 {
    font-size: 46px;
    color: white;
    margin-bottom: 8px;
}
.purple { color: #b99aff; }
.small {
    color: #b7b5c9;
    font-size: 17px;
}
div.stButton > button {
    width: 100%;
    border-radius: 12px;
    background: linear-gradient(90deg,#7c3aed,#a855f7);
    color: white;
    border: 0;
    padding: 13px;
    font-weight: bold;
}
.card {
    background: #171827;
    border: 1px solid #303047;
    padding: 20px;
    border-radius: 17px;
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🎯 AI Quiz Maker</h1>
    <div class="purple">BY PRATEEK SENMAR</div>
    <br>
    <h2>Learn Smarter. <span class="purple">Test Yourself.</span></h2>
    <p class="small">
    Turn your study material into a smarter learning experience.
    </p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.markdown("### ✨ Your Personal Study Assistant")

left, right = st.columns(2)

with left:
    st.markdown("""
    <div class="card">
    <h3>📚 Upload Study Material</h3>
    <p class="small">Upload a PDF to prepare your quiz.</p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown("""
    <div class="card">
    <h3>🎯 Practice & Improve</h3>
    <p class="small">Test your knowledge and build confidence.</p>
    </div>
    """, unsafe_allow_html=True)

pdf = st.file_uploader("📄 Choose your study PDF", type=["pdf"])
count = st.selectbox("Number of questions", [5, 10, 15, 20])

if pdf:
    st.success(f"Uploaded: {pdf.name}")
    st.info(
        f"Your PDF is ready. Selected quiz size: {count} questions. "
        "AI generation will be connected in the next setup step."
    )

st.write("")
st.caption("Made with ❤️ by Prateek Senmar")

