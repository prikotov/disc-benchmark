const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('pageerror:',e.message));
const widths=[320,360,390,480,600,768,900,1024,1280,1440,1920];
for(const w of widths){
  await p.setViewport({width:w,height:900,deviceScaleFactor:1});
  await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
  await new Promise(r=>setTimeout(r,150));
  const a=await p.evaluate(()=>{
    const rects=(sel)=>[...document.querySelectorAll(sel)].map(e=>{const r=e.getBoundingClientRect();return {t:e.textContent.trim().slice(0,18),x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}});
    return {
      docW:document.documentElement.scrollWidth, inW:window.innerWidth,
      buttons:rects('#screenIntro .btn').filter(r=>r.x<0||r.x+r.w>window.innerWidth+1),
      cards:document.querySelectorAll('.scale-preview').length
    };
  });
  console.log('intro',w,JSON.stringify(a));
}
// test screen audit
for(const w of [320,390,768,1024,1440]){
  await p.setViewport({width:w,height:900,deviceScaleFactor:1});
  await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
  await p.click('#startBtn');
  await new Promise(r=>setTimeout(r,250));
  const a=await p.evaluate(()=>{
    const out=[...document.querySelectorAll('.item__word')].filter(e=>e.scrollWidth>e.clientWidth+1).length;
    const tabs=[...document.querySelectorAll('.tab')];
    const actions=[...document.querySelectorAll('.actions .btn')].filter(e=>!e.hidden).map(e=>{const r=e.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),right:Math.round(r.right)}});
    const items=[...document.querySelectorAll('.pane.is-active .item')];
    const heights=[...new Set(items.map(i=>Math.round(i.getBoundingClientRect().height)))];
    const overlaps=actions.filter(r=>r.right>window.innerWidth+1||r.x<0);
    return {docW:document.documentElement.scrollWidth,inW:window.innerWidth,wordOverflow:out,
      tabOverflowTabs:tabs.filter(t=>t.scrollWidth>t.clientWidth+1).length,
      itemHeights:heights, actions:overlaps,
      grid:getComputedStyle(document.querySelector('.grid')).gridTemplateColumns,
      actionsY:actions.map(a=>a.y), vh:window.innerHeight,
      visibleBtns:[...document.querySelectorAll('.actions .btn')].filter(e=>{const r=e.getBoundingClientRect();return r.top<window.innerHeight&&r.bottom>0}).length};
  });
  console.log('test',w,JSON.stringify(a));
}
// result audit
for(const w of [320,390,768,1440]){
  await p.setViewport({width:w,height:900,deviceScaleFactor:1});
  await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
  await p.click('#startBtn');
  await new Promise(r=>setTimeout(r,200));
  // shuffle deterministically: move 3 items with keyboard on a few lists
  for(let i=0;i<6;i++){
    await p.evaluate((idx)=>{document.querySelectorAll('.pane.is-active .disc-list')[idx%3].children[0].focus();},i);
    await p.keyboard.press('End');
  }
  await p.evaluate(()=>{for(let i=0;i<10;i++){const n=document.getElementById('btnNext');if(n.hidden)break;n.click();}});
  await new Promise(r=>setTimeout(r,200));
  await p.evaluate(()=>{const f=document.getElementById('btnFinish');if(!f.hidden)f.click();});
  await new Promise(r=>setTimeout(r,700));
  const a=await p.evaluate(()=>{
    const rows=[...document.querySelectorAll('.scale')].map(s=>{const t=s.querySelector('.scale__track').getBoundingClientRect();const f=s.querySelector('.scale__fill').getBoundingClientRect();return {v:s.querySelector('.scale__val').textContent, inTrack: f.left>=t.left-1&&f.right<=t.right+1, w:Math.round(f.width), track:Math.round(t.width)}});
    return {docW:document.documentElement.scrollWidth,inW:window.innerWidth,line:document.getElementById('scoreLine').textContent,rows,
      resultH:Math.round(document.getElementById('screenResult').getBoundingClientRect().height)};
  });
  console.log('result',w,JSON.stringify(a));
}
await b.close();
})();
