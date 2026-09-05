import os
import torch
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import threading

# --- CONFIGURATION ---
BASE_MODEL = "distilbert-base-uncased"
DATA_PATH = "labeled_dataset.csv"
OUTPUT_DIR = "model_output"
OUTPUT_WEIGHTS = "best_model.pt"
BATCH_SIZE = 4 # Reduced for ZeroGPU stability
EPOCHS = 1     # Reduced for ZeroGPU time limits
LEARNING_RATE = 2e-5

class PromptDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        label = self.labels[item]
        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def run_training_logic(device="cpu"):
    """
    The actual training loop, designed to be called from the Gradio app.
    """
    if not os.path.exists(DATA_PATH):
        return False, f"Error: {DATA_PATH} not found."

    try:
        df = pd.read_csv(DATA_PATH)
        if len(df) < 2:
            return False, "Need at least 2 samples to train."

        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(BASE_MODEL, num_labels=2)
        model.to(device)
        model.train()

        # Simple split
        train_dataset = PromptDataset(df.text.to_numpy(), df.label.to_numpy(), tokenizer)
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)

        # Using torch.optim.AdamW which is the standard in modern environments
        optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)
        
        for epoch in range(EPOCHS):
            for batch in train_loader:
                optimizer.zero_grad()
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs.loss
                loss.backward()
                optimizer.step()

        # Save results
        torch.save(model.state_dict(), OUTPUT_WEIGHTS)
        model.save_pretrained(OUTPUT_DIR)
        tokenizer.save_pretrained(OUTPUT_DIR)
        
        return True, f"Success! Retrained on {len(df)} samples. Restart app to apply."
    except Exception as e:
        return False, f"Training Failed: {str(e)}"
