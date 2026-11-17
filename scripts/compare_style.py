"""Compare matched excerpts; affine registration gives motion proxies, not semantic labels."""
import json
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def movement(path,cuts):
    cap=cv2.VideoCapture(str(path)); fps=cap.get(cv2.CAP_PROP_FPS)
    prev=None; rows=[]; n=0
    while True:
        ok,im=cap.read()
        if not ok:break
        if n%max(1,round(fps/12)):
            n+=1;continue
        t=n/fps; gray=cv2.cvtColor(cv2.resize(im,(320,180)),cv2.COLOR_BGR2GRAY)
        if prev is not None and not any(pt<c<=t for c in cuts):
            flow=cv2.calcOpticalFlowFarneback(prev,gray,None,.5,3,15,3,5,1.2,0)
            ys,xs=np.mgrid[8:180:12,8:320:12]
            src=np.stack([xs.ravel(),ys.ravel()],axis=1).astype(np.float32)
            dst=src+flow[ys,xs].reshape(-1,2)
            affine,inliers=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=.6)
            if affine is not None:
                prediction=src@affine[:,:2].T+affine[:,2]
                residual=np.linalg.norm(dst-prediction,axis=1)
                rows.append(dict(time=t,global_displacement_px=float(np.median(np.linalg.norm(prediction-src,axis=1))),residual_p90_px=float(np.percentile(residual,90)),moving_area_fraction=float(np.mean(residual>.25))))
        prev=gray;pt=t;n+=1
    cap.release()
    return dict(samples=rows,median_global_displacement_px=float(np.median([r['global_displacement_px'] for r in rows])),median_residual_p90_px=float(np.median([r['residual_p90_px'] for r in rows])),low_residual_sample_fraction=float(np.mean([r['residual_p90_px']<.15 for r in rows])))

result={}
for name,analysis,media in [('Daft Punk excerpt','daft-excerpt.json','media/daft-excerpt.mp4'),('Our proof','proof-analysis.json','outputs/blues-motion-proof-v1.mp4')]:
    d=json.loads((ROOT/'outputs'/analysis).read_text());v=d['video'];s=v['visual_samples'];
    if name=='Daft Punk excerpt':
        notes=json.loads((ROOT/'outputs/daft-annotations.json').read_text())
        v['cuts']=notes['reviewed_cut_times_relative_seconds']
        v['shot_lengths_seconds']=np.diff([0]+v['cuts']+[d['audio']['duration']]).tolist()
        b=np.array(d['audio']['beats'])
        v['fraction_cuts_within_100ms_of_beat']=float(np.mean([np.min(abs(b-c))<=.1 for c in v['cuts']])) if len(b) else None
    result[name]=dict(duration=d['audio']['duration'],cut_times=v['cuts'],cuts=len(v['cuts']),median_shot_seconds=float(np.median(v['shot_lengths_seconds'])),cuts_per_minute=len(v['cuts'])/d['audio']['duration']*60,beat_alignment=v['fraction_cuts_within_100ms_of_beat'],median_motion=float(np.median([r['motion_pixels_per_sample'] for r in s if r['motion_pixels_per_sample'] is not None])),mean_brightness=float(np.mean([r['brightness'] for r in s])),mean_saturation=float(np.mean([r['saturation'] for r in s])),motion_registration=movement(ROOT/media,v['cuts']))
(ROOT/'outputs/daft-comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:{a:b for a,b in v.items() if a!='motion_registration'}|{'registration_summary':{a:b for a,b in v['motion_registration'].items() if a!='samples'}} for k,v in result.items()},indent=2))
