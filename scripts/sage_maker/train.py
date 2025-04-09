import os
import glob
import logging
import pandas as pd
from datasets import Dataset
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    Trainer,
    TrainingArguments,
)
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# ✅ Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ SageMaker environment variables
model_dir = os.environ.get("SM_MODEL_DIR", "./model")
train_dir = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")

# ✅ Locate CSV file in training directory
csv_files = glob.glob(os.path.join(train_dir, "*.csv"))
if not csv_files:
    raise FileNotFoundError(f"No CSV files found in {train_dir}")
csv_path = csv_files[0]
logger.info(f"✅ Found training CSV file: {csv_path}")

# ✅ Load and preprocess dataset
df = pd.read_csv(csv_path).dropna()
df = df.rename(columns={"review_body": "text", "label": "label"})

# ✅ Split into train/test using Hugging Face datasets
dataset = Dataset.from_pandas(df).train_test_split(test_size=0.1)

# ✅ Load tokenizer and tokenize dataset
tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")

def tokenize(example):
    return tokenizer(example["text"], padding="max_length", truncation=True)

encoded_dataset = dataset.map(tokenize, batched=True)
encoded_dataset.set_format("torch", columns=["input_ids", "attention_mask", "label"])

# ✅ Load model with updated initialization
model = DistilBertForSequenceClassification.from_pretrained(
    "distilbert-base-uncased",
    num_labels=2,
    attention_dropout=0.1,  # Added for better regularization
    torch_dtype="auto"  # Auto mixed precision
)

# ✅ Define metrics with zero_division parameter
def compute_metrics(p):
    preds = p.predictions.argmax(-1)
    labels = p.label_ids
    return {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision_score(labels, preds, zero_division=0),
        "recall": recall_score(labels, preds, zero_division=0),
        "f1": f1_score(labels, preds, zero_division=0),
    }

# ✅ Updated training arguments with mixed precision
training_args = TrainingArguments(
    output_dir=model_dir,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    num_train_epochs=2,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    logging_dir="./logs",
    logging_steps=10,
    fp16=True,  # Enable mixed precision training
    load_best_model_at_end=True,
    metric_for_best_model="f1",
)

# ✅ Start Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=encoded_dataset["train"],
    eval_dataset=encoded_dataset["test"],
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
)

logger.info("🚀 Starting training...")
trainer.train()

# ✅ Save model and tokenizer
trainer.save_model(model_dir)
tokenizer.save_pretrained(model_dir)
logger.info(f"✅ Model and tokenizer saved to {model_dir}")
