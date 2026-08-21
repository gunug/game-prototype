/**
 * index.html 을 실제로 실행해 보는 스모크 테스트.
 *
 *   node tools/smoke.mjs
 *
 * 문법만 보는 검사는 "정의가 통째로 사라진" 종류의 사고를 못 잡는다. 실제로
 * readField 가 없어진 채 배포돼서 화면이 비어 나갔다. 그래서 DOM 을 최소한만
 * 흉내내고 스크립트를 끝까지 돌린 뒤, 눈에 보여야 할 것들을 센다.
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
  constructor(el) { this.el = el; this.set = new Set(); }
  add(...names) { names.forEach((n) => this.set.add(n)); }
  remove(...names) { names.forEach((n) => this.set.delete(n)); }
  contains(name) { return this.set.has(name); }
  toggle(name, on) { (on ? this.set.add(name) : this.set.delete(name)); }
}

class El {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.style = new Style();
    this.classList = new ClassList(this);
    this.attrs = {};
    this.handlers = {};
    this.textContent = '';
  }
  get className() { return [...this.classList.set].join(' '); }
  set className(v) {
    this.classList.set = new Set(String(v).split(/\s+/).filter(Boolean));
  }
  appendChild(node) {
    if (node instanceof Frag) { node.children.forEach((c) => this.children.push(c)); return node; }
    this.children.push(node);
    return node;
  }
  append(...nodes) { nodes.forEach((n) => this.appendChild(n)); }
  replaceChildren(node) { this.children = []; if (node) this.appendChild(node); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  addEventListener(type, fn) { (this.handlers[type] ??= []).push(fn); }
  dispatch(type, event) { (this.handlers[type] || []).forEach((fn) => fn(event)); }
  setPointerCapture() {}
  releasePointerCapture() {}
  closest() { return null; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 800, height: 800 }; }
}

class Frag extends El {
  constructor() { super('#fragment'); }
}

const nodes = {};
for (const id of ['grid', 'board', 'preview', 'banner', 'stages', 'reset']) {
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
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
  },
  console,
};
sandbox.window.localStorage = sandbox.localStorage;

/* ── 실행 ── */

const js = fs.readFileSync(GAME, 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const run = new Function(...Object.keys(sandbox), js);

const fails = [];
const check = (label, ok, detail = '') => {
  console.log(`  ${ok ? 'OK  ' : '실패'} ${label}${detail ? ' — ' + detail : ''}`);
  if (!ok) fails.push(label);
};

try {
  run(...Object.values(sandbox));
} catch (err) {
  console.log(`  실패 스크립트 실행 — ${err.message}`);
  process.exit(1);
}

const grid = nodes.grid;
const stages = nodes.stages;

check('격자 100칸', grid.children.length === 100, `${grid.children.length}칸`);

const fieldTiles = grid.children.filter((t) => t.classList.contains('field'));
check('활성 칸 있음', fieldTiles.length > 0, `${fieldTiles.length}칸`);

check('스테이지 목록 채워짐', stages.children.length > 0, `${stages.children.length}개`);

const buttons = stages.children.map((li) => li.children[0]).filter(Boolean);
check('스테이지 버튼', buttons.length === stages.children.length);

const withDiff = buttons.filter((b) =>
  b.children.some((c) => c.classList.contains('diff') && /^\d+$/.test(c.textContent)));
check('난이도 표시', withDiff.length === buttons.length, `${withDiff.length}/${buttons.length}`);

const diffs = withDiff.map((b) =>
  Number(b.children.find((c) => c.classList.contains('diff')).textContent));
check('난이도 오름차순', diffs.every((d, i) => i === 0 || diffs[i - 1] <= d), diffs.join(' '));
check('난이도 1~100', diffs.every((d) => d >= 1 && d <= 100));

check('모양 미리보기', nodes.preview.children.length > 0, `${nodes.preview.children.length}칸`);

// 활성 칸 하나를 실제로 눌러 칠해지는지
const cell = 80;   // getBoundingClientRect 가 0,0 이고 칸은 80px 로 잡힌다
const first = grid.children.findIndex((t) => t.classList.contains('field'));
const fc = first % 10, fr = Math.floor(first / 10);
nodes.board.dispatch('pointerdown', {
  button: 0, pointerType: 'mouse', pointerId: 1,
  clientX: fc * cell + cell / 2, clientY: fr * cell + cell / 2,
  target: { closest: () => null }, preventDefault() {},
});
nodes.board.dispatch('pointerup', {});
check('클릭하면 칠해짐', !!grid.children[first].style.backgroundColor,
  grid.children[first].style.backgroundColor || '색 없음');

if (fails.length) {
  console.log(`\n${fails.length}건 실패`);
  process.exit(1);
}
console.log('\n전부 통과');
