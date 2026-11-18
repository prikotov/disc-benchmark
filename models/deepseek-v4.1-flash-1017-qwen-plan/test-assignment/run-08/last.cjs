const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
await p.setViewport({width:1440,height:900});
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
console.log(await p.evaluate(()=>{
  const steps=document.querySelector('.steps');
  const intro=document.getElementById('screenIntro');
  return {
    stepsParent: steps.parentElement.className,
    stepsInsideIntro: intro.contains(steps),
    heroColumns: getComputedStyle(document.querySelector('.hero')).gridTemplateColumns,
    stepCards: document.querySelectorAll('.steps .step').length,
    heights: [...document.querySelectorAll('.step')].map(s=>Math.round(s.getBoundingClientRect().height)),
    introBottom: Math.round(intro.getBoundingClientRect().bottom),
    docH: document.documentElement.scrollHeight
  };
}));
await b.close();
})();
