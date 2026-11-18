const puppeteer=require('puppeteer-core'); const path=require('path');
(async()=>{
 const b=await puppeteer.launch({executablePath:'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
 const p=await b.newPage(); await p.goto('file://'+path.resolve('index.html'));
 const dom=await p.evaluate(()=>[...document.querySelectorAll('.disc-list')].map(ul=>[...ul.children].map(li=>[li.getAttribute('data-type'),li.innerText.trim()])));
 console.log(JSON.stringify(dom));
 await b.close();
})();
