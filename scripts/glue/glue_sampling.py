import logging
import json
import boto3
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql.functions import col, when, rand

# -------------------------------------------
# Logging Setup
# -------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -------------------------------------------
# Spark/Glue Context
# -------------------------------------------
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# -------------------------------------------
# S3 Paths
# -------------------------------------------
input_path = "s3://mlops-sentiment-analysis-data/Bronze/anomaly_flagged.parquet"
parquet_output_path = "s3://mlops-sentiment-analysis-data/Bronze/train_final.parquet"
csv_output_path = "s3://mlops-sentiment-analysis-data/Silver/sampled.csv"
metadata_key = "metadata/class_distribution.json"
bucket = "mlops-sentiment-analysis-data"

# -------------------------------------------
# Load anomaly-flagged data
# -------------------------------------------
df = spark.read.parquet(input_path)
logger.info(f"📥 Loaded anomaly-flagged dataset from: {input_path}")

# -------------------------------------------
# Filter out 3-star reviews and add binary label
# -------------------------------------------
df_filtered = df.filter((col("star_rating").isNotNull()) & (col("star_rating") != 3))
df_labeled = df_filtered.withColumn("label", when(col("star_rating") > 3, 1).otherwise(0))

dropped_3_star = df.count() - df_labeled.count()
logger.info(f"🗑️ Dropped {dropped_3_star} neutral (3-star) reviews")

# -------------------------------------------
# Class distribution logging
# -------------------------------------------
label_dist = df_labeled.groupBy("label").count().collect()
class_counts = {int(row["label"]): row["count"] for row in label_dist}
logger.info(f"📊 Class distribution after dropping 3-star: {class_counts}")

# -------------------------------------------
# Stratified sampling (max 25k per class)
# -------------------------------------------
positive_df = df_labeled.filter(col("label") == 1)
negative_df = df_labeled.filter(col("label") == 0)

pos_count = positive_df.count()
neg_count = negative_df.count()
min_class_count = min(pos_count, neg_count, 25000)

logger.info(f"📦 Sampling {min_class_count} from each class")

positive_sample = positive_df.orderBy(rand()).limit(min_class_count)
negative_sample = negative_df.orderBy(rand()).limit(min_class_count)

df_sampled = positive_sample.union(negative_sample).orderBy(rand())

# -------------------------------------------
# Save as Parquet (Bronze Layer)
# -------------------------------------------
df_sampled.write.mode("overwrite").parquet(parquet_output_path)
logger.info(f"✅ Parquet training data saved to: {parquet_output_path}")

# -------------------------------------------
# Save as CSV (Silver Layer)
# -------------------------------------------
df_sampled.select("review_body", "label").write \
    .option("header", True) \
    .mode("overwrite") \
    .csv(csv_output_path)
logger.info(f"✅ CSV training data saved to: {csv_output_path}")

# -------------------------------------------
# Save metadata to S3
# -------------------------------------------
s3 = boto3.client("s3")
class_meta = {
    "dropped_3_star_reviews": dropped_3_star,
    "original_class_distribution": class_counts,
    "sampled_class_counts": {
        "positive": min_class_count,
        "negative": min_class_count
    }
}
s3.put_object(
    Bucket=bucket,
    Key=metadata_key,
    Body=json.dumps(class_meta),
    ContentType='application/json'
)
logger.info(f"📤 Stored class distribution metadata to: s3://{bucket}/{metadata_key}")
