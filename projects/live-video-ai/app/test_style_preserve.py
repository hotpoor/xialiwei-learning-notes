import unittest
import numpy as np
from PIL import Image
from style_preserve import TemporalStyle

class PreserveTests(unittest.TestCase):
    def test_extreme_model_change_is_bounded_and_new_stream_is_clean(self):
        source=Image.new('RGB',(32,32),(80,120,160)); altered=Image.new('RGB',(32,32),'white')
        history=TemporalStyle();out=history.apply(source,altered,key='a',now=1)
        self.assertLessEqual(np.abs(np.asarray(out,dtype=float)-np.asarray(source,dtype=float)).max(),12)
        clean=TemporalStyle().apply(source,source,key='a',now=1)
        self.assertTrue(np.array_equal(np.asarray(clean),np.asarray(source)))
    def test_motion_or_prompt_change_does_not_reuse_old_residual(self):
        dark=Image.new('RGB',(32,32),(50,50,50)); light=Image.new('RGB',(32,32),(150,150,150))
        for current, new_key in ((light,'a'),(dark,'b')):
            history=TemporalStyle();history.apply(dark,Image.new('RGB',(32,32),'white'),key='a',now=1)
            changed=history.apply(current,current,key=new_key,now=1.1)
            self.assertTrue(np.array_equal(np.asarray(changed),np.asarray(current)))
    def test_static_style_jitter_is_smoothed_but_stale_history_expires(self):
        source=Image.new('RGB',(32,32),(128,128,128)); bright=Image.new('RGB',(32,32),(168,168,168)); dark=Image.new('RGB',(32,32),(88,88,88))
        history=TemporalStyle();a=history.apply(source,bright,key='a',now=1)
        b=history.apply(source,dark,key='a',now=1.1)
        independent=TemporalStyle().apply(source,dark,key='a',now=1.1)
        self.assertLess(np.abs(np.asarray(a,dtype=float)-np.asarray(b,dtype=float)).mean(),np.abs(np.asarray(a,dtype=float)-np.asarray(independent,dtype=float)).mean())
        stale=history.apply(source,dark,key='a',now=3)
        self.assertTrue(np.array_equal(np.asarray(stale),np.asarray(independent)))

if __name__=='__main__':unittest.main()
