import streamlit as st
import boto3
import requests
import os
from datetime import datetime
from io import BytesIO

API_URL = "http://localhost:8000"
BUCKET_NAME = "mlops-sentiment-app"

def upload_file_to_s3(uploaded_file, username):
    s3 = boto3.client("s3")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    s3_key = f"uploads/raw/{username}/{timestamp}_{uploaded_file.name}"

    try:
        file_content = uploaded_file.read()
        s3.upload_fileobj(BytesIO(file_content), BUCKET_NAME, s3_key)
        st.session_state["uploaded_filename"] = f"{timestamp}_{uploaded_file.name}"
        print(f"✅ Uploaded file to S3 as {s3_key}")
        return s3_key
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        print("❌ Upload error:", e)
        return None

def trigger_pipeline(filename, user):
    payload = {"filename": filename, "user": user}
    print(f"📤 Sending request to trigger_pipeline with: {payload}")

    try:
        response = requests.post(f"{API_URL}/trigger_pipeline", json=payload)
        print("🔁 Pipeline Trigger Response:", response.status_code, response.text)

        if response.status_code == 200:
            return True
        else:
            st.error(f"❌ Pipeline failed: {response.text}")
            return False
    except Exception as e:
        st.error(f"❌ Failed to trigger ECS: {e}")
        print("❌ Request Exception:", e)
        return False

# ---------------------------
# 🖥️ Streamlit UI
# ---------------------------
st.title("📤 Upload & Analyze Sentiment")
st.write(f"👤 Logged in as: `{st.session_state.get('user', 'unknown')}`")

uploaded_file = st.file_uploader("Upload your CSV (max 200MB)", type=["csv"])

if uploaded_file and st.button("🚀 Get Sentiment"):
    user = st.session_state.get("user", "")
    print(f"📁 User = {user}")

    s3_key = upload_file_to_s3(uploaded_file, user)
    if s3_key:
        filename = os.path.basename(s3_key)
        st.info("⚙️ Triggering ECS pipeline (cleaning + inference)...")

        success = trigger_pipeline(filename=filename, user=user)

        if success:
            st.success("✅ Sentiment pipeline launched successfully!")
            st.info("⏳ Please wait a minute and check your dashboard.")
            if st.button("📊 View Dashboard"):
                st.switch_page("pages/dashboard.py")
