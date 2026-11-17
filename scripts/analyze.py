"""Repeatable audio/video measurements and beat-relative edit transfer."""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
import librosa
import imageio_ffmpeg

def audio(path, out):
    wav = out.with_suffix('.wav')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', str(path), '-vn', '-ac', '1', '-ar', '22050', str(wav)], check=True, capture_output=True)
    y, sr = librosa.load(wav, sr=22050)
    hop = 512
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop)
    beats = librosa.frames_to_time(frames, sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
    attacks = librosa.onset.onset_detect(onset_envelope=onset, sr=sr, hop_length=hop, units='time')
    # Fixed quarter-second samples make cross-song comparisons manageable.
    ts = np.arange(0, len(y)/sr, .25)
    idx = np.minimum((ts*sr/hop).astype(int), len(rms)-1)
    result = dict(duration=len(y)/sr, tempo_bpm=float(np.asarray(tempo).flat[0]), beats=beats.tolist(), onsets=attacks.tolist(), energy=[dict(time=float(t), rms=float(rms[i]), brightness_hz=float(centroid[i])) for t,i in zip(ts,idx)], reviewed=False)
    return result

def video(path, music):
    import cv2
    from scenedetect import detect, AdaptiveDetector
    scenes = detect(str(path), AdaptiveDetector(min_scene_len=8))
    cuts = [s[0].get_seconds() for s in scenes[1:]]
    beats = np.array(music['beats'])
    offsets = [float(np.min(abs(beats-c))) for c in cuts] if len(beats) else []
    boundaries = [0]+cuts+[music['duration']]
    spans = np.diff(np.interp(boundaries, beats, np.arange(len(beats)))) if len(beats)>1 else []
    cap = cv2.VideoCapture(str(path)); fps=cap.get(cv2.CAP_PROP_FPS)
    rows=[]; previous=None; frame=0
    while True:
        ok, im=cap.read()
        if not ok: break
        if frame % max(1,round(fps/4)) == 0:
            small=cv2.resize(im,(160,90)); hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
            gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
            motion=None
            if previous is not None:
                flow=cv2.calcOpticalFlowFarneback(previous,gray,None,.5,3,15,3,5,1.2,0)
                motion=float(np.median(np.linalg.norm(flow,axis=2)))
            rows.append(dict(time=frame/fps,brightness=float(hsv[:,:,2].mean()/255),saturation=float(hsv[:,:,1].mean()/255),motion_pixels_per_sample=motion))
            previous=gray
        frame+=1
    cap.release()
    return dict(cuts=cuts,shot_lengths_seconds=np.diff(boundaries).tolist(),shot_lengths_beats=list(map(float,spans)),median_cut_to_beat_seconds=float(np.median(offsets)) if offsets else None,fraction_cuts_within_100ms_of_beat=float(np.mean(np.array(offsets)<=.1)) if offsets else None,visual_samples=rows,reviewed=False)

def main():
    p=argparse.ArgumentParser(); p.add_argument('input',type=Path); p.add_argument('--out',type=Path,required=True); p.add_argument('--video',action='store_true'); p.add_argument('--reference',type=Path)
    a=p.parse_args(); a.out.parent.mkdir(parents=True,exist_ok=True)
    data=dict(source=str(a.input),method='librosa audio; PySceneDetect adaptive cuts; OpenCV optical flow',audio=audio(a.input,a.out))
    if a.video: data['video']=video(a.input,data['audio'])
    if a.reference:
        ref=json.loads(a.reference.read_text()); spans=ref['video']['shot_lengths_beats']; spans=[s for s in spans if s>=1]
        if not spans: raise ValueError('Reference has no usable beat-relative shots')
        beats=data['audio']['beats']; events=[]; pos=0.; k=0
        while pos<len(beats)-1:
            t=float(np.interp(pos,np.arange(len(beats)),beats))
            events.append(dict(time=t,beat_position=pos,shot=k,scene=['river','street','window','stage'][k%4]))
            pos+=spans[k%len(spans)]; k+=1
        data['proposed_edit']=dict(method='Repeat observed shot durations in beat units against target beat map; creative proposal, not verified correspondence',cuts=events,reviewed=False)
    a.out.write_text(json.dumps(data,indent=2))
    print(json.dumps(dict(output=str(a.out),duration=data['audio']['duration'],bpm=data['audio']['tempo_bpm'],beats=len(data['audio']['beats']),cuts=len(data.get('video',{}).get('cuts',[])),proposed_shots=len(data.get('proposed_edit',{}).get('cuts',[]))),indent=2))
if __name__=='__main__': main()
