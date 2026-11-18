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
const st=async()=>p.evaluate(()=>({y:Math.round(window.scrollY),step:document.querySelector('.pane.is-active').dataset.step}));
const drag=async(listIdx)=>{
  const box=await p.evaluate((i)=>{
    const l=document.querySelectorAll('.pane.is-active .disc-list')[i];
    const li=l.children[0];
    const h=li.querySelector('.item__handle').getBoundingClientRect();
    const last=l.children[3].getBoundingClientRect();
    return {x:h.x+h.width/2,y:h.y+h.height/2,ty:last.y+last.height-5};
  },listIdx);
  await p.touchscreen.touchStart(box.x,box.y);
  for(let i=1;i<=12;i++){await p.touchscreen.touchMove(box.x,box.y+(box.ty-box.y)*i/12);await new Promise(r=>setTimeout(r,18));}
  await p.touchscreen.touchEnd();
  await new Promise(r=>setTimeout(r,250));
  return p.evaluate((idx)=>[...document.querySelectorAll('.pane.is-active .disc-list')][idx] && [...document.querySelectorAll('.pane.is-active .disc-list')[idx].children].map(li=>li.dataset.type),listIdx);
};
console.log('before', await st());
console.log('drag list0 ->', await drag(0));
console.log('scroll after drag', await st());
// swipe on handle of on-screen list should not scroll page: record scroll position
const y0=(await st()).y;
await p.evaluate(()=>window.scrollTo(0,300));
await new Promise(r=>setTimeout(r,200));
const y1=(await st()).y;
await p.touchscreen.touchStart(200,300);
await p.touchscreen.touchMove(200,200);
await p.touchscreen.touchEnd();
await new Promise(r=>setTimeout(r,300));
console.log('screen scroll after touch on body:', y1, '->', (await st()).y);
// drag mid-list on step 2 (after next), with settle
await p.click('#btnNext');
await new Promise(r=>setTimeout(r,800));
console.log('step2', await st());
console.log('drag on step2 list1 ->', await drag(1));
// finish on mobile
await p.evaluate(()=>document.querySelectorAll('.tab')[7].click());
await new Promise(r=>setTimeout(r,600));
await p.click('#btnFinish');
await new Promise(r=>setTimeout(r,700));
console.log('result', await p.evaluate(()=>({line:document.getElementById('scoreLine').textContent, visible:!document.getElementById('screenResult').hidden, docW:document.documentElement.scrollWidth})));
await b.close();
})();
