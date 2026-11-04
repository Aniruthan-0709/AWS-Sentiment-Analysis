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

## 🔄 Data Pipeline (AWS Glue)

| Step              | Script                  | Input                             | Output                                  |
| ----------------- | ----------------------- | --------------------------------- | --------------------------------------- |
| Preprocessing     | `data_preprocessing.py` | `Bronze/train.parquet`            | `Bronze/pre_processed.parquet`          |
| Schema Validation | `schema_validation.py`  | `Bronze/pre_processed.parquet`    | `Bronze/schema_validated.parquet`       |
| Anomaly Detection | `anomaly_detection.py`  | `Bronze/schema_validated.parquet` | `Bronze/anomaly_flagged.parquet`        |
| Sampling          | `sampling.py`           | `Bronze/anomaly_flagged.parquet`  | `Silver/sampled.csv`, `Silver/test.csv` |

**Orchestrated via**: AWS Glue Workflows

---

## 🤗 Model Training & Evaluation (SageMaker)

* **Model**: DistilBERT
* **Training**: AWS SageMaker (`Silver/sampled.csv`)
* **Evaluation**: Local using Hugging Face `Trainer.evaluate()` on `Silver/test.csv`
* **Metrics**:

  * Accuracy: 93.14%
  * Precision: 94.34%
  * Recall: 91.78%
  * F1 Score: 93.05%
* **Artifacts**: `s3://mlops-sentiment-analysis-data/models/model.tar.gz`

---

## 🚀 Deployment

### 🖥️ Backend (FastAPI)

* `/login` - AWS Cognito
* `/trigger_pipeline` - Launch ECS job
* `/generate_dashboard` - Generate dashboard

### 🌐 Frontend (Streamlit)

* Upload CSV → Trigger pipeline → View dashboard
* Polls ECS job status in real-time

### 🐳 ECS Fargate Execution

* `run_all.py`: Executes preprocessing and inference using Spark and Transformers
* Output saved to S3: `processed/{user}/processed.csv`, `output/{user}/served.csv`

---

## 🔁 CI/CD (GitHub Actions)

The workflow is defined in `.github/workflows/ci_cd.yml`.

### ✅ Continuous Integration (CI)

* Runs on pushes to `main` and on pull requests
* Installs dependencies and checks that all Python files compile
* Runs the backend tests with `pytest` (AWS is mocked, so no credentials are needed)

To run the tests locally:

```bash
cd sentiment-app
pip install -r requirements.txt pytest httpx
python -m pytest tests
```

### 🚀 Continuous Deployment (CD)

The deploy job runs after the tests pass. It starts the EC2 instance, deploys the latest `main`, restarts FastAPI and Streamlit, and fails if either one doesn't respond. It doesn't build the ECS pipeline image or trigger SageMaker training.

* **Manual deploy:** Actions tab → CI/CD → Run workflow, on `main`
* **Deploy on every push to `main`:** set the repository variable `AUTO_DEPLOY` to `true`

The instance keeps running after a deploy. Run `sentiment-app/deployment/ec2_stop.py` to stop it.

Setup required before the first deploy:

| Repository secret       | Value                                                                                     |
| ----------------------- | ----------------------------------------------------------------------------------------- |
| `AWS_ACCESS_KEY_ID`     | Key for an IAM user allowed `ec2:StartInstances` and `ec2:DescribeInstances`               |
| `AWS_SECRET_ACCESS_KEY` | Secret for that key                                                                       |
| `EC2_SSH_KEY`           | Full contents of `key.pem` (must be an RSA key)                                           |
| `BACKEND_ENV`           | Full contents of `sentiment-app/backend/.env`                                             |

The instance's security group must also allow inbound SSH (port 22) from the GitHub Actions runners, and ports 8000 and 8501 for the health checks.

---

## 🔐 Environment Setup

* `.env` file includes credentials for Cognito, ECS, and S3
* Transferred securely via SCP to EC2 instance

---

## 📊 Visual Overview

### 🔸 Data + Model + Deployment Pipeline

```mermaid
flowchart TD
    A[Upload CSV via Streamlit] --> B[FastAPI Trigger]
    B --> C[ECS Fargate: run_all.py]
    C --> D[S3: processed.csv + served.csv]
    D --> E[FastAPI: generate_dashboard]
    E --> F[Streamlit: Display Results]
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

Built using: AWS Glue, SageMaker, ECS Fargate, EC2, FastAPI, Streamlit, HuggingFace, PySpark, MLflow

---

> ✨ Fully CI/CD-enabled, cloud-optimized sentiment analysis app ready for production!
