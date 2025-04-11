import os
import json
import boto3
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, length, regexp_replace, trim, lower, udf
from pyspark.sql.types import BooleanType

# ---------------------------
# Environment Variables
# ---------------------------
bucket = os.environ.get("BUCKET_NAME", "mlops-sentiment-app")
raw_key = os.environ.get("RAW_KEY")
processed_key = os.environ.get("PROCESSED_KEY", "processed/processed.csv")
dropped_key = os.environ.get("DROPPED_KEY", "uploads/dropped/dropped.csv")
summary_key = os.environ.get("SUMMARY_KEY", "metadata/preprocessing_summary.json")

input_path = f"s3a://{bucket}/{raw_key}"
output_cleaned = f"s3a://{bucket}/{processed_key}"
output_dropped = f"s3a://{bucket}/{dropped_key}"

# ---------------------------
# Spark Session Setup
# ---------------------------
spark = SparkSession.builder.appName("SentimentCleaner").getOrCreate()
spark._jsc.hadoopConfiguration().set("fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")

# ---------------------------
# Load Input File
# ---------------------------
df = spark.read.option("header", True).csv(input_path)
original_count = df.count()

# Detect review column
review_col = "review_body" if "review_body" in df.columns else "review" if "review" in df.columns else None
if not review_col:
    raise Exception("❌ Neither 'review' nor 'review_body' column found.")

df = df.withColumn(review_col, trim(col(review_col)))

# ---------------------------
# Clean & Filter
# ---------------------------
df = df.withColumn("review_clean", lower(trim(col(review_col))))

# Drop null or empty
df_filtered = df.filter(col("review_clean").isNotNull() & (length(col("review_clean")) > 0))
null_dropped_count = original_count - df_filtered.count()

# Drop numeric-only rows
df_filtered = df_filtered.filter(~col("review_clean").rlike("^[0-9\\s]+$"))
numeric_dropped_count = original_count - null_dropped_count - df_filtered.count()

# Flag short reviews (<5 words or <30 chars)
def is_short(text):
    if not text:
        return True
    word_count = len(text.split())
    char_count = len(text)
    return word_count < 5 or char_count < 30

is_short_udf = udf(is_short, BooleanType())
df_flagged = df_filtered.withColumn("short_review", is_short_udf(col("review_clean")))

# ---------------------------
# Save Dropped Rows
# ---------------------------
df_dropped_null = df.filter(col("review_clean").isNull() | (length(col("review_clean")) == 0)).withColumn("drop_reason", col(review_col).isNull().cast("string"))
df_dropped_numeric = df.filter(col("review_clean").rlike("^[0-9\\s]+$")).withColumn("drop_reason", col("review_clean"))

df_dropped = df_dropped_null.union(df_dropped_numeric)
df_dropped.write.mode("overwrite").option("header", True).csv(output_dropped)

# ---------------------------
# Save Cleaned Data
# ---------------------------
df_flagged.write.mode("overwrite").option("header", True).csv(output_cleaned)

# ---------------------------
# Save Summary
# ---------------------------
short_count = df_flagged.filter(col("short_review") == True).count()
summary = {
    "original_rows": original_count,
    "dropped_null_or_empty": null_dropped_count,
    "dropped_numeric_only": numeric_dropped_count,
    "short_reviews_flagged": short_count,
    "retained_clean_reviews": df_flagged.count()
}

s3 = boto3.client("s3")
s3.put_object(
    Bucket=bucket,
    Key=summary_key,
    Body=json.dumps(summary, indent=2),
    ContentType="application/json"
)

print("✅ Preprocessing complete.")
