from sagemaker.huggingface import HuggingFace
import sagemaker

role = sagemaker.get_execution_role()

huggingface_estimator = HuggingFace(
    entry_point="train.py",
    source_dir="AWS-Sentiment-Analysis/scripts/sage_maker",
    instance_type="ml.t3.medium",
    instance_count=1,
    role=role,
    transformers_version="4.26",
    pytorch_version="1.13",
    py_version="py39",
    output_path="s3://mlops-sentiment-analysis-data/Silver/",
    base_job_name="distilbert-sentiment"
)

huggingface_estimator.fit({
    "train": "s3://mlops-sentiment-analysis-data/Silver/sampled.csv"
})
