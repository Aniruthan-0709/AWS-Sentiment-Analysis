import streamlit as st
import pandas as pd
import boto3
import json
import matplotlib.pyplot as plt
from io import BytesIO

BUCKET_NAME = "mlops-sentiment-app"

# ----------------------------
# 📥 Load Files from S3
# ----------------------------
def load_csv_from_s3(user):
    s3 = boto3.client("s3")
    key = f"output/{user}/served.csv"
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return pd.read_csv(obj['Body'])

def load_json_from_s3(user):
    s3 = boto3.client("s3")
    key = f"metadata/{user}/inference_summary.json"
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return json.load(obj['Body'])

# ----------------------------
# 🔐 Ensure Logged In
# ----------------------------
if "user" not in st.session_state:
    st.error("🔒 Please log in first.")
    st.stop()

user = st.session_state["user"]

st.title("📊 Sentiment Analysis Dashboard")
st.write(f"👤 User: `{user}`")

# ----------------------------
# 📥 Load Data from S3
# ----------------------------
try:
    df = load_csv_from_s3(user)
    summary = load_json_from_s3(user)
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

# ----------------------------
# 📊 Summary Metrics
# ----------------------------
st.subheader("🔎 Summary")
st.metric("Total Reviews", summary.get("total_reviews", len(df)))
st.metric("Positive Reviews", summary.get("positive_reviews", 0))
st.metric("Negative Reviews", summary.get("negative_reviews", 0))
st.metric("Short Reviews Flagged", summary.get("short_reviews_flagged", 0))
st.metric("Avg Review Length", summary.get("average_review_length", 0))

# ----------------------------
# 📈 Sentiment Chart
# ----------------------------
st.subheader("📈 Sentiment Distribution")

fig1, ax1 = plt.subplots()
df["prediction"].value_counts().plot(kind="bar", ax=ax1)
ax1.set_ylabel("Review Count")
ax1.set_xlabel("Sentiment")
st.pyplot(fig1)

# ----------------------------
# 📊 Review Length Distribution
# ----------------------------
st.subheader("📝 Review Length Distribution")

fig2, ax2 = plt.subplots()
df["review"].dropna().apply(lambda x: len(str(x))).plot.hist(bins=30, ax=ax2)
ax2.set_xlabel("Review Length (characters)")
ax2.set_ylabel("Frequency")
st.pyplot(fig2)

# ----------------------------
# 🏆 Top Reviews
# ----------------------------
st.subheader("🌟 Top 5 Positive Reviews")
for review in summary.get("top_positive_reviews", []):
    st.success(f"✅ {review}")

st.subheader("💢 Top 5 Negative Reviews")
for review in summary.get("top_negative_reviews", []):
    st.error(f"❌ {review}")
