"""Config chung cho backend."""
import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Paths
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
GRAPHRAG_DIR = PROJECT_ROOT / "graphrag"
EVAL_DIR = PROJECT_ROOT / "eval"

# GGUF model cho Docker/llama.cpp. Sinh ra bằng scripts/export_gguf.py.
GGUF_MODEL_PATH = MODELS_DIR / "qwen-fused.gguf"

# llama_server là mặc định portable; llama_cpp dùng khi nhúng binding trong Python.
INFERENCE_BACKEND = os.environ.get("INFERENCE_BACKEND", "llama_server")

# Server
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
