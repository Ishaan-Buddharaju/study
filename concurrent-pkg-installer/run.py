"""Scratch runner. Time your work against install_sequential."""
import time
from pkgmgr.registry import Disk
from pkgmgr import installer

if __name__ == "__main__":
    t = time.perf_counter()
    disk = Disk()
    order = installer.install_sequential("webapp", disk)
    print(f"sequential: {time.perf_counter()-t:.1f}s")
    print("order:", order)
    print("installed:", disk.installed)
