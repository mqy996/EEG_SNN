"""Download the bitstream/ELF and capture the board UART output.

Requires pyserial on the host and a running hw_server on localhost:3121.
"""
from __future__ import annotations

import argparse
import subprocess
import threading
import time
import sys
from pathlib import Path

import serial


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitstream", type=Path, required=True)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--ps7-init", type=Path, required=True)
    parser.add_argument("--serial-port", default="COM5")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--xsct", type=Path, default=Path(r"D:\vitis\2025.1\Vitis\bin\xsct.bat"))
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.bitstream, args.elf, args.ps7_init, args.xsct):
        if not path.exists():
            parser.error(f"missing path: {path}")

    tcl = Path(__file__).with_name("board_replay.tcl")
    output = []
    stop = False

    def capture_uart() -> None:
        nonlocal stop
        try:
            with serial.Serial(args.serial_port, args.baud, timeout=0.2) as port:
                port.reset_input_buffer()
                deadline = time.time() + args.timeout
                while time.time() < deadline and not stop:
                    data = port.read(4096)
                    if data:
                        output.append(data)
        except Exception as exc:  # keep XSCT evidence even if UART is unavailable
            output.append(f"\n[SERIAL_ERROR] {exc}\n".encode())

    cmd = (
        f'cmd.exe /d /c call "{args.xsct}" "{tcl}" '
        f'"{args.bitstream.resolve()}" "{args.elf.resolve()}" "{args.ps7_init.resolve()}"'
    )
    thread = threading.Thread(target=capture_uart, daemon=True)
    thread.start()
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=args.timeout + 45)
    stop = True
    thread.join(timeout=3)

    text = (
        "XSCT_STDOUT\n"
        + result.stdout
        + "\nXSCT_STDERR\n"
        + result.stderr
        + f"\nSERIAL_{args.serial_port}\n"
        + b"".join(output).decode("utf-8", errors="replace")
        + f"\nXSCT_RETURN={result.returncode}\n"
    )
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(text, encoding="utf-8")
    print(text)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
