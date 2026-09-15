#!/usr/bin/env python3
"""Quick verify script for trained LoRA adapter - no GPU required."""
import json
from pathlib import Path

ADAPTER_PATH = Path("models/peft-adapter")

print("="*80)
print("VERIFYING TRAINED ADAPTER")
print("="*80)

# 1. Check required files exist
required_files = [
    "adapter_config.json",
    "adapter_model.safetensors", 
    "tokenizer_config.json",
    "tokenizer.json",
    "special_tokens_map.json",
]

print("\n1. Checking required files:")
all_present = True
for fname in required_files:
    fpath = ADAPTER_PATH / fname
    exists = fpath.exists()
    status = "✓" if exists else "✗"
    print(f"   {status} {fname}")
    if not exists:
        all_present = False

if not all_present:
    print("\n❌ Missing required files!")
    exit(1)

# 2. Load and display adapter config
print("\n2. Adapter configuration:")
with open(ADAPTER_PATH / "adapter_config.json") as f:
    config = json.load(f)
    
print(f"   Base model: {config.get('base_model_name_or_path')}")
print(f"   LoRA rank (r): {config.get('r')}")
print(f"   LoRA alpha: {config.get('lora_alpha')}")
print(f"   Target modules: {config.get('target_modules')}")

# 3. Check adapter size
print("\n3. Adapter size:")
adapter_file = ADAPTER_PATH / "adapter_model.safetensors"
size_mb = adapter_file.stat().st_size / 1024 / 1024
print(f"   {adapter_file.name}: {size_mb:.2f} MB")

# 4. Load eval metrics
print("\n4. Evaluation metrics:")
metrics_file = ADAPTER_PATH / "eval_metrics.json"
if metrics_file.exists():
    with open(metrics_file) as f:
        metrics = json.load(f)
    print(f"   Eval loss: {metrics.get('eval_loss', 'N/A')}")
    print(f"   Epoch: {metrics.get('epoch', 'N/A')}")
else:
    print("   ⚠ No eval_metrics.json found")

# 5. Check checkpoints
print("\n5. Saved checkpoints:")
checkpoints = sorted(ADAPTER_PATH.glob("checkpoint-*"))
if checkpoints:
    for ckpt in checkpoints:
        step = ckpt.name.split("-")[1]
        print(f"   ✓ checkpoint-{step}")
else:
    print("   ⚠ No checkpoints found")

print("\n" + "="*80)
print("✓ ADAPTER VERIFICATION COMPLETE")
print("="*80)
print(f"\nAdapter ready at: {ADAPTER_PATH.absolute()}")
print(f"Total size: {sum(f.stat().st_size for f in ADAPTER_PATH.rglob('*') if f.is_file()) / 1024 / 1024:.2f} MB")
print("\nTo test inference, run on Kaggle or GPU machine:")
print("  python test_adapter_inference.py")
