"""Render a 15-second illustrated motion proof; no reference video assets."""
import json, subprocess
from pathlib import Path
import cv2
import numpy as np
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
W,H,FPS=1280,720,24
art=cv2.imread(str(ROOT/'public/art/blues-storyboard-v1.png'))
alternate=cv2.imread(str(ROOT/'public/art/blues-expression-v1.png'))
if art is None or alternate is None: raise FileNotFoundError('Both storyboard and alternate expression artwork are required')
alternate=cv2.resize(alternate,(art.shape[1],art.shape[0]))
ah,aw=art.shape[:2]
# Panel boundaries exclude the fine white gutters.
wide=cv2.resize(art[0:538],(W,H))
close=cv2.resize(art[545:1080],(W,H))
alt=cv2.resize(alternate[545:1080],(W,H))
# Isolate the changed face region; do not dissolve entire compositions.
mask=np.zeros((H,W),np.float32)
cv2.ellipse(mask,(505,254),(166,165),0,0,360,1,-1)
mask=cv2.GaussianBlur(mask,(51,51),10)[:,:,None]
beats=json.loads((ROOT/'outputs/song.json').read_text())['audio']['beats']
start=12.; duration=15.
cut=min(beats,key=lambda b:abs(b-(start+6.5)))-start
out=ROOT/'outputs/blues-motion-proof-v1.mp4'
ff=imageio_ffmpeg.get_ffmpeg_exe()
p=subprocess.Popen([ff,'-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-ss',str(start),'-i',str(ROOT/'media/st-louis-blues.mp3'),'-t',str(duration),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','afade=t=in:d=0.4,afade=t=out:st=14:d=1','-movflags','+faststart',str(out)],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
rng=np.random.default_rng(27); rain=rng.random((120,4))
for n in range(int(FPS*duration)):
    t=n/FPS; is_close=t>=cut; local=t-cut if is_close else t
    if is_close:
        # Hand-selected expression hold, with a brief cel transition.
        expression=np.clip((local-1.5)/.22,0,1)*np.clip((5.8-local)/.22,0,1)
        frame=close.astype(np.float32)*(1-mask*expression)+alt.astype(np.float32)*mask*expression
    else: frame=wide.astype(np.float32)
    # Restrained camera push and vertical drift.
    zoom=1.025+local*(.002 if is_close else .006)
    m=cv2.getRotationMatrix2D((W*.48,H*.44),0,zoom)
    m[1,2]+=np.sin(local*.7)*1.2
    frame=cv2.warpAffine(frame,m,(W,H),borderMode=cv2.BORDER_REFLECT)
    # Rain stays over window area instead of falling across the singer.
    overlay=np.zeros_like(frame)
    for x,y,speed,length in rain:
        px=int(W*(.58+.42*x)); py=int(((y+t*(.4+.45*speed))%1)*H)
        cv2.line(overlay,(px,py),(px-3,py+int(12+length*22)),(34,20,10),1,cv2.LINE_AA)
    frame+=overlay
    # Candle/lamp flicker is deliberately subtle and spatially local.
    yy,xx=np.ogrid[:H,:W]
    glow=np.exp(-((xx-W*.89)**2+(yy-H*.72)**2)/(2*(W*.11)**2))[:,:,None]
    frame+=glow*(1.5+np.sin(t*7)*1+np.sin(t*13)*.5)*np.array([.3,.7,1.7])
    fade=min(1,t/.6,(duration-t)/.8)
    frame=np.uint8(np.clip(frame*fade,0,255))
    p.stdin.write(frame.tobytes())
    if n in [48,int((cut+3)*FPS),int(13*FPS)]: cv2.imwrite(str(ROOT/f'outputs/proof-frame-{n}.jpg'),frame)
p.stdin.close()
if p.wait()!=0: raise RuntimeError('ffmpeg render failed')
(ROOT/'outputs/proof-timing.json').write_text(json.dumps(dict(duration=duration,source_start=start,cut_seconds=cut,expression_start=cut+1.5,expression_end=cut+5.8,expression_method='Generated alternate facial cel, localized blend; not phoneme lip sync',beat_reviewed=False),indent=2))
print(out)
