import pickle
import re

# ---------------- LOAD MODEL ----------------
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# ---------------- PREDICTION FUNCTION ----------------
def predict_internship(text):
    text_lower = text.lower()

    # ================= RULE-BASED OVERRIDE =================

    # ✅ STRONG GENUINE SIGNALS
    if "paid internship" in text_lower:
        return 0
    if "stipend" in text_lower and "pay" not in text_lower:
        return 0
    if "no fee" in text_lower or "no registration fee" in text_lower:
        return 0
    if "company pays" in text_lower:
        return 0
    if "salary" in text_lower and "fee" not in text_lower:
        return 0

    # ❌ STRONG FAKE SIGNALS
    if "registration fee" in text_lower:
        return 1
    if "pay fee" in text_lower:
        return 1
    if "deposit" in text_lower:
        return 1
    if "send money" in text_lower:
        return 1
    if "payment required" in text_lower:
        return 1

    # ================= ML MODEL =================
    vector = vectorizer.transform([text])
    prediction = model.predict(vector)[0]

    return prediction


# ---------------- RISK SCORE FUNCTION ----------------
def risk_score(text):
    text_lower = text.lower()

    score = 0
    reasons = []

    # ---------------- PAYMENT RISK ----------------
    payment_keywords = [
        "fee", "payment", "pay", "registration", "deposit",
        "amount", "charges", "money"
    ]

    pay_risk = any(word in text_lower for word in payment_keywords)

    if pay_risk:
        # 🔴 BUT avoid false positive for "paid internship"
        if "paid internship" not in text_lower and "stipend" not in text_lower:
            score += 40
            reasons.append("Payment request detected")

    # ---------------- URGENCY RISK ----------------
    urgency_keywords = [
        "urgent", "immediate", "limited", "hurry",
        "apply now", "fast", "last date"
    ]

    urg_risk = any(word in text_lower for word in urgency_keywords)

    if urg_risk:
        score += 25
        reasons.append("Urgency pressure detected")

    # ---------------- CONTACT RISK ----------------
    contact_keywords = [
        "whatsapp", "telegram", "dm", "personal email"
    ]

    cont_risk = any(word in text_lower for word in contact_keywords)

    if cont_risk:
        score += 20
        reasons.append("Unverified contact method")

    # ---------------- GENUINE SIGNAL REDUCTION ----------------
    if "paid internship" in text_lower or "stipend" in text_lower:
        score -= 25
        reasons.append("Legitimate stipend structure")

    if "official website" in text_lower or "careers page" in text_lower:
        score -= 15
        reasons.append("Official application channel")

    if "interview" in text_lower:
        score -= 10
        reasons.append("Structured hiring process")

    # ---------------- CLEAN SCORE ----------------
    score = max(0, min(score, 100))

    return score, reasons, pay_risk, urg_risk, cont_risk