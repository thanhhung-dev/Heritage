#!/usr/bin/env python3
"""Test LoRA adapter inference on Kaggle or GPU machine."""
import json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen3-4B"
ADAPTER_PATH = Path("models/peft-adapter")
VALID_FILE = Path("data/valid.jsonl")

def load_model():
    print(f"Loading base model: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
    
    if torch.cuda.is_available():
        device_map = "auto"
        dtype = torch.bfloat16
        print("Using CUDA")
    else:
        device_map = None
        dtype = torch.float32
        print("Using CPU (slow)")
    
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=dtype,
        device_map=device_map
    )
    
    print(f"Loading adapter from: {ADAPTER_PATH}")
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    model.eval()
    
    return model, tokenizer

def generate_response(model, tokenizer, messages, max_new_tokens=300):
    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True
    ).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id
        )
    
    new_tokens = outputs[0][inputs.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)

def main():
    model, tokenizer = load_model()
    
    print("\n" + "="*80)
    print("TESTING ADAPTER WITH VALIDATION SAMPLES")
    print("="*80 + "\n")
    
    # Load first 3 samples
    with open(VALID_FILE, encoding="utf-8") as f:
        samples = [json.loads(line) for i, line in enumerate(f) if i < 3]
    
    for i, sample in enumerate(samples, 1):
        print(f"\n{'─'*80}")
        print(f"SAMPLE {i}")
        print(f"{'─'*80}")
        
        messages = sample["messages"]
        user_content = messages[1]["content"]
        question = user_content.split("\n\nCâu hỏi:")[-1].strip()
        
        print(f"Question: {question}\n")
        print(f"Expected:\n{messages[2]['content'][:200]}...\n")
        
        generated = generate_response(model, tokenizer, messages[:2])
        print(f"Generated:\n{generated}\n")

if __name__ == "__main__":
    main()
