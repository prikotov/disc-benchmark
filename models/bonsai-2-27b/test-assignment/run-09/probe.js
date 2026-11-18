const { WebSocket } = require('ws');
const { spawn } = require('child_process');
const http = require('http');
const PORT = 9239;
const chrome = spawn('google-chrome',['--headless=new','--no-sandbox','--disable-gpu','--remote-debugging-port='+PORT,'--window-size=1400,900',process.cwd()+'/index.html'],{stdio:'ignore'});
function getJson(){return new Promise((res,rej)=>{http.get('http://127.0.0.1:'+PORT+'/json',(r)=>{let d='';r.on('data',c=>d+=c);r.on('end',()=>res(JSON.parse(d)))}).on('error',rej)})}
function poll(){return new Promise((res,rej)=>{let t=0;(function tick(){getJson().then(ts=>{const p=ts.find(x=>x.type==='page'&&x.url&&x.url.includes('index.html'));if(p)return res(p);t++;if(t>40)return rej(new Error('no'));setTimeout(tick,400)}).catch(()=>{t++;if(t>40)return rej();setTimeout(tick,400)})})();})}
poll().then(p=>{
  const ws=new WebSocket(p.webSocketDebuggerUrl);
  ws.on('open',()=>{
    ws.on('message',(m)=>{
      console.log('TYPE:',typeof m,'BUFFER:',Buffer.isBuffer(m),'obj:',m instanceof Object);
      if(Buffer.isBuffer(m)) console.log('utf8:',JSON.stringify(m.toString('utf8')));
      else console.log('objstr:',JSON.stringify(m));
      setTimeout(()=>{ws.close();process.exit(0);},200);
    });
    ws.send(JSON.stringify({id:1,method:'Runtime.enable',params:{}}));
    console.log('sent Runtime.enable');
  });
  ws.on('error',e=>{console.log('ws err',e.message);process.exit(1)});
}).catch(e=>{console.log('poll err',e.message);process.exit(2)});
