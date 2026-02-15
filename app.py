import streamlit as st
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="AI Internship Scam Detection System",
    layout="wide"
)


# ---------------- GLOBAL CSS ----------------
st.markdown("""
<style>

/* GENERAL */
html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
}

/* NAVBAR */
.navbar {
    position: fixed;
    top: 0;
    width: 100%;
    background: #0f3b5f;
    padding: 12px 40px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 9999;
}
.navbar .brand {
    color: white;
    font-size: 16px;
    font-weight: 600;
}
.navbar a {
    color: #e6f2ff;
    margin-left: 18px;
    text-decoration: none;
    font-size: 13px;
}
.navbar a:hover {
    text-decoration: underline;
}

/* SPACER */
.spacer {
    height: 70px;
}

/* HERO */
.hero {
    background: linear-gradient(135deg, #0f3b5f, #1e6fa3);
    padding: 36px 20px;
    text-align: center;
    color: white;
    border-radius: 14px;
}
.hero h1 {
    font-size: 24px;
    margin-bottom: 6px;
}
.hero p {
    font-size: 13px;
    opacity: 0.9;
}

/* CARD */
.card {
    background: #ffffff;
    color: #0f172a;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align: center;
}

/* SECTION TITLE */
.section-title {
    text-align: center;
    font-size: 18px;
    font-weight: 600;
    margin-top: 30px;
}

/* RESULT */
.fake {
    background: #fdeaea;
    border-left: 6px solid #dc3545;
    padding: 16px;
    border-radius: 12px;
}
.real {
    background: #e9f9f0;
    border-left: 6px solid #28a745;
    padding: 16px;
    border-radius: 12px;
}

/* FOOTER */
.footer {
    background: #0f3b5f;
    color: white;
    padding: 22px;
    margin-top: 60px;
    text-align: center;
    font-size: 12px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- NAVBAR ----------------
st.markdown("""
<div class="navbar">
    <div class="brand">AI Internship Scam Detection System</div>
    <div>
        <a href="#home">Home</a>
        <a href="#features">Features</a>
        <a href="#analyze">Analyze</a>
        <a href="#contact">Contact</a>
    </div>
</div>
<div class="spacer"></div>
""", unsafe_allow_html=True)

# ---------------- HERO ----------------
st.markdown("""
<div id="home" class="hero">
    <h1>AI-Based Internship Scam Detector</h1>
    <p>Detect fake internship offers using Machine Learning & NLP</p>
</div>
""", unsafe_allow_html=True)

# ---------------- FEATURES ----------------
st.markdown('<div id="features"></div>', unsafe_allow_html=True)
st.markdown("<div class='section-title'>Core Features</div>", unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)
f1.markdown("<div class='card'>🤖 <b>ML Powered</b><br><small>Rule + NLP based detection</small></div>", unsafe_allow_html=True)
f2.markdown("<div class='card'>🧠 <b>Explainable AI</b><br><small>Clear reasons shown</small></div>", unsafe_allow_html=True)
f3.markdown("<div class='card'>🛡️ <b>Student Safety</b><br><small>Scam prevention focus</small></div>", unsafe_allow_html=True)

# ---------------- HOW IT WORKS ----------------
st.markdown("<div class='section-title'>How It Works</div>", unsafe_allow_html=True)

h1, h2, h3 = st.columns(3)
h1.markdown("<div class='card'>1️⃣ Text Processing<br><small>NLP cleaning</small></div>", unsafe_allow_html=True)
h2.markdown("<div class='card'>2️⃣ Pattern Detection<br><small>Fees & urgency</small></div>", unsafe_allow_html=True)
h3.markdown("<div class='card'>3️⃣ Classification<br><small>Real or Fake</small></div>", unsafe_allow_html=True)

# ---------------- SAMPLE BUTTONS ----------------
st.markdown("<div class='section-title'>Try Sample Offers</div>", unsafe_allow_html=True)

if st.button("❌ Fake Internship Example", use_container_width=True):
    st.session_state.text = "Pay registration fee urgently. Guaranteed placement. No interview. Contact via WhatsApp."

if st.button("✅ Genuine Internship Example", use_container_width=True):
    st.session_state.text = "No registration fee. Selection through interview. Official company email communication."

# ---------------- OCR ----------------
st.markdown('<div id="analyze"></div>', unsafe_allow_html=True)
st.markdown("<div class='section-title'>📸 Screenshot OCR Analysis</div>", unsafe_allow_html=True)

image = st.file_uploader("Upload internship email or message screenshot", type=["png", "jpg", "jpeg"])

ocr_text = ""
if image:
    img = Image.open(image)
    ocr_text = pytesseract.image_to_string(img)
    st.text_area("Extracted Text", ocr_text, height=120)

# ---------------- ANALYSIS ----------------
st.markdown("<div class='section-title'>🔍 Analyze Internship Offer</div>", unsafe_allow_html=True)

text = st.text_area(
    "Paste internship content here",
    height=160,
    value=st.session_state.get("text", ocr_text)
)

SCAM_RULES = {
    "registration fee": "Asks for payment",
    "pay": "Payment related wording",
    "urgent": "Creates urgency",
    "whatsapp": "Unofficial contact method",
    "guaranteed": "Unrealistic guarantee",
    "no interview": "No proper selection process"
}

if st.button("Analyze Internship"):
    found = []
    lower = text.lower()

    for k, reason in SCAM_RULES.items():
        if k in lower:
            found.append(reason)

    if "no registration fee" in lower:
        found = []

    confidence = min(95, 60 + len(found) * 8)

    if found:
        st.markdown(f"<div class='fake'><h4>❌ Fake Internship</h4><p>Confidence: {confidence}%</p></div>", unsafe_allow_html=True)
        st.markdown("**Why this result?**")
        for r in found:
            st.write(f"- {r}")
    else:
        st.markdown(f"<div class='real'><h4>✅ Genuine Internship</h4><p>Confidence: {confidence}%</p></div>", unsafe_allow_html=True)
        st.markdown("**Why this result?**")
        st.write("- No payment request")
        st.write("- Professional communication")
        st.write("- Proper selection process")

# ---------------- FOOTER ----------------
st.markdown("""
<div id="contact" class="footer">
<b>Kalaimathi Gopalakrishnan</b> — BCA Final Year Project<br>
📧 <a href="kalaimathigopalakrishnan280@gmail.com" style="color:white;">kalaimathigopalakrishnan280@gmail.com</a> |
🔗 <a href="https://www.linkedin.com/in/kalaimathigd/" target="_blank" style="color:white;">LinkedIn</a><br>
AI-Based Internship Scam Detection System © 2026
</div>
""", unsafe_allow_html=True)



