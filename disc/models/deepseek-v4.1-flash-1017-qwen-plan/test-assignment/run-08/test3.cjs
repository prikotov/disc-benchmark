const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('pageerror:',e.message));
p.on('console',m=>console.log('console:',m.text()));
await p.setViewport({width:390,height:844,isMobile:true,hasTouch:true});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
await p.evaluate(()=>{
  window.__log=[];
  ['pointerdown','pointermove','pointerup','pointercancel','touchstart','touchmove','touchend','dragstart'].forEach(t=>{
    window.addEventListener(t,e=>{window.__log.push(t+':'+(e.pointerType||'')+':'+(e.target.className&&e.target.className.baseVal!==undefined?e.target.className.baseVal:e.target.className));},{capture:true});
  });
});
await p.click('#startBtn');
await new Promise(r=>setTimeout(r,200));
const box=await p.evaluate(()=>{
  const li=document.querySelector('.pane.is-active .disc-list').children[0];
  const h=li.querySelector('.item__handle').getBoundingClientRect();
  const last=li.parentNode.children[3].getBoundingClientRect();
  return {x:h.x+h.width/2,y:h.y+h.height/2,ty:last.y+last.height-4};
});
console.log('box',JSON.stringify(box));
await p.touchscreen.touchStart(box.x,box.y);
for(let i=1;i<=10;i++){await p.touchscreen.touchMove(box.x,box.y+(box.ty-box.y)*i/10);await new Promise(r=>setTimeout(r,25));}
await p.touchscreen.touchEnd();
await new Promise(r=>setTimeout(r,200));
const log=await p.evaluate(()=>window.__log.slice(0,25));
console.log(JSON.stringify(log,null,1));
const order=await p.evaluate(()=>[...document.querySelector('.pane.is-active .disc-list').children].map(li=>li.querySelector('.item__word').textContent));
console.log('order',JSON.stringify(order));
await b.close();
})();
