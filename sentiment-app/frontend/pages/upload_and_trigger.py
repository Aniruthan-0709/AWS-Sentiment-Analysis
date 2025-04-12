import streamlit as st
import boto3
import requests
import os
import json
import time
from datetime import datetime
from io import BytesIO

API_URL = "http://localhost:8001"
BUCKET_NAME = "mlops-sentiment-app"

# ---------------------------
# 🚀 Upload File to S3
# ---------------------------
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
        return None

# ---------------------------
# 🔄 Reset pipeline status
# ---------------------------
def reset_pipeline_status(user):
    s3 = boto3.client("s3")
    key = f"metadata/{user}/pipeline_status.json"
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps({"status": "pending"}),
            ContentType="application/json"
        )
        print("🔄 Reset pipeline status to 'pending'")
    except Exception as e:
        st.error(f"❌ Failed to reset status: {e}")

# ---------------------------
# 🛰️ Poll until expected or failed
# ---------------------------
def check_status(user, expected_status, timeout=600):
    s3 = boto3.client("s3")
    key = f"metadata/{user}/pipeline_status.json"
    start_time = time.time()
    interval = 5
    max_checks = timeout // interval

    for attempt in range(max_checks):
        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            status = json.loads(obj["Body"].read().decode("utf-8")).get("status", "")
            print(f"📡 [{attempt+1}/{max_checks}] Status: {status}")

            if status == expected_status:
                return True
            elif status == "failed":
                st.error("❌ Pipeline failed during execution.")
                return False
        except:
            pass
        time.sleep(interval)

    return False

# ---------------------------
# 🧠 Trigger pipeline via FastAPI
# ---------------------------
def trigger_pipeline(filename, user):
    try:
        payload = {"filename": filename, "user": user}
        response = requests.post(f"{API_URL}/trigger_pipeline", json=payload)
        print("🔁 Pipeline Trigger Response:", response.status_code, response.text)
        return response.status_code == 200
    except Exception as e:
        st.error(f"❌ Failed to trigger pipeline: {e}")
        return False

# ---------------------------
# 📊 Call Dashboard Generation
# ---------------------------
def generate_dashboard(filename, user):
    try:
        payload = {"filename": filename, "user": user}
        with st.spinner("📊 Creating dashboard..."):
            response = requests.post(f"{API_URL}/generate_dashboard", json=payload)
        if response.status_code == 200:
            st.success("✅ Dashboard summary generated.")
        else:
            st.warning(f"⚠️ Dashboard not ready: {response.text}")
    except Exception as e:
        st.error(f"❌ Failed to generate dashboard: {e}")

# ---------------------------
# 🖥️ Streamlit UI
# ---------------------------
st.title("📤 Upload & Analyze Sentiment")
st.write(f"👤 Logged in as: `{st.session_state.get('user', 'unknown')}`")
st.warning("⚠️ This pipeline may take 5–10 minutes. Please do not refresh or close this page.")

uploaded_file = st.file_uploader("Upload your CSV (max 200MB)", type=["csv"])

if uploaded_file and st.button("🚀 Get Sentiment"):
    user = st.session_state.get("user", "")
    s3_key = upload_file_to_s3(uploaded_file, user)

    if s3_key:
        filename = os.path.basename(s3_key)

        # Reset old pipeline status
        reset_pipeline_status(user)

        st.info("⚙️ Triggering ECS pipeline...")
        if trigger_pipeline(filename, user):
            st.success("✅ Pipeline triggered.")
            start_time = time.time()

            # -------- Preprocessing Stage --------
            with st.spinner("⏳ Preprocessing your data..."):
                if st.button("❌ Cancel", key="cancel_pre"):
                    st.warning("🚪 Pipeline cancelled.")
                    st.stop()
                preprocessing_done = check_status(user, "preprocessing_complete", timeout=600)

            if preprocessing_done:
                st.success("✅ Preprocessing complete! Starting inference...")

                # -------- Inference Stage --------
                with st.spinner("🧠 Running model inference..."):
                    if st.button("❌ Cancel", key="cancel_infer"):
                        st.warning("🚪 Pipeline cancelled.")
                        st.stop()
                    inference_done = check_status(user, "inference_complete", timeout=600)

                if inference_done:
                    st.success("🎉 Inference complete!")

                    elapsed = int(time.time() - start_time)
                    st.info(f"⏱️ Total time taken: {elapsed // 60} min {elapsed % 60} sec")

                    if st.button("📊 Create Dashboard"):
                        generate_dashboard(filename, user)
                        st.success("✅ Dashboard ready!")
                        st.switch_page("pages/dashboard.py")
                else:
                    st.error("❌ Inference failed or timed out.")
            else:
                st.error("❌ Preprocessing failed or timed out.")
