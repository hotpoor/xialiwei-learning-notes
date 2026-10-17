"""Synthetic sequential-frame benchmark; never captures a webcam."""
import base64
import io
import json
import statistics
import subprocess
import threading
import time
from pathlib import Path
from PIL import Image, ImageDraw
import torch
import server

samples = []
stop = threading.Event()
def sample_power():
    while not stop.is_set():
        try:
            row = subprocess.check_output(['nvidia-smi', '--query-gpu=power.draw,utilization.gpu,memory.used', '--format=csv,noheader,nounits'], text=True).splitlines()[0]
            watts, util, memory = map(float, row.split(','))
            samples.append({'t': time.perf_counter(), 'watts': watts, 'util': util, 'memory_mib': memory})
        except Exception:
            pass
        stop.wait(.5)

def payload(i, resolution):
    image = Image.new('RGB', (resolution, resolution), '#8db8be')
    draw = ImageDraw.Draw(image)
    dx = (i % 15) - 7
    scale = resolution / 256
    box = lambda coords: tuple(int((v + (dx if j % 2 == 0 else 0)) * scale) for j, v in enumerate(coords))
    draw.ellipse(box((76, 26, 180, 130)), fill='#e7b78c')
    draw.rounded_rectangle(box((45, 135, 211, 256)), radius=int(25*scale), fill='#304e7b')
    draw.ellipse(box((101, 65, 108, 73)), fill='#26313b')
    draw.ellipse(box((148, 65, 155, 73)), fill='#26313b')
    buf = io.BytesIO(); image.save(buf, format='JPEG')
    return {'image': base64.b64encode(buf.getvalue()).decode(), 'prompt': 'watercolor portrait painting, soft pastel colors, delicate paper texture', 'resolution': resolution, 'profile': 'legacy', 'strength': .5, 'frame_id': i}

server.load_model()
thread = threading.Thread(target=sample_power, daemon=True); thread.start()
time.sleep(3)
idle = list(samples)
results = []
artifacts = Path('artifacts'); artifacts.mkdir(exist_ok=True)
try:
    for resolution in (256, 512):
        for i in range(3): server.infer(payload(i, resolution))
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter(); times = []; inference = []; count = 0
        while time.perf_counter() - started < 30 or count < 60:
            t = time.perf_counter()
            output = server.infer(payload(count, resolution))
            times.append((time.perf_counter()-t)*1000)
            inference.append(output['infer_ms']); count += 1
        ended = time.perf_counter(); active = [s for s in samples if started <= s['t'] <= ended]
        watts = statistics.mean(s['watts'] for s in active) if active else None
        result = {'resolution': resolution, 'frames': count, 'seconds': round(ended-started,3), 'sequential_server_fps': round(count/(ended-started),2), 'frame_ms_median': round(statistics.median(times),2), 'frame_ms_p95': round(sorted(times)[int(.95*(len(times)-1))],2), 'inference_ms_median': statistics.median(inference), 'gpu_board_watts_mean': round(watts,2) if watts else None, 'gpu_board_kwh_per_hour': round(watts/1000,4) if watts else None, 'cuda_peak_allocated_mib': round(torch.cuda.max_memory_allocated()/1024**2,1), 'power_samples': len(active)}
        results.append(result)
        Image.open(io.BytesIO(base64.b64decode(output['image']))).save(artifacts/f'benchmark-{resolution}.png')
        print(json.dumps(result), flush=True)
finally:
    stop.set(); thread.join(timeout=3)
report = {'model':server.MODEL_ID, 'revision':server.MODEL_REVISION, 'gpu':server.state['gpu'], 'torch':torch.__version__, 'profile':'legacy','strength':.5, 'total_steps':2, 'effective_steps':1, 'warmup_frames':3, 'input':'moving synthetic shapes', 'idle_gpu_board_watts_mean': round(statistics.mean(s['watts'] for s in idle),2) if idle else None, 'results':results, 'limitations':['No webcam capture, network, browser rendering or display latency in FPS.', 'GPU board power only; not whole-machine wall power. Includes other GPU activity if present.', 'Sequential single-user baseline; no temporal model or concurrency claims.']}
(artifacts/'benchmark.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2), flush=True)
