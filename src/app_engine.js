// ---------------- 매칭 엔진 (matching.py와 같은 규칙, 가입자가 늘어도 계산되게 일반화) ----------------
function createEngine(cfg) {
  const W0 = cfg.weights;
  const KEYS = Object.keys(W0);
  const ORD = {
    marriage_view: ["negative", "neutral", "positive"],
    drinking: ["none", "sometimes", "often"],
    spending: ["saver", "balanced", "spender"],
  };
  const LABEL = {
    interests: "관심사", marriage_view: "결혼관", contact_style: "연락 스타일", distance: "거리", appearance: "외모",
    chronotype: "활동 시간대", weekend: "주말 방식", drinking: "음주", spending: "소비 성향", pet: "반려동물",
    smoking: "흡연", religion: "종교",
  };
  const REL = new Set();
  for (const [x, y] of cfg.related) { REL.add(x + "|" + y); REL.add(y + "|" + x); }
  const CAT_OF = {};
  for (const [c, ts] of Object.entries(cfg.categories)) for (const t of ts) CAT_OF[t] = c;
  // 태그 유사도: 같음 1.0 / 관련 있음 0.5 / 같은 분류 cfg.category_sim / 다름 0
  const tagSim = (x, y) => {
    if (x === y) return 1;
    if (REL.has(x + "|" + y)) return 0.5;
    if (CAT_OF[x] && CAT_OF[x] === CAT_OF[y]) return cfg.category_sim;
    return 0;
  };
  // 취향 좌표: 사람 = Σ(중요도 배율 × 관심사 좌표), 비교는 코사인 유사도
  const DIM = cfg.axes.length;
  function vecOfTags(tags, levels) {
    const v = new Array(DIM).fill(0);
    for (const t of tags) {
      const m = levels ? cfg.level_mult[levels[t] ?? 2] : 1;
      (cfg.tag_vec[t] || []).forEach((x, i) => { v[i] += m * x; });
    }
    return v;
  }
  const personVec = p => vecOfTags(p.interests, Object.fromEntries(p.interests.map(t => [t, levelOf(p, t)])));
  function cosine(a, b) {
    let d = 0, na = 0, nb = 0;
    for (let i = 0; i < a.length; i++) { d += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
    return na && nb ? d / Math.sqrt(na * nb) : 0;
  }
  const spread = c => Math.min(1, Math.max(0, (c - cfg.cos_floor) / (1 - cfg.cos_floor)));
  // 여러 사람의 8차원 좌표를 2차원으로 펼치기 (주성분 분석, 화면 지도용)
  function project2D(vecs) {
    const n = vecs.length, mean = new Array(DIM).fill(0);
    vecs.forEach(v => v.forEach((x, i) => { mean[i] += x / n; }));
    const C = vecs.map(v => v.map((x, i) => x - mean[i]));
    const cov = Array.from({ length: DIM }, (_, i) => Array.from({ length: DIM }, (_, j) => C.reduce((s, r) => s + r[i] * r[j], 0)));
    const comps = [];
    for (let c = 0; c < 2; c++) {
      let v = Array.from({ length: DIM }, (_, i) => 1 + i * 0.1);
      for (let it = 0; it < 60; it++) {
        let w = cov.map(row => row.reduce((s, x, j) => s + x * v[j], 0));
        for (const u of comps) { const d = w.reduce((s, x, i) => s + x * u[i], 0); w = w.map((x, i) => x - d * u[i]); }
        const nrm = Math.sqrt(w.reduce((s, x) => s + x * x, 0)) || 1;
        v = w.map(x => x / nrm);
      }
      comps.push(v);
    }
    return { points: C.map(r => comps.map(u => r.reduce((s, x, i) => s + x * u[i], 0))), mean, comps };
  }
  const levelOf = (p, t) => p.interest_level?.[t] ?? (t === p.favorite_tag ? 3 : 2);
  // 거르기 태그: "cat:운동"처럼 분류 전체도 고를 수 있음
  const tagHit = (want, u, related) => want.startsWith("cat:") ? CAT_OF[u] === want.slice(4) : (u === want || (related && tagSim(want, u) >= 0.5));
  const ordSim = (f, x, y) => {
    const i = ORD[f].indexOf(x), j = ORD[f].indexOf(y);
    if (i < 0 || j < 0) return 0;
    return ({ 0: 1, 1: 0.5 })[Math.abs(i - j)] ?? 0;
  };
  const petSim = (x, y) => {
    const fond = v => v === "has" || v === "likes";
    if ((fond(x) && fond(y)) || (x === "dislikes" && y === "dislikes")) return 1;
    if ([x, y].includes("has") && [x, y].includes("dislikes")) return 0;
    return 0.5;
  };
  const satisfies = (f, actual, wanted) => (f === "pet" && wanted === "likes") ? (actual === "has" || actual === "likes") : actual === wanted;

  function dist(a, b) {
    const R = 6371, rad = Math.PI / 180;
    const la1 = a.lat * rad, la2 = b.lat * rad, dla = la2 - la1, dlo = (b.lng - a.lng) * rad;
    const h = Math.sin(dla / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dlo / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  // 희귀도: 지금 가입한 사람 전체 기준으로 다시 계산 (가장 흔한 태그 = 1.0, 상한 cfg.rarity_cap)
  function buildRarity(list) {
    const n = list.length, cnt = {};
    for (const p of list) for (const t of p.interests) cnt[t] = (cnt[t] || 0) + 1;
    const idf = Object.fromEntries(Object.entries(cnt).map(([t, c]) => [t, Math.log(n / c)]));
    const base = Math.min(...Object.values(idf));
    return Object.fromEntries(Object.entries(idf).map(([t, v]) => [t, Math.min(base > 0 ? v / base : 1 + v, cfg.rarity_cap)]));
  }

  function normWeights(w) {
    const s = KEYS.reduce((t, k) => t + (w?.[k] || 0), 0);
    if (s <= 0) return { ...W0 };
    return Object.fromEntries(KEYS.map(k => [k, (w[k] || 0) * 100 / s]));
  }

  function filterOne(a, b, d, tagOpt) {
    const pr = a.preference;
    if (!b.nickname || !b.has_photo) return { code: "R1", text: "프로필 미완성 (사진 없음)" };
    if (!pr.gender.includes(b.gender)) return { code: "R2", text: "성별" };
    if (b.age < pr.age_min || b.age > pr.age_max) return { code: "R3", text: "나이" };
    if (d > pr.max_distance_km && (pr.distance_importance === 3 || d > pr.max_distance_km * 2)) return { code: "R4", text: "거리" };
    if (a.purpose !== b.purpose) return { code: "R5", text: "목적" };
    for (const [f, c] of Object.entries(pr.conditions || {}))
      if (c.importance === 3 && !satisfies(f, b[f], c.value)) return { code: "R6", text: `절대 조건 (${LABEL[f] ?? f})` };
    if (tagOpt && tagOpt.tags && tagOpt.tags.length) {
      const ok = b.interests.some(u => tagOpt.tags.some(tg => tagHit(tg, u, tagOpt.related)));
      if (!ok) return { code: "R7", text: "태그" };
    }
    return null;
  }

  // detail=false: 점수 숫자만 (500명 전체 계산용). detail=true: 화면에 보여줄 근거까지
  function scoreOne(a, b, d, W, rarity, va, vb, detail) {
    let total = 0;
    const reasons = [], parts = [], pens = [];
    const part = detail
      ? (key, pts, note) => { total += pts; parts.push({ key, label: LABEL[key], w: W[key], pts, note: typeof note === "function" ? note() : note }); }
      : (key, pts) => { total += pts; };

    let k = 0; const hits = [];
    for (const tg of a.interests) {
      let bestTag = null, best = 0;
      for (const u of b.interests) { const s = tagSim(tg, u); if (s > best) { best = s; bestTag = u; } }
      if (best > 0) {
        k += best * (rarity[tg] ?? 1) * cfg.level_mult[levelOf(a, tg)];
        if (detail) hits.push({ mine: tg, theirs: bestTag, sim: best });
      }
    }
    const cos = cosine(va, vb);
    let pts = (cfg.overlap_share * (1 - 0.5 ** k) + (1 - cfg.overlap_share) * spread(cos)) * W.interests;
    part("interests", pts, () => (hits.length ? hits.map(h => h.sim === 1 ? h.mine : h.sim >= 0.5 ? `${h.mine}≈${h.theirs}` : `${h.mine}~${h.theirs}(${CAT_OF[h.mine]})`).join(", ") : "겹침 없음") + ` · 좌표 유사도 ${cos.toFixed(2)}`);
    if (detail) { if (hits.length) reasons.push({ key: "interests", pts, hits }); else if (cos >= 0.85) reasons.push({ key: "taste", pts, cos }); }

    for (const f of ["marriage_view", "drinking", "spending"]) {
      const s = ordSim(f, a[f], b[f]); pts = s * W[f];
      part(f, pts, () => `${a[f]} / ${b[f]}`);
      if (detail && s === 1) reasons.push({ key: f, pts, value: a[f] });
    }
    for (const f of ["contact_style", "chronotype", "weekend"]) {
      const s = a[f] === b[f] ? 1 : 0; pts = s * W[f];
      part(f, pts, () => `${a[f]} / ${b[f]}`);
      if (detail && s) reasons.push({ key: f, pts, value: a[f] });
    }
    part("pet", petSim(a.pet, b.pet) * W.pet, () => `${a.pet} / ${b.pet}`);

    const maxD = Math.min(a.preference.max_distance_km, b.preference.max_distance_km);
    let s = Math.max(0, 1 - d / maxD); pts = s * W.distance;
    part("distance", pts, () => `${d.toFixed(1)}km / 기준 ${maxD}km`);
    if (detail && s >= 0.5) reasons.push({ key: "distance", pts, value: d });

    const wanted = Object.entries(a.preference.appearance || {}).filter(([, v]) => v !== "any" && Array.isArray(v) && v.length);
    const matched = wanted.filter(([kk, v]) => v.includes(b.appearance?.[kk]));
    s = wanted.length ? matched.length / wanted.length : 1; pts = s * W.appearance;
    part("appearance", pts, () => wanted.length ? `원하는 ${wanted.length}개 중 ${matched.length}개 일치` : "상관없음");
    if (detail && wanted.length && s > 0) reasons.push({ key: "appearance", pts });

    for (const [f, c] of Object.entries(a.preference.conditions || {})) {
      const pen = cfg.penalty[c.importance];
      if (pen !== undefined && !satisfies(f, b[f], c.value)) { total += pen; if (detail) pens.push({ pts: pen, text: `${LABEL[f] ?? f} 조건 어김` }); }
    }
    const over = d - a.preference.max_distance_km;
    if (over > 0) { const p = cfg.dist_penalty * Math.ceil(over / 5); total += p; if (detail) pens.push({ pts: p, text: `최대 거리 ${over.toFixed(1)}km 초과` }); }

    if (detail) reasons.sort((x, y) => y.pts - x.pts);
    return { total: Math.max(total, 0), reasons, parts, pens };
  }

  // 전체 계산: 사람마다 추천 목록 + 자동 매칭
  function computeAll(list, settingsOf) {
    const rarity = buildRarity(list);
    const lists = {};
    // 사람별로 한 번만 계산해서 재사용
    const VEC = {}, WN = {}, SET = {};
    for (const p of list) { VEC[p.id] = personVec(p); SET[p.id] = settingsOf(p.id); WN[p.id] = normWeights(SET[p.id].weights); }
    for (const a of list) {
      const sa = SET[a.id];
      const recs = [], rejected = { R1: 0, R2: 0, R3: 0, R4: 0, R5: 0, R6: 0, R7: 0, nearestR4: null };
      for (const b of list) {
        if (b.id === a.id) continue;
        if (!a.preference.gender.includes(b.gender)) continue;
        if (!b.preference.gender.includes(a.gender)) { rejected.R2++; continue; }
        const d = dist(a, b);
        const why = filterOne(a, b, d, sa) || filterOne(b, a, d, null);
        if (why) { rejected[why.code]++; if (why.code === "R4" && (rejected.nearestR4 === null || d < rejected.nearestR4)) rejected.nearestR4 = d; continue; }
        const ab = scoreOne(a, b, d, WN[a.id], rarity, VEC[a.id], VEC[b.id], false).total;
        const ba = scoreOne(b, a, d, WN[b.id], rarity, VEC[b.id], VEC[a.id], false).total;
        recs.push({ id: b.id, distance: d, score: Math.sqrt(ab * ba), ab, ba });
      }
      recs.sort((x, y) => (y.score - x.score) || (x.distance - y.distance));
      lists[a.id] = { recs, rejected };
    }
    // 자동 매칭: 서로가 1순위면 연결, 연결된 사람을 빼고 반복
    const auto = {};
    const N = cfg.auto_top_n || 3;
    const inTop = {};
    for (const p of list) inTop[p.id] = new Set(lists[p.id].recs.slice(0, N).map(r => r.id));
    for (let round = 1; ; round++) {
      const top = {};
      for (const p of list) if (!auto[p.id]) top[p.id] = lists[p.id].recs.find(r => !auto[r.id] && inTop[p.id].has(r.id)) || null;
      let found = false;
      for (const [a, r] of Object.entries(top)) {
        if (r && String(a) < String(r.id) && top[r.id] && top[r.id].id === a) {
          auto[a] = { partner: r.id, round, score: r.score };
          auto[r.id] = { partner: a, round, score: r.score };
          found = true;
        }
      }
      if (!found) break;
    }
    return { lists, auto, rarity, ctx: { rarity, VEC, WN } };
  }
  // 화면에 보이는 한 쌍만 근거까지 자세히 계산
  function explain(ctx, a, b) {
    const d = dist(a, b);
    const ab = scoreOne(a, b, d, ctx.WN[a.id], ctx.rarity, ctx.VEC[a.id], ctx.VEC[b.id], true);
    const ba = scoreOne(b, a, d, ctx.WN[b.id], ctx.rarity, ctx.VEC[b.id], ctx.VEC[a.id], true);
    return {
      reasons: ab.reasons, penA: ab.pens, penB: ba.pens,
      parts: ab.parts.map((p, i) => ({ ...p, wB: ba.parts[i].w, ptsB: ba.parts[i].pts, noteB: ba.parts[i].note })),
    };
  }

  return { computeAll, explain, KEYS, LABEL, W0, tagSim, dist, CAT_OF, levelOf, vecOfTags, personVec, cosine, project2D, AXES: cfg.axes };
}
