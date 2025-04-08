import os
import logging
import pandas as pd
import mlflow
import mlflow.transformers
from datasets import Dataset
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# ---------------------------
# ✅ Logging Setup
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# ✅ Environment Vars (SageMaker)
# ---------------------------
model_dir = os.environ.get("SM_MODEL_DIR", "./model")
train_file = os.environ.get("SM_CHANNEL_TRAIN", "./sampled.csv")

# ---------------------------
# ✅ Load Data
# ---------------------------
logger.info(f"📥 Loading training data from: {train_file}")
df = pd.read_csv(os.path.join(train_file, "sampled.csv")).dropna()
df = df.rename(columns={"review_body": "text", "label": "label"})
dataset = Dataset.from_pandas(df).train_test_split(test_size=0.1)

# ---------------------------
# ✅ Tokenization
# ---------------------------
tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")

def tokenize(batch):
    return tokenizer(batch["text"], padding="max_length", truncation=True)

tokenized = dataset.map(tokenize, batched=True)
tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])

# ---------------------------
# ✅ Load Model
# ---------------------------
model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)

# ---------------------------
# ✅ Evaluation Metrics
# ---------------------------
def compute_metrics(p):
    preds = p.predictions.argmax(axis=1)
    labels = p.label_ids
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds),
        "precision": precision_score(labels, preds),
        "recall": recall_score(labels, preds)
    }

# ---------------------------
# ✅ Training Config
# ---------------------------
training_args = TrainingArguments(
    output_dir=model_dir,
    num_train_epochs=2,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=10,
    report_to="none"
)

# ---------------------------
# ✅ MLflow Tracking
# ---------------------------
mlflow.set_tracking_uri("http://127.0.0.1:5000")  # OR your remote MLflow tracking server
mlflow.set_experiment("distilbert-sentiment")

with mlflow.start_run():
    logger.info("🚀 Starting training with MLflow tracking")

    # Log hyperparameters
    mlflow.log_params({
        "model": "distilbert-base-uncased",
        "epochs": training_args.num_train_epochs,
        "train_batch_size": training_args.per_device_train_batch_size,
    })

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )

    trainer.train()
    metrics = trainer.evaluate()
    logger.info(f"📊 Evaluation metrics: {metrics}")

    # Log metrics to MLflow
    mlflow.log_metrics(metrics)

    # Save & log model
    trainer.save_model(model_dir)
    tokenizer.save_pretrained(model_dir)
    mlflow.transformers.log_model(transformers_model=model, artifact_path="model", tokenizer=tokenizer)

    logger.info("✅ Training complete and model logged to MLflow.")
