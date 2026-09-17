// 기본 오류 검사 — 브라우저 없이 index.html 스크립트를 확인
//   1) 문법 검사 (node --check 와 같음)
//   2) 가짜 DOM에서 시작 코드 실행 → 선언 순서(TDZ)·없는 변수 같은 시작 오류
//   3) 등록된 타이머·rAF 콜백을 한 번씩 실행 → 그 안의 오류
// 사용: node tools/check.mjs  (게임 폴더에서)
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let fail = 0;
const report = (step, e) => { fail++; console.log(`✗ ${step}: ${e && e.stack ? e.stack.split('\n').slice(0, 3).join('\n  ') : e}`); };

// 1) 문법
const code = scripts.join('\n;\n');
try { new vm.Script(code, { filename: 'index.html<script>' }); console.log(`✓ 문법 (스크립트 ${scripts.length}개)`); }
catch (e){ report('문법', e); process.exit(1); }

// 2) 가짜 DOM: 무엇을 읽든 호출하든 또 가짜를 돌려줌. 숫자·문자로 쓰면 0/''
function fake(name = 'fake'){
  const store = {};
  return new Proxy(function(){}, {
    get(_, k){
      if (k === Symbol.toPrimitive) return hint => hint === 'string' ? '' : 0;
      if (k === 'then') return undefined;
      if (k === Symbol.iterator) return function*(){};
      if (k in store) return store[k];
      if (k === 'length') return 0;
      return (store[k] = fake(`${name}.${String(k)}`));
    },
    set(_, k, v){ store[k] = v; return true; },
    apply(){ return fake(`${name}()`); },
    construct(){ return fake(`new ${name}`); },
  });
}
const timers = [];
const mem = new Map();
const doc = fake('document');
const ctx = {
  console, Math, JSON, Date, Map, Set, Promise, Object, Array, String, Number, Symbol, Error, RegExp, parseInt, parseFloat, isNaN,
  document: doc,
  localStorage: { getItem: k => mem.has(k) ? mem.get(k) : null, setItem: (k, v) => mem.set(k, String(v)), removeItem: k => mem.delete(k) },
  performance: { now: () => Date.now() },
  innerWidth: 1280, innerHeight: 800, devicePixelRatio: 1,
  setTimeout: (f) => { timers.push(f); return timers.length; }, clearTimeout(){},
  setInterval: (f) => { timers.push(f); return timers.length; }, clearInterval(){},
  requestAnimationFrame: (f) => { timers.push(f); return timers.length; }, cancelAnimationFrame(){},
  addEventListener(){}, removeEventListener(){}, confirm: () => false, alert(){},
  getComputedStyle: () => fake('style'), matchMedia: () => fake('mql'),
};
ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
try { vm.runInContext(code, ctx, { filename: 'index.html<script>' }); console.log('✓ 시작 실행'); }
catch (e){ report('시작 실행', e); }

// 3) 타이머 콜백 한 번씩 (새로 등록되는 건 안 돌림)
const once = timers.splice(0);
for (const f of once){
  try { const r = f(16); if (r && typeof r.catch === 'function') r.catch(e => report('타이머(async)', e)); }
  catch (e){ report('타이머', e); }
}
console.log(`✓ 타이머·rAF 콜백 ${once.length}개 실행`);
setTimeout(() => { console.log(fail ? `\n오류 ${fail}개` : '\n오류 없음'); process.exit(fail ? 1 : 0); }, 50);
