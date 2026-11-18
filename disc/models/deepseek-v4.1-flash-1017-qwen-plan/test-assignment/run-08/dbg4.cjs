const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('PAGEERROR:',e.message));
await p.setViewport({width:390,height:844,isMobile:true,hasTouch:true,deviceScaleFactor:2});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
await p.click('#startBtn');
await new Promise(r=>setTimeout(r,600));
await p.evaluate(()=>window.scrollTo(0,300));
await new Promise(r=>setTimeout(r,200));
const what=await p.evaluate(()=>{const el=document.elementFromPoint(200,300);return {tag:el.tagName,cls:el.className,scroll:window.scrollY};});
console.log('point', JSON.stringify(what));
for (const dy of [10, 100, 200]) {
  await p.evaluate(()=>window.scrollTo(0,300));
  await new Promise(r=>setTimeout(r,150));
  await p.touchscreen.touchStart(200,300);
  for(let i=1;i<=5;i++){await p.touchscreen.touchMove(200,300-dy*i/5); await new Promise(r=>setTimeout(r,30));}
  await p.touchscreen.touchEnd();
  await new Promise(r=>setTimeout(r,400));
  console.log('dy',dy,'scroll',await p.evaluate(()=>Math.round(window.scrollY)));
}
await b.close();
})();
