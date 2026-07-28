"""Capture COM5 while XSCT downloads and runs the HLS-6D diagnostic."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import threading
import time

import serial


MARKERS = (
    b"HLS6D_DIAG_START",
    b"GPIO_READ_BEGIN",
    b"GPIO_READ_DONE",
    b"SNN_VERSION_BEGIN",
    b"SNN_VERSION_DONE",
    b"SNN_STATUS_BEGIN",
    b"SNN_STATUS_DONE",
    b"HLS6D_DIAG_COMPLETE",
)
MARKER_TIMEOUT_SECONDS = 10.0
POST_PROCESS_DRAIN_SECONDS = 5.0
MAX_CAPTURE_SECONDS = 90.0


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: capture_board_diag.py <elf> <ps7_init.tcl> <bitstream> <xsct.tcl> <log>")
    elf, ps7, bit, tcl, log = (Path(value).resolve() for value in sys.argv[1:])
    for path in (elf, ps7, bit, tcl):
        if not path.is_file():
            raise FileNotFoundError(path)

    serial_bytes = bytearray()
    serial_error: list[str] = []
    serial_lock = threading.Lock()
    serial_stop = threading.Event()
    serial_ready = threading.Event()

    def read_serial() -> None:
        try:
            with serial.Serial("COM5", 115200, timeout=0.1) as port:
                port.reset_input_buffer()
                serial_ready.set()
                while not serial_stop.is_set():
                    data = port.read(4096)
                    if data:
                        with serial_lock:
                            serial_bytes.extend(data)
        except Exception as exc:  # preserve hardware/driver evidence in the report
            serial_error.append(f"{type(exc).__name__}: {exc}")
            serial_ready.set()

    serial_thread = threading.Thread(target=read_serial, daemon=True)
    serial_thread.start()
    serial_ready.wait(timeout=3.0)

    xsct = r"D:\vitis\2025.1\Vitis\bin\xsct.bat"
    command = ["cmd.exe", "/d", "/c", "call", xsct, str(tcl), str(elf), str(ps7), str(bit)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    observed: list[tuple[str, float]] = []
    started = time.monotonic()
    deadline = started + MARKER_TIMEOUT_SECONDS
    overall_deadline = started + MAX_CAPTURE_SECONDS
    marker_index = 0
    search_offset = 0
    stop_reason = "completed"
    process_exit_time: float | None = None

    try:
        while marker_index < len(MARKERS):
            marker = MARKERS[marker_index]
            with serial_lock:
                serial_snapshot = bytes(serial_bytes)
            marker_position = serial_snapshot.find(marker, search_offset)
            if marker_position >= 0:
                observed.append((marker.decode(), time.monotonic()))
                marker_index += 1
                search_offset = marker_position + len(marker)
                deadline = time.monotonic() + MARKER_TIMEOUT_SECONDS
                continue
            now = time.monotonic()
            if now >= overall_deadline:
                stop_reason = f"global timeout after {MAX_CAPTURE_SECONDS:.1f}s: {marker.decode()}"
                break
            if now >= deadline:
                stop_reason = f"missing marker after {MARKERS[marker_index - 1].decode() if marker_index else 'XSCT start'}: {marker.decode()}"
                break
            if process.poll() is not None:
                if process_exit_time is None:
                    process_exit_time = time.monotonic()
                elif time.monotonic() - process_exit_time >= POST_PROCESS_DRAIN_SECONDS:
                    stop_reason = f"missing marker after XSCT exit: {marker.decode()}"
                    break
            time.sleep(0.05)
    finally:
        if process.poll() is None:
            process.kill()
        try:
            xsct_stdout, xsct_stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            xsct_stdout, xsct_stderr = process.communicate()
        serial_stop.set()
        serial_thread.join(timeout=2)

    with serial_lock:
        serial_text = bytes(serial_bytes).decode("utf-8", errors="replace")
    output = "\n".join(
        (
            "HLS6D_BOARD_DIAG_CAPTURE=1",
            f"STOP_REASON={stop_reason}",
            f"MARKERS_COMPLETED={marker_index}/{len(MARKERS)}",
            "OBSERVED_MARKERS=" + ",".join(name for name, _ in observed),
            "XSCT_RETURN=" + str(process.returncode),
            "XSCT_STDOUT_BEGIN",
            xsct_stdout.decode("utf-8", errors="replace"),
            "XSCT_STDOUT_END",
            "XSCT_STDERR_BEGIN",
            xsct_stderr.decode("utf-8", errors="replace"),
            "XSCT_STDERR_END",
            "SERIAL_COM5_BEGIN",
            serial_text,
            "SERIAL_COM5_END",
            "SERIAL_ERROR=" + ("; ".join(serial_error) if serial_error else "none"),
        )
    )
    log.write_text(output + "\n", encoding="utf-8", newline="\n")
    sys.stdout.buffer.write((output + "\n").encode("utf-8", errors="replace"))
    return 0 if marker_index == len(MARKERS) else 2


if __name__ == "__main__":
    raise SystemExit(main())
