const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
const errs=[]; p.on('pageerror',e=>errs.push(e.message));
await p.setViewport({width:1280,height:900});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
await p.click('#startBtn');
await new Promise(r=>setTimeout(r,200));
// each list must contain exactly one of each type
const dist=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')].map(l=>[...l.children].map(li=>li.dataset.type).sort().join('')));
console.log('distinct types per list all "cd is":', dist.every(d=>d==='cdis'), new Set(dist).size);
// sort every list to d,i,s,c order via DOM then finish
await p.evaluate(()=>{
  document.querySelectorAll('.disc-list').forEach(l=>{
    const items=[...l.children];
    ['d','i','s','c'].forEach(t=>{const it=items.find(x=>x.dataset.type===t); if(it) l.appendChild(it);});
  });
});
await p.evaluate(()=>{for(let i=0;i<10;i++){const n=document.getElementById('btnNext');if(n.hidden)break;n.click();}});
await new Promise(r=>setTimeout(r,150));
await p.click('#btnFinish');
await new Promise(r=>setTimeout(r,700));
console.log(await p.evaluate(()=>({
  line: document.getElementById('scoreLine').textContent,
  rows: [...document.querySelectorAll('.scale')].map(s=>({t:s.dataset.type, v:s.querySelector('.scale__val').textContent, fill:s.querySelector('.scale__fill').style.cssText, neg:s.classList.contains('is-neg')}))
})));
await p.screenshot({path:'shot-result-forced.png'});
// go back to answers, then finish again -> same score
await p.click('#btnFine');
await new Promise(r=>setTimeout(r,600));
const backTo=await p.evaluate(()=>({testVisible:!document.getElementById('screenTest').hidden, step:document.querySelector('.pane.is-active').dataset.step, tab:document.querySelector('.tab.is-active').textContent, finishHidden:document.getElementById('btnFinish').hidden}));
console.log('back to answers:', JSON.stringify(backTo));
await p.click('#btnFinish');
await new Promise(r=>setTimeout(r,500));
console.log('re-finish line:', await p.evaluate(()=>document.getElementById('scoreLine').textContent));
// drag then prev/next keeps order
await p.click('#btnRestart');
await new Promise(r=>setTimeout(r,200));
const box=await p.evaluate(()=>{const li=document.querySelectorAll('.disc-list')[2].children[0];const h=li.querySelector('.item__handle').getBoundingClientRect();const last=li.parentNode.children[3].getBoundingClientRect();return {x:h.x+h.width/2,y:h.y+h.height/2,ty:last.y+last.height-3};});
await p.mouse.move(box.x,box.y); await p.mouse.down();
for(let i=1;i<=10;i++){await p.mouse.move(box.x,box.y+(box.ty-box.y)*i/10);await new Promise(r=>setTimeout(r,15));}
await p.mouse.up();
const before=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')[2].children].map(li=>li.dataset.type));
await p.click('#btnNext'); await new Promise(r=>setTimeout(r,300));
await p.click('#btnPrev'); await new Promise(r=>setTimeout(r,300));
const after=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')[2].children].map(li=>li.dataset.type));
console.log('order preserved across steps:', JSON.stringify(before), JSON.stringify(after), JSON.stringify(before)===JSON.stringify(after));
console.log('errors:', JSON.stringify(errs));
await b.close();
})();
