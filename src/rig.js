import song from '../outputs/song.json';
const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
const audio=document.querySelector('audio'),status=document.querySelector('#status');
const load=src=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(Error(`Missing asset: ${src}`));im.src=src;});
const [atlas,bg]=await Promise.all([load('/art/singer-rig-atlas-v1.png'),load('/art/blues-empty-club-v1.png')]);
// Source rectangles are trimmed inside fixed atlas cells. Original alpha remains intact.
const scratch=document.createElement('canvas');scratch.width=atlas.width;scratch.height=atlas.height;
const sc=scratch.getContext('2d');sc.drawImage(atlas,0,0);const pixels=sc.getImageData(0,0,atlas.width,atlas.height).data;
const names=['torso','head','singing','leftArm','rightArm','microphone'];
const pieces={};
names.forEach((name,i)=>{const cw=atlas.width/3,ch=atlas.height/2;const ox=Math.round((i%3)*cw),oy=Math.round(Math.floor(i/3)*ch);let x0=atlas.width,y0=atlas.height,x1=0,y1=0;
for(let y=oy;y<Math.floor(oy+ch);y++)for(let x=ox;x<Math.floor(ox+cw);x++)if(pixels[(y*atlas.width+x)*4+3]>40){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}
if(x1<=x0||y1<=y0)throw Error(`Empty atlas cell: ${name}`);
pieces[name]={x:x0,y:y0,w:x1-x0+1,h:y1-y0+1};});
function piece(name,x,y,h,angle=0,ax=.5,ay=0){const p=pieces[name],w=p.w*h/p.h;ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.drawImage(atlas,p.x,p.y,p.w,p.h,-ax*w,-ay*h,w,h);ctx.restore();}
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function smooth(t,a,b){const x=clamp((t-a)/(b-a),0,1);return x*x*(3-2*x);}
const rms=song.audio.energy.map(e=>e.rms).sort((a,b)=>a-b);const norm=rms[Math.floor(rms.length*.95)];
let demo=false;
window.renderRig=(time,options={})=>{
const t=clamp(time,0,song.audio.duration),local=t-12;
const energy=song.audio.energy[Math.min(song.audio.energy.length-1,Math.floor(t/.25))]?.rms||0;
const amount=(options.strength??Number(document.querySelector('#strength').value))*clamp(energy/norm,.15,1);
let mode=options.camera??document.querySelector('#camera').value;
if(mode==='auto')mode=local<4?'medium':local<8?'close':'medium';
ctx.clearRect(0,0,1280,720);ctx.drawImage(bg,0,0,1280,720);
if(document.querySelector('#atlas').checked&&!options.export){ctx.fillStyle='#737a84';ctx.fillRect(0,0,1280,720);ctx.drawImage(atlas,100,0,1080,720);return;}
const zoom=mode==='close'?1.55:mode==='wide'?.95:1;
ctx.save();ctx.translate(640,mode==='close'?430:470);ctx.scale(zoom,zoom);ctx.translate(-640,-470);
// Pivot hierarchy: waist -> torso -> shoulder joints / neck -> head.
ctx.save();ctx.translate(640,745);ctx.rotate(Math.sin(t*.75)*.012);ctx.translate(0,-310);
const gesture=smooth(local,1,3)*(1-smooth(local,6,8));
const left=-.05+Math.sin(t*1.2)*.035*amount;
const right=.09+gesture*.60*amount;
// Arms are drawn behind torso so rounded shoulder overlaps are concealed.
piece('leftArm',-82,65,270,left,.5,.04);
piece('rightArm',82,65,270,-right,.18,.04);
piece('torso',0,0,310,0,.5,0);
const blink=(t%4.7)<.17;const singing=energy>norm*.38&&Math.sin(t*5)>.25;
const head=blink||singing?'singing':'head';
piece(head,0,7,175,Math.sin(t*.62)*.055+gesture*.035,.5,.92);
if(document.querySelector('#guides').checked&&!options.export){ctx.fillStyle='#57ffdb';for(const [x,y]of [[0,7],[-82,65],[82,65],[0,310]]){ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();}}
ctx.restore();
piece('microphone',780,360,490,0,.5,0);
ctx.restore();
status.textContent=`${t.toFixed(2)}s · energy ${(amount).toFixed(2)} · ${mode} · reusable head / torso / arms / microphone`;
};
window.rigReady=true;
document.querySelector('#demo').onclick=()=>{audio.currentTime=12;demo=true;audio.play();};
function tick(){if(demo&&audio.currentTime>=24){audio.pause();demo=false;}window.renderRig(audio.currentTime||12);requestAnimationFrame(tick);}tick();
