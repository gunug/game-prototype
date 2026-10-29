// 퍽 전투 시험판(proto/puck.html)이 쓰는 수치를 본 게임(index.html)에서 뽑는다
//   node tools/puck_data.mjs   →  proto/puck_data.js
// 수치를 손으로 옮기지 않는다 — 본 게임이 바뀌면 다시 돌리면 된다
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const code = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');
function fake(){ const st = {}; return new Proxy(function(){}, { get(_, k){ if (k === Symbol.toPrimitive) return h => h === 'string' ? '' : 0; if (k === 'then') return undefined;
  if (k === Symbol.iterator) return function*(){}; if (k in st) return st[k]; if (k === 'length') return 0; return (st[k] = fake()); }, set(_, k, v){ st[k] = v; return true; }, apply(){ return fake(); }, construct(){ return fake(); } }); }
const mem = new Map();
const ctx = { console: { log(){}, warn(){}, error(){}, info(){} }, Math, JSON, Date, Map, Set, Promise, Object, Array, String, Number, Symbol, Error, RegExp, parseInt, parseFloat, isNaN,
  document: fake(), localStorage: { getItem: k => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, String(v)), removeItem: k => mem.delete(k) },
  performance: { now: () => Date.now() }, innerWidth: 1280, innerHeight: 800, devicePixelRatio: 1,
  setTimeout(){ return 1; }, clearTimeout(){}, setInterval(){ return 1; }, clearInterval(){}, requestAnimationFrame(){ return 1; }, cancelAnimationFrame(){},
  addEventListener(){}, removeEventListener(){}, confirm: () => false, alert(){}, getComputedStyle: () => fake(), matchMedia: () => fake() };
ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx);

const data = vm.runInContext(`(function(){
  const pick = (o, keys) => { const r = {}; for (const k of keys) if (o[k] !== undefined) r[k] = o[k]; return r; };
  const heroes = {};
  for (const k of Object.keys(HERO_KIT)){
    const kit = HERO_KIT[k], base = HERO_BASE(k);
    heroes[k] = { name: PERSON_NAME[k] || base.name, job: base.name, body: kit.body, aps: base.aps || BASE_APS,
      arm: kit.arm, trait: kit.trait, tip: kit.tip,
      slots: slotsFor(k).map(sl => sl.key),
      pic: hPic(k).replace(/^portrait_/, 'bust_'), card: hCard(k) };
  }
  // 장비 — 무기 · 갑옷 · 방패 (장신구 · 소모품은 시험판에서 뺀다)
  const TAGS = { '근접무기':'melee', '도끼':'axe', '창':'spear', '원거리무기':'bow', '방어구':'armor', '방패':'shield' };
  const gear = {};
  for (const [id, d] of Object.entries(DEFS)){
    const tags = useOf(id).map(u => TAGS[u]).filter(Boolean);
    if (!tags.length) continue;
    gear[id] = Object.assign({ name: d.name, tags }, pick(d, ['step', 'atk', 'def', 'spd', 'range', 'rate', 'aps', 'multi', 'pierce', 'bleed', 'shell', 'thorns', 'burnguard']));
  }
  const foes = {};
  for (const [id, e] of Object.entries(ENEMIES))
    foes[id] = pick(e, ['name', 'atk', 'def', 'hp', 'spd', 'aps', 'range', 'regen', 'hits', 'move', 'portrait', 'thorns', 'shell', 'drain', 'burn', 'size']);
  const lands = [];
  for (const f of FIELDS){
    const plan = EXP_PLAN[f.id]; if (!plan) continue;
    const fights = plan.filter(s => s.fight);
    const mob = (fights.find(s => !s.mid && !s.boss) || {}).fight || null;
    const mid = (fights.find(s => s.mid) || {}).fight || null;
    const boss = (fights.find(s => s.boss) || {}).fight || null;
    lands.push({ id: f.id, name: f.name, dungeon: !!f.dungeon, mob, mid, boss });
  }
  const lv = {}; for (const key of ['atk', 'def', 'hp']){ lv[key] = []; for (let i = 1; i <= 40; i++) lv[key].push(lvSumAt(i, key)); }
  return { saveKey: SAVE_KEY, baseRange: BASE_RANGE, baseAps: BASE_APS, heroes, gear, foes, lands, lv,
    armTag: ARM_TAG };
})()`, ctx);

const out = path.join(ROOT, 'proto', 'puck_data.js');
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, '// tools/puck_data.mjs 가 index.html 에서 뽑음 — 손으로 고치지 않는다\nconst PUCK_DATA = ' + JSON.stringify(data, null, 1) + ';\n');
console.log('ok', out, 'heroes', Object.keys(data.heroes).length, 'gear', Object.keys(data.gear).length, 'foes', Object.keys(data.foes).length, 'lands', data.lands.length);
