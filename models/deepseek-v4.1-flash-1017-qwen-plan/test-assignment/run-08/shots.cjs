const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('pageerror:',e.message));
p.on('console',m=>{if(m.type()==='error')console.log('console.error:',m.text())});
await p.setViewport({width:1440,height:1000,deviceScaleFactor:1});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
await new Promise(r=>setTimeout(r,300));
await p.screenshot({path:'shot-intro.png'});
await p.click('#startBtn');
await new Promise(r=>setTimeout(r,300));
await p.screenshot({path:'shot-step1.png'});
// drag visual: mid-drag screenshot
const box=await p.evaluate(()=>{
  const li=document.querySelectorAll('.disc-list')[0].children[0];
  const h=li.querySelector('.item__handle').getBoundingClientRect();
  const last=li.parentNode.children[3].getBoundingClientRect();
  return {x:h.x+h.width/2,y:h.y+h.height/2,ty:last.y+last.height-2};
});
await p.mouse.move(box.x,box.y); await p.mouse.down();
for(let i=1;i<=8;i++){await p.mouse.move(box.x,box.y+(box.ty-box.y)*i/8);await new Promise(r=>setTimeout(r,20));}
await p.screenshot({path:'shot-drag.png'});
await p.mouse.up();
// tab 5 view
await p.evaluate(()=>document.querySelectorAll('.tab')[4].click());
await new Promise(r=>setTimeout(r,300));
await p.screenshot({path:'shot-step5.png'});
// finish
await p.evaluate(()=>document.querySelectorAll('.tab')[7].click());
await new Promise(r=>setTimeout(r,200));
await p.click('#btnFinish');
await new Promise(r=>setTimeout(r,800));
await p.screenshot({path:'shot-result.png'});
// 1440x900 full page intro for completeness
await p.setViewport({width:390,height:844,isMobile:true,hasTouch:true,deviceScaleFactor:2});
await p.evaluate(()=>{document.getElementById('restartTop').click();});
await new Promise(r=>setTimeout(r,300));
await p.evaluate(()=>window.scrollTo(0,0));
await p.screenshot({path:'shot-mobile-top.png'});
await b.close();
})();
