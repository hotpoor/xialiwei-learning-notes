"""Bounded, motion-gated style residuals. No face recognition or frame persistence."""
import time
import numpy as np
from PIL import Image, ImageFilter

PROFILES = {
    'preserve': dict(steps=8, strength=.125, mix=.25, residual_limit=48, history=.70),
    'soft': dict(steps=4, strength=.25, mix=.40, residual_limit=64, history=.55),
    'legacy': dict(steps=2, strength=.5, mix=1., residual_limit=255, history=0.),
}

class TemporalStyle:
    def __init__(self):
        self.source = None
        self.residual = None
        self.key = None
        self.updated = 0.

    def apply(self, source, generated, profile='preserve', key=None, now=None):
        cfg = PROFILES[profile]
        now = time.monotonic() if now is None else now
        original = np.asarray(source, dtype=np.float32)
        rendered = np.asarray(generated, dtype=np.float32)
        if profile == 'legacy':
            self.source = self.residual = None
            self.key = None
            return generated
        # Retain source edges; transfer only a bounded, low-frequency color/style residual.
        residual_image = Image.fromarray(np.uint8(np.clip((rendered-original)/2+128, 0, 255)))
        residual = (np.asarray(residual_image.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)-128)*2
        residual = np.clip(residual, -cfg['residual_limit'], cfg['residual_limit'])
        valid = (self.source is not None and self.source.shape == original.shape
                 and self.key == key and 0 <= now-self.updated < 1.)
        if valid:
            motion = np.mean(np.abs(original-self.source), axis=2, keepdims=True)
            # A scene cut or large motion must not drag an old face/pose into the new frame.
            if float(motion.mean()) < 18:
                weight = cfg['history'] * np.exp(-motion/6.)
                weight[motion > 18] = 0
                residual = residual*(1-weight) + self.residual*weight
        self.source = original
        self.residual = residual
        self.key = key
        self.updated = now
        result = np.rint(np.clip(original + cfg['mix']*residual, 0, 255)).astype(np.uint8)
        return Image.fromarray(result)
