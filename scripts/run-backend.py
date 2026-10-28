"""Run the local API with the correct Windows async PostgreSQL event loop."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Port must be an integer from 1 to 65535") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Port must be an integer from 1 to 65535")
    return port


def main() -> None:
    from dotenv import load_dotenv

    # Load configuration before importing API/security modules that read env vars.
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Start the Heritage FastAPI backend locally")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=port_number, default=os.environ.get("BACKEND_PORT", "8000"))
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    import uvicorn

    uvicorn.run(
        "apps.backend.app:app", host=args.host, port=args.port,
        loop="asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
    )


if __name__ == "__main__":
    main()
