from __future__ import annotations

import argparse

from qwen_tts import __version__
from qwen_tts.constants import DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT
from qwen_tts.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(prog="voicecraft-engine")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default=DEFAULT_SERVER_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT)
    serve.add_argument("--data-dir", required=True)

    args = parser.parse_args()
    if args.command == "serve":
        run_server(args.host, args.port, args.data_dir)


if __name__ == "__main__":
    main()
