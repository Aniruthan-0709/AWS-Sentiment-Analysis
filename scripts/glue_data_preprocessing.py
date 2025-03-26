from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType
import logging

# ✅ Initialize Glue and Spark Context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# ✅ Setup Logging
logging.basicConfig(level=logging.INFO)

# ✅ Define S3 Input & Output Paths
s3_input_path = "s3://mlops-sentiment-analysis-data/processed/reviews.parquet"
s3_output_path = "s3://mlops-sentiment-analysis-data/processed/preprocessed_reviews.parquet"

# ✅ Load Data
df = spark.read.parquet(s3_input_path)
logging.info("🔹 Data loaded from S3.")

# ✅ Remove Duplicates
df = df.dropDuplicates()
logging.info("🔹 Duplicates removed.")

# ✅ Handle Missing Values (Drop rows where critical fields are null)
df = df.dropna(subset=["star_rating", "review_body", "product_category"])
df = df.na.fill({"review_body": "unknown", "star_rating": 3})
logging.info("🔹 Missing values handled.")

# ✅ Standardize Text (Lowercase + Remove Punctuation)
df = df.withColumn("review_body", F.lower(F.col("review_body")))
df = df.withColumn("review_body", F.regexp_replace(F.col("review_body"), "[^a-zA-Z0-9 ]", ""))
logging.info("🔹 Text standardized (lowercased + punctuation removed).")

# ✅ Scale Star Ratings to Ensure They Are Between 1 and 5
df = df.withColumn("star_rating", F.when(F.col("star_rating") < 1, 1)
                                      .when(F.col("star_rating") > 5, 5)
                                      .otherwise(F.col("star_rating")))
df = df.withColumn("star_rating", F.col("star_rating").cast(IntegerType()))
logging.info("🔹 Star ratings scaled to 1-5.")

# ✅ Encode Product Category (Convert to Numeric)
df = df.withColumn("product_category_encoded", 
                   F.when(F.col("product_category") == "Electronics", 0)
                    .when(F.col("product_category") == "Books", 1)
                    .otherwise(2))
logging.info("🔹 Product category encoded.")

# ✅ Create Sentiment Labels Based on Star Rating
df = df.withColumn("review_sentiment",
                   F.when(F.col("star_rating") <= 2, "negative")
                    .when(F.col("star_rating") == 3, "neutral")
                    .otherwise("positive"))
logging.info("🔹 Sentiment labels created.")

# ✅ Save Processed Data to S3 (Only as Parquet)
df.write.mode("overwrite").parquet(s3_output_path)
logging.info(f"✅ Data preprocessing completed. Saved as Parquet at {s3_output_path}.")
