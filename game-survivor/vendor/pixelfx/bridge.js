// pixelfx 다리 (0.149.0) — patch-gg/pixelfx (MIT, vendor/pixelfx/LICENSE · NOTICE.md) 의 코드로 그리는 픽셀 이펙트를 게임에 붙인다.
// 게임 쪽은 window.PFX 만 쓴다: spawn(이름, 월드 x, y, 옵션) · tick(dt) · draw(ctx, ox, oy, W, H)
//   한 화면 크기 픽셀 버퍼(frame) 하나에 살아 있는 이펙트를 모두 그리고, 투명 RGBA 로 합쳐 게임 캔버스 위에 얹는다 (1 월드 px = 1 이펙트 px)
import { createFrame, clearFrame, createFx, composite } from "./src/core/index.js";
import * as hitSpark from "./src/fx/impacts/hit-spark.js";
import * as critHit from "./src/fx/impacts/crit-hit.js";
import * as bluntHit from "./src/fx/impacts/blunt-hit.js";
import * as poof from "./src/fx/spawn/poof.js";
import * as pow from "./src/fx/explosions/cartoon-pow.js";
import * as heart from "./src/fx/pickups/heart-pickup.js";
import * as loot from "./src/fx/pickups/loot-beam.js";
import * as portal from "./src/fx/spawn/spawn-portal.js";
// 무기마다 (0.149.1)
import * as bulletImp from "./src/fx/impacts/bullet-impact.js";
import * as ricochet from "./src/fx/impacts/ricochet.js";
import * as shieldBlock from "./src/fx/impacts/shield-block.js";
import * as heavyLanding from "./src/fx/impacts/heavy-landing.js";
import * as impactFrame from "./src/fx/impacts/impact-frame.js";
import * as muzzlePistol from "./src/fx/projectiles/muzzle-pistol.js";
import * as muzzleShotgun from "./src/fx/projectiles/muzzle-shotgun.js";
import * as zapHit from "./src/fx/lightning/zap-hit.js";
import * as spinSlash from "./src/fx/melee/spin-slash.js";
import * as manaBurst from "./src/fx/arcane/mana-burst.js";
import * as implosion from "./src/fx/explosions/implosion.js";
import * as plasmaExp from "./src/fx/explosions/plasma-explosion.js";
import * as flamethrower from "./src/fx/fire/flamethrower.js";
import * as acidSplash from "./src/fx/nature/acid-splash.js";

// 게임 이름 → [효과, 같은 이름 최소 간격(초), 동시에 살아 있을 수 있는 수]
const KIND = {
  hit: [hitSpark, 0.06, 12], crit: [critHit, 0.12, 6], hurt: [bluntHit, 0.2, 2], kill: [poof, 0.05, 8],
  pow: [pow, 0.08, 3], boss: [pow, 0, 4], heart: [heart, 0.2, 3], loot: [loot, 0.5, 3], portal: [portal, 0.5, 3],   // 보스 죽음도 POW (big-explosion 은 한 프레임 9ms 라 뺌)
  // 무기마다 (0.149.1)
  mpist: [muzzlePistol, 0.12, 3], mshot: [muzzleShotgun, 0.3, 2], bimp: [bulletImp, 0.07, 6], rico: [ricochet, 0.08, 6], zap: [zapHit, 0.12, 4],
  spin: [spinSlash, 0.25, 2], block: [shieldBlock, 0.15, 3], land: [heavyLanding, 0.2, 2], frame: [impactFrame, 0.3, 2], mana: [manaBurst, 0.3, 2],
  implode: [implosion, 0.3, 2], plasma: [plasmaExp, 0.25, 2], acid: [acidSplash, 0.2, 4], flame: [flamethrower, 0, 3],
};
const FX = [], last = {}, LOOPS = {};
let frame = null, img = null, off = null, octx = null, clock = 0, seed = 1;

window.PFX = {
  spawn(k, x, y, o = {}) {
    const K = KIND[k]; if (!K) return;
    if (clock - (last[k] ?? -9) < K[1]) return;
    if (FX.filter(f => f.k === k).length >= K[2]) return;
    last[k] = clock;
    const fx = createFx(K[0], { x: Math.round(x), y: Math.round(y), seed: seed++, ...o });
    fx.k = k; FX.push(fx);
  },
  tick(dt) {
    clock += dt;
    for (const f of FX) f.update(dt);
    for (let i = FX.length - 1; i >= 0; i--) if (FX[i].done()) FX.splice(i, 1);
  },
  // 이어지는 이펙트 (화염방사기 불길): 켜진 동안 자리 · 각도를 따라가고, 꺼지면 천천히 사라짐 (0.149.1)
  loop(key, k, on, x, y, o = {}) {
    let f = LOOPS[key];
    if (f && (f.done() || !FX.includes(f))) { f = null; delete LOOPS[key]; }
    if (!on) { if (f) { f.stop(); delete LOOPS[key]; } return; }
    if (!f) { const K = KIND[k]; if (!K) return; f = createFx(K[0], {x: Math.round(x), y: Math.round(y), seed: seed++, ...o}); f.k = k; FX.push(f); LOOPS[key] = f; }
    f.options.x = Math.round(x); f.options.y = Math.round(y); Object.assign(f.options, o);
  },
  clear() { FX.length = 0; for (const k in LOOPS) delete LOOPS[k]; },
  count() { return FX.length; },
  // 월드 좌표로 그려진 상태(ctx 가 translate(ox, oy))에서 부름 — 화면 왼쪽 위 = 월드 (-ox, -oy)
  //   화면 전체가 아니라 살아 있는 이펙트들이 차지하는 네모(meta.size · origin 의 합)만 버퍼로 — 합치기(composite) 비용을 줄임
  draw(ctx, ox, oy, W, H) {
    if (!FX.length) return;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const f of FX) {
      const m = f.meta, sz = m.size || [128, 128], og = m.origin || [sz[0] / 2, sz[1] / 2], o = f.options, fl = o.flip;
      const lx = o.x - (fl ? sz[0] - og[0] : og[0]), ty = o.y - og[1];
      x0 = Math.min(x0, lx); y0 = Math.min(y0, ty); x1 = Math.max(x1, lx + sz[0]); y1 = Math.max(y1, ty + sz[1]);
    }
    x0 = Math.max(x0, -ox) | 0; y0 = Math.max(y0, -oy) | 0; x1 = Math.ceil(Math.min(x1, -ox + W)); y1 = Math.ceil(Math.min(y1, -oy + H));
    const w = x1 - x0, h = y1 - y0; if (w <= 0 || h <= 0) return;
    if (!frame || frame.w !== w || frame.h !== h) {
      frame = createFrame(w, h); img = new ImageData(w, h);
      if (!off) { off = document.createElement("canvas"); octx = off.getContext("2d"); }
      off.width = w; off.height = h;
    }
    frame.ox = x0; frame.oy = y0;
    clearFrame(frame);
    for (const f of FX) f.draw(frame);
    composite(frame, img.data, null);
    octx.putImageData(img, 0, 0);
    ctx.save(); ctx.imageSmoothingEnabled = false; ctx.drawImage(off, x0, y0, w, h); ctx.restore();
  },
};
