// 밸런스 시뮬 (0.139.0) — 브라우저 콘솔(?raw)에서: 붙여 넣고 simBatch([...]) → window.SIM 에 결과
// 자동 조종: 적 · 탄에서 멀어지고, 가까운 보석 쪽으로 조금. 레벨업 · 상자는 무작위로 고름. 패널티 · 보조 없이 무기 하나로
function apMove() {
  const p = G.p; let fx = 0, fy = 0;
  const R = Math.max(60, Math.min(...G.weapons.map(w => wstat(w.id).range)) * 0.75);   // 이 거리 안의 적에게서 멀어짐 — 밖이면 다가가 싸움
  let ne = null, nd = Infinity;
  for (const e of G.enemies) { if (e.dead) continue; const dx = p.x - e.x, dy = p.y - e.y, d2 = dx * dx + dy * dy;
    if (d2 < nd) { nd = d2; ne = e; }
    const rr = R + (e.boss ? e.r + 40 : 0);
    if (d2 < rr * rr) { const w = (e.boss ? 4 : e.elite != null ? 2 : 1) / (d2 + 50); fx += dx * w; fy += dy * w; } }
  if (ne && nd > R * R * 1.4) { const d = Math.sqrt(nd); fx -= (p.x - ne.x) / d * 0.004; fy -= (p.y - ne.y) / d * 0.004; }
  for (const b of G.eshots) { if (b.dead) continue;
    if (b.lob || b.blast) { const dx = p.x - b.x, dy = p.y - b.y, d = Math.hypot(dx, dy) || 1; if (d < b.aoe + 30) { fx += dx / d * 0.08; fy += dy / d * 0.08; } continue; }
    const dx = p.x - b.x, dy = p.y - b.y, d2 = dx * dx + dy * dy; if (d2 < 140 * 140) { const w = 2 / (d2 + 50); fx += dx * w; fy += dy * w; } }
  let best = null, bd = 200 * 200;
  for (const g of G.gems) { const d2 = (g.x - p.x) ** 2 + (g.y - p.y) ** 2; if (d2 < bd) { bd = d2; best = g; } }
  for (const c of G.chests) { const d2 = (c.x - p.x) ** 2 + (c.y - p.y) ** 2; best = c; bd = d2; break; }   // 상자는 거리 없이 먼저
  const fm = Math.hypot(fx, fy);
  if (best) { const d = Math.sqrt(bd) || 1; const k = fm < 0.004 ? 1 : 0.3; fx += (best.x - p.x) / d * 0.01 * k; fy += (best.y - p.y) / d * 0.01 * k; }
  const l = Math.hypot(fx, fy); pad.v.x = l ? fx / l : 0; pad.v.y = l ? fy / l : 0;
}
function simRun(o) {   // o: {w: 무기 id, wi: 월드 0~2, lv: 1~, ch: 캐릭터 i(기본 0), dt}
  charIdx = o.ch || 0; localStorage.setItem('survivor.diff', JSON.stringify({[WORLDS[o.wi].id]: o.lv}));
  const save = getRec; newGame(o.wi, o.w); G.pens = []; G.subs = []; G.revives = 0; G.permRR = 0;
  G.dl = o.lv; G.dm = worldDm(o.wi, o.lv);
  return G;
}
function simStep(n, dt) {
  for (let i = 0; i < n; i++) {
    if (!G) return 'gone';
    if (G.mode === 'levelup') { G.inputLock = 0; choose(Math.floor(Math.random() * G.choices.length)); if (G.mode === 'play') G.mode = 'sim'; continue; }
    if (G.mode === 'opening') { tickOpening(dt); continue; }      // 상자 열림 연출 (0.141.0)
    if (G.mode === 'play') G.mode = 'sim';                        // 화면 루프가 같이 돌지 않게
    if (G.dying || G.mode === 'over') return 'dead';
    if (G.mode === 'clear') return 'clear';
    if (G.t > (window.SIM_TMAX || 720)) return 'timeout';
    apMove(); update(dt);
  }
  return 'run';
}
window.SIM = window.SIM || [];
async function simBatch(list, dt = 1 / 30) {
  window.SIM_DONE = false;
  const keepPerm = window.permUp, permRaw = localStorage.getItem('survivor.perm'), pbanRaw = localStorage.getItem('survivor.pban');
  window.permUp = () => {}; window.SIM_ACTIVE = true;             // 시뮬은 영구 저장(영구 업그레이드 · 무기 상자)을 건드리지 않음
  const realRec = localStorage.getItem('survivor.diff');
  for (const o of list) {
    simRun(o); G.mode = 'sim'; let st = 'run';
    const keepSave = window.saveRec; window.saveRec = () => '';
    while (st === 'run') { st = simStep(600, dt); await new Promise(r => setTimeout(r, 0)); }
    window.saveRec = keepSave;
    window.SIM.push({...o, res: st, t: Math.round(G.t), lv: G.lv, kills: G.kills, hp: Math.round(G.p.hp)});
  }
  realRec == null ? localStorage.removeItem('survivor.diff') : localStorage.setItem('survivor.diff', realRec);
  window.permUp = keepPerm; window.SIM_ACTIVE = false;
  permRaw == null ? localStorage.removeItem('survivor.perm') : localStorage.setItem('survivor.perm', permRaw);
  pbanRaw == null ? localStorage.removeItem('survivor.pban') : localStorage.setItem('survivor.pban', pbanRaw);
  window.SIM_DONE = true;
}
