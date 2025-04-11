import os
import json
import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length, trim, lower, udf
from pyspark.sql.types import BooleanType

# -----------------------------------------
# Read environment variables
# -----------------------------------------
bucket = os.environ.get("BUCKET_NAME", "mlops-sentiment-app")
user = os.environ.get("USER_NAME", "").strip()

# Build S3 keys (default to test if user not passed)
if user:
    raw_key = f"raw/{user}/raw.csv"
    processed_key = f"processed/{user}/processed.csv"
    dropped_key = f"uploads/dropped/{user}/dropped.csv"
    summary_key = f"metadata/{user}/preprocessing_summary.json"
else:
    raw_key = "raw/test.csv"
    processed_key = "processed/processed.csv"
    dropped_key = "uploads/dropped/dropped.csv"
    summary_key = "metadata/preprocessing_summary.json"

input_path = f"s3a://{bucket}/{raw_key}"
output_cleaned = f"s3a://{bucket}/{processed_key}"
output_dropped = f"s3a://{bucket}/{dropped_key}"

# -----------------------------------------
# Fetch latest version ID of the uploaded file
# -----------------------------------------
s3 = boto3.client("s3")
latest_version_id = None
try:
    version_info = s3.list_object_versions(Bucket=bucket, Prefix=raw_key)
    for version in version_info.get("Versions", []):
        if version["IsLatest"] and version["Key"] == raw_key:
            latest_version_id = version["VersionId"]
            print(f"📦 Using S3 version ID: {latest_version_id}")
            break
except Exception as e:
    print(f"⚠️ Failed to get version ID for {raw_key}: {e}")

# -----------------------------------------
# Initialize Spark
# -----------------------------------------
spark = SparkSession.builder.appName("SentimentCleaner").getOrCreate()
spark._jsc.hadoopConfiguration().set(
    "fs.s3a.aws.credentials.provider",
    "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
)

# -----------------------------------------
# Load CSV from S3 (uses latest version automatically)
# -----------------------------------------
df = spark.read.option("header", True).csv(input_path)
original_count = df.count()

# Detect review column
review_col = "review_body" if "review_body" in df.columns else "review" if "review" in df.columns else None
if not review_col:
    raise Exception("❌ Neither 'review' nor 'review_body' column found.")

df = df.withColumn(review_col, trim(col(review_col)))
df = df.withColumn("review_clean", lower(col(review_col)))

# -----------------------------------------
# Drop null/empty reviews
# -----------------------------------------
df_filtered = df.filter(col("review_clean").isNotNull() & (length(col("review_clean")) > 0))
null_dropped = original_count - df_filtered.count()

# Drop numeric-only reviews
df_filtered = df_filtered.filter(~col("review_clean").rlike("^[0-9\\s]+$"))
numeric_dropped = original_count - null_dropped - df_filtered.count()

# -----------------------------------------
# Flag short reviews
def is_short(text):
    if not text:
        return True
    words = len(text.split())
    chars = len(text)
    return words < 5 or chars < 30

is_short_udf = udf(is_short, BooleanType())
df_flagged = df_filtered.withColumn("short_review", is_short_udf(col("review_clean")))

# -----------------------------------------
# Save dropped rows
df_dropped_null = df.filter(col("review_clean").isNull() | (length(col("review_clean")) == 0))
df_dropped_numeric = df.filter(col("review_clean").rlike("^[0-9\\s]+$"))
df_dropped = df_dropped_null.union(df_dropped_numeric)
df_dropped.write.mode("overwrite").option("header", True).csv(output_dropped)

# -----------------------------------------
# Save cleaned data
df_flagged.write.mode("overwrite").option("header", True).csv(output_cleaned)

# -----------------------------------------
# Save summary JSON to S3
short_count = df_flagged.filter(col("short_review")).count()
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
cd ..