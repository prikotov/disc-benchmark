const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('PAGEERROR:',e.message));
await p.setViewport({width:1280,height:900});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
await p.click('#startBtn'); await new Promise(r=>setTimeout(r,200));
await p.evaluate(()=>{for(let i=0;i<10;i++){const n=document.getElementById('btnNext');if(n.hidden)break;n.click();}});
await new Promise(r=>setTimeout(r,200));
await p.click('#btnFinish'); await new Promise(r=>setTimeout(r,400));
await p.click('#btnRestart'); await new Promise(r=>setTimeout(r,200));
await p.setViewport({width:390,height:844,isMobile:true,hasTouch:true,deviceScaleFactor:2});
await new Promise(r=>setTimeout(r,300));
console.log(await p.evaluate(()=>{
  const n=document.getElementById('btnNext');
  const r=n.getBoundingClientRect();
  return {hidden:n.hidden, display:getComputedStyle(n).display, offsetParent:!!n.offsetParent, rect:{x:r.x,y:r.y,w:r.width,h:r.height},
    screenTestHidden:document.getElementById('screenTest').hidden, screenResultHidden:document.getElementById('screenResult').hidden,
    stepHidden:document.getElementById('pane-0').className, actionsDisplay:getComputedStyle(document.querySelector('.actions')).display};
}));
await b.close();
})();
