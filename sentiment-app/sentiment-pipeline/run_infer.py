import os
import boto3
import pandas as pd
import tarfile
import joblib
import json
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv

# Load .env if running locally (optional)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# 🔧 Environment Variables
bucket = os.environ.get("BUCKET_NAME", "mlops-sentiment-app")
user = os.environ.get("USER_NAME")
filename = "served.csv"

if not user:
    raise ValueError("❌ USER_NAME is not set.")

# S3 paths
input_key = f"processed/{user}/processed.csv"
output_key = f"output/{user}/{filename}"
summary_key = f"metadata/{user}/inference_summary.json"
model_key = "models/model.tar.gz"

s3 = boto3.client("s3")

# 📦 Load model from tar.gz
def load_model():
    obj = s3.get_object(Bucket=bucket, Key=model_key)
    tar_bytes = BytesIO(obj['Body'].read())

    with tarfile.open(fileobj=tar_bytes, mode='r:gz') as tar:
        model_file = [m for m in tar.getnames() if m.endswith(".pkl")][0]
        extracted = tar.extractfile(model_file)
        return joblib.load(extracted)

# 📥 Load processed data
def load_processed_data():
    obj = s3.get_object(Bucket=bucket, Key=input_key)
    return pd.read_csv(obj['Body'])

# 📊 Generate metrics summary
def generate_summary(df_pred):
    sentiment_counts = df_pred['predicted_label'].value_counts().to_dict()
    avg_len = df_pred['review_clean'].apply(lambda x: len(str(x))).mean()
    short_count = df_pred['short_review'].sum() if 'short_review' in df_pred.columns else 0

    top_pos = df_pred[df_pred['predicted_label'] == 'positive'].nlargest(5, 'score', default=0)['review'].tolist()
    top_neg = df_pred[df_pred['predicted_label'] == 'negative'].nlargest(5, 'score', default=0)['review'].tolist()

    return {
        "positive_reviews": sentiment_counts.get("positive", 0),
        "negative_reviews": sentiment_counts.get("negative", 0),
        "short_reviews_flagged": int(short_count),
        "average_length": round(avg_len, 2),
        "top_positive": top_pos,
        "top_negative": top_neg,
        "timestamp": datetime.now().isoformat()
    }

# 🚀 Run inference
def run_inference():
    print(f"📥 Loading {input_key}...")
    df = load_processed_data()

    print("📦 Loading model...")
    model = load_model()

    print("🔮 Predicting sentiment...")
    df["predicted_label"] = model.predict(df["review_clean"])

    try:
        df["score"] = model.predict_proba(df["review_clean"]).max(axis=1)
    except:
        df["score"] = 0.0

    # Upload predictions
    print(f"💾 Saving to {output_key}...")
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    s3.put_object(Bucket=bucket, Key=output_key, Body=csv_buffer.getvalue(), ContentType="text/csv")

    # Upload summary
    print(f"📊 Saving metrics to {summary_key}...")
    summary = generate_summary(df)
    s3.put_object(Bucket=bucket, Key=summary_key, Body=json.dumps(summary, indent=2), ContentType="application/json")

    print("✅ Inference complete.")

# 🔁 Entry point
if __name__ == "__main__":
    run_inference()
