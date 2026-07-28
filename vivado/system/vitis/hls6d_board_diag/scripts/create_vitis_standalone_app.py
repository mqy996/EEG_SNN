"""Build the bounded HLS-6D standalone board diagnostic with Vitis 2025.1."""
from hashlib import sha256
from pathlib import Path
import os
import shutil
import vitis


def required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    path = Path(value).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def build_status(path: Path, label: str, timeout_seconds: int = 180) -> str:
    """Wait for Vitis asynchronous build status, then fail boundedly."""
    status_file = path / ".buildstatus"
    deadline = __import__("time").monotonic() + timeout_seconds
    last_status = "<missing>"
    while __import__("time").monotonic() < deadline:
        if status_file.exists():
            last_status = status_file.read_text(encoding="utf-8", errors="replace").strip()
            if last_status.endswith("=SUCCESS"):
                return last_status
            if last_status.endswith("=ERROR"):
                raise RuntimeError(f"{label} build failed: {status_file}\n{last_status}")
        __import__("time").sleep(2)
    raise TimeoutError(
        f"Timed out waiting {timeout_seconds}s for {label} build: "
        f"{status_file}\nlast_status={last_status}"
    )


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


xsa = required_path("HLS6D_DIAG_XSA")
source = required_path("HLS6D_DIAG_SOURCE")
workspace_value = os.environ.get("HLS6D_DIAG_WORKSPACE")
if not workspace_value:
    raise RuntimeError("Missing environment variable: HLS6D_DIAG_WORKSPACE")
workspace = Path(workspace_value).resolve()
artifact_dir = Path(os.environ.get("HLS6D_DIAG_ARTIFACT_DIR", str(source / "artifacts"))).resolve()
platform_name = "hls6d_diag_platform_20260728"
app_name = "hls6d_diag_app_20260728"
platform_dir = workspace / platform_name
app_dir = workspace / app_name
platform_xpfm = platform_dir / "export" / platform_name / f"{platform_name}.xpfm"
elf = app_dir / "build" / f"{app_name}.elf"

for relative in (Path("src/main.c"), Path("include/hls6d_board_diag_regs.h")):
    if not (source / relative).is_file():
        raise FileNotFoundError(source / relative)
workspace.parent.mkdir(parents=True, exist_ok=True)
artifact_dir.mkdir(parents=True, exist_ok=True)

print("VITIS_VERSION_EXPECTED=2025.1")
print(f"XSA={xsa}")
print(f"XSA_SHA256={sha256_file(xsa)}")
print(f"WORKSPACE={workspace}")
print(f"SOURCE={source}")
print(f"PLATFORM={platform_name}")
print(f"APP={app_name}")

client = vitis.create_client()
try:
    client.set_workspace(str(workspace))
    platform = client.create_platform_component(name=platform_name, hw_design=str(xsa))
    platform.add_domain(name="standalone_a9_0", cpu="ps7_cortexa9_0", os="standalone")
    print(f"PLATFORM_BUILD_RETURN={platform.build()}")
    build_status(platform_dir / "export", "platform")
    if not platform_xpfm.exists():
        raise RuntimeError(f"Platform XPFM is missing: {platform_xpfm}")
    print(f"PLATFORM_XPFM={platform_xpfm}")
    platform_ref = client.find_platform_in_repos(platform_name)
    if platform_ref is None:
        raise RuntimeError(f"Platform repository lookup failed: {platform_name}")

    app = client.create_app_component(
        name=app_name,
        platform=platform_ref,
        domain="standalone_a9_0",
        template="empty_application",
    )
    app.import_files(from_loc=str(source / "src"), files=["main.c"], dest_dir_in_cmp="src")
    app.import_files(
        from_loc=str(source / "include"),
        files=["hls6d_board_diag_regs.h"],
        dest_dir_in_cmp="src",
    )
    app.set_app_config(key="USER_INCLUDE_DIRECTORIES", values=str(source / "include"))
    print(f"APP_BUILD_RETURN={app.build()}")
    build_status(app_dir / "build", "application")
    if not elf.exists():
        raise RuntimeError(f"ELF is missing: {elf}")
    print(f"ELF={elf}")
    print(f"ELF_SHA256={sha256_file(elf)}")

    shutil.copy2(platform_xpfm, artifact_dir / f"{platform_name}.xpfm")
    shutil.copy2(elf, artifact_dir / f"{app_name}.elf")
    manifest = artifact_dir / "hls6d_board_diag_build.txt"
    manifest.write_text(
        "\n".join(
            (
                "HLS6D_BOARD_DIAG_BUILD=PASS",
                "VITIS_VERSION_EXPECTED=2025.1",
                f"XSA_SHA256={sha256_file(xsa)}",
                f"PLATFORM_XPFM={platform_xpfm}",
                f"PLATFORM_SHA256={sha256_file(platform_xpfm)}",
                f"ELF={elf}",
                f"ELF_SHA256={sha256_file(elf)}",
                "HLS6B_BITSTREAM_UNCHANGED=TRUE",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"CURATED_ARTIFACT_DIR={artifact_dir}")
    print(f"BUILD_MANIFEST={manifest}")
finally:
    vitis.dispose()
