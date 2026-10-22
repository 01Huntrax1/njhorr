const fs=require('fs');
const src=fs.readFileSync('/home/claude/njhorr/patch/index.js','utf8');
const a=src.indexOf('const LFO_DRAWN'), b=src.indexOf('const MOD_SRC_SHORT');
const code=src.slice(a,b)+';return {lfoBuiltinPts,lfoTableFromPts,LFO_PRESETS};';
const {lfoBuiltinPts,lfoTableFromPts,LFO_PRESETS}=new Function(code)();
const lines=fs.readFileSync('/tmp/shots_modt/tables.txt','utf8').trim().split('\n');
let bad=0,max=0;
let pi=0;
lines.forEach(l=>{const t=l.split(' ');const n=t.shift();const v=t.map(Number);
 let ref;
 if(n[0]=='b') ref=lfoTableFromPts(lfoBuiltinPts(+n[1]));
 else ref=lfoTableFromPts(LFO_PRESETS[+n.slice(1)].pts);
 let m=0; for(let i=0;i<256;i++) m=Math.max(m,Math.abs(v[i]-ref[i]));
 max=Math.max(max,m); if(m>2e-5){bad++;console.log('DIFF',n,m);}
});
console.log(lines.length,'tables, bad',bad,'max diff',max);
