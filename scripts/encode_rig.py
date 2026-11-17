"""Encode deterministic browser frames with the existing song excerpt."""
import subprocess
import imageio_ffmpeg
ff=imageio_ffmpeg.get_ffmpeg_exe()
out='outputs/blues-rig-proof-v1.mp4'
subprocess.run([ff,'-y','-framerate','24','-i','outputs/rig-frames/%04d.png','-ss','12','-i','media/st-louis-blues.mp3','-t','12','-vf','scale=1280:720','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','afade=t=out:st=11:d=1','-movflags','+faststart',out],check=True,capture_output=True)
subprocess.run([ff,'-v','error','-i',out,'-f','null','-'],check=True)
print(out)
