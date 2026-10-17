"""Measure a localhost/SSH WebSocket path with synthetic frames, not camera FPS."""
import asyncio
import base64
import io
import json
import statistics
import time
from pathlib import Path
import urllib.request
from PIL import Image, ImageDraw
import websockets

BASE = 'http://127.0.0.1:8767'
def frame(i, prompt):
    image = Image.new('RGB', (256,256), '#8db8be'); draw = ImageDraw.Draw(image)
    dx = i % 15 - 7
    draw.ellipse((76+dx,26,180+dx,130),fill='#e7b78c')
    draw.rectangle((45+dx,135,211+dx,256),fill='#304e7b')
    buf = io.BytesIO();image.save(buf,format='JPEG')
    return json.dumps({'image':base64.b64encode(buf.getvalue()).decode(),'prompt':prompt,'resolution':256,'strength':.5,'frame_id':i})

async def main():
    with urllib.request.urlopen(BASE+'/health',timeout=10) as response: health=json.load(response)
    if health['status']!='ready': raise RuntimeError(health)
    latencies=[];count=0
    prompt='watercolor portrait painting, soft pastel colors, delicate paper texture'
    async with websockets.connect(BASE.replace('http','ws')+'/ws',origin=BASE,max_size=2_100_000,compression=None) as ws:
        for i in range(3):
            await ws.send(frame(i,prompt));r=json.loads(await ws.recv())
            if 'error' in r: raise RuntimeError(r['error'])
        started=time.perf_counter()
        while time.perf_counter()-started<30:
            t=time.perf_counter();await ws.send(frame(count,prompt));r=json.loads(await ws.recv())
            if 'error' in r: raise RuntimeError(r['error'])
            assert r['frame_id']==count
            assert Image.open(io.BytesIO(base64.b64decode(r['image']))).size==(256,256)
            latencies.append((time.perf_counter()-t)*1000);count+=1
        seconds=time.perf_counter()-started
        await ws.send(frame(0,'charcoal pencil portrait drawing, black and white, rough paper'));changed=json.loads(await ws.recv())
        if 'error' in changed: raise RuntimeError(changed['error'])
    report={'input':'moving synthetic shapes','path':'localhost WebSocket; record whether run on server or through SSH in accompanying report','resolution':256,'frames':count,'seconds':round(seconds,3),'sequential_client_fps':round(count/seconds,2),'roundtrip_ms_median':round(statistics.median(latencies),2),'roundtrip_ms_p95':round(sorted(latencies)[int(.95*(len(latencies)-1))],2),'prompt_change_request':'passed','limitations':'No camera capture, browser decoding/rendering or screen scanout in this measurement.'}
    out=Path('artifacts');out.mkdir(exist_ok=True);(out/'client-benchmark.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':asyncio.run(main())
