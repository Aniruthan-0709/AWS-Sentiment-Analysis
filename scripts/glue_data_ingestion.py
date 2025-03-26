from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql import functions as F

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

s3_input_path = "s3://mlops-sentiment-analysis-data/raw/reviews.csv"
s3_output_path = "s3://mlops-sentiment-analysis-data/processed/reviews.parquet"

df = spark.read.option("header", "true").csv(s3_input_path)
df.write.mode("overwrite").parquet(s3_output_path)

print(f"✅ Data ingestion completed. Saved to {s3_output_path}")
