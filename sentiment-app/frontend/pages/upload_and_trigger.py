import streamlit as st
import boto3
import requests
from datetime import datetime
import pandas as pd
import io

API_URL = "http://localhost:8000"
BUCKET_NAME = "mlops-sentiment-app"

# ✅ Upload and keep a safe copy in memory
def upload_file_to_s3_and_buffer(uploaded_file, username):
    s3 = boto3.client("s3")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    cleaned_filename = f"{timestamp}_{uploaded_file.name}"
    s3_key = f"uploads/raw/{username}/{cleaned_filename}"

    try:
        # ✅ Make a fresh memory copy
        file_bytes = uploaded_file.read()
        buffer_for_upload = io.BytesIO(file_bytes)
        buffer_for_preview = io.BytesIO(file_bytes)

        # Upload to S3
        s3.upload_fileobj(buffer_for_upload, BUCKET_NAME, s3_key)
        st.success(f"✅ Uploaded to S3: `{s3_key}`")

        return buffer_for_preview, cleaned_filename
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return None, None

# ✅ Trigger ECS via FastAPI
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

# 🔐 Ensure login
if "user" not in st.session_state:
    st.warning("🔒 Please log in first.")
    st.stop()

# 🖼️ Page content
st.title("📤 Upload Your CSV for Sentiment Preprocessing")
st.write(f"👤 Logged in as: `{st.session_state['user']}`")

uploaded_file = st.file_uploader("Upload a CSV file (max 200 MB)", type=["csv"])

if uploaded_file:
    preview_buffer, cleaned_filename = upload_file_to_s3_and_buffer(uploaded_file, st.session_state["user"])

    if preview_buffer:
        try:
            df_preview = pd.read_csv(preview_buffer, nrows=5)
            st.subheader("👁️ Sample of Uploaded File:")
            st.dataframe(df_preview)
        except Exception as e:
            st.warning(f"⚠️ Could not preview file: {e}")

        st.markdown("---")
        st.info("📌 Ready to preprocess the uploaded file.")
        if st.button("🚀 Start Preprocessing"):
            trigger_ecs_task(cleaned_filename, st.session_state["user"])
