import streamlit as st
from auth import login, signup
import pytesseract
from PIL import Image
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import re
import plotly.graph_objects as go
from utils import predict_internship, risk_score
import os
import socket
import dns.resolver
import fitz  # PyMuPDF for PDF reading

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(layout="wide")

# ==================== SESSION ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "history" not in st.session_state:
    st.session_state.history = []
if "text" not in st.session_state:
    st.session_state.text = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==================== CSS ====================
st.markdown("""
<style>
body {background-color:#0d1117;color:white;}

.left-panel {
    background:#161b22;
    padding:50px;
    border-radius:12px;
    color:white;
}
.left-panel p { color:white !important; }
.highlight { color:#3fb950; font-weight:bold; }

.card {
    background:#161b22;
    padding:18px;
    border-radius:10px;
    margin-bottom:15px;
    color:white;
}
.module-box {
    background:#21262d;
    padding:15px;
    border-radius:10px;
    margin-bottom:10px;
    color:white;
}
.chat-user {
    background:#1f6feb;
    padding:10px 15px;
    border-radius:10px 10px 0 10px;
    margin:6px 0;
    color:white;
    max-width:75%;
    margin-left:auto;
    text-align:right;
}
.chat-bot {
    background:#21262d;
    padding:10px 15px;
    border-radius:10px 10px 10px 0;
    margin:6px 0;
    color:white;
    max-width:75%;
}
input, textarea { background:white !important; color:black !important; }
.stButton > button {
    width:100%;
    background:#238636;
    color:white;
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)


# ==================== HELPER FUNCTIONS ====================

# ---------- COMPANY / EMAIL / LOCATION EXTRACTION ----------
def extract_entities(text):
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"\b[\+]?[\d\s\-]{10,15}\b", text)
    company_match = re.search(r"(?:at|from|company[:\s]+|organization[:\s]+)([A-Z][A-Za-z0-9&\s.]+)", text)
    company = company_match.group(1).strip() if company_match else "Not Detected"
    location_patterns = [
        r"\b(?:Mumbai|Delhi|Bangalore|Bengaluru|Chennai|Hyderabad|Kolkata|Pune|Ahmedabad|"
        r"Jaipur|Lucknow|Noida|Gurugram|Gurgaon|Coimbatore|Madurai|Kochi|Chandigarh|"
        r"New York|London|San Francisco|Berlin|Singapore|Dubai|Remote|Work from Home|WFH)\b"
    ]
    locations = []
    for pattern in location_patterns:
        locations += re.findall(pattern, text, re.IGNORECASE)
    locations = list(set(locations))
    return {
        "company": company,
        "emails": emails if emails else ["None"],
        "phones": [p.strip() for p in phones if len(p.strip()) >= 10] or ["None"],
        "locations": locations if locations else ["Not Detected"]
    }


# ---------- EMAIL VERIFICATION ----------
KNOWN_SCAM_DOMAINS = [
    "yopmail.com", "mailinator.com", "guerrillamail.com",
    "trashmail.com", "tempmail.com", "10minutemail.com",
    "fakeinbox.com", "sharklasers.com", "throwam.com"
]

PERSONAL_DOMAINS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
                    "rediffmail.com", "aol.com", "icloud.com", "protonmail.com"]

def check_mx_record(domain):
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return True, [str(r.exchange) for r in records]
    except Exception:
        return False, []

def verify_email(email):
    result = {}
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        result["valid_format"] = False
        result["summary"] = "❌ Invalid email format."
        return result
    result["valid_format"] = True
    domain = email.split("@")[1].lower()
    result["domain"] = domain

    # Scam domain check
    if domain in KNOWN_SCAM_DOMAINS:
        result["scam_domain"] = True
        result["risk"] = "HIGH"
        result["summary"] = f"🚨 Known scam/disposable domain detected: {domain}"
        return result
    result["scam_domain"] = False

    # Personal email flag
    result["is_personal"] = domain in PERSONAL_DOMAINS
    if result["is_personal"]:
        result["risk"] = "MODERATE"
        result["personal_note"] = "⚠️ Personal email domain (not a company domain). Genuine companies use official domains."
    else:
        result["risk"] = "LOW"
        result["personal_note"] = "✅ Company/organisation domain detected."

    # MX record lookup
    mx_found, mx_records = check_mx_record(domain)
    result["mx_found"] = mx_found
    result["mx_records"] = mx_records[:3] if mx_records else []
    if not mx_found:
        result["risk"] = "HIGH"
        result["mx_note"] = "❌ No MX records found — domain may not be real."
    else:
        result["mx_note"] = f"✅ MX records found: {', '.join(result['mx_records'][:2])}"

    # Final summary
    if result["risk"] == "HIGH":
        result["summary"] = "🚨 HIGH RISK — This email shows strong signs of being fraudulent."
    elif result["risk"] == "MODERATE":
        result["summary"] = "⚠️ MODERATE RISK — Personal email used. Verify company identity separately."
    else:
        result["summary"] = "✅ LOW RISK — Email domain appears legitimate."

    return result


# ---------- CERTIFICATE / OFFER LETTER VERIFICATION ----------
FAKE_CERTIFICATE_SIGNALS = [
    "pay to get certificate", "payment required", "registration fee",
    "send money", "pay now", "fee required", "deposit required",
    "guaranteed certificate", "no exam", "instant certificate"
]

GENUINE_CERTIFICATE_SIGNALS = [
    "this is to certify", "certificate of completion", "certificate of internship",
    "offer letter", "we are pleased to offer", "letter of intent",
    "joining date", "designation", "stipend", "department",
    "authorized signatory", "on behalf of", "human resources"
]

COURSE_SIGNALS = [
    "certificate of completion", "course", "online course", "completed the course",
    "udemy", "coursera", "nptel", "great learning", "simplilearn",
    "edx", "swayam", "learning path", "module", "training program"
]

REAL_COMPANY_INDICATORS = [
    "cin", "gst", "registered office", "pvt ltd", "private limited",
    "llp", "inc.", "ltd.", "corporation", "solutions", "technologies",
    "services", "systems", "enterprises"
]

def extract_text_from_pdf(file):
    try:
        pdf_bytes = file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def verify_certificate(text):
    text_lower = text.lower()
    result = {}

    # Detect if it's a course certificate (not internship)
    course_hits = [s for s in COURSE_SIGNALS if s in text_lower]
    internship_hits = [s for s in GENUINE_CERTIFICATE_SIGNALS if s in text_lower]
    is_internship = any(k in text_lower for k in ["internship", "intern", "offer letter", "joining letter"])

    if course_hits and not is_internship:
        result["type"] = "Course Certificate"
        result["is_internship"] = False
        result["summary"] = ("📚 This appears to be a **Course/Training Certificate** — "
                             "no internship information found. This is not an internship offer or completion letter.")
        result["risk"] = "N/A"
        result["genuine"] = None
        return result

    result["is_internship"] = True

    # Check for fake signals
    fake_hits = [s for s in FAKE_CERTIFICATE_SIGNALS if s in text_lower]
    genuine_hits = [s for s in GENUINE_CERTIFICATE_SIGNALS if s in text_lower]
    company_hits = [s for s in REAL_COMPANY_INDICATORS if s in text_lower]

    # QR / Certificate ID / Verification
    has_qr_mention = any(k in text_lower for k in ["qr", "scan", "verify at", "verification link", "verify online"])
    cert_id_match = re.search(r"(?:certificate\s*(?:no|id|number)[:\s#]*)([\w\-/]+)", text, re.IGNORECASE)
    cert_id = cert_id_match.group(1) if cert_id_match else None

    result["has_verification"] = has_qr_mention or cert_id is not None
    result["cert_id"] = cert_id
    result["has_qr"] = has_qr_mention

    # Scoring
    score = 0
    score += len(genuine_hits) * 10
    score += len(company_hits) * 8
    score -= len(fake_hits) * 15
    if result["has_verification"]:
        score += 20

    result["genuine"] = score >= 20
    result["genuine_signals"] = genuine_hits
    result["fake_signals"] = fake_hits
    result["company_signals"] = company_hits

    # Extracted company name
    company_match = re.search(
        r"(?:from|by|at|issued\s+by|company[:\s]+)([A-Z][A-Za-z0-9&\s.]+(?:Pvt\.?\s*Ltd\.?|LLC|Inc\.?|LLP|Technologies|Solutions|Services)?)",
        text)
    result["company"] = company_match.group(1).strip() if company_match else "Not Detected"

    if result["genuine"]:
        result["type"] = "Internship Certificate / Offer Letter"
        result["risk"] = "LOW"
        result["summary"] = "✅ This document appears to be a **genuine internship certificate or offer letter**."
    else:
        result["type"] = "Suspicious Internship Document"
        result["risk"] = "HIGH"
        result["summary"] = "🚨 This document shows signs of being **fake or fraudulent**."

    return result


# ---------- RULE-BASED CHATBOT ----------
CHATBOT_KB = {
    # Scam detection
    "payment": "🚨 Legitimate internships NEVER ask for payment. If an internship asks you to pay a registration, training, or deposit fee — it is a scam. Report it immediately.",
    "fee": "🚨 Any internship that asks for a fee upfront is fraudulent. Real companies pay YOU, not the other way around.",
    "registration fee": "🚨 Registration fees for internships are a classic scam tactic. Do not pay. Walk away and report the listing.",
    "scam": "🛡️ Common internship scam signs: payment requests, WhatsApp/Telegram-only contact, guaranteed selection without interviews, no company website, and too-good-to-be-true stipends.",
    "fake": "🛡️ To identify fake internships: check the company on LinkedIn, look for an official website, verify the email domain, and never pay money to apply.",

    # Applications
    "apply": "📋 Apply for internships via official platforms like LinkedIn, Internshala, Naukri, Indeed, or company career pages. Always use the official apply link.",
    "resume": "📄 Keep your resume concise (1 page for freshers). Include skills, projects, education, and certifications. Use action verbs and quantify achievements where possible.",
    "linkedin": "🔗 LinkedIn is one of the best platforms for internships. Complete your profile with a photo, skills, and projects. Connect with professionals in your target field.",
    "internshala": "🎓 Internshala is great for Indian students. Set up job alerts, complete your profile 100%, and apply with a customised cover letter.",
    "portfolio": "💼 Build a portfolio with GitHub (for tech), Behance (for design), or a personal website. Projects speak louder than grades for most internships.",

    # Interview prep
    "interview": "🎯 Prepare for internship interviews by: practising common HR questions, revising your projects, studying the company background, and doing mock interviews with friends.",
    "hr round": "💬 In HR rounds: be honest, show enthusiasm, explain your goals clearly, and always ask a thoughtful question at the end about the team or work culture.",
    "technical interview": "💻 For tech interviews: practise DSA on LeetCode/HackerRank, revise core subjects (DBMS, OS, CN), and be ready to explain your projects end-to-end.",
    "salary": "💰 For freshers/interns, stipends in India typically range ₹5,000–₹25,000/month depending on company and role. Don't accept zero stipend if you have strong skills.",
    "stipend": "💰 A genuine internship offers a stipend. If no stipend is offered, ask why. Unpaid internships can still be valuable if the company and learning are credible.",

    # Career advice
    "skills": "🛠️ Top skills employers look for in 2025: Python, data analysis, communication, problem-solving, cloud basics, and domain knowledge. Focus on 2–3 skills and go deep.",
    "certificate": "📜 Certificates help but projects matter more. Certifications from Google, Microsoft, AWS, or NPTEL carry good weight. Avoid paying for random certifications.",
    "career": "🚀 For career planning: identify your interests early, do internships in your 2nd and 3rd year, build a network, and get at least one solid project live before graduation.",
    "fresher": "🎓 As a fresher: focus on skills + projects over grades alone, attend college placement drives, apply early to internships, and don't be afraid of rejections — they're part of the process.",
    "work from home": "🏠 Remote internships are completely legitimate when offered by genuine companies. However, be extra careful — scammers use 'work from home' as bait. Always verify the company.",

    # Red flags
    "whatsapp": "⚠️ Beware of recruiters who communicate ONLY via WhatsApp or Telegram. Genuine companies use official email (company domain) for formal communications.",
    "telegram": "⚠️ Telegram-only recruitment is a red flag. Scammers prefer Telegram/WhatsApp to avoid accountability. Always request an official email communication.",
    "guaranteed": "🚨 No internship can guarantee selection. 'Guaranteed placement after payment' is always a scam — 100% of the time.",
    "urgent": "⚠️ Urgency is a manipulation tactic. Phrases like 'Apply in 2 hours or lose the slot' are designed to stop you from thinking clearly. Take your time to verify.",

    # General
    "hello": "👋 Hello! I'm your Internship Safety Assistant. Ask me anything about internship scams, job applications, resume tips, interview prep, or career advice!",
    "hi": "👋 Hi there! How can I help you today? You can ask me about scam detection, resume tips, interview prep, or career guidance.",
    "help": "🤖 I can help you with:\n• Detecting internship scams\n• Resume & LinkedIn tips\n• Interview preparation\n• Career advice for students\n• Email & certificate verification tips\n\nJust type your question!",
    "thank": "😊 You're welcome! Stay safe from scams and best of luck with your internship hunt! 🚀",
    "bye": "👋 Goodbye! Remember — never pay for an internship. Stay safe and good luck! 🌟",
}

def chatbot_response(user_input):
    user_lower = user_input.lower().strip()
    # Direct keyword match
    for key, response in CHATBOT_KB.items():
        if key in user_lower:
            return response
    # Fallback patterns
    if any(w in user_lower for w in ["how", "what", "when", "where", "who", "why", "can", "should", "is", "do"]):
        return ("🤔 I'm not sure about that specific question, but I can help you with:\n"
                "• Internship scam detection\n• Resume tips\n• Interview preparation\n"
                "• Career guidance for students\n\nTry asking something like: "
                "'How do I detect a fake internship?' or 'What should my resume include?'")
    return ("💡 I didn't quite understand that. Try asking about:\n"
            "• **Scam signs** — 'What are signs of a fake internship?'\n"
            "• **Resume** — 'How do I write a good resume?'\n"
            "• **Interview** — 'How do I prepare for an interview?'\n"
            "• **Career** — 'What skills should I learn as a fresher?'")


# ==================== AUTH ====================
if not st.session_state.logged_in:

    col1, col2 = st.columns([1.3, 1])

    with col1:
        st.markdown("""
        <div class='left-panel'>
        <h1>AI Internship Analyzer</h1>
        <p>Advanced <span class='highlight'>AI-based system</span> to detect internship scams.</p>
        <br>
        <p>✔ Detect fraudulent offers</p>
        <p>✔ Analyze risk patterns</p>
        <p>✔ Verify company signals</p>
        <p>✔ Certificate & Offer Letter Verification</p>
        <p>✔ Email Verification</p>
        <p>✔ AI Chatbot Assistant</p>
        <p>✔ Generate professional reports</p>
        <br>
        <p><span class='highlight'>Built for students & job seekers</span></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        option = st.radio("", ["Login", "Signup"])
        email_input = st.text_input("Email")
        password_input = st.text_input("Password", type="password")

        if option == "Login":
            if st.button("Login"):
                if login(email_input, password_input):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        else:
            if st.button("Signup"):
                success, msg = signup(email_input, password_input)
                if success:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)

# ==================== MAIN APP ====================
else:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("", [
        "Dashboard",
        "Internship Advisory",
        "Certificate Verification",
        "Chatbot Assistant",
        "History"
    ])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ================================================================
    # PAGE 1 — DASHBOARD
    # ================================================================
    if page == "Dashboard":

        st.title("Internship Analysis Dashboard")
        colA, colB = st.columns([1, 2])

        with colA:
            st.markdown("""
            <div class='module-box'>
            <h3>System Modules</h3>
            ✔ ML Classification Engine<br>
            ✔ Risk Assessment Engine<br>
            ✔ OCR Text Extraction<br>
            ✔ Email Verifier<br>
            ✔ Entity Extractor<br>
            ✔ Automated Report Generator
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class='module-box'>
            <h3>Analysis Capabilities</h3>
            Detects <span style='color:#3fb950;'>fraud indicators</span> such as:
            <br>• Payment requests
            <br>• Urgency pressure
            <br>• Informal communication
            <br>• Lack of company credibility
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div class='module-box'>
            <h3>System Objective</h3>
            This system helps users identify 
            <span style='color:#3fb950;'>potential internship scams</span> 
            using AI-driven insights and structured evaluation.
            </div>
            """, unsafe_allow_html=True)

        with colB:
            st.subheader("Sample Inputs")
            c1, c2 = st.columns(2)
            if c1.button("Fake Example"):
                st.session_state.text = "Pay registration fee to start internship immediately. Limited seats apply now!"
                st.rerun()
            if c2.button("Genuine Example"):
                st.session_state.text = "We are offering a paid internship with structured training and official onboarding process."
                st.rerun()

            image = st.file_uploader("Upload Screenshot", type=["png", "jpg"])
            if image:
                img = Image.open(image)
                extracted = pytesseract.image_to_string(img)
                st.session_state.text = extracted
                st.text_area("Extracted Text", extracted)

            text = st.text_area("Internship Description", value=st.session_state.text)

            if st.button("Clear Input"):
                st.session_state.text = ""
                st.rerun()

            # -------- ANALYSIS --------
            if st.button("Analyze"):
                result = predict_internship(text)
                score, reasons, pay_risk, urg_risk, cont_risk = risk_score(text)
                confidence = 100 - score if result == 0 else min(score + 20, 100)

                # Final Prediction
                st.subheader("Final Prediction")
                if result == 1:
                    st.error("⚠️ This internship is predicted to be FRAUDULENT based on multiple high-risk indicators.")
                else:
                    st.success("✅ This internship appears to be GENUINE based on evaluated parameters.")

                # -------- ENTITY EXTRACTION --------
                st.subheader("🔍 Extracted Information")
                entities = extract_entities(text)

                ent_col1, ent_col2 = st.columns(2)
                with ent_col1:
                    st.markdown(f"""
                    <div class='module-box'>
                    <b>🏢 Company:</b> {entities['company']}<br><br>
                    <b>📍 Locations:</b> {', '.join(entities['locations'])}
                    </div>
                    """, unsafe_allow_html=True)
                with ent_col2:
                    st.markdown(f"""
                    <div class='module-box'>
                    <b>📧 Emails:</b> {', '.join(entities['emails'])}<br><br>
                    <b>📞 Phones:</b> {', '.join(entities['phones'])}
                    </div>
                    """, unsafe_allow_html=True)

                # -------- EMAIL VERIFICATION --------
                if entities['emails'] and entities['emails'][0] != "None":
                    st.subheader("📧 Email Verification")
                    for em in entities['emails']:
                        ev = verify_email(em)
                        risk_color = {"HIGH": "#f85149", "MODERATE": "#d29922", "LOW": "#3fb950"}.get(ev.get("risk","LOW"), "#3fb950")
                        st.markdown(f"""
                        <div style="background:#161b22; padding:15px; border-radius:10px;
                             border-left:5px solid {risk_color}; margin-bottom:10px; color:white;">
                        <b>Email:</b> {em}<br>
                        <b>Risk:</b> <span style="color:{risk_color};">{ev.get('risk','N/A')}</span><br>
                        {ev.get('summary','')}<br>
                        {ev.get('personal_note','')}<br>
                        {ev.get('mx_note','')}<br>
                        {f"<b>MX Records:</b> {', '.join(ev.get('mx_records', []))}" if ev.get('mx_records') else ''}
                        </div>
                        """, unsafe_allow_html=True)

                # -------- RISK SCORECARD --------
                st.subheader("Risk Assessment Summary")
                if score <= 30:
                    risk_level, color = "LOW RISK", "#3fb950"
                elif score <= 70:
                    risk_level, color = "MODERATE RISK", "#d29922"
                else:
                    risk_level, color = "HIGH RISK", "#f85149"

                payment_flag = "Yes" if pay_risk else "No"
                urgency_flag = "Yes" if urg_risk else "No"
                contact_flag = "Yes" if cont_risk else "No"

                st.markdown(f"""
                <div style="background:#161b22; padding:25px; border-radius:12px;
                     border-left:6px solid {color}; color:white;">
                <h2 style="color:white; margin-bottom:10px;">Risk Score: {score}/100</h2>
                <p style="font-size:18px;"><b>Status:</b> <span style="color:{color};">{risk_level}</span></p>
                <hr style="border:1px solid #30363d;">
                <h4 style="color:#3fb950;">Risk Indicators</h4>
                <table style="width:100%; color:white; font-size:15px;">
                <tr><td>Payment Request</td><td><b>{payment_flag}</b></td></tr>
                <tr><td>Urgency Pressure</td><td><b>{urgency_flag}</b></td></tr>
                <tr><td>Unverified Contact</td><td><b>{contact_flag}</b></td></tr>
                </table>
                <br>
                <h4 style="color:#3fb950;">Top Detected Signals</h4>
                <ul style="color:white;">
                {''.join([f"<li>{r}</li>" for r in reasons[:5]])}
                </ul>
                </div>
                """, unsafe_allow_html=True)

                def gauge(value, title):
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=value,
                        title={'text': title},
                        gauge={
                            'axis': {'range': [0, 100]},
                            'steps': [
                                {'range': [0, 30], 'color': "green"},
                                {'range': [30, 70], 'color': "yellow"},
                                {'range': [70, 100], 'color': "red"}
                            ]
                        }
                    ))
                    return fig

                g1, g2 = st.columns(2)
                g1.plotly_chart(gauge(score, "Risk Score"), use_container_width=True)
                g2.plotly_chart(gauge(confidence, "Confidence"), use_container_width=True)

                # Explanation
                st.subheader("Analysis Explanation")
                st.write(f"""
The internship posting has been evaluated using a hybrid ML and rule-based system.
Key indicators such as {", ".join(reasons[:6])} were detected.

The computed risk score of {score}/100 suggests this opportunity is
{'highly suspicious' if score > 70 else 'moderately uncertain' if score > 40 else 'low risk'}.
""")

                # Save history
                st.session_state.history.append({
                    "time": datetime.now().strftime("%H:%M"),
                    "text": text,
                    "result": "Fake" if result else "Genuine",
                    "score": score,
                    "confidence": confidence,
                    "company": entities['company'],
                    "email": entities['emails'],
                    "phone": entities['phones'],
                    "locations": entities['locations']
                })

    # ================================================================
    # PAGE 2 — INTERNSHIP ADVISORY
    # ================================================================
    elif page == "Internship Advisory":
        st.title("Internship Advisory & Recommendation System")

        if len(st.session_state.history) == 0:
            st.warning("No analysis data available. Please analyze an internship first.")
        else:
            latest = st.session_state.history[-1]

            st.subheader("Latest Analysis Summary")
            st.write(f"**Result:** {latest['result']}")
            st.write(f"**Risk Score:** {latest['score']}")
            st.write(f"**Confidence:** {latest['confidence']}%")

            st.subheader("Professional Advisory")
            if latest['result'] == "Fake":
                st.markdown("""
                Based on system analysis, this internship exhibits strong indicators of fraudulent activity.

                **Do not** share personal information, make any payment, or communicate through
                unofficial channels like personal emails or messaging apps.

                Verify opportunities through official company websites and trusted job platforms.
                """)
            else:
                st.markdown("""
                The internship appears legitimate based on current evaluation metrics.

                Still recommended: verify the company's official presence, confirm offer details,
                and ensure proper onboarding procedures are followed.
                """)

            st.subheader("Smart Recommendations")
            if latest['score'] > 70:
                st.markdown("""
                • Focus on internships listed on verified platforms like LinkedIn and company portals
                • Avoid opportunities requiring upfront payment
                • Prefer structured hiring processes with interviews and documentation
                """)
            else:
                st.markdown("""
                • Continue applying to structured internship programs
                • Build a portfolio to improve selection chances
                • Target companies with strong digital presence
                """)

            st.subheader("Detected Company Insights")
            st.write(f"**Company:** {latest['company']}")
            st.write(f"**Email:** {latest['email']}")
            st.write(f"**Phone:** {latest['phone']}")
            st.write(f"**Locations:** {latest.get('locations', ['Not Detected'])}")

    # ================================================================
    # PAGE 3 — CERTIFICATE VERIFICATION (NEW)
    # ================================================================
    elif page == "Certificate Verification":
        st.title("📜 Certificate & Offer Letter Verification")
        st.markdown("Upload or paste your internship certificate or offer letter to verify its authenticity.")

        tab1, tab2, tab3 = st.tabs(["📷 Upload Image (OCR)", "📄 Upload PDF", "✍️ Paste Text"])

        cert_text = ""

        with tab1:
            cert_image = st.file_uploader("Upload Certificate Image", type=["png", "jpg", "jpeg"], key="cert_img")
            if cert_image:
                img = Image.open(cert_image)
                st.image(img, caption="Uploaded Certificate", use_column_width=True)
                cert_text = pytesseract.image_to_string(img)
                st.text_area("Extracted Text (OCR)", cert_text, height=200)

        with tab2:
            cert_pdf = st.file_uploader("Upload Certificate PDF", type=["pdf"], key="cert_pdf")
            if cert_pdf:
                cert_text = extract_text_from_pdf(cert_pdf)
                st.text_area("Extracted Text (PDF)", cert_text, height=200)

        with tab3:
            cert_text = st.text_area("Paste Certificate / Offer Letter Text Here", height=250)

        if st.button("🔍 Verify Certificate"):
            if not cert_text.strip():
                st.warning("Please provide certificate text via image, PDF, or manual paste.")
            else:
                vr = verify_certificate(cert_text)

                # Show type badge
                st.markdown(f"### Document Type Detected: `{vr['type']}`")

                # If course certificate
                if not vr["is_internship"]:
                    st.info(vr["summary"])
                    st.stop()

                # Risk color
                risk_color = {"LOW": "#3fb950", "HIGH": "#f85149", "N/A": "#8b949e"}.get(vr["risk"], "#8b949e")

                st.markdown(f"""
                <div style="background:#161b22; padding:25px; border-radius:12px;
                     border-left:6px solid {risk_color}; color:white; margin-bottom:20px;">

                <h3 style="color:white;">{vr['summary']}</h3>

                <hr style="border:1px solid #30363d;">

                <h4 style="color:#3fb950;">📋 Verification Details</h4>
                <table style="width:100%; color:white; font-size:15px;">
                <tr><td><b>Company Detected</b></td><td>{vr['company']}</td></tr>
                <tr><td><b>Risk Level</b></td><td><span style="color:{risk_color};">{vr['risk']}</span></td></tr>
                <tr><td><b>Genuine Signals Found</b></td><td>{len(vr.get('genuine_signals', []))}</td></tr>
                <tr><td><b>Fake Signals Found</b></td><td>{len(vr.get('fake_signals', []))}</td></tr>
                <tr><td><b>Certificate ID/No</b></td>
                    <td>{'✅ ' + vr['cert_id'] if vr.get('cert_id') else '❌ Not Found'}</td></tr>
                <tr><td><b>QR / Verification Link</b></td>
                    <td>{'✅ Present' if vr.get('has_qr') else '❌ Not Found'}</td></tr>
                </table>
                </div>
                """, unsafe_allow_html=True)

                if vr.get("genuine_signals"):
                    st.markdown("**✅ Genuine Signals Detected:**")
                    for s in vr["genuine_signals"]:
                        st.markdown(f"- {s}")

                if vr.get("fake_signals"):
                    st.markdown("**🚨 Suspicious Signals Detected:**")
                    for s in vr["fake_signals"]:
                        st.markdown(f"- {s}")

                if not vr.get("has_verification"):
                    st.warning(
                        "⚠️ No certificate ID or QR code found in this document. "
                        "Genuine certificates usually carry a verifiable ID or QR code. "
                        "Verify directly with the issuing company via their official website."
                    )
                else:
                    st.success("✅ Verification proof (Certificate ID / QR code) detected in document.")

    # ================================================================
    # PAGE 4 — CHATBOT ASSISTANT (NEW)
    # ================================================================
    elif page == "Chatbot Assistant":
        st.title("🤖 Internship Safety Chatbot")
        st.markdown("Ask me anything about internship scams, resumes, interviews, or career advice!")

        # Chat display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"<div class='chat-user'>👤 {msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bot'>🤖 {msg['content']}</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Suggested questions
        st.markdown("**💡 Quick Questions:**")
        qcol1, qcol2, qcol3 = st.columns(3)
        quick_questions = [
            "What are signs of a fake internship?",
            "How do I write a good resume?",
            "How do I prepare for an interview?",
            "Is work from home internship safe?",
            "What skills should I learn as a fresher?",
            "Why are fees a scam?"
        ]
        for i, q in enumerate(quick_questions):
            col = [qcol1, qcol2, qcol3][i % 3]
            if col.button(q, key=f"quick_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": q})
                response = chatbot_response(q)
                st.session_state.chat_history.append({"role": "bot", "content": response})
                st.rerun()

        # User input
        user_input = st.text_input("Type your question here...", key="chat_input", placeholder="e.g. How do I spot a fake internship?")
        send_col, clear_col = st.columns([3, 1])

        with send_col:
            if st.button("Send 💬"):
                if user_input.strip():
                    st.session_state.chat_history.append({"role": "user", "content": user_input})
                    response = chatbot_response(user_input)
                    st.session_state.chat_history.append({"role": "bot", "content": response})
                    st.rerun()

        with clear_col:
            if st.button("Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()

    # ================================================================
    # PAGE 5 — HISTORY
    # ================================================================
    elif page == "History":
        st.title("History")

        for item in reversed(st.session_state.history):
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.write(f"**Time:** {item['time']}")
            st.write(f"**Result:** {item['result']}")
            st.write(f"**Risk Score:** {item['score']}")
            st.write(f"**Confidence:** {item['confidence']}%")
            st.write(f"**Company:** {item['company']}")
            st.write(f"**Email:** {item['email']}")
            st.write(f"**Phone:** {item['phone']}")
            st.write(f"**Locations:** {item.get('locations', ['Not Detected'])}")
            st.write("**Description:**")
            st.write(item['text'])
            st.markdown("</div>", unsafe_allow_html=True)

        def create_pdf():
            doc = SimpleDocTemplate("history.pdf")
            styles = getSampleStyleSheet()
            content = []
            for item in st.session_state.history:
                content.append(Paragraph(f"<b>Time:</b> {item['time']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Result:</b> {item['result']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Risk Score:</b> {item['score']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Confidence:</b> {item['confidence']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Company:</b> {item['company']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Email:</b> {str(item['email'])}", styles["Normal"]))
                content.append(Paragraph(f"<b>Phone:</b> {str(item['phone'])}", styles["Normal"]))
                content.append(Paragraph(f"<b>Locations:</b> {str(item.get('locations', []))}", styles["Normal"]))
                content.append(Paragraph(f"<b>Description:</b> {item['text']}", styles["Normal"]))
                content.append(Spacer(1, 15))
            doc.build(content)

        create_pdf()
        with open("history.pdf", "rb") as f:
            st.download_button("Download Full Report", f, file_name="history.pdf")