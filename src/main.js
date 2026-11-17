import * as THREE from 'three';
import data from '../outputs/target.json';
const audio=document.querySelector('audio'),label=document.querySelector('#label');
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerWidth*9/16);document.body.append(renderer.domElement);
const world=new THREE.Scene();world.background=new THREE.Color('#182534');world.fog=new THREE.Fog('#182534',15,65);
const camera=new THREE.PerspectiveCamera(45,16/9,.1,100);world.add(new THREE.HemisphereLight('#a2bcdb','#352b28',2));
const moon=new THREE.DirectionalLight('#ffe4b0',3);moon.position.set(-5,12,5);world.add(moon);
function box(w,h,d,color,x,y,z){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color,roughness:.8}));m.position.set(x,y,z);world.add(m);return m;}
box(70,.2,70,'#252c31',0,-.2,0);box(7,.05,65,'#101e2c',0,0,0);
for(let i=0;i<24;i++){const z=12-i*2.8;for(const side of [-1,1]){const h=3+(i*7%8);box(3,h,2.4,i%2?'#55483f':'#3b4650',side*7,h/2,z);for(let j=1;j<h;j+=1.4)box(.55,.6,.06,'#c99e53',side*7,j,z+1.23);}}
const stars=new THREE.BufferGeometry();const points=[];for(let i=0;i<300;i++)points.push(Math.sin(i*133)*45,12+(i%19),Math.cos(i*71)*45);stars.setAttribute('position',new THREE.Float32BufferAttribute(points,3));world.add(new THREE.Points(stars,new THREE.PointsMaterial({size:.09,color:'#eddfbf'})));
const edits=data.proposed_edit.cuts;const poses=[[0,4,17,0,3,-12],[-3,2,7,-7,3,-6],[5,5,3,7,4,-5],[0,9,21,0,1,-15]];
renderer.setAnimationLoop(()=>{const t=audio.currentTime;let shot=0;while(shot+1<edits.length&&edits[shot+1].time<=t)shot++;const e=edits[shot],p=poses[shot%poses.length],dt=t-e.time;camera.position.set(p[0]+Math.sin(dt*.1)*.4,p[1],p[2]-Math.min(dt*.12,2));camera.lookAt(p[3],p[4],p[5]);label.textContent=`Shot ${shot+1}/${edits.length} · ${t.toFixed(1)}s · ${e.scene}`;renderer.render(world,camera);});
addEventListener('resize',()=>renderer.setSize(innerWidth,innerWidth*9/16));
