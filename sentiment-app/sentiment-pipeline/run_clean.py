import os
import json
import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, lower, length, udf
from pyspark.sql.types import BooleanType
from io import BytesIO

# 🔧 Environment Variables
bucket = os.environ.get("BUCKET_NAME", "mlops-sentiment-app")
user = os.environ.get("USER_NAME", "default")
filename = os.environ.get("FILENAME", "test.csv")

raw_key = f"uploads/raw/{user}/{filename}"
processed_key = f"processed/{user}/processed.csv"
dropped_key = f"uploads/dropped/{user}/dropped.csv"
summary_key = f"metadata/{user}/preprocessing_summary.json"

input_path = f"s3a://{bucket}/{raw_key}"
output_cleaned = f"s3a://{bucket}/{processed_key}"
output_dropped = f"s3a://{bucket}/{dropped_key}"

s3 = boto3.client("s3")

# 🔁 Get S3 version info (optional)
def get_latest_version_id():
    try:
        versions = s3.list_object_versions(Bucket=bucket, Prefix=raw_key)
        for version in versions.get("Versions", []):
            if version["IsLatest"] and version["Key"] == raw_key:
                return version["VersionId"]
    except Exception as e:
        print(f"⚠️ Could not fetch version ID: {e}")
    return None

latest_version_id = get_latest_version_id()

# 🚀 Start Spark
spark = SparkSession.builder.appName("SentimentCleaner").getOrCreate()
spark._jsc.hadoopConfiguration().set(
    "fs.s3a.aws.credentials.provider",
    "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
)

# 📥 Load CSV
df = spark.read.option("header", True).csv(input_path)
original_count = df.count()

# 🧠 Determine review column
review_col = "review_body" if "review_body" in df.columns else "review"
if review_col not in df.columns:
    raise Exception("❌ No review column found.")

df = df.withColumn(review_col, trim(col(review_col)))
df = df.withColumn("review_clean", lower(col(review_col)))

# 🧹 Filter out null/empty and numeric-only
df_filtered = df.filter(col("review_clean").isNotNull() & (length(col("review_clean")) > 0))
null_dropped = original_count - df_filtered.count()
df_filtered = df_filtered.filter(~col("review_clean").rlike("^[0-9\\s]+$"))
numeric_dropped = original_count - null_dropped - df_filtered.count()

# 🏷 Flag short reviews
def is_short(text):
    if not text:
        return True
    words = len(text.split())
    chars = len(text)
    return words < 5 or chars < 30

is_short_udf = udf(is_short, BooleanType())
df_flagged = df_filtered.withColumn("short_review", is_short_udf(col("review_clean")))
short_count = df_flagged.filter(col("short_review")).count()

# 💾 Save dropped rows
df_dropped_null = df.filter(col("review_clean").isNull() | (length(col("review_clean")) == 0))
df_dropped_numeric = df.filter(col("review_clean").rlike("^[0-9\\s]+$"))
df_dropped = df_dropped_null.union(df_dropped_numeric)
df_dropped.coalesce(1).write.mode("overwrite").option("header", True).csv(output_dropped)

# 💾 Save cleaned
df_flagged.coalesce(1).write.mode("overwrite").option("header", True).csv(output_cleaned)

# 📊 Save summary JSON
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
