#!/usr/bin/env python3
"""Gera prototype/avaliacao-maturidade-ia.html a partir do modelo oficial da plataforma."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "backend" / "data" / "ai_maturity_model.json"
OUT_PATH = ROOT / "prototype" / "avaliacao-maturidade-ia.html"


def slim_model(model: dict) -> dict:
    """Mantém o que a avaliação e o score precisam; corta rótulos SWOT/TOWS (não usados aqui)."""
    slim = {
        "assessment_title": model.get("assessment_title"),
        "title": model.get("title"),
        "version": model.get("version"),
        "levels": model.get("levels"),
        "scoring": model.get("scoring"),
        "dimensions": [],
    }
    for dim in model.get("dimensions") or []:
        qs = []
        for q in dim.get("questions") or []:
            qs.append(
                {
                    "id": q["id"],
                    "tier": q["tier"],
                    "text": q["text"],
                    "weight": q.get("weight", 1),
                    "originType": q.get("originType"),
                    "csfId": q.get("csfId"),
                    "csfName": q.get("csfName"),
                    "ref": q.get("ref"),
                    "levels": q["levels"],
                }
            )
        slim["dimensions"].append({"id": dim["id"], "name": dim["name"], "questions": qs})
    return slim


HTML = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Diagnóstico de Maturidade em IA — Protótipo (plataforma)</title>
<style>
:root{
  --navy:#0e1b33; --navy-2:#16243f; --ink:#242a33; --k0:#0c2340;
  --gold:#c6a15b; --gold-2:#e3cb93; --gold-app:#9b7e46;
  --ivory:#f6f1e7; --ivory-2:#fbf8f1; --wh:#fff;
  --oxblood:#7c3a3a; --muted:#6e6a60; --k5:#a6a6a6; --k8:#f0f0ee; --k9:#f8f8f6;
  --line:rgba(198,161,91,.32); --bd:rgba(14,14,14,.08);
  --serif:Cambria,'Hoefler Text',Georgia,'Times New Roman',serif;
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',Arial,sans-serif;
  --lvl1:#b6543f; --lvl2:#c07a44; --lvl3:#b79a3e; --lvl4:#6f9457; --lvl5:#3f8563;
  --dim-strategy:#7a5aa3; --dim-data:#3d6fa8; --dim-people:#b9822f; --dim-gov:#a3453f;
  --tier-basico:#6f9457; --tier-completo:#b79a3e; --tier-complementar:#3d6fa8;
  --bar-h:56px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--sans);background:var(--k9);color:var(--ink);min-height:100vh;line-height:1.5}
button,select{font:inherit}
a{color:inherit}

.topbar{position:sticky;top:0;z-index:40;height:var(--bar-h);background:var(--navy);color:var(--ivory-2);
  display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 18px;
  border-bottom:1px solid rgba(255,255,255,.06)}
.topbar .brand{font-family:var(--serif);font-size:15px;letter-spacing:.02em}
.topbar .brand span{color:var(--gold);font-size:11px;letter-spacing:.14em;text-transform:uppercase;display:block;margin-bottom:2px}
.topbar nav{display:flex;gap:6px;flex-wrap:wrap}
.topbar .nav-btn{border:1px solid rgba(255,255,255,.14);background:transparent;color:var(--ivory-2);
  padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.topbar .nav-btn.active,.topbar .nav-btn:hover{background:rgba(198,161,91,.18);border-color:var(--gold)}

.wrap{max-width:1440px;margin:0 auto;padding:20px 16px 72px}
.eyebrow{font-size:.7rem;letter-spacing:.22em;text-transform:uppercase;color:var(--gold);font-weight:600;margin:0 0 6px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(1.7rem,4.5vw,2.5rem);line-height:1.08;color:var(--ink);margin:0 0 8px}
h1 em{font-style:italic;color:var(--navy)}
.lede{color:var(--muted);font-size:14px;max-width:62ch}

.card{background:var(--wh);border:1px solid var(--bd);border-radius:12px;padding:18px 20px}
.card.ivory{background:var(--ivory-2);border-color:var(--line);border-radius:4px}

.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--navy);background:var(--navy);color:var(--wh);
  padding:9px 14px;border-radius:6px;cursor:pointer;font-size:13px;text-decoration:none}
.btn:hover{background:var(--navy-2)}
.btn.ghost{background:transparent;color:var(--navy)}
.btn.ghost:hover{background:rgba(14,27,51,.05)}
.btn.danger{background:transparent;border-color:#c9a0a0;color:var(--oxblood)}
.btn:disabled{opacity:.55;cursor:not-allowed}

/* ——— LIST ——— */
.list-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.list-grid{display:grid;gap:12px}
.resp-card{display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;cursor:pointer;transition:border-color .15s}
.resp-card:hover{border-color:var(--gold)}
.resp-meta{font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:6px}
.badge{display:inline-block;font-size:11px;font-weight:600;padding:3px 8px;border-radius:999px;border:1px solid var(--bd);background:var(--k8)}
.badge.tier-basico{color:var(--tier-basico);border-color:rgba(111,148,87,.35);background:rgba(111,148,87,.1)}
.badge.tier-completo{color:#8a7420;border-color:rgba(183,154,62,.4);background:rgba(183,154,62,.12)}
.badge.tier-complementar{color:var(--tier-complementar);border-color:rgba(61,111,168,.35);background:rgba(61,111,168,.1)}
.badge.ok{color:#2f6e4a;background:#e8f0e7;border-color:#bbd3b7}
.badge.draft{color:#8a6d1f;background:#fef5e8;border-color:#ead7a8}
.score-chip{font-family:var(--serif);font-size:28px;color:var(--navy);line-height:1}
.score-chip small{display:block;font-family:var(--sans);font-size:11px;color:var(--muted);margin-top:4px}
.empty{padding:40px 20px;text-align:center;color:var(--muted)}
.mini-bars{display:flex;gap:4px;height:28px;align-items:flex-end;margin-top:10px}
.mini-bars i{display:block;width:18px;border-radius:3px 3px 0 0;background:var(--gold-app);opacity:.85}

/* ——— ASSESS ——— */
.assess-header{display:flex;flex-direction:column;gap:16px;margin-bottom:16px}
.header-row{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start;justify-content:space-between}
.tier-switch{display:flex;gap:6px;flex-wrap:wrap}
.tier-btn{border:1px solid var(--line);background:var(--ivory-2);color:var(--ink);padding:8px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.tier-btn.active{background:var(--navy);color:var(--ivory-2);border-color:var(--navy)}
.tier-btn b{display:block;font-size:13px}
.tier-btn span{opacity:.75;font-size:11px}
.live-dims{display:flex;gap:10px;flex-wrap:wrap;min-width:220px}
.live-dim{flex:1;min-width:100px}
.live-dim .lbl{font-size:11px;color:var(--muted);margin-bottom:4px;display:flex;justify-content:space-between}
.live-dim .bar{height:6px;background:rgba(0,0,0,.06);border-radius:99px;overflow:hidden}
.live-dim .bar > i{display:block;height:100%;border-radius:99px;background:var(--gold)}

.toolbar{position:sticky;top:var(--bar-h);z-index:20;background:rgba(248,248,246,.92);backdrop-filter:blur(8px);
  border:1px solid var(--bd);border-radius:10px;padding:12px 14px;margin-bottom:16px;
  display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center}
.progress-block{flex:1;min-width:200px}
.progress-block .nums{font-size:13px;font-weight:600;color:var(--navy);margin-bottom:4px}
.progress-block .hint{font-size:12px;color:var(--muted)}
.progress-track{height:8px;background:rgba(0,0,0,.06);border-radius:99px;overflow:hidden;margin:6px 0}
.progress-track > i{display:block;height:100%;background:linear-gradient(90deg,var(--gold),var(--gold-2));border-radius:99px;transition:width .2s}
.save-pill{font-size:12px;color:var(--muted);padding:4px 10px;border-radius:999px;border:1px solid var(--bd);background:var(--wh)}
.save-pill.ok{color:#2f6e4a;border-color:#bbd3b7;background:#e8f0e7}
.save-pill.err{color:var(--oxblood);border-color:#e0b4b4;background:#fdecec}
.scale-legend{display:flex;gap:4px;flex-wrap:wrap}
.scale-legend span{font-size:10px;font-weight:700;padding:3px 7px;border-radius:4px;color:#fff}
.scale-legend span:nth-child(1){background:var(--lvl1)}
.scale-legend span:nth-child(2){background:var(--lvl2)}
.scale-legend span:nth-child(3){background:var(--lvl3)}
.scale-legend span:nth-child(4){background:var(--lvl4)}
.scale-legend span:nth-child(5){background:var(--lvl5)}
.pillar-nav{display:flex;gap:6px;flex-wrap:wrap}
.pillar-nav a{font-size:11px;padding:4px 9px;border-radius:999px;border:1px solid var(--line);text-decoration:none;color:var(--navy);background:var(--ivory-2)}
.pillar-nav a:hover{border-color:var(--gold)}

.matrix-wrap{display:flex;flex-direction:column;gap:18px}
.pillar-section{scroll-margin-top:calc(var(--bar-h) + 90px)}
.pillar-band{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;
  border-radius:6px 6px 0 0;color:#fff;font-weight:600;font-size:14px}
.pillar-band[data-dim="strategy"]{background:var(--dim-strategy)}
.pillar-band[data-dim="data_infra"]{background:var(--dim-data)}
.pillar-band[data-dim="people_culture"]{background:var(--dim-people)}
.pillar-band[data-dim="gov_risk"]{background:var(--dim-gov)}
.pillar-band .avg{font-size:12px;font-weight:500;opacity:.9}
.csf-row{display:grid;grid-template-columns:minmax(220px,1.2fr) repeat(5,minmax(90px,1fr));
  border:1px solid var(--line);border-top:none;background:var(--ivory-2)}
.csf-row.hidden{display:none}
.stem{padding:12px 14px;border-right:1px solid var(--line)}
.stem .code{font-size:11px;font-weight:700;color:var(--gold);letter-spacing:.04em}
.stem .tier-pill{display:inline-block;font-size:10px;padding:1px 6px;border-radius:999px;margin-left:6px;border:1px solid var(--bd);color:var(--muted)}
.stem .qtext{font-size:13px;font-weight:600;color:var(--ink);margin:6px 0 4px}
.stem .origin{font-size:11px;color:var(--muted)}
.cell{padding:10px 8px;border-right:1px solid var(--line);cursor:pointer;font-size:11px;line-height:1.35;color:var(--muted);
  transition:background .12s,color .12s;position:relative}
.cell:last-child{border-right:none}
.cell:hover{background:rgba(198,161,91,.1);color:var(--ink)}
.cell.selected{color:#fff;font-weight:600}
.cell.selected[data-lvl="1"]{background:var(--lvl1)}
.cell.selected[data-lvl="2"]{background:var(--lvl2)}
.cell.selected[data-lvl="3"]{background:var(--lvl3)}
.cell.selected[data-lvl="4"]{background:var(--lvl4)}
.cell.selected[data-lvl="5"]{background:var(--lvl5)}
.matrix-head{display:grid;grid-template-columns:minmax(220px,1.2fr) repeat(5,minmax(90px,1fr));
  border:1px solid var(--line);border-bottom:none;background:var(--navy);color:var(--ivory-2);font-size:11px;font-weight:600}
.matrix-head > div{padding:8px;text-align:center;border-right:1px solid rgba(255,255,255,.1)}
.matrix-head > div:first-child{text-align:left;padding-left:14px}
.matrix-head > div:last-child{border-right:none}

@media (max-width:1099px){
  .csf-row,.matrix-head{grid-template-columns:1fr}
  .stem{border-right:none;border-bottom:1px solid var(--line)}
  .cell{border-right:none;border-bottom:1px solid var(--line)}
  .cell:last-child{border-bottom:none}
  .matrix-head{display:none}
}

/* ——— DETAIL ——— */
.hero{display:grid;grid-template-columns:auto 1fr;gap:24px;align-items:center;margin-bottom:16px}
.score-ring{position:relative;width:140px;height:140px}
.score-ring svg{transform:rotate(-90deg)}
.score-ring .center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.score-ring .pct{font-family:var(--serif);font-size:32px;color:var(--navy);line-height:1}
.score-ring .pts{font-size:11px;color:var(--muted)}
.level-badge{display:inline-block;margin-top:8px;padding:6px 12px;border-radius:999px;background:var(--golddim,rgba(155,126,70,.09));
  border:1px solid rgba(155,126,70,.22);color:var(--navy);font-weight:600;font-size:13px}
.level-desc{margin-top:8px;font-size:13px;color:var(--muted);max-width:52ch}
.kpi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.kpi{background:var(--wh);border:1px solid var(--bd);border-radius:12px;padding:14px 16px}
.kpi .k{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.kpi .v{font-family:var(--serif);font-size:22px;color:var(--navy);margin-top:4px}
.kpi .s{font-size:12px;color:var(--muted);margin-top:2px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.radar-wrap{display:flex;justify-content:center;padding:8px}
.dim-row{display:grid;grid-template-columns:140px 1fr auto;gap:10px;align-items:center;margin-bottom:12px}
.dim-row .name{font-size:13px;font-weight:600}
.dim-row .track{height:8px;background:var(--k8);border-radius:99px;overflow:hidden}
.dim-row .track > i{display:block;height:100%;border-radius:99px}
.dim-row .nums{font-size:12px;color:var(--muted);white-space:nowrap}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.note{margin-top:18px;font-size:12px;color:var(--muted);border-top:1px solid var(--bd);padding-top:12px}
@media (max-width:800px){
  .hero,.split,.kpi-grid{grid-template-columns:1fr}
  .resp-card{grid-template-columns:1fr}
}
.view{display:none}
.view.active{display:block}
</style>
</head>
<body>
<header class="topbar">
  <div class="brand"><span>Valorian 4 Future · Protótipo</span>Diagnóstico de Maturidade em IA</div>
  <nav>
    <button type="button" class="nav-btn" data-go="list">Avaliações</button>
    <button type="button" class="nav-btn" data-go="assess">Responder</button>
    <button type="button" class="nav-btn" data-go="detail" id="nav-detail" disabled>Resultado</button>
  </nav>
</header>

<main class="wrap">
  <!-- LIST -->
  <section id="view-list" class="view active">
    <div class="list-head">
      <div>
        <p class="eyebrow">AI Hub · Maturidade</p>
        <h1>Suas <em>autoavaliações</em></h1>
        <p class="lede">Espelho funcional da tela da plataforma: matriz por dimensão × níveis 1–5, abrangências Básico / Completo / Complementar, autosave local e resultado com radar.</p>
      </div>
      <button type="button" class="btn" id="btn-new">Nova autoavaliação</button>
    </div>
    <div id="list-empty" class="card empty" hidden>Nenhuma avaliação ainda. Clique em <strong>Nova autoavaliação</strong>.</div>
    <div id="list-grid" class="list-grid"></div>
  </section>

  <!-- ASSESS -->
  <section id="view-assess" class="view">
    <div class="assess-header">
      <div class="header-row">
        <div>
          <p class="eyebrow" id="assess-eyebrow">Diagnóstico de Maturidade em IA</p>
          <h1 id="assess-title">Avaliação</h1>
          <p class="lede" id="tier-desc"></p>
        </div>
        <div class="tier-switch" id="tier-switch"></div>
      </div>
      <div class="live-dims" id="live-dims"></div>
    </div>

    <div class="toolbar">
      <div class="progress-block">
        <div class="nums"><span id="answered">0</span> / <span id="total">0</span></div>
        <div class="progress-track"><i id="progress-fill" style="width:0%"></i></div>
        <div class="hint" id="progress-label">Nenhuma pergunta respondida ainda</div>
      </div>
      <div class="save-pill" id="save-pill">Salva no navegador</div>
      <div class="scale-legend" aria-label="Escala 1 a 5">
        <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
      </div>
      <div class="pillar-nav" id="pillar-nav"></div>
      <button type="button" class="btn ghost" id="btn-to-result" disabled>Ver resultado</button>
    </div>

    <div class="matrix-wrap" id="matrix"></div>
  </section>

  <!-- DETAIL -->
  <section id="view-detail" class="view">
    <p class="eyebrow">Resultado</p>
    <h1 id="detail-title">Diagnóstico</h1>
    <p class="lede" id="detail-date"></p>

    <section class="card hero" style="margin-top:16px">
      <div class="score-ring">
        <svg width="140" height="140" viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r="54" fill="none" stroke="#e8e4da" stroke-width="8"/>
          <circle id="ring-arc" cx="60" cy="60" r="54" fill="none" stroke="#9b7e46" stroke-width="8"
            stroke-linecap="round" stroke-dasharray="339.292" stroke-dashoffset="339.292"/>
        </svg>
        <div class="center">
          <div class="pct" id="ring-pct">0%</div>
          <div class="pts" id="ring-pts">0 / 0 pts</div>
        </div>
      </div>
      <div>
        <div class="badge" id="detail-tier"></div>
        <div class="level-badge" id="level-label">—</div>
        <p class="level-desc" id="level-desc"></p>
      </div>
    </section>

    <section class="kpi-grid">
      <div class="kpi"><div class="k">Dimensões</div><div class="v" id="kpi-dims">4</div><div class="s">no modelo</div></div>
      <div class="kpi"><div class="k">Mais madura</div><div class="v" id="kpi-strong">—</div><div class="s" id="kpi-strong-s"></div></div>
      <div class="kpi"><div class="k">Mais frágil</div><div class="v" id="kpi-weak">—</div><div class="s" id="kpi-weak-s"></div></div>
    </section>

    <section class="split">
      <div class="card">
        <h3 style="font-family:var(--serif);font-size:18px;margin-bottom:8px">Radar por dimensão</h3>
        <div class="radar-wrap">
          <svg id="radar" width="320" height="320" viewBox="0 0 320 320"></svg>
        </div>
      </div>
      <div class="card">
        <h3 style="font-family:var(--serif);font-size:18px;margin-bottom:12px">Pontuação por dimensão</h3>
        <div id="dim-bars"></div>
      </div>
    </section>

    <div class="actions">
      <button type="button" class="btn" id="btn-edit">Editar respostas</button>
      <button type="button" class="btn ghost" id="btn-export">Exportar JSON</button>
      <button type="button" class="btn ghost" data-go="list">Voltar à lista</button>
      <button type="button" class="btn danger" id="btn-delete">Excluir</button>
    </div>
  </section>

  <p class="note">
    Protótipo offline espelhando a avaliação da plataforma AEGIS (modelo v<span id="model-ver">3.0</span>).
    Persistência em <code>localStorage</code> — sem API. Fonte do questionário:
    <code>backend/data/ai_maturity_model.json</code>. Gerado por <code>util/export_maturity_prototype.py</code>.
  </p>
</main>

<script>
const MODEL = __MODEL_JSON__;
const STORAGE_KEY = 'aegis.maturity.prototype.v1';
const TIER_ORDER = { basico: 0, completo: 1, complementar: 2 };
const TIER_KEYS = ['basico', 'completo', 'complementar'];
const TIER_SHORT = { basico: 'Básico', completo: 'Completo', complementar: 'Complementar' };
const DIM_COLOR = {
  strategy: 'var(--dim-strategy)',
  data_infra: 'var(--dim-data)',
  people_culture: 'var(--dim-people)',
  gov_risk: 'var(--dim-gov)',
};
const RING_C = 2 * Math.PI * 54;

const state = {
  view: 'list',
  currentId: null,
  tier: 'basico',
  answers: {},
  saveTimer: null,
};

function loadStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { items: [] };
    const data = JSON.parse(raw);
    return { items: Array.isArray(data.items) ? data.items : [] };
  } catch { return { items: [] }; }
}
function saveStore(store) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}
function uid() {
  return 'm_' + Math.random().toString(36).slice(2, 10);
}

function questionIndex() {
  const map = {};
  for (const dim of MODEL.dimensions || []) {
    for (const q of dim.questions || []) map[q.id] = { ...q, dimId: dim.id, dimName: dim.name };
  }
  return map;
}
const QINDEX = questionIndex();

function isVisibleTier(qTier, selected) {
  return (TIER_ORDER[qTier] ?? 0) <= (TIER_ORDER[selected] ?? 0);
}
function visibleQuestions(tier) {
  return Object.values(QINDEX).filter((q) => isVisibleTier(q.tier, tier));
}
function totalForTier(tier) {
  return MODEL.levels?.[tier]?.question_count ?? visibleQuestions(tier).length;
}

/** Mesma fórmula de `backend/app/routes/maturity.py` `_score_submission`. */
function scoreSubmission(answers, tier) {
  const questions = visibleQuestions(tier);
  const levelsCfg = MODEL.levels?.[tier] || {};
  const maxScore = Number(levelsCfg.max_score || questions.length * 5);
  let totalScore = 0;
  const dimensionScores = {};

  for (const dim of MODEL.dimensions || []) {
    const dimQs = (dim.questions || []).filter((q) => isVisibleTier(q.tier, tier));
    let dimScore = 0, dimMax = 0;
    for (const q of dimQs) {
      const weight = Number(q.weight || 1);
      let value = Number(answers[q.id] || 0);
      if (value < 1 || value > 5) value = 0;
      dimScore += value * weight;
      dimMax += 5 * weight;
    }
    const avg = dimQs.length ? dimScore / dimQs.length : 0;
    dimensionScores[dim.id] = {
      name: dim.name,
      score: dimScore,
      max: dimMax,
      avg: Math.round(avg * 100) / 100,
    };
    totalScore += dimScore;
  }

  const scoring = MODEL.scoring?.[tier] || {};
  let level = null;
  for (const key of ['level_1', 'level_2', 'level_3', 'level_4', 'level_5']) {
    const cfg = scoring[key];
    if (!cfg) continue;
    if (cfg.min <= totalScore && totalScore <= cfg.max) { level = cfg; break; }
  }
  if (!level && scoring.level_1) {
    if (totalScore < scoring.level_1.min) level = scoring.level_1;
    else level = scoring.level_5 || scoring.level_1;
  }

  return {
    total_score: totalScore,
    max_score: maxScore,
    percent_score: maxScore ? Math.round((totalScore / maxScore) * 10000) / 100 : 0,
    dimension_scores: dimensionScores,
    level,
    tier,
  };
}

function isComplete(answers, tier) {
  const ids = visibleQuestions(tier).map((q) => q.id);
  return ids.length > 0 && ids.every((id) => answers[id] != null);
}

function showView(name) {
  state.view = name;
  document.querySelectorAll('.view').forEach((el) => el.classList.toggle('active', el.id === 'view-' + name));
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.getAttribute('data-go') === name);
  });
  const navDetail = document.getElementById('nav-detail');
  navDetail.disabled = !state.currentId;
}

function formatDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

/* ——— LIST ——— */
function renderList() {
  const store = loadStore();
  const grid = document.getElementById('list-grid');
  const empty = document.getElementById('list-empty');
  grid.innerHTML = '';
  if (!store.items.length) {
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  const items = [...store.items].sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
  for (const item of items) {
    const result = item.result || scoreSubmission(item.answers || {}, item.tier || 'basico');
    const complete = !!item.complete;
    const card = document.createElement('article');
    card.className = 'card resp-card';
    const dims = MODEL.dimensions || [];
    const bars = dims.map((d) => {
      const ds = result.dimension_scores?.[d.id];
      const pct = ds && ds.max ? (ds.score / ds.max) * 100 : 0;
      return `<i style="height:${Math.max(4, pct * 0.28)}px;background:${DIM_COLOR[d.id] || 'var(--gold)'}" title="${d.name}"></i>`;
    }).join('');
    card.innerHTML = `
      <div>
        <strong>${result.level?.label || (complete ? 'Concluída' : 'Em andamento')}</strong>
        <div class="resp-meta">
          <span class="badge tier-${item.tier}">${TIER_SHORT[item.tier] || item.tier}</span>
          <span class="badge ${complete ? 'ok' : 'draft'}">${complete ? 'Completa' : 'Rascunho'}</span>
          <span>Atualizada ${formatDate(item.updated_at)}</span>
        </div>
        <div class="mini-bars">${bars}</div>
      </div>
      <div class="score-chip">${Math.round(result.percent_score || 0)}%<small>${result.total_score}/${result.max_score} pts</small></div>
    `;
    card.addEventListener('click', () => openItem(item.id, complete ? 'detail' : 'assess'));
    grid.appendChild(card);
  }
}

function openItem(id, view) {
  const store = loadStore();
  const item = store.items.find((x) => x.id === id);
  if (!item) return;
  state.currentId = id;
  state.tier = TIER_KEYS.includes(item.tier) ? item.tier : 'basico';
  state.answers = { ...(item.answers || {}) };
  document.getElementById('nav-detail').disabled = false;
  if (view === 'detail') renderDetail();
  else renderAssess();
  showView(view);
}

function newAssessment() {
  state.currentId = null;
  state.tier = 'basico';
  state.answers = {};
  document.getElementById('nav-detail').disabled = true;
  renderAssess();
  showView('assess');
  setSavePill('idle');
}

/* ——— ASSESS ——— */
function persistNow() {
  const store = loadStore();
  const now = new Date().toISOString();
  const result = scoreSubmission(state.answers, state.tier);
  const complete = isComplete(state.answers, state.tier);
  if (!state.currentId && !Object.keys(state.answers).length) {
    setSavePill('idle');
    return;
  }
  if (!state.currentId) {
    state.currentId = uid();
    store.items.push({
      id: state.currentId,
      tier: state.tier,
      answers: { ...state.answers },
      result,
      complete,
      created_at: now,
      updated_at: now,
    });
  } else {
    const item = store.items.find((x) => x.id === state.currentId);
    if (!item) return;
    item.tier = state.tier;
    item.answers = { ...state.answers };
    item.result = result;
    item.complete = complete;
    item.updated_at = now;
  }
  saveStore(store);
  document.getElementById('nav-detail').disabled = false;
  document.getElementById('btn-to-result').disabled = !complete;
  setSavePill('saved');
  updateProgress();
  updateLiveDims();
}

function schedulePersist() {
  setSavePill('saving');
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(persistNow, 280);
}

function setSavePill(mode) {
  const el = document.getElementById('save-pill');
  el.classList.remove('ok', 'err');
  if (mode === 'saving') el.textContent = 'Salvando…';
  else if (mode === 'saved') { el.textContent = 'Salvo neste navegador'; el.classList.add('ok'); }
  else if (mode === 'error') { el.textContent = 'Falha ao salvar'; el.classList.add('err'); }
  else el.textContent = 'Salva no navegador';
}

function updateProgress() {
  const ids = visibleQuestions(state.tier).map((q) => q.id);
  const answered = ids.filter((id) => state.answers[id] != null).length;
  const total = totalForTier(state.tier);
  document.getElementById('answered').textContent = String(answered);
  document.getElementById('total').textContent = String(total);
  document.getElementById('progress-fill').style.width = (total ? (answered / total) * 100 : 0) + '%';
  const complete = answered === total && total > 0;
  document.getElementById('btn-to-result').disabled = !complete;
  const label = document.getElementById('progress-label');
  if (answered === 0) label.textContent = 'Nenhuma pergunta respondida ainda';
  else if (complete) {
    const v = scoreSubmission(state.answers, state.tier);
    label.textContent = `Abrangência ${TIER_SHORT[state.tier]} concluída · ${v.total_score}/${v.max_score} pts · ${v.level?.label || '—'}`;
  } else {
    label.textContent = `${total - answered} pergunta(s) restante(s) na abrangência ${TIER_SHORT[state.tier]}`;
  }
}

function updateLiveDims() {
  const root = document.getElementById('live-dims');
  root.innerHTML = '';
  for (const dim of MODEL.dimensions || []) {
    const qs = (dim.questions || []).filter((q) => isVisibleTier(q.tier, state.tier));
    const answered = qs.filter((q) => state.answers[q.id] != null);
    const avg = answered.length
      ? answered.reduce((a, q) => a + Number(state.answers[q.id]), 0) / answered.length
      : null;
    const pct = avg != null ? (avg / 5) * 100 : 0;
    const el = document.createElement('div');
    el.className = 'live-dim';
    el.innerHTML = `
      <div class="lbl"><span>${dim.name}</span><span>${avg != null ? avg.toFixed(1) : '—'}</span></div>
      <div class="bar"><i style="width:${pct}%;background:${DIM_COLOR[dim.id]}"></i></div>`;
    root.appendChild(el);
  }
}

function originLine(q) {
  if (q.csfId) return `Abrangência ${TIER_SHORT[q.tier]} · CSF ${q.csfId}${q.csfName ? ' · ' + q.csfName : ''}`;
  return `Abrangência ${TIER_SHORT[q.tier]}${q.ref ? ' · ' + q.ref : ''}`;
}

function renderAssess() {
  document.getElementById('assess-eyebrow').textContent = MODEL.assessment_title || MODEL.title || 'Maturidade';
  document.getElementById('assess-title').innerHTML = (MODEL.title || 'Avaliação') + ' <em>v' + (MODEL.version || '') + '</em>';
  document.getElementById('model-ver').textContent = MODEL.version || '3.0';

  const switchEl = document.getElementById('tier-switch');
  switchEl.innerHTML = '';
  for (const key of TIER_KEYS) {
    const cfg = MODEL.levels?.[key] || {};
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tier-btn' + (key === state.tier ? ' active' : '');
    btn.innerHTML = `<b>${cfg.label || TIER_SHORT[key]}</b><span>${cfg.question_count || 0} perguntas · máx. ${cfg.max_score || 0}</span>`;
    btn.addEventListener('click', () => {
      state.tier = key;
      renderAssess();
      if (state.currentId || Object.keys(state.answers).length) schedulePersist();
    });
    switchEl.appendChild(btn);
  }
  document.getElementById('tier-desc').textContent = MODEL.levels?.[state.tier]?.description || '';

  const nav = document.getElementById('pillar-nav');
  nav.innerHTML = '';
  (MODEL.dimensions || []).forEach((dim, idx) => {
    const a = document.createElement('a');
    a.href = '#dim-' + idx;
    a.textContent = dim.name;
    nav.appendChild(a);
  });

  const matrix = document.getElementById('matrix');
  matrix.innerHTML = `
    <div class="matrix-head">
      <div>Pergunta</div>
      <div>1 · Inicial</div><div>2 · Emergente</div><div>3 · Estruturado</div><div>4 · Gerenciado</div><div>5 · Otimizado</div>
    </div>`;

  (MODEL.dimensions || []).forEach((dim, dIdx) => {
    const section = document.createElement('section');
    section.className = 'pillar-section';
    section.id = 'dim-' + dIdx;
    const qs = [...(dim.questions || [])].sort((a, b) => String(a.id).localeCompare(String(b.id), undefined, { numeric: true }));
    const answered = qs.filter((q) => isVisibleTier(q.tier, state.tier) && state.answers[q.id] != null);
    const avg = answered.length
      ? answered.reduce((a, q) => a + Number(state.answers[q.id]), 0) / answered.length
      : null;
    section.innerHTML = `<div class="pillar-band" data-dim="${dim.id}"><span>${dim.name}</span><span class="avg">${avg != null ? 'média ' + avg.toFixed(1) + '/5' : '—'}</span></div>`;

    for (const q of qs) {
      const visible = isVisibleTier(q.tier, state.tier);
      const row = document.createElement('div');
      row.className = 'csf-row' + (visible ? '' : ' hidden');
      row.dataset.qid = q.id;
      let cells = '';
      for (let lvl = 1; lvl <= 5; lvl++) {
        const sel = state.answers[q.id] === lvl ? ' selected' : '';
        const txt = (q.levels && (q.levels[String(lvl)] || q.levels[lvl])) || ('Nível ' + lvl);
        cells += `<div class="cell${sel}" data-lvl="${lvl}" role="button" tabindex="0" title="${txt.replace(/"/g, '&quot;')}"><span class="txt">${txt}</span></div>`;
      }
      row.innerHTML = `
        <div class="stem">
          <div><span class="code">${q.id}</span><span class="tier-pill">${TIER_SHORT[q.tier]}</span></div>
          <div class="qtext">${q.text}</div>
          <div class="origin">${originLine(q)}</div>
        </div>${cells}`;
      row.querySelectorAll('.cell').forEach((cell) => {
        const activate = () => {
          const lvl = Number(cell.dataset.lvl);
          if (state.answers[q.id] === lvl) delete state.answers[q.id];
          else state.answers[q.id] = lvl;
          renderAssess();
          schedulePersist();
        };
        cell.addEventListener('click', activate);
        cell.addEventListener('keydown', (ev) => {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); activate(); }
        });
      });
      section.appendChild(row);
    }
    matrix.appendChild(section);
  });

  updateProgress();
  updateLiveDims();
}

/* ——— DETAIL ——— */
function renderDetail() {
  const store = loadStore();
  const item = store.items.find((x) => x.id === state.currentId);
  if (!item) { showView('list'); return; }
  const result = scoreSubmission(item.answers || {}, item.tier || 'basico');
  item.result = result;
  item.complete = isComplete(item.answers || {}, item.tier || 'basico');
  saveStore(store);

  document.getElementById('detail-title').textContent = result.level?.label || 'Resultado';
  document.getElementById('detail-date').textContent = `Atualizada ${formatDate(item.updated_at)} · modelo v${MODEL.version || ''}`;
  document.getElementById('detail-tier').textContent = TIER_SHORT[item.tier] || item.tier;
  document.getElementById('detail-tier').className = 'badge tier-' + item.tier;
  document.getElementById('level-label').textContent = result.level?.label || '—';
  document.getElementById('level-desc').textContent = result.level?.description || '';
  document.getElementById('ring-pct').textContent = Math.round(result.percent_score) + '%';
  document.getElementById('ring-pts').textContent = `${result.total_score} / ${result.max_score} pts`;
  document.getElementById('ring-arc').setAttribute(
    'stroke-dashoffset',
    String(RING_C * (1 - Math.min(100, Math.max(0, result.percent_score)) / 100))
  );

  const rows = (MODEL.dimensions || []).map((dim) => {
    const ds = result.dimension_scores?.[dim.id] || { name: dim.name, score: 0, max: 0, avg: 0 };
    const pct = ds.max ? Math.round((ds.score / ds.max) * 100) : 0;
    return { id: dim.id, name: ds.name || dim.name, score: ds.score, max: ds.max, avg: ds.avg, pct };
  });
  document.getElementById('kpi-dims').textContent = String(rows.length);
  const strong = rows.reduce((a, b) => (b.avg > a.avg ? b : a), rows[0] || { name: '—', avg: 0 });
  const weak = rows.reduce((a, b) => (b.avg < a.avg ? b : a), rows[0] || { name: '—', avg: 0 });
  document.getElementById('kpi-strong').textContent = strong.name || '—';
  document.getElementById('kpi-strong-s').textContent = strong.avg != null ? `média ${Number(strong.avg).toFixed(1)}/5` : '';
  document.getElementById('kpi-weak').textContent = weak.name || '—';
  document.getElementById('kpi-weak-s').textContent = weak.avg != null ? `média ${Number(weak.avg).toFixed(1)}/5` : '';

  const bars = document.getElementById('dim-bars');
  bars.innerHTML = rows.map((r) => `
    <div class="dim-row">
      <div class="name">${r.name}</div>
      <div class="track"><i style="width:${r.pct}%;background:${DIM_COLOR[r.id] || 'var(--gold-app)'}"></i></div>
      <div class="nums">${r.pct}% · ${r.score}/${r.max}</div>
    </div>`).join('');

  drawRadar(rows);
}

function drawRadar(rows) {
  const svg = document.getElementById('radar');
  const CX = 160, CY = 160, R = 110, LR = 132;
  const n = rows.length || 1;
  const point = (i, pct) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    const r = (pct / 100) * R;
    return [CX + r * Math.cos(angle), CY + r * Math.sin(angle)];
  };
  let html = '';
  for (const g of [0.2, 0.4, 0.6, 0.8, 1]) {
    const pts = rows.map((_, i) => point(i, g * 100).join(',')).join(' ');
    html += `<polygon points="${pts}" fill="none" stroke="#e2ddd2" stroke-width="1"/>`;
  }
  for (let i = 0; i < n; i++) {
    const [x, y] = point(i, 100);
    html += `<line x1="${CX}" y1="${CY}" x2="${x}" y2="${y}" stroke="#e2ddd2" stroke-width="1"/>`;
    const angle = -Math.PI / 2 + (2 * Math.PI * i) / n;
    const lx = CX + LR * Math.cos(angle);
    const ly = CY + LR * Math.sin(angle);
    const anchor = Math.cos(angle) > 0.2 ? 'start' : Math.cos(angle) < -0.2 ? 'end' : 'middle';
    html += `<text x="${lx}" y="${ly}" text-anchor="${anchor}" dominant-baseline="middle" font-size="11" fill="#6e6a60">${rows[i].name}</text>`;
  }
  const poly = rows.map((r, i) => point(i, r.pct).join(',')).join(' ');
  html += `<polygon points="${poly}" fill="rgba(155,126,70,.28)" stroke="#9b7e46" stroke-width="2"/>`;
  rows.forEach((r, i) => {
    const [x, y] = point(i, r.pct);
    html += `<circle cx="${x}" cy="${y}" r="4" fill="${DIM_COLOR[r.id] || '#9b7e46'}"/>`;
  });
  svg.innerHTML = html;
}

/* ——— EXPORT / DELETE ——— */
function exportJson() {
  const store = loadStore();
  const item = store.items.find((x) => x.id === state.currentId);
  if (!item) return;
  const result = scoreSubmission(item.answers || {}, item.tier || 'basico');
  const doc = {
    schema: 'aegis.maturidade-ia',
    versao: '1',
    modelo: { title: MODEL.title, version: MODEL.version },
    tier: item.tier,
    answers: item.answers,
    result,
    exported_at: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `maturidade-${item.id}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function deleteCurrent() {
  if (!state.currentId) return;
  if (!confirm('Excluir esta autoavaliação deste navegador?')) return;
  const store = loadStore();
  store.items = store.items.filter((x) => x.id !== state.currentId);
  saveStore(store);
  state.currentId = null;
  state.answers = {};
  document.getElementById('nav-detail').disabled = true;
  renderList();
  showView('list');
}

/* ——— WIRE ——— */
document.querySelectorAll('[data-go]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const go = btn.getAttribute('data-go');
    if (go === 'list') { renderList(); showView('list'); }
    else if (go === 'assess') {
      if (!state.currentId) newAssessment();
      else { renderAssess(); showView('assess'); }
    }
    else if (go === 'detail' && state.currentId) { renderDetail(); showView('detail'); }
  });
});
document.getElementById('btn-new').addEventListener('click', newAssessment);
document.getElementById('btn-to-result').addEventListener('click', () => {
  persistNow();
  if (state.currentId && isComplete(state.answers, state.tier)) {
    renderDetail();
    showView('detail');
  }
});
document.getElementById('btn-edit').addEventListener('click', () => {
  renderAssess();
  showView('assess');
});
document.getElementById('btn-export').addEventListener('click', exportJson);
document.getElementById('btn-delete').addEventListener('click', deleteCurrent);

document.getElementById('model-ver').textContent = MODEL.version || '3.0';
renderList();
</script>
</body>
</html>
'''


def main() -> None:
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    slim = slim_model(model)
    model_js = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    html = HTML.replace("__MODEL_JSON__", model_js)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes, {sum(len(d['questions']) for d in slim['dimensions'])} questions)")


if __name__ == "__main__":
    main()
