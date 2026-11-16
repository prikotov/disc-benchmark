const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('pageerror:',e.message));
for(const [w,h] of [[320,640],[390,844],[768,1024]]){
  await p.setViewport({width:w,height:h,isMobile:w<800,hasTouch:w<800,deviceScaleFactor:1});
  await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
  await p.click('#startBtn');
  await new Promise(r=>setTimeout(r,300));
  const res=[];
  for(const y of [0,400,900,100000]){
    await p.evaluate(yy=>window.scrollTo(0,yy),y);
    await new Promise(r=>setTimeout(r,120));
    res.push(await p.evaluate(()=>{
      const n=document.getElementById('btnNext').getBoundingClientRect();
      const pr=document.getElementById('btnPrev').getBoundingClientRect();
      return {y:Math.round(window.scrollY), nextTop:Math.round(n.top), nextBottom:Math.round(n.bottom), prevBottom:Math.round(pr.bottom), vh:window.innerHeight, docW:document.documentElement.scrollWidth};
    }));
  }
  console.log(w+'x'+h, JSON.stringify(res));
  // sticky bar must not cover the last item when scrolled to the very bottom
  const cover=await p.evaluate(()=>{
    window.scrollTo(0,document.body.scrollHeight);
    const items=[...document.querySelectorAll('.pane.is-active .item')];
    const last=items[items.length-1].getBoundingClientRect();
    const bar=document.querySelector('.actions').getBoundingClientRect();
    return {lastBottom:Math.round(last.bottom), barTop:Math.round(bar.top), overlap: last.bottom>bar.top};
  });
  console.log(' bottom-overlap', JSON.stringify(cover));
}
await b.close();
})();
