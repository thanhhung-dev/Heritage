# Test LoRA Adapter Inference trên Kaggle

## Upload adapter lên Kaggle Dataset

Trước tiên, nén adapter (chỉ lấy best model, không checkpoints):

```python
import os
import zipfile

# Tạo thư mục tạm
os.makedirs("/kaggle/working/adapter-upload", exist_ok=True)

# Copy chỉ các file cần thiết
files_to_copy = [
    "adapter_config.json",
    "adapter_model.safetensors",
    "tokenizer_config.json", 
    "tokenizer.json",
    "special_tokens_map.json",
    "chat_template.jinja",
    "vocab.json",
    "merges.txt",
    "eval_metrics.json"
]

for fname in files_to_copy:
    src = f"/kaggle/working/HeritageGraph/models/peft-adapter/{fname}"
    if os.path.exists(src):
        !cp {src} /kaggle/working/adapter-upload/

# Nén lại
!cd /kaggle/working && zip -r peft-adapter-best.zip adapter-upload/

print("\n✓ Đã tạo peft-adapter-best.zip")
!ls -lh /kaggle/working/peft-adapter-best.zip
```

Tải file `peft-adapter-best.zip` (~130MB) về máy.

## Upload lên Kaggle Dataset

1. Vào https://www.kaggle.com/datasets
2. Click "New Dataset"
3. Upload `peft-adapter-best.zip`
4. Đặt tên: `heritage-graph-qwen3-4b-lora`

## Test Inference trên Kaggle Notebook

Tạo notebook mới với code sau:

```python
# Cell 1: Setup
!pip install -q peft transformers accelerate
!unzip /kaggle/input/heritage-graph-qwen3-4b-lora/peft-adapter-best.zip -d /kaggle/working/

import json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL = "Qwen/Qwen3-4B"
ADAPTER_PATH = Path("/kaggle/working/adapter-upload")

print(f"Loading base model: {BASE_MODEL}")
tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
model = PeftModel.from_pretrained(model, ADAPTER_PATH)
model.eval()
print("✓ Model loaded")

# Cell 2: Test function
def ask(question, source="", max_tokens=300):
    messages = [
        {"role": "system", "content": "Bạn là trợ lý văn hóa dân gian Việt Nam, chuyên về Đà Nẵng và Huế."},
        {"role": "user", "content": f"Nguồn: {source}\n\nCâu hỏi: {question}" if source else question}
    ]
    
    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True
    ).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id
        )
    
    new_tokens = outputs[0][inputs.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)

# Cell 3: Test cases
print("="*80)
print("TEST 1: Câu hỏi đơn giản")
print("="*80)
response = ask("Chùa Từ Hiếu có những đặc điểm gì nổi bật?")
print(response)

print("\n" + "="*80)
print("TEST 2: Câu hỏi có nguồn")
print("="*80)
source = "Kinh thành Huế được xây dựng vào năm 1805 dưới triều vua Gia Long."
response = ask("Kinh thành Huế được xây dựng khi nào?", source)
print(response)

print("\n" + "="*80)
print("TEST 3: Từ chối khi không có nguồn")
print("="*80)
response = ask("Ai là người xây dựng Tháp Eiffel?")
print(response)
```

## Expected Output

```
================================================================================
TEST 1: Câu hỏi đơn giản
================================================================================
Chùa Từ Hiếu nổi bật với khuôn viên rộng chừng 8 mẫu...

================================================================================
TEST 2: Câu hỏi có nguồn  
================================================================================
Kinh thành Huế được xây dựng vào năm 1805 dưới triều vua Gia Long...

================================================================================
TEST 3: Từ chối khi không có nguồn
================================================================================
Xin lỗi, tôi không có thông tin về Tháp Eiffel trong nguồn được cung cấp...
```

## So sánh Base vs Adapter

```python
# Load base model (không có adapter)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
base_model.eval()

def ask_base(question):
    messages = [
        {"role": "system", "content": "Bạn là trợ lý văn hóa dân gian Việt Nam."},
        {"role": "user", "content": question}
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True
    ).to(base_model.device)
    
    with torch.no_grad():
        outputs = base_model.generate(inputs, max_new_tokens=200, temperature=0.7, do_sample=True)
    return tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)

# Compare
question = "Kinh thành Huế được xây dựng khi nào?"

print("BASE MODEL (chưa train):")
print(ask_base(question))

print("\nFINE-TUNED MODEL (với adapter):")
print(ask(question, "Kinh thành Huế được xây dựng vào năm 1805."))
```

Adapter sẽ trả lời chính xác và theo format yêu cầu (có trích nguồn), base model sẽ trả lời chung chung.
