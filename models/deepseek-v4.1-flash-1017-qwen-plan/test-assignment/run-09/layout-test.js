const puppeteer = require('puppeteer-core');
const path = require('path');
(async () => {
  const browser = await puppeteer.launch({executablePath:'/usr/bin/google-chrome', headless:'new', args:['--no-sandbox','--disable-gpu']});
  const page = await browser.newPage();
  const errors=[]; page.on('pageerror', e=>errors.push(e.message)); page.on('console', m=>{if(m.type()==='error')errors.push(m.text())});
  await page.goto('file://'+path.resolve('index.html'), {waitUntil:'load'});

  // desktop layout
  await page.setViewport({width:1440,height:1000});
  await page.click('[data-disc-open]');
  await new Promise(r=>setTimeout(r,200));
  let layout = await page.evaluate(() => {
    const d=document.querySelector('.disc-modal__dialog').getBoundingClientRect();
    const f=document.querySelector('.disc-modal__footer').getBoundingClientRect();
    const body=document.querySelector('.disc-modal__body').getBoundingClientRect();
    return {dialog:[d.x,d.y,d.width,d.height], footerBottom:f.bottom, bodyH:body.height,
      docScrollW:document.documentElement.scrollWidth, winW:innerWidth,
      activeTabs:document.querySelectorAll('.disc-tab.is-active').length,
      visiblePanes:[...document.querySelectorAll('.disc-pane')].filter(p=>!p.hidden).length,
      itemCount:document.querySelectorAll('.disc-item').length};
  });
  console.log('desktop', JSON.stringify(layout));

  // tab navigation + keyboard
  await page.click('[data-step-btn="3"]');
  console.log('jump step', await page.$eval('#rootwizard', e=>e.dataset.step), 'prevDisabled', await page.$eval('[data-disc-prev]',e=>e.disabled));
  const firstHandle=await page.$('#draggable-list10 .disc-handle');
  await firstHandle.focus();
  await page.keyboard.press('ArrowDown');
  console.log('keyboard order', await page.$$eval('#draggable-list10 .disc-item', els=>els.map(e=>e.textContent.trim())));

  // touch-like synthetic drag via handle
  await page.evaluate(() => {
    const h=document.querySelector('#draggable-list10 .disc-handle');
    const r=h.getBoundingClientRect();
    const opts={bubbles:true,cancelable:true,pointerId:77,pointerType:'touch',isPrimary:true,button:0,buttons:1,clientX:r.left+5,clientY:r.top+5};
    h.dispatchEvent(new PointerEvent('pointerdown',opts));
    document.dispatchEvent(new PointerEvent('pointermove',{...opts,clientY:r.top+180}));
    document.dispatchEvent(new PointerEvent('pointerup',{...opts,buttons:0,clientY:r.top+180}));
  });
  console.log('touch-like order', await page.$$eval('#draggable-list10 .disc-item', els=>els.map(e=>e.textContent.trim())));

  // mobile layout
  await page.setViewport({width:390,height:844,isMobile:true,hasTouch:true,deviceScaleFactor:2});
  await page.reload({waitUntil:'load'});
  await page.click('[data-disc-open]');
  await new Promise(r=>setTimeout(r,250));
  let mlayout = await page.evaluate(() => {
    const d=document.querySelector('.disc-modal__dialog').getBoundingClientRect();
    const f=document.querySelector('.disc-modal__footer').getBoundingClientRect();
    return {dialog:[d.x,d.y,d.width,d.height],footerBottom:f.bottom,winW:innerWidth,winH:innerHeight,
      docScrollW:document.documentElement.scrollWidth,
      gridCols:getComputedStyle(document.querySelector('.disc-grid3')).gridTemplateColumns,
      tabScrolls:document.querySelector('.disc-modal__tabs').scrollWidth>document.querySelector('.disc-modal__tabs').clientWidth};
  });
  console.log('mobile', JSON.stringify(mlayout));
  await page.screenshot({path:'shot-mobile-step1.png',fullPage:false});

  // go to last step, finish, check result mobile
  for(let i=0;i<7;i++){await page.click('[data-disc-next]'); await new Promise(r=>setTimeout(r,60));}
  await page.click('[data-disc-finish]');
  await new Promise(r=>setTimeout(r,250));
  const mresult=await page.evaluate(()=>({score:document.querySelector('#scoreText').textContent, visible:!document.querySelector('#resultView').hidden, scrollW:document.querySelector('.result-view').scrollWidth, clientW:document.querySelector('.result-view').clientWidth}));
  console.log('mobile result', JSON.stringify(mresult));
  await page.screenshot({path:'shot-mobile-result.png',fullPage:false});

  console.log('errors',JSON.stringify(errors));
  await browser.close();
})();
