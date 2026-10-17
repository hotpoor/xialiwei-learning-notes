"""Read-only CUDA compute check; does not download model weights."""
import json
import torch

if not torch.cuda.is_available():
    raise SystemExit('CUDA unavailable in this Python environment')
a = torch.randn((256, 256), device='cuda')
result = a @ a.T
assert bool(torch.isfinite(result).all()), 'Non-finite CUDA result'
torch.cuda.synchronize()
print(json.dumps({
    'torch': torch.__version__,
    'cuda_runtime': torch.version.cuda,
    'gpu': torch.cuda.get_device_name(0),
    'compute_check': 'pass',
    'free_vram_mib': round(torch.cuda.mem_get_info()[0] / 1024**2),
}, indent=2))
