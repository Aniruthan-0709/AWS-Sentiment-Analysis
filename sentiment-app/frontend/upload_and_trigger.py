import streamlit as st
import boto3
import requests
from datetime import datetime
import pandas as pd

API_URL = "http://localhost:8000"
BUCKET_NAME = "mlops-sentiment-app"

def upload_file_to_s3(uploaded_file, username):
    s3 = boto3.client("s3")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    s3_key = f"uploads/raw/{username}/{timestamp}_{uploaded_file.name}"

    try:
        s3.upload_fileobj(uploaded_file, BUCKET_NAME, s3_key)
        st.success(f"✅ Uploaded to S3: `{s3_key}`")
        return s3_key, f"{timestamp}_{uploaded_file.name}"
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return None, None

def trigger_ecs_task(filename, username):
    try:
        response = requests.post(
            f"{API_URL}/trigger_preprocess",
            json={"filename": filename, "user": username}
        )

        if response.status_code == 200:
            task_arn = response.json().get("task_arn")
            st.success("🚀 Preprocessing Task Triggered")
            st.write(f"📦 Task ARN: `{task_arn}`")
        else:
            st.error(f"❌ ECS trigger failed: {response.json().get('detail')}")
    except Exception as e:
        st.error(f"❌ ECS trigger error: {e}")

# 🔐 Check login
if "user" not in st.session_state:
    st.warning("🔒 Please log in first.")
    st.stop()

st.title("📤 Upload Your CSV for Sentiment Processing")
st.write(f"👤 Logged in as: `{st.session_state['user']}`")

uploaded_file = st.file_uploader("Upload a CSV file (max 2GB)", type=["csv"])

if uploaded_file:
    s3_key, cleaned_filename = upload_file_to_s3(uploaded_file, st.session_state["user"])

    # 👀 Preview uploaded file locally
    try:
        df_preview = pd.read_csv(uploaded_file, nrows=5)
        st.subheader("👁️ Sample of Uploaded File:")
        st.dataframe(df_preview)
    except Exception as e:
        st.warning(f"⚠️ Could not preview file: {e}")

    # ✅ Ask user to trigger manually
    st.markdown("---")
    st.info("📌 Ready to preprocess the uploaded file.")
    if st.button("🚀 Start Preprocessing"):
        trigger_ecs_task(cleaned_filename, st.session_state["user"])
