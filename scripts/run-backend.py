"""Chạy backend FastAPI trên Windows với SelectorEventLoop.

Vì sao cần script này thay vì `uvicorn apps.backend.app:app`:

psycopg (async) không chạy trên ProactorEventLoop — loại event loop mặc định của
Windows từ Python 3.8. `uvicorn.run()` tự gọi `config.setup_event_loop()` và đặt
lại policy về mặc định, nên mọi query DB sẽ ném `InterfaceError` ngay lần đầu.
Script này tự tạo event loop (đã là Selector nhờ policy) rồi chạy `Server.serve()`
trên chính loop đó.

    .venv/Scripts/python.exe scripts/run-backend.py            # cổng theo .env
    .venv/Scripts/python.exe scripts/run-backend.py --port 8001

Không có auto-reload: reloader của uvicorn chạy app trong tiến trình con và tiến
trình đó không đi qua script này nên policy lại về mặc định. Sửa code thì Ctrl+C
rồi chạy lại.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import uvicorn  # noqa: E402


def read_env(path: str = ".env") -> dict[str, str]:
    """Đọc .env, mở rộng `${VAR}` — chỉ để in thông tin lúc khởi động."""
    values: dict[str, str] = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            value = re.sub(
                r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
                lambda m: values.get(m.group(1), os.environ.get(m.group(1), "")),
                value,
            )
            values[key.strip()] = value
    return values


def main() -> int:
    env = read_env()
    parser = argparse.ArgumentParser(description="Chạy Heritage backend (Windows-safe)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(env.get("BACKEND_PORT") or 8000))
    args = parser.parse_args()

    target = env.get("DATABASE_URL", "")
    target = re.sub(r"(://[^:]+:)[^@]*@", r"\1***@", target) or "(chưa cấu hình)"
    print(f"[backend] DB   : {target}")
    print(f"[backend] nghe : http://{args.host}:{args.port}  (docs: /docs)")
    print("[backend] dừng : Ctrl+C")

    config = uvicorn.Config(
        "apps.backend.app:app",
        host=args.host,
        port=args.port,
        loop="asyncio",
        log_level="info",
    )
    server = uvicorn.Server(config)
    loop = asyncio.new_event_loop()  # policy đã là Selector ⇒ loop hợp với psycopg
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
