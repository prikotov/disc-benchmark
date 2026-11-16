const path=require('path');
const puppeteer=require('/home/dp/.npm-global/lib/node_modules/puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
const p=await b.newPage();
p.on('pageerror',e=>console.log('PAGEERROR:',e.message));
p.on('console',m=>console.log('console['+m.type()+']:',m.text()));
await p.goto('file://'+path.resolve('index.html'),{waitUntil:'load'});
console.log(await p.evaluate(()=>({
  tabs:document.querySelectorAll('.tab').length,
  lists:document.querySelectorAll('.disc-list').length,
  items:document.querySelectorAll('.item').length,
  firstItem:document.querySelector('.item') && document.querySelector('.item').outerHTML.slice(0,150),
  hands:document.querySelectorAll('.item__handle').length,
  testHidden:document.getElementById('screenTest').hidden,
  startBtn: !!document.getElementById('startBtn')
})));
await b.close();
})();
