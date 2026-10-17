"""Matched synthetic sequence: variation, residual jitter and speed, not face identity scores."""
import base64,io,json,time,statistics
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import server
from style_preserve import TemporalStyle,PROFILES

PROMPT='natural photograph of the same person, original face and expression, subtle soft color grading, realistic skin texture'
root=Path('artifacts/preserve-v2');root.mkdir(parents=True,exist_ok=True)
frames=[]
for i in range(20):
    image=Image.new('RGB',(256,256),(139,177,184));d=ImageDraw.Draw(image)
    dx=0 if i<12 else (i-12)*4
    d.ellipse((76+dx,26,180+dx,130),fill=(211,169,136));d.rounded_rectangle((45+dx,135,211+dx,260),radius=25,fill=(48,78,123))
    d.ellipse((101+dx,65,108+dx,73),fill=(38,49,59));d.ellipse((148+dx,65,155+dx,73),fill=(38,49,59));d.arc((106+dx,82,152+dx,108),0,180,fill=(134,78,70),width=3)
    arr=np.asarray(image,dtype=float);rng=np.random.default_rng(i)
    arr=np.clip(arr+rng.normal(0,.7,arr.shape),0,255).astype(np.uint8)
    frames.append(Image.fromarray(arr))
server.load_model();report={'prompt':PROMPT,'frames':len(frames),'resolution':256,'input':'synthetic portrait; frames 0-11 stationary with tiny sensor-like noise; 12-19 translate 4px per frame','results':{},'limitations':['Pixel variation and residual jitter are diagnostic, not identity or perceptual quality scores.','No real face/camera captured.','Lower edit error is partly guaranteed by residual limiting and blending; does not prove better stylization.']}
outputs={}
for profile in PROFILES:
    temporal=TemporalStyle();times=[];maes=[];residuals=[];images=[]
    def run(image,i,history):
        buf=io.BytesIO();image.save(buf,format='JPEG',quality=90)
        payload={'image':base64.b64encode(buf.getvalue()).decode(),'prompt':PROMPT,'resolution':256,'profile':profile,'frame_id':i}
        # Decode the exact JPEG source for fair pixel comparisons.
        source=np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert('RGB'),dtype=np.float32)
        start=time.perf_counter();result=server.infer(payload,history);ms=(time.perf_counter()-start)*1000
        out=Image.open(io.BytesIO(base64.b64decode(result['image']))).convert('RGB')
        return out,ms,np.asarray(out,dtype=np.float32)-source
    for _ in range(3):run(frames[0],-1,TemporalStyle())
    started=time.perf_counter()
    for i,image in enumerate(frames):
        out,ms,residual=run(image,i,temporal);times.append(ms);maes.append(float(np.abs(residual).mean()));residuals.append(residual);images.append(out.copy())
    elapsed=time.perf_counter()-started
    report['results'][profile]={'config':PROFILES[profile],'sequential_fps':round(len(frames)/elapsed,2),'frame_ms_median':round(statistics.median(times),2),'source_mae_after_jpeg':round(statistics.mean(maes),3),'stationary_residual_jitter_mae':round(statistics.mean(float(np.abs(residuals[i]-residuals[i-1]).mean()) for i in range(1,12)),3),'model_steps':int(PROFILES[profile]['steps']*PROFILES[profile]['strength'])}
    outputs[profile]=images
    images[0].save(root/f'{profile}.png');print(profile,report['results'][profile],flush=True)
frames[0].save(root/'input.png')
contact=Image.new('RGB',(1024,300),'#f2f5f0');draw=ImageDraw.Draw(contact)
for i,(label,image) in enumerate([('Input',frames[0]),('Old redraw',outputs['legacy'][0]),('Preserve default',outputs['preserve'][0]),('Soft style',outputs['soft'][0])]):
    draw.text((i*256+12,12),label,fill='#20392e');contact.paste(image,(i*256,40))
contact.save(root/'comparison.png')
(root/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
