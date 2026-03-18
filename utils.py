import pickle

# Load model and vectorizer
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

def predict_internship(text):
    text_vec = vectorizer.transform([text])
    result = model.predict(text_vec)[0]
    return result


def risk_score(text):
    score = 0
    reasons = []

    text_lower = text.lower()

    payment_words = ["fee", "payment", "pay", "registration"]
    urgency_words = ["urgent", "immediate", "limited", "hurry"]
    contact_words = ["whatsapp", "telegram", "dm"]

    payment_risk = 0
    urgency_risk = 0
    contact_risk = 0

    # Payment risk
    for word in payment_words:
        if word in text_lower:
            payment_risk += 20
            reasons.append(f"Payment related word detected: {word}")

    # Urgency risk
    for word in urgency_words:
        if word in text_lower:
            urgency_risk += 15
            reasons.append(f"Urgency word detected: {word}")

    # Contact risk
    for word in contact_words:
        if word in text_lower:
            contact_risk += 20
            reasons.append(f"Unofficial contact method: {word}")

    score = payment_risk + urgency_risk + contact_risk

    if score > 100:
        score = 100

    return score, reasons, payment_risk, urgency_risk, contact_risk