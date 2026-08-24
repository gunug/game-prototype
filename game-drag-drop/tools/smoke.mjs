/**
 * index.html 을 실제로 실행해 보는 스모크 테스트.
 *
 *   node tools/smoke.mjs
 *
 * 문법만 보는 검사는 "정의가 통째로 사라진" 종류의 사고를 못 잡는다.
 * generate.py --apply 가 스테이지 블록을 통째로 갈아치우기 때문에, 그 블록
 * 안에 있는 readField 가 같이 날아가도 파싱은 통과해 버린다. 그래서 DOM 을
 * 최소한만 흉내내고 스크립트를 끝까지 돌린 뒤 눈에 보여야 할 것을 센다.
 *
 * 드래그는 실제로 흉내낸다. 판 칸 크기를 알고 있으니 좌표를 만들어
 * pointerdown -> pointermove -> pointerup 을 그대로 쏘면 된다.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GAME = path.join(HERE, '..', 'index.html');

/* ── 최소 DOM ── */

class Style {
  setProperty(name, value) { this[name] = String(value); }
  removeProperty(name) { delete this[name]; }
}

class ClassList {
  constructor() { this.set = new Set(); }
  add(...n) { n.forEach((x) => this.set.add(x)); }
  remove(...n) { n.forEach((x) => this.set.delete(x)); }
  contains(n) { return this.set.has(n); }
  toggle(n, on) { (on ? this.set.add(n) : this.set.delete(n)); }
}

class El {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.style = new Style();
    this.classList = new ClassList();
    this.attrs = {};
    this.handlers = {};
    this.textContent = '';
    this.rect = { left: 0, top: 0, width: 800, height: 800 };
  }
  get className() { return [...this.classList.set].join(' '); }
  set className(v) { this.classList.set = new Set(String(v).split(/\s+/).filter(Boolean)); }
  appendChild(node) {
    if (node instanceof Frag) { node.children.forEach((c) => this.children.push(c)); return node; }
    this.children.push(node);
    return node;
  }
  append(...nodes) { nodes.forEach((n) => this.appendChild(n)); }
  replaceChildren(...nodes) { this.children = []; nodes.forEach((n) => n && this.appendChild(n)); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  addEventListener(type, fn) { (this.handlers[type] ??= []).push(fn); }
  dispatch(type, event) { (this.handlers[type] || []).forEach((fn) => fn(event)); }
  setPointerCapture() {}
  releasePointerCapture() {}
  closest() { return null; }
  getBoundingClientRect() { return this.rect; }
}

class Frag extends El {
  constructor() { super('#fragment'); }
}

const nodes = {};
for (const id of ['select', 'play', 'cards', 'progress', 'grid', 'board',
                  'outline', 'outline-path', 'tray', 'ghost', 'banner',
                  'stage-name', 'left', 'back', 'next', 'reset']) {
  nodes[id] = new El('div');
  nodes[id].attrs.id = id;
}

const store = new Map();
const sandbox = {
  document: {
    getElementById: (id) => nodes[id] ?? null,
    createElement: (tag) => new El(tag),
    createDocumentFragment: () => new Frag(),
  },
  window: { addEventListener() {}, innerWidth: 900, innerHeight: 900 },
  localStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
  },
  console,
};
sandbox.window.localStorage = sandbox.localStorage;

/* ── 실행 ── */

const html = fs.readFileSync(GAME, 'utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const css = html.match(/<style>([\s\S]*?)<\/style>/)[1];

const fails = [];
const check = (label, ok, detail = '') => {
  console.log(`  ${ok ? 'OK  ' : '실패'} ${label}${detail ? ' — ' + detail : ''}`);
  if (!ok) fails.push(label);
};

/**
 * 조상 없는 `.foo{position:absolute}` 같은 전역 규칙은 그 클래스를 쓰는 다른
 * 곳까지 끌고 간다. 카드가 쓰는 클래스와 겹치면 카드가 엉뚱한 자리로 튄다.
 */
{
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const relocating = new Set();
  for (const [, sel, body] of bare.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    if (!/position\s*:\s*(absolute|fixed)/.test(body)) continue;
    for (const one of sel.split(',')) {
      const m = one.trim().match(/^\.([\w-]+)(?:[.:][\w-]+)*$/);
      if (m) relocating.add(m[1]);
    }
  }
  const cardClasses = ['row', 'title', 'meta', 'check', 'mini', 'item'];
  const clash = cardClasses.filter((c) => relocating.has(c));
  check('자리를 옮기는 전역 클래스 규칙 없음', clash.length === 0, clash.join(' '));
}

let run;
try {
  run = new Function(...Object.keys(sandbox), js);
  run(...Object.values(sandbox));
} catch (err) {
  console.log(`  실패 스크립트 실행 — ${err.message}`);
  process.exit(1);
}

/* ── 스테이지 데이터 ── */

const stagesBlock = js.split('const STAGES = [')[1].split('\n  ];')[0];
const stageCount = [...stagesBlock.matchAll(/\n      name: '/g)].length;

check('스테이지 5개', stageCount === 5, `${stageCount}개`);
check('readField 살아 있음', /function readField/.test(js));

/* ── 고르는 페이지 ── */

const cards = nodes.cards.children.map((li) => li.children[0]);
check('스테이지 카드', cards.length === stageCount, `${cards.length}개`);
check('진행 표시', nodes.progress.textContent === `0 / ${stageCount} 클리어`,
  nodes.progress.textContent);

const miniOf = (b) => b.children[1].children.find((c) => c.classList.contains('mini'));
check('카드 미리보기 100칸',
  cards.every((b) => miniOf(b) && miniOf(b).children.length === 100));
check('카드에 조각 수 표시',
  cards.every((b) => /조각 \d+ · \d+칸/.test(
    b.children[1].children.find((c) => c.classList.contains('meta')).textContent)));

/* ── 푸는 페이지 ── */

cards[0].dispatch('click', {});
check('카드 누르면 푸는 화면', nodes.play.hidden === false && nodes.select.hidden === true);
check('격자 100칸 + 외곽선',
  nodes.grid.children.filter((c) => c.classList.contains('tile')).length === 100
  && nodes.grid.children.some((c) => c.attrs.id === 'outline'));

const tiles = nodes.grid.children.filter((c) => c.classList.contains('tile'));
const fieldCount = tiles.filter((t) => t.classList.contains('on')).length;
check('필드 칸 있음', fieldCount > 0, `${fieldCount}칸`);
check('필드 외곽선 path', (nodes['outline-path'].getAttribute('d') || '').length > 0);

const trayItems = () => nodes.tray.children.filter((c) => c.classList.contains('item'));
check('서랍에 조각', trayItems().length > 0, `${trayItems().length}개`);
check('남은 조각 표시', /남은 조각 \d+ \/ \d+/.test(nodes.left.textContent),
  nodes.left.textContent);

/* ── 드래그 ── */

// 판 800px / 10칸이라 칸 하나가 80px. 칸 (c,r) 의 한가운데를 짚는다
const CELL = Math.floor((800 - 16) / 10);
const at = (c, r) => ({ clientX: c * CELL + CELL / 2, clientY: r * CELL + CELL / 2, pointerId: 1 });

/** 스테이지의 원래 답을 다시 풀어서, 어느 조각을 어디에 놓을지 알아낸다 */
function solve(fieldBits, pieces) {
  const field = new Set();
  for (let i = 0; i < 100; i++) if (fieldBits[i] === '1') field.add(i);
  const used = new Array(pieces.length).fill(false);
  const occ = new Set();
  const plan = [];

  const order = [...field].sort((a, b) => a - b);
  function step() {
    const first = order.find((i) => !occ.has(i));
    if (first === undefined) return true;
    const fc = first % 10, fr = Math.floor(first / 10);
    for (let pi = 0; pi < pieces.length; pi++) {
      if (used[pi]) continue;
      for (const [ac, ar] of pieces[pi]) {
        const c0 = fc - ac, r0 = fr - ar;
        const ids = [];
        let ok = true;
        for (const [c, r] of pieces[pi]) {
          const cc = c0 + c, rr = r0 + r;
          if (cc < 0 || rr < 0 || cc > 9 || rr > 9) { ok = false; break; }
          const i = rr * 10 + cc;
          if (!field.has(i) || occ.has(i)) { ok = false; break; }
          ids.push(i);
        }
        if (!ok) continue;
        used[pi] = true;
        ids.forEach((i) => occ.add(i));
        plan.push({ pi, c0, r0 });
        if (step()) return true;
        plan.pop();
        ids.forEach((i) => occ.delete(i));
        used[pi] = false;
      }
    }
    return false;
  }
  return step() ? plan : null;
}

const first = JSON.parse(JSON.stringify(readStage(0)));

function readStage(n) {
  const body = stagesBlock.split('\n    {').slice(1)[n];
  return {
    pieces: JSON.parse(body.match(/pieces: (\[.*\]),/)[1].replace(/\]\[/g, '],[')),
    field: body.match(/field: '([01]+)'/)[1],
  };
}

/**
 * 서랍의 조각 pi 를 (c0,r0) 에 끌어다 놓는다.
 *
 * 조각의 첫 칸을 쥐고, 그 칸이 가야 할 자리에서 손을 뗀다. 정규화만 해 둔
 * 모양은 (0,0) 이 비어 있을 수 있어서(S4 가 그렇다) 그 자리를 쥐면 게임이
 * 가장 가까운 칸으로 당겨 잡아 버리고, 그만큼 어긋난 자리에 놓인다.
 */
function dragPiece(pi, c0, r0) {
  const item = trayItems().find((it) => it.getAttribute('data-piece') === String(pi));
  if (!item) return false;
  const [ac, ar] = first.pieces[pi][0];
  item.dispatch('pointerdown', {
    clientX: 7 + (ac + 0.5) * 15, clientY: 7 + (ar + 0.5) * 15, pointerId: 1,
  });
  const p = at(c0 + ac, r0 + ar);
  nodes.tray.dispatch('pointermove', p);
  nodes.tray.dispatch('pointerup', p);
  return true;
}

const plan = solve(first.field, first.pieces);
check('1스테이지 답 찾음', plan !== null, plan ? `${plan.length}조각` : '');

if (plan) {
  // 한 조각만 놓아 보고 판에 칠이 생겼는지
  const before = tiles.filter((t) => t.classList.contains('fill')).length;
  dragPiece(plan[0].pi, plan[0].c0, plan[0].r0);
  const after = tiles.filter((t) => t.classList.contains('fill')).length;
  check('끌어다 놓으면 칸이 채워진다', after - before === first.pieces[plan[0].pi].length,
    `${after - before}칸`);
  check('놓은 조각은 서랍에서 빠진다',
    !trayItems().some((it) => it.getAttribute('data-piece') === String(plan[0].pi)));

  // 판에 놓인 조각을 집어 올려 서랍으로 되돌린다
  const filledTile = tiles.findIndex((t) => t.classList.contains('fill'));
  tiles[filledTile].dispatch('pointerdown', at(filledTile % 10, Math.floor(filledTile / 10)));
  nodes.grid.dispatch('pointermove', { clientX: -500, clientY: -500, pointerId: 1 });
  nodes.grid.dispatch('pointerup', { clientX: -500, clientY: -500, pointerId: 1 });
  check('판 밖에 떼면 서랍으로 돌아온다',
    trayItems().length === first.pieces.length
    && tiles.filter((t) => t.classList.contains('fill')).length === 0);

  // 겹치는 자리에는 안 놓인다
  dragPiece(plan[0].pi, plan[0].c0, plan[0].r0);
  const filled = tiles.filter((t) => t.classList.contains('fill')).length;
  dragPiece(plan[1].pi, plan[0].c0, plan[0].r0);
  check('겹치는 자리에는 안 놓인다',
    tiles.filter((t) => t.classList.contains('fill')).length === filled);

  // 지우기
  nodes.reset.dispatch('click', {});
  check('지우기 누르면 전부 서랍으로',
    trayItems().length === first.pieces.length
    && tiles.filter((t) => t.classList.contains('fill')).length === 0);

  // 답을 끝까지 놓으면 클리어
  plan.forEach(({ pi, c0, r0 }) => dragPiece(pi, c0, r0));
  check('다 채우면 클리어', nodes.banner.classList.contains('show'));
  check('클리어 기록 저장', (store.get('drag-drop.cleared') || '').length > 2,
    store.get('drag-drop.cleared'));

  // 다음 스테이지
  nodes.next.dispatch('click', {});
  check('다음 버튼이 다음 스테이지를 연다',
    nodes['stage-name'].textContent !== '첫 걸음' && nodes.play.hidden === false,
    nodes['stage-name'].textContent);

  nodes.back.dispatch('click', {});
  check('뒤로 가면 목록', nodes.select.hidden === false && nodes.play.hidden === true);
  check('클리어 표시', nodes.cards.children[0].children[0].classList.contains('done'));
}

console.log(fails.length ? `\n${fails.length}건 실패` : '\n전부 통과');
process.exit(fails.length ? 1 : 0);
