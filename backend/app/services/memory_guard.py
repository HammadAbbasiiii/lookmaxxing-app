"""
Runtime memory guard for low-RAM hosts.

Render's ``starter`` plan gives the web worker only 512 MB of RAM. The full ML
pipeline (torch + torchvision + a 98 MB ResNet50, plus MediaPipe's
FaceLandmarker graph) needs far more than that. If we load either subsystem on
a 512 MB box, the Linux OOM-killer terminates the whole worker, which orphans
every upload in ``processing`` and restarts the service in a loop.

These helpers let each heavy subsystem degrade to a lightweight fallback
(mock landmarks / mock score) *before* it can exhaust memory. On a large
enough host (or in local macOS development, where the cgroup files don't
exist) the full pipeline is used.
"""

_MIN_FREE_MB_TORCH = 800       # torch + torchvision + 98 MB ResNet50 + activations
_MIN_FREE_MB_MEDIAPIPE = 450   # MediaPipe FaceLandmarker graph + inference


def available_memory_mb() -> int | None:
    """Return available memory in MiB, or None if it can't be determined."""
    # cgroup v2 (Render / modern containers)
    try:
        with open("/sys/fs/cgroup/memory.max", "r") as fh:
            limit = fh.read().strip()
        with open("/sys/fs/cgroup/memory.current", "r") as fh:
            current = int(fh.read().strip())
        if limit != "max":
            return max(0, (int(limit) - current)) // (1024 * 1024)
    except (OSError, ValueError):
        pass

    # cgroup v1
    try:
        with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r") as fh:
            limit = int(fh.read().strip())
        with open("/sys/fs/cgroup/memory/memory.usage_in_bytes", "r") as fh:
            current = int(fh.read().strip())
        # A value near 2^60 means "unlimited".
        if limit < (1 << 60):
            return max(0, (limit - current)) // (1024 * 1024)
    except (OSError, ValueError):
        pass

    # /proc/meminfo (fallback for bare Linux)
    try:
        with open("/proc/meminfo", "r") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass

    return None


def can_load_torch() -> bool:
    mem = available_memory_mb()
    return mem is None or mem >= _MIN_FREE_MB_TORCH


def can_load_mediapipe() -> bool:
    mem = available_memory_mb()
    return mem is None or mem >= _MIN_FREE_MB_MEDIAPIPE
