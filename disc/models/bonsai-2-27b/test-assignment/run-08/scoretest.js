function calc(order){
  const d={D:0,I:0,S:0,C:0};
  order.forEach((t,pos)=>{
    if(pos===0) d[t]=(d[t]||0)+1;
    else if(pos===3) d[t]=(d[t]||0)-1;
  });
  return d;
}
function dominantType(s){
  return ['D','I','S','C'].slice().sort((a,b)=>s[b]-s[a])[0];
}
let r={D:0,I:0,S:0,C:0};
for(let c=0;c<24;c++){
  const card=['D','I','S','C'];
  const a=calc(card);
  r.D+=a.D; r.I+=a.I; r.S+=a.S; r.C+=a.C;
}
console.log('24x[D,I,S,C] ->', r);
console.log('dominant:', dominantType(r));
// opposite ranking
r={D:0,I:0,S:0,C:0};
for(let c=0;c<24;c++){
  const a=calc(['S','C','D','I']);
  r.D+=a.D; r.I+=a.I; r.S+=a.S; r.C+=a.C;
}
console.log('24x[S,C,D,I] ->', r, 'dominant:', dominantType(r));
// one card default (as in original first card): [i,c,d,s]
console.log('one card [i,c,d,s] ->', calc(['i','c','d','s']));
console.log('OK');
