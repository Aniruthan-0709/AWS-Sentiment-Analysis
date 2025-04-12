import streamlit as st
import requests

API_URL = "http://localhost:8000"  # Backend FastAPI URL

def login():
    st.title("🔐 Login to Sentiment Analysis App")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        print("🧪 Submitting login to FastAPI:")
        print(f"   ▶ Username: {username}")
        print(f"   ▶ Password: {password}")

        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"username": username, "password": password}
            )

            print("🔁 Response status:", response.status_code)
            print("🔁 Response body:", response.text)

            if response.status_code == 200:
                st.success("✅ Login successful!")
                st.session_state["user"] = username
                st.session_state["tokens"] = response.json()["tokens"]

                # ✅ Redirect to multipage-compatible upload page
                st.switch_page("pages/upload_and_trigger.py")

            else:
                st.error("❌ Login failed. Check credentials.")
        except Exception as e:
            st.error(f"🚨 Request failed: {e}")

# 👇 Page logic
if "user" not in st.session_state:
    login()
else:
    # Already logged in — redirect
    st.switch_page("pages/upload_and_trigger.py")

