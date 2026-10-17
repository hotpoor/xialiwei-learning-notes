"""Synthetic-frame GPU smoke test. Saves only the generated test fixture/results."""
import base64
import json
from pathlib import Path
import io
from PIL import Image, ImageDraw
import server

server.load_model()
image = Image.new('RGB', (256, 256), '#8db8be')
draw = ImageDraw.Draw(image)
draw.ellipse((76, 26, 180, 130), fill='#e7b78c')
draw.rounded_rectangle((45, 135, 211, 260), radius=25, fill='#304e7b')
draw.ellipse((101, 65, 108, 73), fill='#26313b')
draw.ellipse((148, 65, 155, 73), fill='#26313b')
draw.arc((106, 82, 152, 108), 0, 180, fill='#985440', width=3)
buf = io.BytesIO()
image.save(buf, format='JPEG')
payload = {'image': base64.b64encode(buf.getvalue()).decode(),
           'prompt': 'watercolor portrait painting, soft pastel colors, delicate paper texture',
           'resolution': 256, 'strength': .5, 'frame_id': 'synthetic-smoke'}
outputs = []
for _ in range(3):
    result = server.infer(payload)
    assert result['resolution'] == 256
    output = Image.open(io.BytesIO(base64.b64decode(result['image'])))
    assert output.size == (256, 256)
    outputs.append(result['infer_ms'])
artifacts = Path('artifacts'); artifacts.mkdir(exist_ok=True)
image.save(artifacts / 'synthetic-input.png')
output.save(artifacts / 'synthetic-output.png')
metrics = {'input': 'synthetic fixture, no camera', 'resolution': 256,
           'inference_ms': outputs, 'gpu': server.state.get('gpu'),
           'model': server.MODEL_ID, 'model_revision': server.MODEL_REVISION,
           'note': 'single-frame sequential test; not end-to-end camera FPS'}
(artifacts / 'smoke-result.json').write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
