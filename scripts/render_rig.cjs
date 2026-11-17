const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1400,height:1100},deviceScaleFactor:1});
page.on('pageerror',e=>console.error(e));
await page.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
await page.goto(process.env.RIG_URL||'http://127.0.0.1:5173/rig.html');
await page.waitForFunction(()=>window.rigReady,{timeout:30000});
fs.mkdirSync('outputs/rig-frames',{recursive:true});
const preview=process.argv.includes('--preview');
const frames=preview?[0,100,200]:Array.from({length:288},(_,i)=>i);
for(const i of frames){await page.evaluate(t=>window.renderRig(t,{export:true}),12+i/24);await page.locator('canvas').screenshot({path:`outputs/rig-frames/${String(i).padStart(4,'0')}.png`});}
await page.screenshot({path:'outputs/rig-ui.png'});
await browser.close();
console.log(`Captured ${frames.length} frames`);
})();
