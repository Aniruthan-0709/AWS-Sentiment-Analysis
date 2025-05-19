# 🧠 AWS Sentiment Analysis Pipeline

This repository implements an end-to-end sentiment analysis pipeline using AWS services with fully automated CI/CD using GitHub Actions. It handles data ingestion, preprocessing, model training, evaluation, and deployment with a web-based user interface.

---

## 📁 Project Structure

```
sentiment-app/
├── backend/                # FastAPI backend APIs
│   ├── main.py             # Entry point for FastAPI
│   ├── routes/             # API endpoints
│   └── utils/              # Utility functions
├── frontend/               # Streamlit user interface
│   └── streamlit_app.py    # Frontend application
├── sentiment-pipeline/     # PySpark + BERT inference logic
│   ├── run_clean.py        # Preprocessing
│   ├── run_infer.py        # Inference
│   └── run_all.py          # Combined pipeline for ECS
├── Dockerfile              # Containerization for Spark + Transformers
├── requirements.txt        # Unified Python dependencies
└── .github/workflows/      # GitHub Actions CI/CD workflows
```

---

## 🔄 Data Pipeline (AWS Glue with Amazon S3)

**AWS Services**: Amazon S3, AWS Glue, AWS Glue Workflows

1. **Amazon S3 (Raw Zone)**:

   * Raw review data is uploaded to `s3://mlops-sentiment-analysis-data/raw/reviews.csv`

2. **Glue Job - Preprocessing (`data_preprocessing.py`)**:

   * Drops null/empty `review_body`
   * Cleans & normalizes review text
   * Saves cleaned data to `Bronze/pre_processed.parquet`

3. **Glue Job - Schema Validation (`schema_validation.py`)**:

   * Checks for nulls, logs out-of-range star ratings
   * Calculates average review length → saved to metadata
   * Output: `Bronze/schema_validated.parquet`

4. **Glue Job - Anomaly Detection (`anomaly_detection.py`)**:

   * Flags anomalies based on review length and star rating
   * Output: `Bronze/anomaly_flagged.parquet`

5. **Glue Job - Sampling (`sampling.py`)**:

   * Drops 3-star reviews
   * Adds binary labels
   * Saves to `Silver/sampled.csv` and `Silver/test.csv`

6. **Workflow**:

   * Orchestrated using **AWS Glue Workflows**

---

## 🤗 Model Training & Evaluation (Amazon SageMaker)

**AWS Services**: Amazon S3, Amazon SageMaker

* **Model**: DistilBERT (binary classification)
* **Training**:

  * Input: `s3://mlops-sentiment-analysis-data/Silver/sampled.csv`
  * Output: `s3://mlops-sentiment-analysis-data/models/model.tar.gz`
* **Evaluation**:

  * Input: `Silver/test.csv`
  * Metrics: Accuracy (93.14%), Precision (94.34%), Recall (91.78%), F1 Score (93.05%)
  * Metadata: `model_evaluation_summary.json`

---

## 🚀 Deployment (Amazon ECS + EC2)

**AWS Services**: Amazon ECS Fargate, Amazon EC2, Amazon S3, AWS Cognito

### 🐳 ECS Fargate Execution

* Containerized with Spark + Transformers
* `run_all.py`: Combines `run_clean.py` and `run_infer.py`
* Output:

  * `processed/{user}/processed.csv`
  * `output/{user}/served.csv`

### 🖥️ Backend (FastAPI on EC2)

* `/login` - AWS Cognito-based auth
* `/trigger_pipeline` - Launch ECS task
* `/generate_dashboard` - Serve metrics and top reviews

### 🌐 Frontend (Streamlit on EC2)

* Uploads CSV → triggers ECS → displays dashboard
* Monitors pipeline progress in real-time

---

## 🔁 CI/CD (GitHub Actions)

### ✅ Continuous Integration

* Triggered on push
* Installs dependencies
* Runs `pytest`

### 🚀 Continuous Deployment

* Builds Docker image
* Pushes to AWS ECR
* Updates ECS task with new image
* Optionally triggers SageMaker training

---

## 🔐 Environment Setup

* `.env` includes credentials for Cognito, S3, ECS task definition, and ECR repository
* Transferred securely via SCP to EC2

---

## 📊 Visual Overview

### 🔸 AWS-Based Pipeline Architecture

```mermaid
flowchart TD
  subgraph Data Pipeline
    A1[Amazon S3 (Raw)] --> A2[AWS Glue: Preprocessing]
    A2 --> A3[AWS Glue: Schema Validation]
    A3 --> A4[AWS Glue: Anomaly Detection]
    A4 --> A5[AWS Glue: Sampling]
    A5 --> A6[Amazon S3 (Silver)]
  end

  subgraph Model Training
    A6 --> B1[Amazon SageMaker: Train DistilBERT]
    B1 --> B2[Amazon S3: model.tar.gz]
  end

  subgraph Model Deployment
    B2 --> C1[Amazon ECS Fargate: run_all.py]
    C1 --> C2[Amazon S3: Predictions]
    C2 --> C3[EC2 FastAPI + Streamlit]
    C3 --> C4[User Dashboard]
  end
```

---

## 📁 S3 Bucket Structure

```
s3://mlops-sentiment-analysis-data/
├── raw/
├── Bronze/
├── Silver/
├── test/
├── output/{user}/served.csv
├── processed/{user}/processed.csv
├── metadata/
```

---

## 📡 Monitoring & Logs

```bash
# Backend logs
$ tail -f fastapi.log

# Frontend logs
$ tail -f streamlit.log
```

---

## 🙌 Credits

Built using: Amazon S3, AWS Glue, Amazon SageMaker, Amazon ECS, Amazon EC2, AWS Cognito, FastAPI, Streamlit, HuggingFace, PySpark, MLflow

---

> ✨ Fully CI/CD-enabled, AWS-architected sentiment analysis app ready for production!
