import os
import torch
import numpy as np
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer, AutoModelForSequenceClassification
HF_MODEL_REPO="dk7706/Adversarial_Prompt_Injection_Defensive_System"
# Hugging Face ZeroGPU Support
try:
    import spaces
    HAS_SPACES = True
except ImportError:
    HAS_SPACES = False

def gpu_decorator(func):
    if HAS_SPACES:
        return spaces.GPU(func)
    return func

# Configuration
# Priority 1: Specific weights file
BEST_MODEL_FILE = "best_model.pt"
# Priority 2: Full model directory
MODEL_DIR = "model_output"
# Fallback: Base model
DEFAULT_MODEL = "distilbert-base-uncased"

# NEW: Confidence Threshold (L2 Security Guard)
ATTACK_THRESHOLD = 0.85 

# Global objects
tokenizer = None
model = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_model():
    global tokenizer, model
    
    # Always use the base tokenizer
    tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL)
    
    try:
        # Step 1: Check for best_model.pt (State Dict)
        if HF_MODEL_REPO:
            print(f"Loading fine-tuned weights from  HF Hub:{HF_MODEL_REPO}")
            model = AutoModelForSequenceClassification.from_pretrained(
                DEFAULT_MODEL, 
                num_labels=2,
                attn_implementation="eager"
            )
            weights_path=hf_hub_download(
                repo_id=HF_MODEL_REPO,
                filename=BEST_MODEL_FILE,
                token=os.environ.get("HF_TOKEN")
            )
            # Load weights (map to CPU first to avoid ZeroGPU init issues during load)
            state_dict = torch.load(weights_path, map_location="cpu")
            model.load_state_dict(state_dict)
            model.to(device)
            model.eval()
            return True
            
        # Step 2: Check for model_output directory
        elif os.path.exists(MODEL_DIR):
            print(f"Loading model from directory: {MODEL_DIR}...")
            model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_DIR, 
                num_labels=2,
                attn_implementation="eager"
            )
            model.to(device)
            model.eval()
            return True
            
        # Step 3: Fallback to base model
        else:
            print("No fine-tuned weights found. Falling back to base model.")
            model = AutoModelForSequenceClassification.from_pretrained(
                DEFAULT_MODEL, 
                num_labels=2,
                attn_implementation="eager"
            )
            model.to(device)
            model.eval()
            return True
            
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

# Initial load attempt
MODEL_ACTIVE = load_model()

@gpu_decorator
def run_ensemble(text, c_res=None):
    """
    ML Detection Engine with False Positive Protection.
    """
    if not MODEL_ACTIVE:
        return {"verdict": "FALLBACK", "confidence": 0.0, "attack_type": "---"}
    
    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(device)
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            confidence = torch.max(probs).item()
            prediction = torch.argmax(probs).item()
            
        # --- FALSE POSITIVE PROTECTION LOGIC ---
        
        # Rule 1: Threshold Enforcement
        if prediction == 1 and confidence < ATTACK_THRESHOLD:
            return {
                "verdict": "BENIGN",
                "confidence": confidence,
                "attack_type": "---",
                "triggered_by": "Ensemble (Low Confidence Bypass)"
            }
            
        # Rule 2: Short Prompt Protection
        if len(text) < 30 and prediction == 1 and confidence < 0.98:
             return {
                "verdict": "BENIGN",
                "confidence": confidence,
                "attack_type": "---",
                "triggered_by": "Ensemble (Short Prompt Bypass)"
            }

        verdict = "ATTACK" if prediction == 1 else "BENIGN"
        return {
            "verdict": verdict,
            "confidence": confidence,
            "attack_type": "ml_ensemble_detection" if verdict == "ATTACK" else "---",
            "triggered_by": "DistilBERT Ensemble"
        }
    except Exception as e:
        return {"verdict": "ERROR", "confidence": 0.0, "attack_type": str(e)}
