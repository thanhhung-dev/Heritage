#!/usr/bin/env python3
"""Test script for trained LoRA adapter."""
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Paths
BASE_MODEL = "Qwen/Qwen3-4B"
ADAPTER_PATH = Path("models/peft-adapter")
VALID_FILE = Path("data/valid.jsonl")

print(f"Loading base model: {BASE_MODEL}")
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)

# Device selection
if torch.cuda.is_available():
    device_map = "auto"
    dtype = torch.bfloat16
    print("Using CUDA")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device_map = None  # MPS doesn't support device_map
    dtype = torch.float16
    print("Using MPS (Apple Silicon)")
else:
    device_map = None
    dtype = torch.float32
    print("Using CPU")

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=dtype,
    device_map=device_map
)

if device_map is None:
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        model = model.to("mps")
    else:
        model = model.to("cpu")

print(f"Loading adapter from: {ADAPTER_PATH}")
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
model.eval()

print("\n" + "="*80)
print("Testing adapter with validation samples")
print("="*80 + "\n")

# Load first 3 samples from valid.jsonl
with open(VALID_FILE, encoding="utf-8") as f:
    samples = [json.loads(line) for i, line in enumerate(f) if i < 3]

for i, sample in enumerate(samples, 1):
    print(f"\n{'─'*80}")
    print(f"SAMPLE {i}")
    print(f"{'─'*80}")
    
    messages = sample["messages"]
    
    # Show question (user message)
    user_content = messages[1]["content"]
    question = user_content.split("\n\nCâu hỏi:")[-1].strip()
    print(f"Question: {question}\n")
    
    # Show expected answer
    expected = messages[2]["content"]
    print(f"Expected answer (truncated):\n{expected[:200]}...\n")
    
    # Generate with adapter
    inputs = tokenizer.apply_chat_template(
        messages[:2],  # Only system + user
        return_tensors="pt",
        add_generation_prompt=True
    ).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=300,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id
        )
    
    # Decode only new tokens
    new_tokens = outputs[0][inputs.shape[1]:]
    generated = tokenizer.decode(new_tokens, skip_special_tokens=True)
    
    print(f"Generated answer:\n{generated}\n")
    print(f"{'─'*80}\n")

print("\nTest completed!")
