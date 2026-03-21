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

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

st.set_page_config(layout="wide")

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "history" not in st.session_state:
    st.session_state.history = []
if "text" not in st.session_state:
    st.session_state.text = ""

# ---------------- CSS ----------------
st.markdown("""
<style>
body {background-color:#0d1117;color:white;}

.left-panel {
    background:#161b22;
    padding:50px;
    border-radius:12px;
    color:white;   /* FIX: makes all text white */
}

.left-panel p {
    color:white !important;  /* FIX: override grey text */
}

.highlight {
    color:#3fb950;
    font-weight:bold;
}

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

input, textarea {
    background:white !important;
    color:black !important;
}

.stButton > button {
    width:100%;
    background:#238636;
    color:white;
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:

    col1, col2 = st.columns([1.3,1])

    with col1:
        st.markdown("""
        <div class='left-panel'>
        <h1>AI Internship Analyzer</h1>
        <p>Advanced <span class='highlight'>AI-based system</span> to detect internship scams.</p>

        <br>

        <p>✔ Detect fraudulent offers</p>
        <p>✔ Analyze risk patterns</p>
        <p>✔ Verify company signals</p>
        <p>✔ Generate professional reports</p>

        <br>

        <p><span class='highlight'>Built for students & job seekers</span></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)

        option = st.radio("", ["Login", "Signup"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if option == "Login":
            if st.button("Login"):
                if login(email, password):
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        else:
            if st.button("Signup"):
                success, msg = signup(email, password)
                if success:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("</div>", unsafe_allow_html=True)

# ---------------- MAIN ----------------
else:

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("", ["Dashboard", "Internship Advisory", "History"])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ---------------- DASHBOARD ----------------
    if page == "Dashboard":

        st.title("Internship Analysis Dashboard")

        colA, colB = st.columns([1,2])

        # -------- LEFT SYSTEM MODULES --------
        with colA:
            st.markdown("""
            <div class='module-box'>
            <h3>System Modules</h3>
            ✔ ML Classification Engine<br>
            ✔ Risk Assessment Engine<br>
            ✔ OCR Text Extraction<br>
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
            This system is designed to help users identify 
            <span style='color:#3fb950;'>potential internship scams</span> 
            using AI-driven insights and structured evaluation.
            </div>
            """, unsafe_allow_html=True)

        # -------- RIGHT MAIN --------
        with colB:

            # SAMPLE INPUTS
            st.subheader("Sample Inputs")
            c1, c2 = st.columns(2)

            if c1.button("Fake Example"):
                st.session_state.text = "Pay registration fee to start internship immediately. Limited seats apply now!"
                st.rerun()

            if c2.button("Genuine Example"):
                st.session_state.text = "We are offering a paid internship with structured training and official onboarding process."
                st.rerun()

            # OCR Upload
            image = st.file_uploader("Upload Screenshot", type=["png","jpg"])

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
                st.write("DEBUG Prediction:", result)
                st.write("DEBUG Score:", score)
                # -------- FINAL RESULT --------
                st.subheader("Final Prediction")

                if result == 1:
                    st.error(
                        "⚠️ This internship is predicted to be FRAUDULENT based on multiple high-risk indicators identified in the analysis.")
                else:
                    st.success(
                        "✅ This internship appears to be GENUINE based on the evaluated parameters and model prediction.")
                # -------- RISK SCORECARD --------
                st.subheader("Risk Assessment Summary")

                # Risk level logic
                if score <= 30:
                    risk_level = "LOW RISK"
                    color = "#3fb950"
                elif score <= 70:
                    risk_level = "MODERATE RISK"
                    color = "#d29922"
                else:
                    risk_level = "HIGH RISK"
                    color = "#f85149"

                # Numeric indicators
                payment_flag = "Yes" if pay_risk else "No"
                urgency_flag = "Yes" if urg_risk else "No"
                contact_flag = "Yes" if cont_risk else "No"

                st.markdown(f"""
                <div style="background:#161b22; padding:25px; border-radius:12px; border-left:6px solid {color}; color:white;">

                <h2 style="color:white; margin-bottom:10px;">Risk Score: {score}/100</h2>

                <p style="font-size:18px;">
                <b>Status:</b> <span style="color:{color};">{risk_level}</span>
                </p>

                <hr style="border:1px solid #30363d;">

                <h4 style="color:#3fb950;">Risk Indicators</h4>

                <table style="width:100%; color:white; font-size:15px;">
                <tr>
                <td>Payment Request</td>
                <td><b>{payment_flag}</b></td>
                </tr>
                <tr>
                <td>Urgency Pressure</td>
                <td><b>{urgency_flag}</b></td>
                </tr>
                <tr>
                <td>Unverified Contact</td>
                <td><b>{contact_flag}</b></td>
                </tr>
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
                            'axis': {'range': [0,100]},
                            'steps': [
                                {'range': [0,30], 'color': "green"},
                                {'range': [30,70], 'color': "yellow"},
                                {'range': [70,100], 'color': "red"}
                            ]
                        }
                    ))
                    return fig

                g1, g2 = st.columns(2)
                g1.plotly_chart(gauge(score, "Risk Score"), use_container_width=True)
                g2.plotly_chart(gauge(confidence, "Confidence"), use_container_width=True)

                # -------- EXPLANATION --------
                st.subheader("Analysis Explanation")
                st.write(f"""
The internship posting has been evaluated using a hybrid machine learning and rule-based system. 
Key indicators such as {", ".join(reasons[:6])} were detected, which strongly influence the classification.

The computed risk score of {score}/100 suggests that this opportunity is 
{'highly suspicious' if score>70 else 'moderately uncertain' if score>40 else 'low risk'}.

Patterns such as payment requests, urgency pressure, and lack of formal structure significantly impact this decision.
""")

                # -------- COMPANY DETECTION --------
                st.subheader("Company Detection")

                email_match = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
                phone_match = re.findall(r"\b\d{10}\b", text)
                company_match = re.search(r"(?:at|from)\s([A-Z][A-Za-z0-9& ]+)", text)

                company = company_match.group(1) if company_match else "Unknown"

                st.write(f"Detected Company: {company}")
                st.write(f"Email: {email_match if email_match else 'None'}")
                st.write(f"Phone: {phone_match if phone_match else 'None'}")

                # SAVE HISTORY
                st.session_state.history.append({
                    "time": datetime.now().strftime("%H:%M"),
                    "text": text,
                    "result": "Fake" if result else "Genuine",
                    "score": score,
                    "confidence": confidence,
                    "company": company,
                    "email": email_match,
                    "phone": phone_match
                })
    # ---------------- ADVISORY PAGE ----------------
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
                Based on the system analysis, the internship exhibits strong indicators of fraudulent activity. 

                It is recommended that you avoid engaging with this opportunity. Do not share personal information, 
                avoid making any payments, and refrain from communicating through unofficial channels such as personal emails or messaging apps.

                You are advised to verify opportunities through official company websites and trusted job platforms.
                """)
            else:
                st.markdown("""
                The internship appears to be legitimate based on current evaluation metrics. 

                However, it is still recommended to perform due diligence by verifying the company’s official presence, 
                confirming offer details, and ensuring proper onboarding procedures are followed.

                Proceed cautiously while maintaining standard professional verification practices.
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
            st.write(f"Company: {latest['company']}")
            st.write(f"Email: {latest['email']}")
            st.write(f"Phone: {latest['phone']}")
    # ---------------- HISTORY ----------------
    elif page == "History":

        st.title("History")

        for item in reversed(st.session_state.history):
            for item in reversed(st.session_state.history):
                st.markdown("<div class='card'>", unsafe_allow_html=True)

                st.write(f"**Time:** {item['time']}")
                st.write(f"**Result:** {item['result']}")
                st.write(f"**Risk Score:** {item['score']}")
                st.write(f"**Confidence:** {item['confidence']}%")
                st.write(f"**Company:** {item['company']}")
                st.write(f"**Email:** {item['email']}")
                st.write(f"**Phone:** {item['phone']}")
                st.write("**Description:**")
                st.write(item['text'])

                st.markdown("</div>", unsafe_allow_html=True)

        # PDF FIXED (NO EXTRA </div>)
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
                content.append(Paragraph(f"<b>Email:</b> {item['email']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Phone:</b> {item['phone']}", styles["Normal"]))
                content.append(Paragraph(f"<b>Description:</b> {item['text']}", styles["Normal"]))
                content.append(Spacer(1,15))

            doc.build(content)

        create_pdf()

        with open("history.pdf","rb") as f:
            st.download_button("Download Full Report", f, file_name="history.pdf")