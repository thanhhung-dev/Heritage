#!/usr/bin/env python3
"""Test LoRA adapter với cùng prompt và decoding như production."""
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.core.prompt import chat_messages

BASE_MODEL = "Qwen/Qwen3-4B"
ADAPTER_PATH = Path("models/peft-adapter/checkpoint-125")

# Setup device
if torch.cuda.is_available():
    device = "cuda"
    dtype = torch.bfloat16
    print("✓ Using CUDA GPU")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
    dtype = torch.float16
    print("✓ Using Apple Silicon MPS")
else:
    device = "cpu"
    dtype = torch.float32
    print("⚠ Using CPU (chậm)")

# Load model
print(f"\nLoading {BASE_MODEL}...")
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=dtype,
    device_map=None
)
model = model.to(device)

print(f"Loading adapter from {ADAPTER_PATH}...")
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
model.eval()
print("✓ Model ready\n")

def ask(question, source="", max_tokens=200):
    """Hỏi model một câu."""
    messages = chat_messages(source, question)
    
    encoded = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True,
        return_dict=True,
        enable_thinking=False,  # Tắt thinking mode (giống lúc train)
    )
    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        outputs = model.generate(
            **encoded,
            max_new_tokens=max_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id
        )

    prompt_length = encoded["input_ids"].shape[1]
    return tokenizer.decode(outputs[0][prompt_length:], skip_special_tokens=True).strip()

# Test cases
print("="*80)
print("TEST 1: Câu hỏi có nguồn đúng")
print("="*80)
source = (
    "Chùa Thiên Mụ, còn gọi là chùa Linh Mụ, là một ngôi chùa cổ nằm "
    "trên đồi Hà Khê, tả ngạn sông Hương, cách trung tâm thành phố Huế "
    "khoảng 5 km về phía tây. "
    "URL: https://vi.wikipedia.org/wiki/Ch%C3%B9a_Thi%C3%AAn_M%E1%BB%A5"
)
print(ask("Chùa Thiên Mụ ở đâu?", source))

print("\n" + "="*80)
print("TEST 2: Câu hỏi có nguồn")  
print("="*80)
source = (
    "Sông Hương dài 80 km, bắt nguồn từ dãy Trường Sơn. "
    "URL: https://vi.wikipedia.org/wiki/S%C3%B4ng_H%C6%B0%C6%A1ng"
)
print(ask("Sông Hương dài bao nhiêu?", source))

print("\n" + "="*80)
print("TEST 3: Câu hỏi không có nguồn (phải từ chối)")
print("="*80)
print(ask("Thủ đô của Pháp là gì?"))
