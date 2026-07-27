from pathlib import Path
import os
import vitis


def required(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing {name}")
    path = Path(value).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path

xsa = required("AX7020_GPIO_XSA")
source = required("AX7020_GPIO_SOURCE")
source_file = os.environ.get("AX7020_GPIO_SOURCE_FILE", "main.c")
workspace = Path(os.environ.get("AX7020_GPIO_WORKSPACE", str(source.parent / "workspace"))).resolve()
workspace.mkdir(parents=True, exist_ok=True)
platform_name = os.environ.get("AX7020_GPIO_PLATFORM", "ax7020_gpio_platform")
app_name = os.environ.get("AX7020_GPIO_APP", "ax7020_gpio_smoke_app")

client = vitis.create_client()
client.set_workspace(str(workspace))
platform = client.create_platform_component(name=platform_name, hw_design=str(xsa))
platform.add_domain(name="standalone_a9_0", cpu="ps7_cortexa9_0", os="standalone")
platform.build()
platform_xpfm = client.find_platform_in_repos(platform_name)
app = client.create_app_component(name=app_name, platform=platform_xpfm, domain="standalone_a9_0", template="empty_application")
app.import_files(from_loc=str(source), files=[source_file], dest_dir_in_cmp="src")
app.build()
elf = Path(app.component_location) / "build" / f"{app_name}.elf"
if not elf.exists():
    raise RuntimeError(f"ELF missing: {elf}")
print(f"PLATFORM={platform_xpfm}")
print(f"ELF={elf}")
