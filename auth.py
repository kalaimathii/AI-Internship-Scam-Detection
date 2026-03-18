import pandas as pd
import os

FILE = "users.csv"

def load_users():
    if not os.path.exists(FILE):
        df = pd.DataFrame(columns=["email", "password"])
        df.to_csv(FILE, index=False)
    return pd.read_csv(FILE)

def signup(email, password):
    df = load_users()

    if email in df["email"].values:
        return False, "User already exists"

    new_user = pd.DataFrame([[email, password]], columns=["email", "password"])
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(FILE, index=False)

    return True, "Signup successful"

def login(email, password):
    df = load_users()

    user = df[(df["email"] == email) & (df["password"] == password)]

    if not user.empty:
        return True
    return False