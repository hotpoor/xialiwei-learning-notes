"""Local single-user SD-Turbo image-stream baseline. No camera images are saved."""
import asyncio
import base64
import io
import json
import os
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
import torch
from style_preserve import PROFILES, TemporalStyle
from diffusers import AutoPipelineForImage2Image

ROOT = Path(__file__).resolve().parent
MODEL_ID = 'stabilityai/sd-turbo'
MODEL_REVISION = os.environ.get('LIVEAI_MODEL_REVISION', 'b261bac6fd2cf515557d5d0707481eafa0485ec2')
lock = asyncio.Lock()
state = {'status': 'loading', 'model': MODEL_ID, 'resolution': 256, 'error': None, 'default_profile': 'preserve', 'version': 'preserve-v2'}
pipe = None
embedding_cache = {}
Image.MAX_IMAGE_PIXELS = 16_000_000


def load_model():
    global pipe
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    kwargs = dict(torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
    if MODEL_REVISION:
        kwargs['revision'] = MODEL_REVISION
    pipe = AutoPipelineForImage2Image.from_pretrained(MODEL_ID, **kwargs).to('cuda')
    pipe.set_progress_bar_config(disable=True)
    state['gpu'] = torch.cuda.get_device_name(0)
    state['status'] = 'ready'


async def load_background():
    try:
        await asyncio.to_thread(load_model)
    except Exception as exc:
        state['status'] = 'error'
        state['error'] = f'{type(exc).__name__}: {str(exc)[:500]}'


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(load_background())
    yield
    if not task.done():
        task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get('/')
async def index():
    return FileResponse(ROOT / 'index.html')


@app.get('/health')
async def health():
    return dict(state)


@app.middleware('http')
async def local_only_http(request: Request, call_next):
    # Browser traffic is intended to be same-origin over localhost/SSH forwarding.
    host = request.url.hostname
    if host not in ('localhost', '127.0.0.1', '::1', 'testserver'):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Use localhost or an SSH tunnel'}, status_code=403)
    return await call_next(request)


def infer(payload, temporal=None):
    if not isinstance(payload, dict):
        raise ValueError('Expected JSON object')
    if state['status'] != 'ready':
        raise ValueError('Model is not ready')
    resolution = int(payload.get('resolution', 256))
    if resolution not in (256, 512):
        raise ValueError('Resolution must be 256 or 512')
    prompt = str(payload.get('prompt', '')).strip()
    if not prompt or len(prompt) > 1200:
        raise ValueError('Prompt must contain 1–1200 characters')
    profile = str(payload.get('profile', 'preserve'))
    if profile not in PROFILES:
        raise ValueError('Unknown style profile')
    cfg = PROFILES[profile]
    encoded = payload.get('image', '')
    if not isinstance(encoded, str) or len(encoded) > 2_000_000:
        raise ValueError('Frame too large')
    raw = base64.b64decode(encoded, validate=True)
    image = Image.open(io.BytesIO(raw))
    image.load()
    image = ImageOps.fit(image.convert('RGB'), (resolution, resolution))
    started = time.perf_counter()
    with torch.inference_mode():
        if prompt not in embedding_cache:
            embedding_cache.clear()
            embedding_cache[prompt] = pipe.encode_prompt(
                prompt, device='cuda', num_images_per_prompt=1,
                do_classifier_free_guidance=False,
            )[0]
        # Same seed reduces one source of frame-to-frame variation; not temporal modeling.
        generator = torch.Generator(device='cuda').manual_seed(42)
        output = pipe(
            prompt_embeds=embedding_cache[prompt], image=image,
            num_inference_steps=cfg['steps'], strength=cfg['strength'], guidance_scale=0.0,
            generator=generator,
        ).images[0]
        torch.cuda.synchronize()
    model_ms = (time.perf_counter() - started) * 1000
    temporal = temporal if temporal is not None else TemporalStyle()
    output = temporal.apply(image, output, profile, key=(profile, resolution, prompt))
    infer_ms = (time.perf_counter() - started) * 1000
    buf = io.BytesIO()
    output.save(buf, format='JPEG', quality=88)
    return dict(image=base64.b64encode(buf.getvalue()).decode(),
                infer_ms=round(infer_ms, 1), resolution=resolution,
                frame_id=payload.get('frame_id'), profile=profile, model_ms=round(model_ms, 1),
                effective_steps=int(cfg['steps']*cfg['strength']))


@app.post('/api/frame')
async def frame(request: Request):
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > 2_100_000:
        raise HTTPException(413, 'Frame too large')
    raw = await request.body()
    if len(raw) > 2_100_000:
        raise HTTPException(413, 'Frame too large')
    try:
        payload = json.loads(raw)
        async with lock:
            return await asyncio.to_thread(infer, payload)
    except (ValueError, TypeError, KeyError, UnidentifiedImageError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.websocket('/ws')
async def socket(ws: WebSocket):
    origin = ws.headers.get('origin')
    from urllib.parse import urlparse
    if origin and urlparse(origin).netloc != ws.headers.get('host'):
        await ws.close(code=1008)
        return
    await ws.accept()
    temporal = TemporalStyle()  # Private to this connection, cleared on disconnect.
    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > 2_100_000:
                await ws.send_json({'error': 'Frame too large'})
                continue
            try:
                payload = json.loads(raw)
                async with lock:
                    result = await asyncio.to_thread(infer, payload, temporal)
                await ws.send_json(result)
            except (ValueError, TypeError, KeyError, UnidentifiedImageError) as exc:
                await ws.send_json({'error': str(exc)})
    except WebSocketDisconnect:
        pass
