"""Build the HLS-6C Vitis 2025.1 standalone replay application.

The script is intentionally evidence-oriented: it uses the HLS-6B XSA as the
only hardware input, keeps the generated workspace outside the curated source
scope, checks component build-status files, and verifies the final ELF exists.
"""
from hashlib import sha256
from pathlib import Path
import os
import vitis


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    path = Path(value).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def build_status(path: Path, label: str) -> str:
    status_file = path / ".buildstatus"
    if not status_file.exists():
        raise RuntimeError(f"{label} build-status file is missing: {status_file}")
    status = status_file.read_text(encoding="utf-8", errors="replace").strip()
    if not status.endswith("=SUCCESS"):
        raise RuntimeError(f"{label} build failed: {status_file}\n{status}")
    return status


xsa = required_path("SNN_REPLAY_XSA")
if not xsa.is_file():
    raise IsADirectoryError(f"SNN_REPLAY_XSA is not a file: {xsa}")
workspace_value = os.environ.get("SNN_REPLAY_WORKSPACE")
if not workspace_value:
    raise RuntimeError("Missing environment variable: SNN_REPLAY_WORKSPACE")
workspace = Path(workspace_value).resolve()
workspace.parent.mkdir(parents=True, exist_ok=True)
src_dir = required_path("SNN_REPLAY_SOURCE")
if not src_dir.is_dir():
    raise NotADirectoryError(f"SNN_REPLAY_SOURCE is not a directory: {src_dir}")
for relative_path in (
    Path("src/main.c"),
    Path("include/snn_replay_regs.h"),
    Path("include/golden_vectors_q12_6.h"),
):
    source_file = src_dir / relative_path
    if not source_file.is_file():
        raise FileNotFoundError(f"Missing replay source file: {source_file}")
platform_name = os.environ.get("SNN_REPLAY_PLATFORM", "snn_replay_platform_hls6c_20260728")
app_name = os.environ.get("SNN_REPLAY_APP", "snn_replay_app_hls6c_20260728")
platform_dir = workspace / platform_name
platform_xpfm = platform_dir / "export" / platform_name / f"{platform_name}.xpfm"
app_dir = workspace / app_name
elf = app_dir / "build" / f"{app_name}.elf"

print("VITIS_VERSION_EXPECTED=2025.1")
print(f"XSA={xsa}")
print(f"XSA_SHA256={sha256(xsa.read_bytes()).hexdigest()}")
print(f"WORKSPACE={workspace}")
print(f"SOURCE={src_dir}")
print(f"PLATFORM={platform_name}")
print(f"APP={app_name}")

client = vitis.create_client()
try:
    client.set_workspace(str(workspace))
    platform = client.create_platform_component(
        name=platform_name,
        hw_design=str(xsa),
    )
    platform.add_domain(
        name="standalone_a9_0",
        cpu="ps7_cortexa9_0",
        os="standalone",
    )
    platform_status = platform.build()
    print(f"PLATFORM_BUILD_RETURN={platform_status}")
    build_status(platform_dir / "export", "platform")
    if not platform_xpfm.exists():
        raise RuntimeError(f"Platform XPFM is missing: {platform_xpfm}")
    print(f"PLATFORM_XPFM={platform_xpfm}")
    platform_ref = client.find_platform_in_repos(platform_name)
    if platform_ref is None:
        raise RuntimeError(f"Vitis platform repository lookup failed: {platform_name}")

    app = client.create_app_component(
        name=app_name,
        platform=platform_ref,
        domain="standalone_a9_0",
        template="empty_application",
    )
    app.import_files(
        from_loc=str(src_dir / "src"),
        files=["main.c"],
        dest_dir_in_cmp="src",
    )
    app.import_files(
        from_loc=str(src_dir / "include"),
        files=["snn_replay_regs.h", "golden_vectors_q12_6.h"],
        dest_dir_in_cmp="src",
    )
    app.set_app_config(
        key="USER_INCLUDE_DIRECTORIES",
        values=str(src_dir / "include"),
    )
    app_status = app.build()
    print(f"APP_BUILD_RETURN={app_status}")
    build_status(app_dir / "build", "application")
    if not elf.exists():
        raise RuntimeError(f"Vitis reported build completion but ELF is missing: {elf}")
    print(f"ELF={elf}")
    print(f"ELF_SHA256={sha256(elf.read_bytes()).hexdigest()}")
finally:
    vitis.dispose()
