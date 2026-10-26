"""Record GPU IOMMU domains and reject unsupported bare-metal DMA translation."""
import argparse
import json
import pathlib
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("--devices", required=True)
parser.add_argument("--output", type=pathlib.Path)
parser.add_argument("--require-compatible", action="store_true")
args = parser.parse_args()
virtualization = subprocess.run(["systemd-detect-virt", "--vm"], capture_output=True, text=True)
raw = subprocess.check_output(["nvidia-smi", "--id=" + args.devices,
                               "--query-gpu=index,uuid,pci.bus_id", "--format=csv,noheader"], text=True)
devices = []
for line in raw.splitlines():
    index, uuid, bus = (part.strip() for part in line.split(","))
    normalized_bus = "0000:" + bus.split(":", 1)[1].lower()
    group = pathlib.Path("/sys/bus/pci/devices") / normalized_bus / "iommu_group"
    domain = (group / "type").read_text().strip() if (group / "type").exists() else None
    devices.append({"index": int(index), "uuid": uuid, "pci_bus": normalized_bus,
                    "iommu_group": str(group.resolve()) if group.exists() else None, "domain_type": domain})
unsupported = virtualization.returncode != 0 and any((device["domain_type"] or "").startswith("DMA") for device in devices)
result = {"kernel_cmdline": pathlib.Path("/proc/cmdline").read_text().strip(),
          "boot_id": pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
          "vm_detection": virtualization.stdout.strip(), "vm_detection_exit_code": virtualization.returncode,
          "devices": devices, "unsupported_bare_metal_dma_iommu": unsupported,
          "note": "Configuration check only; CUDA-runtime P2P and original KV data checks are still required"}
if args.output:
    args.output.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
if args.require_compatible and unsupported:
    raise SystemExit("NVIDIA does not support bare-metal PCIe P2P with DMA IOMMU translation; arrange administrator maintenance or use a validated host")
