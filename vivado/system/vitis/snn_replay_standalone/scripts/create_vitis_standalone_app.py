"""Create and build the standalone replay application with Vitis 2025.1.

Run with:
    vitis -s create_vitis_standalone_app.py

Paths are supplied through SNN_REPLAY_XSA, SNN_REPLAY_WORKSPACE and
SNN_REPLAY_SOURCE so the script is reproducible on another Windows host.
"""
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


xsa = required_path("SNN_REPLAY_XSA")
workspace_value = os.environ.get("SNN_REPLAY_WORKSPACE")
if not workspace_value:
    raise RuntimeError("Missing environment variable: SNN_REPLAY_WORKSPACE")
workspace = Path(workspace_value).resolve()
workspace.mkdir(parents=True, exist_ok=True)
src_dir = required_path("SNN_REPLAY_SOURCE")
platform_name = os.environ.get("SNN_REPLAY_PLATFORM", "snn_replay_platform_20260727")
app_name = os.environ.get("SNN_REPLAY_APP", "snn_replay_app_uart1_20260727")

client = vitis.create_client()
client.set_workspace(str(workspace))
platform = client.create_platform_component(name=platform_name, hw_design=str(xsa))
platform.add_domain(name="standalone_a9_0", cpu="ps7_cortexa9_0", os="standalone")
platform.build()
platform_xpfm = client.find_platform_in_repos(platform_name)

app = client.create_app_component(
    name=app_name,
    platform=platform_xpfm,
    domain="standalone_a9_0",
    template="empty_application",
)
app.import_files(from_loc=str(src_dir / "src"), files=["main.c"], dest_dir_in_cmp="src")
app.import_files(
    from_loc=str(src_dir / "include"),
    files=["snn_replay_regs.h", "golden_vectors_q12_6.h"],
    dest_dir_in_cmp="src",
)
app.set_app_config(key="USER_INCLUDE_DIRECTORIES", values=str(src_dir / "include"))
app.build()

elf = Path(app.component_location) / "build" / f"{app_name}.elf"
if not elf.exists():
    raise RuntimeError(f"Vitis reported build completion but ELF is missing: {elf}")
print(f"PLATFORM={platform_xpfm}")
print(f"ELF={elf}")
vitis.dispose()
