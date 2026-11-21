"""
gpu.py

GPU support for the transcription step. faster-whisper runs on NVIDIA GPUs
through CTranslate2, which needs NVIDIA's cuBLAS 12 and cuDNN 9 libraries.
Rather than a system-wide CUDA install, requirements-gpu.txt pulls them in
as pip packages (nvidia-cublas-cu12, nvidia-cudnn-cu12), which put their
DLLs under site-packages/nvidia/*/bin - a folder Windows doesn't search on
its own. register_cuda_dlls() adds those folders to the DLL search path.

Kept free of faster-whisper/ctranslate2 imports at module level, same
reason as config.py: importing this must stay cheap.
"""

import glob
import os
import site
import sys


def register_cuda_dlls() -> None:
    """Make pip-installed NVIDIA libraries findable (Windows only; Linux
    wheels set their own rpath, so this is a no-op there)."""
    if sys.platform != "win32":
        return
    roots = list(site.getsitepackages()) + [site.getusersitepackages()]
    for root in roots:
        for dll_dir in glob.glob(os.path.join(root, "nvidia", "*", "bin")):
            os.add_dll_directory(dll_dir)
            os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")


def cuda_device_count() -> int:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count()
    except Exception:
        return 0
