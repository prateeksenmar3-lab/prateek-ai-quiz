import streamlit as st
from streamlit_autorefresh import st_autorefresh
from pypdf import PdfReader
from google import genai
from supabase import create_client
import json, re, time, random

st.set_page_config(page_title="AI Quiz Maker | Prateek Senmar", page_icon="🧠", layout="centered")
st.markdown('''<style>
.stApp{background:radial-gradient(circle at top left,#29204f 0%,#101426 48%,#090d18 100%);color:#f5f7ff}
.block-container{max-width:850px;padding-top:1.2rem}
.hero{padding:24px 16px;border-radius:22px;text-align:center;background:linear-gradient(135deg,#6d3be8,#39206f,#182448);border:1px solid #8b6af0;margin-bottom:20px}
.hero h1{color:white;margin:0}.hero p{color:#e8e2ff;margin:8px 0 0}
div.stButton>button{border-radius:12px;min-height:44px;font-weight:650}
div[data-testid="stMetric"]{background:#ffffff0b;border:1px solid #ffffff1a;padding:12px;border-radius:14px}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🧠 AI Quiz Maker</h1><p>Learn smarter. Practice better. Achieve more.</p><p><b>✨ PRATEEK SENMAR ✨</b></p></div>', unsafe_allow_html=True)

def secret(k, default=""):
    try: return st.secrets.get(k, default)
    except Exception: return default

URL, KEY, GEMINI_KEY = secret("SUPABASE_URL"), secret("SUPABASE_KEY"), secret("GEMINI_API_KEY")
if not URL or not KEY:
    st.error("Streamlit Secrets में SUPABASE_URL और SUPABASE_KEY सेट करें।"); st.stop()
@st.cache_resource
def sb_client(url, key): return create_client(url, key)
sb = sb_client(URL, KEY)

def reset():
    for k,v in {"questions":[],"answers":{},"quiz_title":"","quiz_source":"","quiz_started":0.0,"quiz_duration":0,"submitted":False,"show_solutions":False,"category":None}.items():
        st.session_state[k]=v

for k,v in {"user":None,"section":"PDF to Quiz","questions":[],"answers":{},"quiz_title":"","quiz_source":"","quiz_started":0.0,"quiz_duration":0,"submitted":False,"show_solutions":False,"category":None,"auth_mode":"Login"}.items():
    if k not in st.session_state: st.session_state[k]=v

def email_for(uid):
    uid=uid.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,24}",uid): raise ValueError("ID 3–24 अक्षरों की हो; a-z, 0-9, dot, underscore या hyphen इस्तेमाल करें।")
    return uid+"@users.aiquizmaker.app"

if not st.session_state.user:
    st.subheader("🔐 Login / Signup")
    mode=st.radio("Account",["Login","Signup"],horizontal=True)
    with st.form("auth"):
        uid=st.text_input("User ID")
        pw=st.text_input("Password",type="password")
        go=st.form_submit_button("आगे बढ़ें",use_container_width=True)
    if go:
        try:
            em=email_for(uid)
            if len(pw)<6: st.error("Password कम से कम 6 अक्षर का हो।")
            elif mode=="Login":
                res=sb.auth.sign_in_with_password({"email":em,"password":pw})
                st.session_state.user=res.user; st.rerun()
            else:
                res=sb.auth.sign_up({"email":em,"password":pw})
                st.success("Signup किया गया। अगर email confirmation चालू है तो उसे verify करें, फिर Login करें।")
        except Exception as e: st.error(f"Login/Signup नहीं हुआ: {e}")
    st.stop()

with st.sidebar:
    st.markdown("### 🧠 AI Quiz Maker")
    if st.button("🚪 Logout",use_container_width=True):
        st.session_state.user=None; reset(); st.rerun()
    st.divider()
    st.session_state.section=st.radio("Section",["PDF to Quiz","PYQ Practice","AI Practice"],index=["PDF to Quiz","PYQ Practice","AI Practice"].index(st.session_state.section))

def ai_questions(source,count,difficulty,topic,language):
    if not GEMINI_KEY: raise ValueError("Streamlit Secrets में GEMINI_API_KEY सेट करें।")
    client=genai.Client(api_key=GEMINI_KEY)
    prompt=f'''Create exactly {count} multiple-choice questions in {language}. Difficulty {difficulty}. Topic {topic}.
Use only the source text below. Return ONLY a JSON array with fields question, options (exactly 4 strings), answer (integer 0-3), explanation.
SOURCE: {source[:40000]}'''
    response=client.models.generate_content(model="gemini-2.5-flash",contents=prompt,config={"response_mime_type":"application/json"})
    raw=response.text or "[]"
    m=re.search(r"\[[\s\S]*\]",raw)
    data=json.loads(m.group(0) if m else raw)
    out=[]
    for q in data:
        if isinstance(q,dict) and isinstance(q.get("options"),list) and len(q["options"])==4 and isinstance(q.get("answer"),int) and 0<=q["answer"]<4:
            out.append({"question":str(q["question"]),"options":[str(x) for x in q["options"]],"answer":q["answer"],"explanation":str(q.get("explanation","समाधान उपलब्ध नहीं है।")),"source_url":"","exam_year":"","shift":""})
    if not out: raise ValueError("AI से सही format में प्रश्न नहीं मिले।")
    return out[:count]

def start(qs,title,source,minutes):
    if not qs: st.warning("कोई प्रश्न उपलब्ध नहीं है।"); return
    reset(); st.session_state.questions=qs; st.session_state.quiz_title=title; st.session_state.quiz_source=source
    st.session_state.quiz_started=time.time(); st.session_state.quiz_duration=minutes*60; st.rerun()

def status(i,q):
    a=st.session_state.answers.get(i)
    return "skipped" if a is None else ("correct" if a==q["answer"] else "wrong")

def show_result():
    qs=st.session_state.questions; ans=st.session_state.answers
    counts={x:sum(status(i,q)==x for i,q in enumerate(qs)) for x in ("correct","wrong","skipped")}
    st.subheader("📊 आपका रिज़ल्ट")
    cols=st.columns(4)
    for col,label,val in zip(cols,["कुल","सही","गलत","छोड़े"],[len(qs),counts["correct"],counts["wrong"],counts["skipped"]]): col.metric(label,val)
    st.metric("स्कोर",f'{counts["correct"]} / {len(qs)}')
    if not st.session_state.show_solutions:
        if st.button("📖 Solutions देखें",type="primary",use_container_width=True):
            st.session_state.show_solutions=True; st.rerun()
        return
    c1,c2,c3=st.columns(3)
    for col,cat,label in [(c1,"wrong","🔴 गलत"),(c2,"correct","🟢 सही"),(c3,"skipped","⚪ छोड़े")]:
        if col.button(f'{label} ({counts[cat]})',use_container_width=True): st.session_state.category=cat
    cat=st.session_state.category
    if not cat: st.info("प्रश्न देखने के लिए ऊपर एक श्रेणी चुनें।"); return
    for i,q in enumerate(qs):
        if status(i,q)!=cat: continue
        a=ans.get(i)
        with st.expander(f'प्रश्न {i+1}: {q["question"]}'):
            st.write(q["question"])
            for j,opt in enumerate(q["options"]): st.write(("✅ " if j==q["answer"] else ("👉 " if j==a else "▫️ "))+f"{chr(65+j)}. {opt}")
            st.write("आपका उत्तर:", "उत्तर नहीं दिया" if a is None else q["options"][a])
            st.write("सही उत्तर:",q["options"][q["answer"]])
            st.write("समाधान:",q.get("explanation","समाधान उपलब्ध नहीं है।"))
            if q.get("source_url"): st.markdown(f'[स्रोत देखें]({q["source_url"]})')
            meta=[str(q.get(x)) for x in ("exam_year","shift") if q.get(x)]
            if meta: st.caption(" · ".join(meta))
    if st.button("🔁 नया टेस्ट",type="primary",use_container_width=True): reset(); st.rerun()

if st.session_state.questions:
    if st.session_state.submitted:
        show_result(); st.stop()
    qs=st.session_state.questions; total=st.session_state.quiz_duration
    remaining=max(0,total-int(time.time()-st.session_state.quiz_started))
    if remaining==0: st.session_state.submitted=True; st.rerun()
    st_autorefresh(interval=1000,key="timer")
    st.subheader(st.session_state.quiz_title)
    st.caption(f'समय बाकी: {remaining//60:02d}:{remaining%60:02d} मिनट')
    st.progress(remaining/total if total else 0)
    with st.form("test_form"):
        picks={}
        for i,q in enumerate(qs):
            st.markdown(f'**प्रश्न {i+1}.** {q["question"]}')
            old=st.session_state.answers.get(i)
            picks[i]=st.radio(f"उत्तर {i+1}",list(range(4)),index=old if isinstance(old,int) else None,format_func=lambda n,opts=q["options"]:f"{chr(65+n)}. {opts[n]}",key=f'pick_{st.session_state.quiz_started}_{i}',label_visibility="collapsed")
        submit=st.form_submit_button("✅ टेस्ट सबमिट करें",type="primary",use_container_width=True)
    if submit:
        st.session_state.answers.update(picks); st.session_state.submitted=True; st.rerun()
    st.stop()

if st.session_state.section=="PDF to Quiz":
    st.subheader("📄 PDF से Quiz बनाएँ")
    file=st.file_uploader("PDF अपलोड करें",type=["pdf"])
    a,b=st.columns(2)
    count=a.selectbox("कितने प्रश्न?",[5,10,15,20,25,30,40,50],index=1)
    difficulty=a.selectbox("कठिनाई",["Easy","Medium","Hard"],index=1)
    minutes=b.selectbox("टाइमर (मिनट)",[5,10,15,20,30,45,60,90,120,150,180,240],index=4)
    language=b.selectbox("भाषा",["Hindi","English"])
    topic=st.text_input("विषय (वैकल्पिक)")
    if st.button("✨ Quiz बनाओ",type="primary",use_container_width=True):
        if not file: st.warning("पहले PDF अपलोड करो।")
        else:
            try:
                text="\n".join(p.extract_text() or "" for p in PdfReader(file).pages)
                if len(text.strip())<80: raise ValueError("PDF में पढ़ने योग्य text नहीं मिला।")
                with st.spinner("प्रश्न बनाए जा रहे हैं..."): qs=ai_questions(text,count,difficulty,topic or file.name,language)
                start(qs,f"PDF Quiz · {file.name}","pdf",minutes)
            except Exception as e: st.error(f"Quiz नहीं बन पाया: {e}")

elif st.session_state.section=="PYQ Practice":
    st.subheader("📝 PYQ Practice")
    st.caption("सिर्फ verified=true और source URL वाले वास्तविक PYQ। AI-generated प्रश्न यहाँ नहीं मिलेंगे।")
    a,b=st.columns(2)
    exam=a.selectbox("Exam Select",["SSC CGL","SSC CHSL","Railway","NEET","UPSC","UP Police","Other"])
    subject=a.selectbox("Subject Select",["All Subjects","Maths / Quant","Reasoning","English","General Awareness","Physics","Chemistry","Biology","History","Geography","Polity","Economics"])
    count=b.selectbox("कितने प्रश्न?",[10,25,50,100,150,200],index=1)
    minutes=b.selectbox("टाइमर (मिनट)",[15,30,45,60,90,120,150,180,240,300],index=3)
    st.caption("120 मिनट = 2 घंटे; 150, 180, 240 और 300 मिनट भी उपलब्ध हैं।")
    if st.button("🔎 असली PYQ खोजें",type="primary",use_container_width=True):
        try:
            q=sb.table("pyq_questions").select("*").eq("verified",True).eq("exam",exam).limit(1000)
            if subject!="All Subjects": q=q.eq("subject",subject)
            rows=q.execute().data or []; bank=[]
            for r in rows:
                opts=r.get("options"); ans=r.get("answer"); url=r.get("source_url","")
                if isinstance(opts,str):
                    try: opts=json.loads(opts)
                    except Exception: opts=[]
                if isinstance(opts,list) and len(opts)==4 and isinstance(ans,int) and 0<=ans<4 and str(url).startswith("http") and r.get("question"):
                    bank.append({"question":str(r["question"]),"options":[str(x) for x in opts],"answer":ans,"explanation":str(r.get("explanation") or "समाधान उपलब्ध नहीं है।"),"source_url":url,"exam_year":r.get("exam_year") or "","shift":r.get("shift") or ""})
            random.shuffle(bank); chosen=bank[:count]
            if not chosen: st.warning("इस Exam/Subject के लिए verified PYQ नहीं मिले। नकली प्रश्नों से संख्या पूरी नहीं की जाएगी। Supabase में pyq_questions table में सत्यापित प्रश्न जोड़ें।")
            else:
                st.info(f"{len(chosen)} असली, verified प्रश्न मिले।")
                start(chosen,f"{exam} · {subject} PYQ","verified_pyq",minutes)
        except Exception as e: st.error(f"PYQ bank उपलब्ध नहीं है। पहले साथ दी गई SQL setup फ़ाइल चलाएँ। विवरण: {e}")

else:
    st.subheader("✨ AI Practice")
    st.caption("यहाँ AI-generated अभ्यास प्रश्न मिलेंगे; इन्हें असली PYQ नहीं कहा जाएगा।")
    a,b=st.columns(2)
    topic=st.text_input("Topic",placeholder="जैसे प्रतिशत, संविधान, कोशिका")
    count=a.selectbox("कितने प्रश्न?",[5,10,15,20,25,30,50],index=1)
    difficulty=a.selectbox("कठिनाई",["Easy","Medium","Hard"],index=1)
    minutes=b.selectbox("टाइमर (मिनट)",[5,10,15,20,30,45,60,90,120,150,180,240],index=4)
    language=b.selectbox("भाषा",["Hindi","English"])
    if st.button("🚀 Practice शुरू करें",type="primary",use_container_width=True):
        if not topic.strip(): st.warning("पहले Topic लिखो।")
        else:
            try:
                with st.spinner("AI प्रश्न बना रहा है..."):
                    qs=ai_questions(f"Generate standard exam practice questions about {topic}.",count,difficulty,topic,language)
                start(qs,f"AI Practice · {topic}","ai_generated",minutes)
            except Exception as e: st.error(f"प्रश्न नहीं बन पाए: {e}")

st.markdown("---")
st.markdown('<div style="text-align:center;color:#9baed2;padding:10px">Made with ❤️ by <b>Prateek Senmar</b> · Your Personal Study Companion</div>',unsafe_allow_html=True)
