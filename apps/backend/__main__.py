"""Local API entry point with a psycopg-compatible Windows event loop."""
import argparse
import asyncio
import sys

import uvicorn


def database_event_loop():
    # Uvicorn 0.53 explicitly chooses Proactor on Windows without reload.
    # Setting only the global asyncio policy does not override its loop factory.
    return asyncio.SelectorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    uvicorn.run("apps.backend.app:app", host=args.host, port=args.port, reload=args.reload,
                loop="apps.backend.__main__:database_event_loop" if sys.platform == "win32" else "auto")


if __name__ == "__main__":
    main()
