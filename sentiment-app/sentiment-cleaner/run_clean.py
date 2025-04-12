import os
import json
import boto3
import uuid
import re
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length, trim, lower, udf
from pyspark.sql.types import IntegerType

# Clean HTML tags and encoded entities
def clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text)        # remove HTML tags
    text = re.sub(r"&[a-z]+;", " ", text)       # remove encoded entities
    return re.sub(r"\s+", " ", text).strip()    # normalize spaces

html_clean_udf = udf(clean_html)

# -----------------------------------------
# 🔧 Environment Variables
# -----------------------------------------
bucket = os.environ.get("BUCKET_NAME", "mlops-sentiment-app")
user = os.environ.get("USER_NAME", "").strip() or "default"
filename = os.environ.get("FILENAME", "test.csv").strip()

# -----------------------------------------
# 📂 S3 Path Construction
raw_key = f"uploads/raw/{user}/{filename}"
processed_prefix = f"processed/{user}/"
dropped_prefix = f"uploads/dropped/{user}/"
summary_key = f"metadata/{user}/preprocessing_summary.json"

input_path = f"s3a://{bucket}/{raw_key}"
tmp_processed = f"s3a://{bucket}/tmp/{user}/processed_{uuid.uuid4()}"
tmp_dropped = f"s3a://{bucket}/tmp/{user}/dropped_{uuid.uuid4()}"

# -----------------------------------------
# 🔍 Get Latest Version ID
# -----------------------------------------
s3 = boto3.client("s3")
latest_version_id = None
try:
    versions = s3.list_object_versions(Bucket=bucket, Prefix=raw_key)
    for version in versions.get("Versions", []):
        if version["IsLatest"] and version["Key"] == raw_key:
            latest_version_id = version["VersionId"]
            print(f"📦 Using S3 version ID: {latest_version_id}")
            break
except Exception as e:
    print(f"⚠️ Failed to get version ID for {raw_key}: {e}")

# -----------------------------------------
# 🚀 Initialize Spark
# -----------------------------------------
spark = SparkSession.builder.appName("SentimentCleaner").getOrCreate()
spark._jsc.hadoopConfiguration().set(
    "fs.s3a.aws.credentials.provider",
    "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
)

# -----------------------------------------
# 📥 Load CSV from S3
# -----------------------------------------
df = spark.read.option("header", True).csv(input_path)
original_count = df.count()

review_col = "review_body" if "review_body" in df.columns else "review" if "review" in df.columns else None
if not review_col:
    raise Exception("❌ Neither 'review' nor 'review_body' column found.")

# Basic clean: trim → lower → clean HTML
df = df.withColumn(review_col, trim(col(review_col)))
df = df.withColumn("review_clean", lower(col(review_col)))
df = df.withColumn("review_clean", html_clean_udf(col("review_clean")))

# -----------------------------------------
# 🧹 Clean Text
# -----------------------------------------
df_filtered = df.filter(col("review_clean").isNotNull() & (length(col("review_clean")) > 0))
null_dropped = original_count - df_filtered.count()

df_filtered = df_filtered.filter(~col("review_clean").rlike("^[0-9\\s]+$"))
numeric_dropped = original_count - null_dropped - df_filtered.count()

# Flag short reviews
def is_short(text):
    if not text:
        return 1
    return int(len(text.split()) < 5 or len(text) < 30)

is_short_udf = udf(is_short, IntegerType())
df_flagged = df_filtered.withColumn("short_review", is_short_udf(col("review_clean")))
short_count = df_flagged.filter(col("short_review") == 1).count()

# Dropped rows
df_dropped_null = df.filter(col("review_clean").isNull() | (length(col("review_clean")) == 0))
df_dropped_numeric = df.filter(col("review_clean").rlike("^[0-9\\s]+$"))
df_dropped = df_dropped_null.union(df_dropped_numeric)

# -----------------------------------------
# 💾 Save to temporary folders
# -----------------------------------------
df_flagged.coalesce(1).write.mode("overwrite").option("header", True).csv(tmp_processed)
df_dropped.coalesce(1).write.mode("overwrite").option("header", True).csv(tmp_dropped)

# -----------------------------------------
# ✅ Rename part files to .csv
# -----------------------------------------
def move_single_file(s3_client, source_prefix, destination_key):
    resp = s3_client.list_objects_v2(Bucket=bucket, Prefix=source_prefix)
    part_file = next(obj["Key"] for obj in resp["Contents"] if "part-00000" in obj["Key"])

    s3_client.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': part_file},
        Key=destination_key
    )
    for obj in resp["Contents"]:
        s3_client.delete_object(Bucket=bucket, Key=obj["Key"])

# Final saved files
move_single_file(s3, f"tmp/{user}/processed_", f"{processed_prefix}processed.csv")
move_single_file(s3, f"tmp/{user}/dropped_", f"{dropped_prefix}dropped.csv")

# -----------------------------------------
# 📝 Summary
# -----------------------------------------
summary = {
    "original_rows": original_count,
    "dropped_null_or_empty": null_dropped,
    "dropped_numeric_only": numeric_dropped,
    "short_reviews_flagged": short_count,
    "retained_clean_reviews": df_flagged.count(),
    "raw_file_version_id": latest_version_id
}

s3.put_object(
    Bucket=bucket,
    Key=summary_key,
    Body=json.dumps(summary, indent=2),
    ContentType="application/json"
)

print("✅ Preprocessing complete.")
