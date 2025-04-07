from datasets import load_dataset
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification, Trainer, TrainingArguments
import os

def main():
    # Load dataset from SageMaker channel (S3-mounted)
    dataset = load_dataset("csv", data_files={"train": os.path.join(os.environ["SM_CHANNEL_TRAIN"], "sampled.csv")}, split="train")

    # Preprocess text: tokenize
    tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")
    dataset = dataset.map(lambda x: tokenizer(x["review_body"], truncation=True, padding="max_length"), batched=True)
    dataset = dataset.rename_column("label", "labels")
    dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    # Load pre-trained model for binary classification
    model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)

    # Define training arguments
    training_args = TrainingArguments(
        output_dir="/opt/ml/model",  # SageMaker expects model artifacts here
        per_device_train_batch_size=16,
        num_train_epochs=2,
        logging_dir="/opt/ml/logs",
        logging_steps=50,
        save_strategy="epoch"
    )

    # Define Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )

    # Start training
    trainer.train()

    # Save final model to /opt/ml/model (for SageMaker to capture)
    trainer.save_model("/opt/ml/model")

if __name__ == "__main__":
    main()
