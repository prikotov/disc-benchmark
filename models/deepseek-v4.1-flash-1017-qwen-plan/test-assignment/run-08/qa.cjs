const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
const msgs=[]; const reqs=[];
p.on('pageerror',e=>msgs.push('PAGEERROR '+e.message));
p.on('console',m=>msgs.push(m.type().toUpperCase()+' '+m.text()));
p.on('request',r=>reqs.push(r.url()));
p.on('requestfailed',r=>msgs.push('REQFAIL '+r.url()));
await p.setViewport({width:1440,height:900});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
await new Promise(r=>setTimeout(r,300));

const geo=await p.evaluate(()=>{
  const overlaps=[];
  document.querySelectorAll('.pane').forEach(pane=>{
    pane.querySelectorAll('.card').forEach(card=>{
      const items=[...card.querySelectorAll('.item')];
      items.forEach(it=>{
        const w=it.querySelector('.item__word').getBoundingClientRect();
        const h=it.querySelector('.item__handle').getBoundingClientRect();
        if (w.right > h.left + 1) overlaps.push('word/handle overlap: '+it.textContent.trim());
      });
      const hs=[...card.querySelectorAll('.item')].map(i=>Math.round(i.getBoundingClientRect().height));
      if (new Set(hs).size>1) overlaps.push('uneven item heights '+hs.join(','));
    });
    const cards=[...pane.querySelectorAll('.card')].map(c=>Math.round(c.getBoundingClientRect().height));
    if (new Set(cards).size>1) overlaps.push('uneven card heights '+cards.join(','));
  });
  return {overlaps:overlaps.slice(0,5), count:overlaps.length};
});
console.log('geometry:', JSON.stringify(geo));

// no-named buttons / links
console.log('a11y:', JSON.stringify(await p.evaluate(()=>{
  const bad=[...document.querySelectorAll('button')].filter(b=>!b.textContent.trim() && !b.getAttribute('aria-label'));
  const imgs=[...document.querySelectorAll('img')];
  const tabs=[...document.querySelectorAll('.tab')].map(t=>t.getAttribute('aria-selected')+':'+t.tabIndex);
  return {unnamedButtons:bad.length, imgs:imgs.length, tabs, lists:document.querySelectorAll('.disc-list').length, itemsPerList:[...document.querySelectorAll('.disc-list')].map(l=>l.children.length).filter(n=>n!==4).length};
})));

// reorder everything a bit, restart twice, verify identical original order & score
const order0=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')].map(l=>[...l.children].map(li=>li.dataset.pos).join('')));
await p.click('#startBtn');
await new Promise(r=>setTimeout(r,200));
for(let i=0;i<5;i++){
  await p.evaluate((k)=>{document.querySelectorAll('.pane.is-active .disc-list')[k%3].children[0].focus();},i);
  await p.keyboard.press('ArrowDown'); await p.keyboard.press('End');
}
const changed=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')].map(l=>[...l.children].map(li=>li.dataset.pos).join('')));
await p.click('#restartTop');
await new Promise(r=>setTimeout(r,200));
const order1=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')].map(l=>[...l.children].map(li=>li.dataset.pos).join('')));
console.log('reset:', JSON.stringify({changedSome: changed.join()!==order0.join(), restored: order0.join()===order1.join()}));

// untouched test score must equal the source example D:-1, I:0, S:-3, C:4
await p.evaluate(()=>document.querySelectorAll('.tab')[7].click());
await new Promise(r=>setTimeout(r,250));
await p.click('#btnFinish');
await new Promise(r=>setTimeout(r,600));
console.log('untouched score:', await p.evaluate(()=>document.getElementById('scoreLine').textContent));
console.log('msgs:', JSON.stringify(msgs));
console.log('requests:', JSON.stringify(reqs));
await b.close();
})();
