import os
import boto3
import json
import pandas as pd
from io import StringIO

# ✅ Hardcoded config values
ECS_CLUSTER = "default"
ECS_TASK_DEFINITION = "sentiment-cleaner-task"
SUBNET_ID = "subnet-061495d7090433d6f"
SECURITY_GROUP_ID = "sg-0817514159f510735"
BUCKET_NAME = "mlops-sentiment-app"

# 🐛 Debug
print("🐛 CONFIG VALUES:")
print(f"   ECS_CLUSTER         = {ECS_CLUSTER}")
print(f"   ECS_TASK_DEFINITION = {ECS_TASK_DEFINITION}")
print(f"   SUBNET_ID           = {SUBNET_ID}")
print(f"   SECURITY_GROUP_ID   = {SECURITY_GROUP_ID}")
print(f"   BUCKET_NAME         = {BUCKET_NAME}")

ecs_client = boto3.client("ecs", region_name="us-east-1")
s3 = boto3.client("s3")

def trigger_ecs_pipeline(filename: str, user: str):
    ECS_TASK_DEFINITION = "arn:aws:ecs:us-east-1:593026487135:task-definition/sentiment-cleaner-task:1"
    print(f"🚀 Launching ECS task for user={user}, file={filename}")
    print(f"🛠 Using task definition: {ECS_TASK_DEFINITION}")

    response = ecs_client.run_task(
        cluster="default",
        launchType="FARGATE",
        taskDefinition=ECS_TASK_DEFINITION,
        count=1,
        platformVersion="LATEST",
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": ["subnet-061495d7090433d6f"],
                "securityGroups": ["sg-0817514159f510735"],
                "assignPublicIp": "ENABLED"
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": "sentiment-pipeline",  # Your ECS container name
                    "environment": [
                        {"name": "BUCKET_NAME", "value": BUCKET_NAME},
                        {"name": "USER_NAME", "value": user},
                        {"name": "FILENAME", "value": filename}
                    ]
                }
            ]
        }
    )


def generate_dashboard(user: str, filename: str):
    output_key = f"output/{user}/served.csv"
    metadata_key = f"metadata/{user}/inference_summary.json"

    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=output_key)
        csv_str = response["Body"].read().decode("utf-8")
        df = pd.read_csv(StringIO(csv_str))

        summary = {
            "total_reviews": len(df),
            "positive_reviews": int((df["prediction"] == "positive").sum()),
            "negative_reviews": int((df["prediction"] == "negative").sum()),
            "neutral_reviews": int((df["prediction"] == "neutral").sum()) if "neutral" in df["prediction"].unique() else 0,
            "average_review_length": round(df["review"].astype(str).str.len().mean(), 2),
            "short_reviews_flagged": int(df.get("short_review", pd.Series([False] * len(df))).sum()),
            "top_positive_reviews": df[df["prediction"] == "positive"]["review"].head(5).tolist(),
            "top_negative_reviews": df[df["prediction"] == "negative"]["review"].head(5).tolist()
        }

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=metadata_key,
            Body=json.dumps(summary, indent=2),
            ContentType="application/json"
        )

        print(f"✅ Dashboard summary uploaded to s3://{BUCKET_NAME}/{metadata_key}")

    except Exception as e:
        print(f"❌ Failed to generate dashboard: {e}")
