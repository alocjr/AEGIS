(function(){
"use strict";

var DATA = JSON.parse(document.getElementById('data-json').textContent);

var CAT_COLOR = {
  mitos:'var(--cat-mitos)', literatura:'var(--cat-literatura)', cinema:'var(--cat-cinema)',
  series:'var(--cat-series)', animes:'var(--cat-animes)', games:'var(--cat-games)',
  ciborgues:'var(--cat-ciborgues)', transumanismo:'var(--cat-transumanismo)'
};
var CAT_ORDER = ['mitos','literatura','cinema','series','animes','games','ciborgues','transumanismo'];
var CAT_LABEL = {
  mitos:'Mitos', literatura:'Literatura', cinema:'Cinema', series:'Séries de TV',
  animes:'Animes & Mangás', games:'Games', ciborgues:'Ciborgues', transumanismo:'Transumanismo'
};
var PERIODS = [
  {id:'ancient', label:'Antiguidade e Idade Média', min:null, max:1799},
  {id:'p1800', label:'1800–1919', min:1800, max:1919},
  {id:'p1920', label:'1920–1949', min:1920, max:1949},
  {id:'p1950', label:'Anos 1950', min:1950, max:1959},
  {id:'p1960', label:'Anos 1960', min:1960, max:1969},
  {id:'p1970', label:'Anos 1970', min:1970, max:1979},
  {id:'p1980', label:'Anos 1980', min:1980, max:1989},
  {id:'p1990', label:'Anos 1990', min:1990, max:1999},
  {id:'p2000', label:'2000–2009', min:2000, max:2009},
  {id:'p2010', label:'2010–2019', min:2010, max:2019},
  {id:'p2020', label:'2020–2026', min:2020, max:9999}
];

function esc(s){
  if(s===undefined||s===null) return '';
  var d=document.createElement('div'); d.textContent=s; return d.innerHTML;
}

/* =========================================================
   1. FRONTIER CARDS (Mapa Conceitual)
   ========================================================= */
function renderFrontiers(){
  var grid = document.getElementById('frontier-grid');
  var html = DATA.frontiers.map(function(f,i){
    return '<div class="frontier-card">' +
      '<div class="frontier-num">FRENTE 0'+(i+1)+'</div>' +
      '<h3>'+esc(f.name)+'</h3>' +
      '<div class="frontier-q">'+esc(f.question)+'</div>' +
      '<div class="frontier-works">'+esc(f.works)+'</div>' +
    '</div>';
  }).join('');
  grid.innerHTML = html;
}

/* =========================================================
   2. GENEALOGY TREE (SVG)
   ========================================================= */
var LIN_BY_ID = {};
function renderGenealogy(){
  var W = 1080, H = 1024;
  var wrap = document.getElementById('genealogy-wrap');

  (DATA.graph.lineages||[]).forEach(function(L){ LIN_BY_ID[L.id] = L; });

  function count(linId){
    var L = LIN_BY_ID[linId];
    return L ? L.members.length : 0;
  }

  function node(linId,x,y,w,label,sub,fill,textFill){
    var h = 70;
    textFill = textFill || '#F7F3EB';
    var n = count(linId);
    var bw = 104, bh = 19, by = y + 14;
    return '<g class="tree-node" data-lin="'+linId+'" tabindex="0" role="button" ' +
             'aria-label="Explorar '+esc(label)+'">' +
      '<rect class="tn-box" x="'+(x-w/2)+'" y="'+(y-h/2)+'" width="'+w+'" height="'+h+'" rx="6" fill="'+fill+'" stroke="#C9A227" stroke-width="1"/>' +
      '<text x="'+x+'" y="'+(y-16)+'" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="11.5" font-weight="700" fill="'+textFill+'" letter-spacing="0.4">'+esc(label)+'</text>' +
      (sub ? '<text x="'+x+'" y="'+(y-3)+'" text-anchor="middle" font-family="Inter, sans-serif" font-size="9.5" fill="'+textFill+'" opacity="0.72">'+esc(sub)+'</text>' : '') +
      '<g class="tn-btn">' +
        '<rect x="'+(x-bw/2)+'" y="'+(by-bh/2)+'" width="'+bw+'" height="'+bh+'" rx="9.5" fill="#C9A227"/>' +
        '<text x="'+x+'" y="'+(by+3.6)+'" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="9" font-weight="700" fill="#0A1F33" letter-spacing="0.9">EXPLORAR · '+n+'</text>' +
      '</g>' +
    '</g>';
  }
  function link(x1,y1,x2,y2){
    var midY = (y1+y2)/2;
    return '<path d="M'+x1+','+y1+' C'+x1+','+midY+' '+x2+','+midY+' '+x2+','+y2+'" fill="none" stroke="#C9A227" stroke-width="1.4" opacity="0.5"/>';
  }
  function straight(x1,y1,x2,y2){
    return '<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="#C9A227" stroke-width="1.4" opacity="0.5"/>';
  }

  var navy='#13293D', navyDark='#0A1F33', stone='#33506B', ochre='#8A6A16', slate='#4A4F55';
  var yR=48, y2=168, y3=282, y4=386, y5=500, y6=620, y7=734, y8=848, y9=962;
  var T=35; // half height

  var svg = '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="min-width:880px;display:block;font-family:Inter,sans-serif;">';

  // links first (drawn under nodes)
  svg += link(W/2,yR+T, 300,y2-T) + link(W/2,yR+T, 740,y2-T);
  svg += link(740,y2+T, 740,y3-T);
  svg += link(740,y3+T, 740,y4-T);
  svg += link(300,y2+T, 520,y5-T) + link(740,y4+T, 520,y5-T);
  svg += link(520,y5+T, 250,y6-T) + link(520,y5+T, 540,y6-T) + link(520,y5+T, 830,y6-T);
  svg += link(540,y6+T, 660,y7-T) + link(830,y6+T, 660,y7-T);
  svg += link(250,y6+T, 250,y7-T);
  svg += straight(520,y5+T, 520,y8-T);
  svg += link(520,y8+T, 340,y9-T) + link(520,y8+T, 700,y9-T);

  // nodes
  svg += node('raiz',        W/2, yR, 258, 'CRIAÇÃO ARTIFICIAL', 'a rede completa', navyDark);
  svg += node('vida',        300, y2, 232, 'VIDA ARTIFICIAL', 'Golem · Frankenstein', stone);
  svg += node('automatos',   740, y2, 232, 'AUTÔMATOS', 'Talos · Pigmalião', stone);
  svg += node('robos',       740, y3, 206, 'ROBÔS', 'R.U.R., 1920', navy);
  svg += node('robotica',    740, y4, 206, 'ROBÓTICA', 'Asimov, 1942', navy);
  svg += node('computacao',  520, y5, 244, 'COMPUTAÇÃO', 'Babbage · Lovelace · Turing', navyDark);
  svg += node('cibernetica', 250, y6, 218, 'CIBERNÉTICA', 'Wiener, 1948', stone);
  svg += node('ia',          540, y6, 228, 'INTELIGÊNCIA ARTIFICIAL', 'Dartmouth, 1956', ochre);
  svg += node('redes',       830, y6, 218, 'REDES NEURAIS', 'McCulloch–Pitts', stone);
  svg += node('ciborgues',   250, y7, 232, 'CIBORGUES', 'RoboCop · Ghost in the Shell', slate);
  svg += node('generativa',  660, y7, 228, 'IA GENERATIVA', 'Agentes · LLMs', ochre);
  svg += node('androides',   520, y8, 244, 'ANDROIDES', '"O que é humano?"', navy);
  svg += node('transumanismo',340,y9, 228, 'TRANSUMANISMO', 'enhancement · Kurzweil', ochre);
  svg += node('poshumanismo',700, y9, 240, 'PÓS-HUMANISMO', 'upload · consciência distribuída', ochre);

  svg += '</svg>';
  wrap.innerHTML = svg;

  function fire(el){
    var lin = el.getAttribute('data-lin');
    if(lin) openGraph(lin);
  }
  wrap.addEventListener('click', function(ev){
    var g = ev.target.closest('.tree-node');
    if(g) fire(g);
  });
  wrap.addEventListener('keydown', function(ev){
    if(ev.key!=='Enter' && ev.key!==' ') return;
    var g = ev.target.closest ? ev.target.closest('.tree-node') : null;
    if(g){ ev.preventDefault(); fire(g); }
  });
}

/* =========================================================
   3. TIMELINE TABLE
   ========================================================= */
function renderTimeline(){
  var cols = [
    {key:'ia', label:'Inteligência Artificial'},
    {key:'comp', label:'Computação & Cibernética'},
    {key:'robotics', label:'Robótica'},
    {key:'androids', label:'Androides & Vida Art.'},
    {key:'cyborgs', label:'Ciborgues'},
    {key:'trans', label:'Transumanismo'}
  ];
  var thead = '<thead><tr><th>Período</th>' + cols.map(function(c){return '<th>'+esc(c.label)+'</th>';}).join('') + '</tr></thead>';
  var rows = DATA.timeline.map(function(r){
    var cells = cols.map(function(c){
      var val = r[c.key];
      var cls = (val==='—') ? ' class="empty-cell"' : '';
      return '<td'+cls+'>'+esc(val)+'</td>';
    }).join('');
    return '<tr><td>'+esc(r.period)+'</td>'+cells+'</tr>';
  }).join('');
  document.getElementById('timeline-table').innerHTML = thead + '<tbody>'+rows+'</tbody>';
}

/* =========================================================
   COVER THUMBNAILS — generated, self-contained, no external assets
   Each work gets a deterministic "capa" built from its own data:
   media drives the palette and the motif, the title seeds the variation.
   ========================================================= */
var COVER_BASE = {
  mitos:        {bg:'#3F2E57', ink:'#C9A9E8'},
  literatura:   {bg:'#1B3448', ink:'#9FC0DA'},
  cinema:       {bg:'#4A1F1D', ink:'#E39A93'},
  series:       {bg:'#17324E', ink:'#8FBBE8'},
  animes:       {bg:'#4A3413', ink:'#E8BE72'},
  ciborgues:    {bg:'#2A2E33', ink:'#B4BDC6'},
  games:        {bg:'#15382C', ink:'#7FCFAA'},
  transumanismo:{bg:'#453714', ink:'#E5C868'}
};

function hashStr(s){
  var h=2166136261;
  for(var i=0;i<s.length;i++){ h^=s.charCodeAt(i); h=Math.imul(h,16777619); }
  return h>>>0;
}
function seeded(seed){
  var s=seed>>>0;
  return function(){ s=(s*1664525+1013904223)>>>0; return s/4294967296; };
}
function wrapTitle(t, maxChars, maxLines){
  var words=String(t).split(/\s+/), lines=[], cur='';
  for(var i=0;i<words.length;i++){
    var w=words[i];
    if(w.length>maxChars) w=w.slice(0,maxChars-1)+'…';
    var test = cur ? cur+' '+w : w;
    if(test.length<=maxChars){ cur=test; }
    else{
      if(cur) lines.push(cur);
      cur=w;
      if(lines.length>=maxLines) break;
    }
  }
  if(cur && lines.length<maxLines) lines.push(cur);
  if(lines.length===maxLines){
    var used=lines.join(' ').split(/\s+/).length;
    if(used < words.length){
      var last=lines[maxLines-1];
      lines[maxLines-1]= last.length>maxChars-1 ? last.slice(0,maxChars-1)+'…' : last+'…';
    }
  }
  return lines;
}

/* --- motifs: one visual language per media --- */
function motif(media, rnd, ink){
  var o='', i, y, x;
  var op=function(v){ return ' opacity="'+v+'"'; };
  switch(media){
    case 'cinema': // film perforations + frame lines
      for(i=0;i<7;i++){
        y=8+i*13;
        o+='<rect x="5" y="'+y+'" width="7" height="8" rx="1.4" fill="'+ink+'"'+op(.30)+'/>';
        o+='<rect x="108" y="'+y+'" width="7" height="8" rx="1.4" fill="'+ink+'"'+op(.30)+'/>';
      }
      o+='<rect x="20" y="16" width="80" height="52" fill="none" stroke="'+ink+'" stroke-width="1.6"'+op(.42)+'/>';
      o+='<circle cx="60" cy="42" r="'+(11+rnd()*5)+'" fill="none" stroke="'+ink+'" stroke-width="1.4"'+op(.5)+'/>';
      break;
    case 'literatura': // page block + spine
      o+='<rect x="18" y="12" width="84" height="70" fill="none" stroke="'+ink+'" stroke-width="1.4"'+op(.4)+'/>';
      o+='<line x1="34" y1="12" x2="34" y2="82" stroke="'+ink+'" stroke-width="1.2"'+op(.4)+'/>';
      for(i=0;i<7;i++){
        y=22+i*8;
        o+='<line x1="42" y1="'+y+'" x2="'+(94-rnd()*26)+'" y2="'+y+'" stroke="'+ink+'" stroke-width="1.5"'+op(.26)+'/>';
      }
      break;
    case 'series': // screen + scanlines
      o+='<rect x="16" y="14" width="88" height="60" rx="5" fill="none" stroke="'+ink+'" stroke-width="1.8"'+op(.45)+'/>';
      for(i=0;i<11;i++){
        y=20+i*5;
        o+='<line x1="22" y1="'+y+'" x2="98" y2="'+y+'" stroke="'+ink+'" stroke-width="1"'+op(.16+(i%2)*.10)+'/>';
      }
      o+='<line x1="46" y1="78" x2="74" y2="78" stroke="'+ink+'" stroke-width="2"'+op(.4)+'/>';
      break;
    case 'games': // pixel grid
      for(i=0;i<26;i++){
        x=16+Math.floor(rnd()*9)*10;
        y=14+Math.floor(rnd()*7)*10;
        o+='<rect x="'+x+'" y="'+y+'" width="9" height="9" fill="'+ink+'"'+op(.14+rnd()*.34)+'/>';
      }
      o+='<rect x="16" y="14" width="88" height="68" fill="none" stroke="'+ink+'" stroke-width="1.2"'+op(.35)+'/>';
      break;
    case 'animes': // radiating speed lines
      for(i=0;i<16;i++){
        var a=(i/16)*Math.PI*2 + rnd()*.16;
        var r0=13+rnd()*5, r1=40+rnd()*16;
        o+='<line x1="'+(60+Math.cos(a)*r0).toFixed(1)+'" y1="'+(46+Math.sin(a)*r0).toFixed(1)+'" x2="'+
              (60+Math.cos(a)*r1).toFixed(1)+'" y2="'+(46+Math.sin(a)*r1).toFixed(1)+
              '" stroke="'+ink+'" stroke-width="1.5"'+op(.22+rnd()*.3)+'/>';
      }
      o+='<circle cx="60" cy="46" r="10" fill="none" stroke="'+ink+'" stroke-width="1.8"'+op(.55)+'/>';
      break;
    case 'ciborgues': // circuit traces
      for(i=0;i<6;i++){
        y=16+i*11;
        var mid=30+rnd()*54;
        o+='<path d="M14 '+y+' H'+mid.toFixed(0)+' V'+(y+9)+' H106" fill="none" stroke="'+ink+'" stroke-width="1.3"'+op(.30)+'/>';
        o+='<circle cx="'+mid.toFixed(0)+'" cy="'+y+'" r="2.2" fill="'+ink+'"'+op(.55)+'/>';
      }
      break;
    case 'transumanismo': // orbits
      for(i=0;i<4;i++){
        o+='<ellipse cx="60" cy="46" rx="'+(16+i*11)+'" ry="'+(9+i*6.5)+'" fill="none" stroke="'+ink+
           '" stroke-width="1.3" transform="rotate('+(rnd()*70-35).toFixed(0)+' 60 46)"'+op(.36-i*.05)+'/>';
      }
      o+='<circle cx="60" cy="46" r="5.5" fill="'+ink+'"'+op(.75)+'/>';
      break;
    default: // mitos — greek meander
      for(i=0;i<5;i++){
        x=12+i*20;
        o+='<path d="M'+x+' 30 h14 v14 h-9 v-8 h4" fill="none" stroke="'+ink+'" stroke-width="1.8"'+op(.4)+'/>';
        o+='<path d="M'+x+' 62 h14 v14 h-9 v-8 h4" fill="none" stroke="'+ink+'" stroke-width="1.8"'+op(.28)+'/>';
      }
      o+='<line x1="10" y1="22" x2="110" y2="22" stroke="'+ink+'" stroke-width="1.4"'+op(.45)+'/>';
      o+='<line x1="10" y1="86" x2="110" y2="86" stroke="'+ink+'" stroke-width="1.4"'+op(.45)+'/>';
  }
  return o;
}

/* --- the cover itself --- */
function coverSVG(e, opts){
  opts = opts || {};
  var W=120, H=180;
  var media = e.media || 'literatura';
  var pal = COVER_BASE[media] || COVER_BASE.literatura;
  var title = (e.kind==='quick' ? (e.name||e.title) : e.title) || '';
  var clean = title.replace(/\s*\((?:[^()]|\([^()]*\))*\)\s*$/,'').replace(/\s*—\s*.*$/,'').trim() || title;
  var rnd = seeded(hashStr(e.id+'|'+title));
  var big = !!opts.big;

  // the card thumbnail is drawn at ~55% scale, so it needs proportionally larger
  // type to stay legible; the modal cover can afford finer typography
  var fs      = big ? 12.5 : 17;
  var maxCh   = big ? 15 : 11;
  var maxLn   = big ? 4 : 2;
  var yearFs  = big ? 8 : 11;
  var kickFs  = big ? 6.4 : 8.6;
  var lines = wrapTitle(clean, maxCh, maxLn);
  var startY = H - (big?26:30) - (lines.length-1)*(fs+2.2);

  var s = '<svg viewBox="0 0 '+W+' '+H+'" class="cv" preserveAspectRatio="xMidYMid slice" aria-hidden="true">';
  s += '<rect width="'+W+'" height="'+H+'" fill="'+pal.bg+'"/>';
  s += '<rect width="'+W+'" height="'+H+'" fill="#0A1F33" opacity="0.34"/>';
  s += motif(media, rnd, pal.ink);
  // scrim so the type always reads
  var scrimTop = big ? 72 : 84, scrimSolid = big ? 52 : 66, rule = big ? 60 : 72;
  s += '<rect x="0" y="'+(H-scrimTop)+'" width="'+W+'" height="'+scrimTop+'" fill="#0A1F33" opacity="0.55"/>';
  s += '<rect x="0" y="'+(H-scrimSolid)+'" width="'+W+'" height="'+scrimSolid+'" fill="#0A1F33" opacity="0.82"/>';
  s += '<line x1="12" y1="'+(H-rule)+'" x2="'+(W-12)+'" y2="'+(H-rule)+'" stroke="#C9A227" stroke-width="1.4" opacity="0.85"/>';
  var kicker = (e.mediaLabel||'').toUpperCase();
  if(!big && kicker.length>12) kicker = kicker.split(' ')[0];
  s += '<text x="12" y="'+(big?16:19)+'" font-family="JetBrains Mono, monospace" font-size="'+kickFs+
       '" letter-spacing="1.1" fill="#C9A227" opacity="0.9">'+esc(kicker)+'</text>';
  lines.forEach(function(ln,i){
    s += '<text x="12" y="'+(startY+i*(fs+2.2))+'" font-family="Fraunces, Georgia, serif" font-weight="600" font-size="'+fs+
         '" fill="#F7F3EB">'+esc(ln)+'</text>';
  });
  if(e.year) s += '<text x="12" y="'+(H-(big?8:9))+'" font-family="JetBrains Mono, monospace" font-size="'+yearFs+
                  '" letter-spacing="0.8" fill="#C9A227">'+e.year+'</text>';
  s += '<rect x="2.5" y="2.5" width="'+(W-5)+'" height="'+(H-5)+'" fill="none" stroke="#C9A227" stroke-width="1.2" opacity="0.42"/>';
  s += '</svg>';
  return s;
}

/* =========================================================
   4. CATALOG (filters + grid + modal)
   ========================================================= */
var state = { query:'', cat:'all', includeQuick:true, forcedTitles:null };

function allEntries(){
  var full = DATA.works.map(function(w){ return Object.assign({},w,{kind:'full'}); });
  var qk = DATA.quick.map(function(q){ return Object.assign({},q,{kind:'quick'}); });
  return full.concat(qk);
}
var ENTRIES = allEntries();

function matchesQuery(e, q){
  if(!q) return true;
  q = q.toLowerCase();
  var hay = [e.title, e.name, e.creator, e.desc, e.synopsis, e.concepts, e.legacy, e.mediaLabel].filter(Boolean).join(' ').toLowerCase();
  return hay.indexOf(q) !== -1;
}

function renderChips(){
  var counts = {};
  ENTRIES.forEach(function(e){ counts[e.media] = (counts[e.media]||0)+1; });
  var chips = ['<button class="chip active" data-cat="all">Todas ('+ENTRIES.length+')</button>'];
  CAT_ORDER.forEach(function(c){
    if(!counts[c]) return;
    chips.push('<button class="chip" data-cat="'+c+'"><span class="chip-dot" style="background:'+CAT_COLOR[c]+'"></span>'+CAT_LABEL[c]+' ('+counts[c]+')</button>');
  });
  var row = document.getElementById('chip-row');
  row.innerHTML = chips.join('');
  row.addEventListener('click', function(ev){
    var btn = ev.target.closest('.chip');
    if(!btn) return;
    state.cat = btn.getAttribute('data-cat');
    state.forcedTitles = null;
    row.querySelectorAll('.chip').forEach(function(c){c.classList.remove('active');});
    btn.classList.add('active');
    renderCatalog();
  });
}

function yearKey(e){
  var y = e.year;
  if(y===undefined || y===null || y==='') return -1e9;
  var n = Number(y);
  return isNaN(n) ? -1e9 : n;
}

function periodOf(e){
  var y = yearKey(e);
  for(var i=0;i<PERIODS.length;i++){
    var p = PERIODS[i];
    var min = (p.min===null || p.min===undefined) ? -Infinity : p.min;
    var max = (p.max===null || p.max===undefined) ? Infinity : p.max;
    if(y>=min && y<=max) return p;
  }
  return PERIODS[0];
}

function sortByDate(a,b){
  var ya = yearKey(a), yb = yearKey(b);
  if(ya!==yb) return ya-yb;
  return (a.title||a.name||'').localeCompare(b.title||b.name||'', 'pt-BR');
}

function cardHTML(e){
  var color = CAT_COLOR[e.media] || 'var(--cat-mitos)';
  var title = e.kind==='quick' ? e.name : e.title.replace(/\s*\(\d{4}[^)]*\)\s*$/,'').replace(/\s*\([^)]*\d{4}[^)]*\)\s*$/,'');
  if(!title) title = e.title;
  var quickMeta = (e.meta && /^\d{4}$/.test(e.meta.trim())) ? '' : e.meta;
  var metaLine = e.kind==='quick' ? esc(quickMeta) : [e.creator, e.origin].filter(Boolean).join(' · ');
  var desc = e.kind==='quick' ? e.desc : (e.synopsis || e.legacy || '');
  return '<div class="work-card'+(e.kind==='quick'?' quick':'')+'" data-id="'+e.id+'" data-kind="'+e.kind+'" style="border-left-color:'+color+'">' +
    '<div class="wc-cover">'+coverSVG(e)+'</div>' +
    '<div class="wc-body">' +
      '<div class="work-tag-row">' +
        '<span class="work-tag">'+esc(e.mediaLabel)+'</span>' +
        (e.year ? '<span class="work-year">'+e.year+'</span>' : '<span class="work-year">&nbsp;</span>') +
      '</div>' +
      '<div class="work-title">'+esc(title)+'</div>' +
      (metaLine ? '<div class="work-meta">'+esc(metaLine)+'</div>' : '') +
      '<div class="work-desc">'+esc(desc)+'</div>' +
      (e.kind==='quick' ? '<div class="work-quick-badge">◆ menção rápida</div>' : '') +
    '</div>' +
  '</div>';
}

function renderCatalog(){
  var list = ENTRIES.filter(function(e){
    if(!state.includeQuick && e.kind==='quick') return false;
    if(state.cat!=='all' && e.media!==state.cat) return false;
    if(state.forcedTitles){
      var t = (e.title||'').toLowerCase();
      var ok = state.forcedTitles.some(function(ft){ return t.indexOf(ft.toLowerCase())!==-1 || ft.toLowerCase().indexOf(t)!==-1; });
      if(!ok) return false;
      return true;
    }
    if(!matchesQuery(e, state.query)) return false;
    return true;
  });

  list.sort(sortByDate);

  var grid = document.getElementById('catalog-grid');
  document.getElementById('result-count').textContent = list.length + ' obra' + (list.length===1?'':'s');

  if(list.length===0){
    grid.className = 'catalog-matrix-scroll';
    grid.innerHTML = '<div class="empty-state">Nenhuma obra encontrada. Tente outro termo ou limpe os filtros.</div>';
    return;
  }

  var catCounts = {};
  var byPeriodCat = {};
  list.forEach(function(e){
    var c = e.media || 'literatura';
    catCounts[c] = (catCounts[c]||0)+1;
    var pid = periodOf(e).id;
    if(!byPeriodCat[pid]) byPeriodCat[pid] = {};
    (byPeriodCat[pid][c] = byPeriodCat[pid][c] || []).push(e);
  });
  var cats = CAT_ORDER.filter(function(c){ return catCounts[c]; });
  Object.keys(catCounts).forEach(function(c){
    if(cats.indexOf(c)===-1) cats.push(c);
  });
  var periods = PERIODS.filter(function(p){ return !!byPeriodCat[p.id]; });

  var thead = '<thead><tr><th>Período</th>' + cats.map(function(c){
    return '<th><span class="chip-dot" style="background:'+CAT_COLOR[c]+'"></span>'+esc(CAT_LABEL[c]||c)+' <b>'+catCounts[c]+'</b></th>';
  }).join('') + '</tr></thead>';

  var rows = periods.map(function(p){
    var cells = cats.map(function(c){
      var items = (byPeriodCat[p.id] && byPeriodCat[p.id][c]) || [];
      if(!items.length) return '<td class="empty-cell"></td>';
      return '<td><div class="cm-stack">'+items.map(cardHTML).join('')+'</div></td>';
    }).join('');
    return '<tr><th class="cm-period">'+esc(p.label)+'</th>'+cells+'</tr>';
  }).join('');

  grid.className = 'catalog-matrix-scroll';
  grid.innerHTML = '<table class="catalog-matrix">'+thead+'<tbody>'+rows+'</tbody></table>';
}

function openModal(id, kind){
  var e = ENTRIES.find(function(x){ return x.id===id && x.kind===kind; });
  if(!e) return;
  var body = document.getElementById('modal-body');
  var color = CAT_COLOR[e.media] || 'var(--cat-mitos)';

  if(e.kind==='quick'){
    var qMeta = (e.meta && /^\d{4}$/.test(e.meta.trim())) ? '' : e.meta;
    var metaLineModal = [qMeta, e.year].filter(Boolean).join(' · ');
    body.innerHTML =
      '<div class="modal-head">' +
        '<div class="modal-cover">'+coverSVG(e,{big:true})+'</div>' +
        '<div class="modal-head-txt">' +
          '<span class="modal-tag" style="background:'+color+'">'+esc(e.mediaLabel)+' · menção rápida</span>' +
          '<div class="modal-title">'+esc(e.name)+'</div>' +
          (metaLineModal ? '<div class="modal-meta">'+esc(metaLineModal)+'</div>' : '') +
        '</div>' +
      '</div>' +
      '<div class="modal-section"><div class="modal-text">'+esc(e.desc)+'</div></div>';
  } else {
    var metaParts = [];
    if(e.creator) metaParts.push('<span>Criador</span> '+esc(e.creator));
    if(e.mediaType) metaParts.push('<span>Mídia</span> '+esc(e.mediaType));
    if(e.origin) metaParts.push('<span>Origem</span> '+esc(e.origin));
    body.innerHTML =
      '<div class="modal-head">' +
        '<div class="modal-cover">'+coverSVG(e,{big:true})+'</div>' +
        '<div class="modal-head-txt">' +
          '<span class="modal-tag" style="background:'+color+'">'+esc(e.mediaLabel)+(e.year?' · '+e.year:'')+'</span>' +
          '<div class="modal-title">'+esc(e.title)+'</div>' +
          (metaParts.length ? '<div class="modal-meta">'+metaParts.join(' &nbsp;·&nbsp; ')+'</div>' : '') +
        '</div>' +
      '</div>' +
      (e.synopsis ? '<div class="modal-section"><div class="modal-label">Sinopse</div><div class="modal-text">'+esc(e.synopsis)+'</div></div>' : '') +
      (e.concepts ? '<div class="modal-section"><div class="modal-label">Conceitos de IA</div><div class="modal-text">'+esc(e.concepts)+'</div></div>' : '') +
      (e.legacy ? '<div class="modal-section"><div class="modal-label">Legado</div><div class="modal-text">'+esc(e.legacy)+'</div></div>' : '');
  }
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeModal(){
  document.getElementById('modal-overlay').classList.remove('open');
  var g = document.getElementById('graph-overlay');
  // if the graph is still open underneath, keep the page scroll locked
  document.body.style.overflow = (g && g.classList.contains('open')) ? 'hidden' : '';
}

function bindCatalogEvents(){
  document.getElementById('search-input').addEventListener('input', function(ev){
    state.query = ev.target.value;
    state.forcedTitles = null;
    renderCatalog();
  });
  document.getElementById('toggle-quick').addEventListener('change', function(ev){
    state.includeQuick = ev.target.checked;
    renderCatalog();
  });
  document.getElementById('catalog-grid').addEventListener('click', function(ev){
    var card = ev.target.closest('.work-card');
    if(!card) return;
    openModal(card.getAttribute('data-id'), card.getAttribute('data-kind'));
  });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', function(ev){
    if(ev.target.id==='modal-overlay') closeModal();
  });
  // one Escape handler for every layer: closes the topmost open one only,
  // so dismissing a ficha opened from the graph does not also close the graph
  document.addEventListener('keydown', function(ev){
    if(ev.key!=='Escape') return;
    if(document.getElementById('modal-overlay').classList.contains('open')){ closeModal(); return; }
    var g = document.getElementById('graph-overlay');
    if(g && g.classList.contains('open')) GRAPH.close();
  });
}

/* =========================================================
   5. THEMATIC INDEX
   ========================================================= */
function renderThematic(){
  var grid = document.getElementById('thematic-grid');
  grid.innerHTML = DATA.thematic.map(function(t,i){
    return '<button class="thematic-pill" data-idx="'+i+'">' +
      '<div class="thematic-concept">'+esc(t.concept)+'</div>' +
      '<div class="thematic-works">'+esc(t.works)+'</div>' +
    '</button>';
  }).join('');
  grid.addEventListener('click', function(ev){
    var btn = ev.target.closest('.thematic-pill');
    if(!btn) return;
    var t = DATA.thematic[parseInt(btn.getAttribute('data-idx'),10)];
    var titles = t.works.split('·').map(function(s){
      return s.replace(/\(.*?\)/g,'').trim();
    }).filter(Boolean);
    state.forcedTitles = titles;
    state.cat = 'all';
    state.query = '';
    document.getElementById('search-input').value = '';
    document.querySelectorAll('#chip-row .chip').forEach(function(c){c.classList.remove('active');});
    document.querySelector('#chip-row .chip[data-cat="all"]').classList.add('active');
    renderCatalog();
    document.getElementById('catalogo').scrollIntoView({behavior:'smooth', block:'start'});
  });
}

/* =========================================================
   6. COMPUTING SECTION
   ========================================================= */
function renderComputing(){
  var el = document.getElementById('computing-content');
  var html = '<p class="section-desc" style="max-width:none;text-align:left;margin-bottom:36px;">'+esc(DATA.computing.intro)+'</p>';

  DATA.computing.sections.forEach(function(s){
    html += '<div class="comp-block"><h4>'+esc(s.title)+'</h4>';
    if(s.table && s.table.length){
      var keys = Object.keys(s.table[0]);
      html += '<div class="comp-table-scroll"><table class="comp-table"><thead><tr>' + keys.map(function(k){return '<th>'+esc(k)+'</th>';}).join('') + '</tr></thead><tbody>';
      s.table.forEach(function(row){
        html += '<tr>' + keys.map(function(k){return '<td>'+esc(row[k])+'</td>';}).join('') + '</tr>';
      });
      html += '</tbody></table></div>';
    } else if(s.parsedMilestones){
      html += '<div class="milestone-chips">' + s.parsedMilestones.map(function(m){
        return '<div class="milestone-chip">'+esc(m)+'</div>';
      }).join('') + '</div>';
    }
    html += '</div>';
  });
  el.innerHTML = html;
}

/* =========================================================
   7. ART SECTION
   ========================================================= */
function renderArt(){
  var grid = document.getElementById('art-grid');
  grid.innerHTML = DATA.art.sections.map(function(s){
    return '<div class="art-card">' +
      '<h4>'+esc(s.title)+'</h4>' +
      (s.subtitle ? '<div class="art-q">'+esc(s.subtitle)+'</div>' : '') +
      s.items.map(function(it){
        return '<div class="art-item"><b>'+esc(it.name)+'</b>' + (it.meta ? ' <span class="meta">('+esc(it.meta)+')</span>' : '') + ' — '+esc(it.desc)+'</div>';
      }).join('') +
    '</div>';
  }).join('');
}

/* =========================================================
   8. REALITY GRID
   ========================================================= */
function renderReality(){
  var grid = document.getElementById('reality-grid');
  grid.innerHTML = DATA.reality.map(function(r){
    return '<div class="reality-card"><b>'+esc(r.lead)+'</b><span>'+esc(r.text)+'</span></div>';
  }).join('');
}

/* =========================================================
   9. USAGE BOX
   ========================================================= */
function renderUsage(){
  var box = document.getElementById('usage-box');
  var items = DATA.usage.map(function(u,i){
    return '<div class="usage-item"><span class="usage-num">0'+(i+1)+'</span><div><b>'+esc(u.title)+'</b><span>'+esc(u.text)+'</span></div></div>';
  }).join('');
  box.innerHTML = '<h3>Como explorar este catálogo</h3>' + items;
}

/* =========================================================
   10. NAV ACTIVE STATE + STAT COUNTER
   ========================================================= */
function bindNav(){
  var links = document.querySelectorAll('.sitenav-links a');
  var sections = Array.prototype.slice.call(links).map(function(a){
    return document.querySelector(a.getAttribute('href'));
  }).filter(Boolean);
  function onScroll(){
    var y = window.scrollY + 120;
    var current = null;
    sections.forEach(function(sec){
      if(sec.offsetTop <= y) current = sec;
    });
    links.forEach(function(a){ a.classList.remove('active'); });
    if(current){
      var link = document.querySelector('.sitenav-links a[href="#'+current.id+'"]');
      if(link) link.classList.add('active');
    }
  }
  window.addEventListener('scroll', onScroll, {passive:true});
  onScroll();
}

function animateStat(){
  var target = DATA.works.length + DATA.quick.length;
  var el = document.getElementById('stat-works');
  var start = 0, dur = 1100, t0 = null;
  function step(ts){
    if(!t0) t0 = ts;
    var p = Math.min(1, (ts - t0) / dur);
    var val = Math.round(start + (target-start) * (1 - Math.pow(1-p, 3)));
    el.textContent = val;
    if(p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}


/* =========================================================
   GRAPH EXPLORER — one full network, camera focus per lineage
   ========================================================= */
var GRAPH = (function(){
  var MEDIA_COLOR = {
    mitos:'#7A5AA3', literatura:'#33506B', cinema:'#A3453F', series:'#3D6FA8',
    animes:'#B9822F', games:'#3F8563', ciborgues:'#4A4F55', transumanismo:'#B08A1A'
  };
  var HUB_COLOR = '#C9A227';

  var model=null, sim=null, raf=null;
  var svgEl, gLinks, gNodes, gLabels, viewBox;
  var focusId=null, hoverId=null;
  var dragNode=null, dragging=false, panning=false, panStart=null, vbStart=null;
  var tween=null;
  var mini={svg:null, dots:[], rect:null, box:null, frame:0};
  var adj={};           // lineage adjacency
  var built=false;

  /* ---------- model: the entire network, built once ---------- */
  function buildModel(){
    var nodes=[], links=[], index={};

    (DATA.graph.nodes||[]).forEach(function(n){
      var nd = {
        id:n.id, label:n.label, full:n.full, year:n.year, media:n.media,
        mediaLabel:n.mediaLabel, kind:'work', lin:n.lin||[], prim:n.prim,
        color: MEDIA_COLOR[n.media] || '#33506B', r:6, x:0, y:0, vx:0, vy:0, deg:0
      };
      nodes.push(nd); index[n.id]=nd;
    });

    var hubs = (DATA.graph.lineages||[]).filter(function(L){ return !L.all; });
    hubs.forEach(function(L){
      var nd = {
        id:'hub:'+L.id, linId:L.id, label:L.label, desc:L.desc, kind:'hub',
        color:HUB_COLOR, r:14, x:0, y:0, vx:0, vy:0, deg:0,
        memberCount:L.members.length
      };
      nodes.push(nd); index['hub:'+L.id]=nd;
    });

    // backbone: each work hangs from its primary lineage
    hubs.forEach(function(L){
      L.members.forEach(function(mid){
        var m = index[mid];
        if(m && m.prim===L.id) links.push({s:index['hub:'+L.id], t:m, k:'lin'});
      });
    });
    // genealogy edges between lineages
    (DATA.graph.treeEdges||[]).forEach(function(pair){
      var a=index['hub:'+pair[0]], b=index['hub:'+pair[1]];
      if(a&&b) links.push({s:a,t:b,k:'tree'});
      adj[pair[0]] = adj[pair[0]]||{}; adj[pair[1]] = adj[pair[1]]||{};
      adj[pair[0]][pair[1]]=true; adj[pair[1]][pair[0]]=true;
    });
    // influence + thematic edges between works
    (DATA.graph.links||[]).forEach(function(l){
      var a=index[l.s], b=index[l.t];
      if(a&&b) links.push({s:a,t:b,k:l.k});
    });

    links.forEach(function(l){ l.s.deg++; l.t.deg++; });
    // work-to-work degree drives size, so the canonical works read as bigger
    nodes.forEach(function(n){
      if(n.kind!=='work') return;
      n.wdeg = 0;
    });
    links.forEach(function(l){
      if(l.k==='influence'||l.k==='tema'){ l.s.wdeg=(l.s.wdeg||0)+1; l.t.wdeg=(l.t.wdeg||0)+1; }
    });
    nodes.forEach(function(n){
      if(n.kind==='work') n.r = 6 + Math.min(15, Math.sqrt(n.wdeg||0)*4.4);
      else n.r = 22 + Math.min(16, Math.sqrt(n.memberCount)*2.4);
    });

    // seed: hubs on a ring, works around their primary hub
    var HN=hubs.length;
    hubs.forEach(function(L,i){
      var nd=index['hub:'+L.id], a=(i/HN)*Math.PI*2;
      nd.x=Math.cos(a)*430; nd.y=Math.sin(a)*430;
    });
    nodes.forEach(function(n,i){
      if(n.kind==='hub') return;
      var host = index['hub:'+n.prim] || null;
      var a=i*2.399963, rad=70+(i%9)*17;
      n.x=(host?host.x:0)+Math.cos(a)*rad;
      n.y=(host?host.y:0)+Math.sin(a)*rad;
    });

    return {nodes:nodes, links:links, index:index, hubs:hubs};
  }

  /* ---------- force simulation ---------- */
  function makeSim(m){
    var nodes=m.nodes, links=m.links;
    var alpha=1, alphaDecay=0.014, alphaMin=0.03;
    var REP=8200, CENTER=0.0020, CUT2=1200*1200, HUBREP=10;

    function tick(){
      var i,j,n,mm,dx,dy,d2,d,f;
      for(i=0;i<nodes.length;i++){
        n=nodes[i];
        for(j=i+1;j<nodes.length;j++){
          mm=nodes[j];
          dx=mm.x-n.x; dy=mm.y-n.y; d2=dx*dx+dy*dy;
          if(d2<0.01){ dx=(Math.random()-0.5)*0.6; dy=(Math.random()-0.5)*0.6; d2=dx*dx+dy*dy; }
          var bothHub=(n.kind==='hub'&&mm.kind==='hub');
          if(d2>CUT2 && !bothHub) continue;
          d=Math.sqrt(d2);
          var mult = bothHub ? HUBREP : ((n.kind==='hub'||mm.kind==='hub')?1.8:1);
          f=(REP*mult)/d2;
          var ux=dx/d, uy=dy/d;
          n.vx-=ux*f; n.vy-=uy*f; mm.vx+=ux*f; mm.vy+=uy*f;
        }
      }
      for(i=0;i<links.length;i++){
        var l=links[i]; n=l.s; mm=l.t;
        dx=mm.x-n.x; dy=mm.y-n.y;
        d=Math.sqrt(dx*dx+dy*dy)||0.01;
        var target = l.k==='tree' ? 340 : (l.k==='lin' ? 130 : 105);
        var strength = l.k==='tree' ? 0.05 : (l.k==='lin' ? 0.06 : 0.075);
        f=(d-target)*strength;
        var vx2=(dx/d)*f, vy2=(dy/d)*f;
        n.vx+=vx2; n.vy+=vy2; mm.vx-=vx2; mm.vy-=vy2;
      }
      for(i=0;i<nodes.length;i++){
        n=nodes[i];
        n.vx-=n.x*CENTER; n.vy-=n.y*CENTER;
        if(n.fixed){ n.vx=0; n.vy=0; continue; }
        n.vx*=0.82; n.vy*=0.82;
        var sp=Math.sqrt(n.vx*n.vx+n.vy*n.vy);
        if(sp>22){ n.vx=n.vx/sp*22; n.vy=n.vy/sp*22; }
        n.x+=n.vx*alpha; n.y+=n.vy*alpha;
      }
      for(i=0;i<nodes.length;i++){
        n=nodes[i];
        for(j=i+1;j<nodes.length;j++){
          mm=nodes[j];
          dx=mm.x-n.x; dy=mm.y-n.y;
          var min=n.r+mm.r+16; d2=dx*dx+dy*dy;
          if(d2>=min*min||d2===0) continue;
          d=Math.sqrt(d2)||0.01;
          var push=(min-d)/d*0.5, px=dx*push, py=dy*push;
          if(!n.fixed){ n.x-=px; n.y-=py; }
          if(!mm.fixed){ mm.x+=px; mm.y+=py; }
        }
      }
      alpha=Math.max(alphaMin, alpha-alphaDecay*alpha);
    }
    return {tick:tick, reheat:function(){alpha=0.7;}};
  }

  /* ---------- focus sets ---------- */
  function inFocus(n){
    if(!focusId) return true;
    if(n.kind==='hub') return n.linId===focusId || (adj[focusId]&&adj[focusId][n.linId]);
    return (n.lin||[]).indexOf(focusId) !== -1;
  }
  function isCore(n){
    if(!focusId) return false;
    return n.kind==='hub' ? n.linId===focusId : (n.lin||[]).indexOf(focusId)!==-1;
  }
  function neighborsOf(id){
    var set={}; set[id]=true;
    model.links.forEach(function(l){
      if(l.s.id===id) set[l.t.id]=true;
      if(l.t.id===id) set[l.s.id]=true;
    });
    return set;
  }

  /* ---------- draw ---------- */
  function draw(){
    var hl = hoverId ? neighborsOf(hoverId) : null;
    var i,l,n;

    for(i=0;i<model.links.length;i++){
      l=model.links[i];
      if(!l._el) continue;
      l._el.setAttribute('x1',l.s.x); l._el.setAttribute('y1',l.s.y);
      l._el.setAttribute('x2',l.t.x); l._el.setAttribute('y2',l.t.y);
      var base;
      if(l.k==='tree') base=0.75;
      else if(l.k==='lin') base=0.20;
      else base=0.55;
      var op=base;
      if(focusId){
        var bothCore = isCore(l.s)&&isCore(l.t);
        var touchesFocusHub = (l.s.kind==='hub'&&l.s.linId===focusId)||(l.t.kind==='hub'&&l.t.linId===focusId);
        if(l.k==='tree') op = (touchesFocusHub||(inFocus(l.s)&&inFocus(l.t))) ? 0.9 : 0.18;
        else if(bothCore||touchesFocusHub) op = Math.max(base,0.7);
        else op = 0.05;
      }
      if(hl){
        op = (hl[l.s.id]&&hl[l.t.id]) ? 0.9 : 0.04;
      }
      l._el.setAttribute('opacity',op);
      if(l._glow){
        l._glow.setAttribute('x1',l.s.x); l._glow.setAttribute('y1',l.s.y);
        l._glow.setAttribute('x2',l.t.x); l._glow.setAttribute('y2',l.t.y);
        l._glow.setAttribute('opacity', op*0.22);
      }
    }

    for(i=0;i<model.nodes.length;i++){
      n=model.nodes[i];
      if(n._halo){
        n._halo.setAttribute('cx',n.x); n._halo.setAttribute('cy',n.y);
        var hop = focusId ? (n.linId===focusId ? 0.30 : (adj[focusId]&&adj[focusId][n.linId] ? 0.16 : 0.05)) : 0.14;
        if(hoverId) hop = (hoverId===n.id) ? 0.34 : hop*0.35;
        n._halo.setAttribute('opacity', hop);
        n._halo.setAttribute('r', (n.linId===focusId ? n.r*2.25 : n.r*1.9));
      }
      if(n._el){
        n._el.setAttribute('cx',n.x); n._el.setAttribute('cy',n.y);
        var nop = 1;
        if(focusId) nop = isCore(n) ? 1 : (inFocus(n) ? 0.72 : 0.13);
        if(hl) nop = hl[n.id] ? 1 : 0.12;
        n._el.setAttribute('opacity',nop);
        var isFocusHub = (n.kind==='hub'&&n.linId===focusId);
        var isNeighbourHub = (n.kind==='hub'&&focusId&&adj[focusId]&&adj[focusId][n.linId]);
        n._el.setAttribute('stroke', isFocusHub ? '#FFFFFF' : (isNeighbourHub ? '#F1E8D0' : (n.kind==='hub'?'#F7F3EB':'rgba(247,243,235,.55)')));
        n._el.setAttribute('stroke-width', isFocusHub ? 6 : (n.kind==='hub'?3:1.2));
      }
      if(n._lbl){
        n._lbl.setAttribute('x',n.x); n._lbl.setAttribute('y',n.y-n.r-(n.kind==='hub'?11:6));
        var show;
        if(hl) show = !!hl[n.id];
        else if(focusId) show = (n.kind==='hub') || isCore(n);
        else show = (n.kind==='hub') || (n.wdeg||0)>=4;   // overview: lineages + the canonical works only
        var lop = show ? 1 : 0;
        if(show && focusId && !isCore(n) && n.kind!=='hub') lop=0.35;
        if(show && focusId && n.kind==='hub' && n.linId!==focusId && !(adj[focusId]&&adj[focusId][n.linId])) lop=0.32;
        n._lbl.setAttribute('opacity',lop);
        n._lbl.setAttribute('font-size', (n.kind==='hub') ? (n.linId===focusId?24:19) : (n.wdeg>=3?13.5:12));
      }
    }
  }

  function loop(){
    if(!sim) return;
    if(tween) stepTween();
    for(var k=0;k<2;k++) sim.tick();
    draw();
    updateMini();
    raf=requestAnimationFrame(loop);
  }

  /* ---------- camera ---------- */
  function applyVB(){ svgEl.setAttribute('viewBox', viewBox.x+' '+viewBox.y+' '+viewBox.w+' '+viewBox.h); }
  function boxOf(nodes, pad){
    var minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
    nodes.forEach(function(n){
      if(n.x-n.r<minX)minX=n.x-n.r; if(n.x+n.r>maxX)maxX=n.x+n.r;
      if(n.y-n.r<minY)minY=n.y-n.r; if(n.y+n.r>maxY)maxY=n.y+n.r;
    });
    if(minX>maxX) return null;
    var w=(maxX-minX)+pad*2, h=(maxY-minY)+pad*2;
    var host=document.getElementById('graph-canvas').getBoundingClientRect();
    var ar=host.width/Math.max(1,host.height);
    if(w/h<ar) w=h*ar; else h=w/ar;
    return {x:(minX+maxX)/2-w/2, y:(minY+maxY)/2-h/2, w:w, h:h};
  }
  function tweenTo(target, ms){
    if(!target) return;
    tween={from:{x:viewBox.x,y:viewBox.y,w:viewBox.w,h:viewBox.h}, to:target, t0:performance.now(), ms:ms||620};
  }
  function stepTween(){
    var p=(performance.now()-tween.t0)/tween.ms;
    if(p>=1){ viewBox={x:tween.to.x,y:tween.to.y,w:tween.to.w,h:tween.to.h}; tween=null; applyVB(); return; }
    var e=1-Math.pow(1-p,3);
    viewBox.x=tween.from.x+(tween.to.x-tween.from.x)*e;
    viewBox.y=tween.from.y+(tween.to.y-tween.from.y)*e;
    viewBox.w=tween.from.w+(tween.to.w-tween.from.w)*e;
    viewBox.h=tween.from.h+(tween.to.h-tween.from.h)*e;
    applyVB();
  }
  function cameraForFocus(animate){
    var subset;
    if(focusId){
      subset = model.nodes.filter(function(n){
        return isCore(n) || (n.kind==='hub' && adj[focusId] && adj[focusId][n.linId]);
      });
    } else {
      subset = model.nodes;
    }
    var box = boxOf(subset.length?subset:model.nodes, focusId?110:60);
    if(!box) return;
    if(animate) tweenTo(box); else { viewBox=box; applyVB(); }
  }

  /* ---------- focus ---------- */
  function setFocus(linId, animate){
    focusId = (linId && linId!=='raiz') ? linId : null;
    var L = focusId ? LIN_BY_ID[focusId] : null;

    document.getElementById('graph-title').textContent = L ? L.label : 'A rede completa';
    document.getElementById('graph-desc').textContent = L ? L.desc :
      'Todas as obras do catálogo e as conexões entre elas. Clique em uma linhagem (círculo dourado) para aproximar.';

    var total = model.nodes.filter(function(n){return n.kind==='work';}).length;
    var inSet = focusId ? model.nodes.filter(function(n){return n.kind==='work'&&isCore(n);}).length : total;
    var ww = model.links.filter(function(l){return l.k==='influence'||l.k==='tema';}).length;
    document.getElementById('graph-count').innerHTML = focusId
      ? '<b>'+inSet+'</b> obras nesta linhagem &nbsp;·&nbsp; de <b>'+total+'</b> no total'
      : '<b>'+total+'</b> obras &nbsp;·&nbsp; <b>'+ww+'</b> conexões diretas';

    // neighbouring lineages as quick jumps
    var nav = document.getElementById('graph-nav');
    if(focusId && adj[focusId]){
      var ids = Object.keys(adj[focusId]);
      nav.innerHTML = '<span class="gnav-label">Conecta com</span>' + ids.map(function(id){
        var LL=LIN_BY_ID[id];
        return '<button class="gnav-chip" data-lin="'+id+'">'+esc(LL?LL.label:id)+'</button>';
      }).join('');
      nav.style.display='flex';
    } else {
      nav.innerHTML=''; nav.style.display='none';
    }
    document.getElementById('graph-overview').style.display = focusId ? 'inline-flex' : 'none';
    // the thumbnail keeps the whole network in sight while the camera is zoomed in
    document.getElementById('graph-mini').classList.toggle('on', !!focusId);
    if(focusId && mini.svg){ mini.frame=0; updateMini(); }

    cameraForFocus(animate);
    draw();
  }

  /* ---------- minimap: the whole network, always in view ---------- */
  function worldBox(pad){
    var minX=1e9,minY=1e9,maxX=-1e9,maxY=-1e9;
    model.nodes.forEach(function(n){
      if(n.x<minX)minX=n.x; if(n.x>maxX)maxX=n.x;
      if(n.y<minY)minY=n.y; if(n.y>maxY)maxY=n.y;
    });
    pad = pad||40;
    return {x:minX-pad, y:minY-pad, w:(maxX-minX)+pad*2, h:(maxY-minY)+pad*2};
  }
  function buildMini(){
    var host=document.querySelector('#graph-mini .mini-body');
    if(!host) return;
    host.innerHTML='';
    var NS='http://www.w3.org/2000/svg';
    var svg=document.createElementNS(NS,'svg');
    svg.setAttribute('preserveAspectRatio','xMidYMid meet');
    var gl=document.createElementNS(NS,'g'), gn=document.createElementNS(NS,'g');
    svg.appendChild(gl); svg.appendChild(gn);

    // only the genealogy skeleton, so the thumbnail stays readable
    mini.treeLinks=[];
    model.links.forEach(function(l){
      if(l.k!=='tree') return;
      var ln=document.createElementNS(NS,'line');
      ln.setAttribute('stroke','#C9A227'); ln.setAttribute('stroke-width',2.5);
      ln.setAttribute('opacity',.55);
      gl.appendChild(ln); mini.treeLinks.push({l:l, el:ln});
    });

    mini.dots=[];
    model.nodes.forEach(function(n){
      var c=document.createElementNS(NS,'circle');
      c.setAttribute('r', n.kind==='hub'?16:5);
      c.setAttribute('fill', n.color);
      c.setAttribute('pointer-events','none');
      gn.appendChild(c); mini.dots.push({n:n, el:c});
    });

    var rect=document.createElementNS(NS,'rect');
    rect.setAttribute('fill','rgba(247,243,235,.10)');
    rect.setAttribute('stroke','#F7F3EB');
    rect.setAttribute('stroke-width',6);
    rect.setAttribute('pointer-events','none');
    svg.appendChild(rect);
    mini.rect=rect; mini.svg=svg;
    host.appendChild(svg);

    mini.box=worldBox();
    svg.setAttribute('viewBox', mini.box.x+' '+mini.box.y+' '+mini.box.w+' '+mini.box.h);
    bindMini(host);
  }
  function updateMini(){
    if(!mini.svg || !document.getElementById('graph-mini').classList.contains('on')) return;

    // the layout drifts slowly: refresh the node bounds only now and then
    if((mini.frame++ % 30)===0 || !mini.wbox) mini.wbox = worldBox();

    // ...but always union with the live camera, so the viewport rect stays inside the thumbnail
    var w=mini.wbox, v=viewBox;
    var x0=Math.min(w.x, v.x), y0=Math.min(w.y, v.y);
    var x1=Math.max(w.x+w.w, v.x+v.w), y1=Math.max(w.y+w.h, v.y+v.h);
    var box={x:x0, y:y0, w:x1-x0, h:y1-y0};
    var changed = !mini.box || Math.abs(box.w-mini.box.w)/box.w > 0.02 ||
                  Math.abs(box.x-mini.box.x) > box.w*0.02 || Math.abs(box.y-mini.box.y) > box.h*0.02;
    if(changed){
      mini.box=box;
      mini.svg.setAttribute('viewBox', box.x+' '+box.y+' '+box.w+' '+box.h);
      var sw = box.w/216;                    // keep strokes ~constant on screen
      mini.rect.setAttribute('stroke-width', Math.max(2, sw*1.6));
      mini.treeLinks.forEach(function(t){ t.el.setAttribute('stroke-width', Math.max(1.5, sw*1.4)); });
      mini.dots.forEach(function(d){
        if(d.n.kind==='hub' && d.n.linId===focusId) return;   // focus ring sized below
        d.el.setAttribute('r', (d.n.kind==='hub'?14:4)*Math.max(1, sw*0.55));
      });
    }
    mini.treeLinks.forEach(function(t){
      t.el.setAttribute('x1',t.l.s.x); t.el.setAttribute('y1',t.l.s.y);
      t.el.setAttribute('x2',t.l.t.x); t.el.setAttribute('y2',t.l.t.y);
    });
    var sw2 = mini.box.w/216;
    void sw2;
    mini.dots.forEach(function(d){
      d.el.setAttribute('cx',d.n.x); d.el.setAttribute('cy',d.n.y);
      var op = focusId ? (isCore(d.n) ? 1 : 0.22) : 0.8;
      if(d.n.kind==='hub') op = focusId ? (d.n.linId===focusId ? 1 : 0.5) : 0.95;
      d.el.setAttribute('opacity', op);
      // ring the lineage you are standing in, so the thumbnail answers "where am I?"
      var isFocusHub = (d.n.kind==='hub' && d.n.linId===focusId);
      if(isFocusHub){
        d.el.setAttribute('r', 22*Math.max(1, sw2*0.55));
        d.el.setAttribute('stroke','#FFFFFF');
        d.el.setAttribute('stroke-width', Math.max(2, sw2*1.8));
      } else if(d.el.getAttribute('stroke')){
        d.el.setAttribute('stroke','none'); d.el.setAttribute('stroke-width',0);
      }
    });
    mini.rect.setAttribute('x',viewBox.x); mini.rect.setAttribute('y',viewBox.y);
    mini.rect.setAttribute('width',Math.max(1,viewBox.w)); mini.rect.setAttribute('height',Math.max(1,viewBox.h));
  }
  function miniToWorld(ev, host){
    var r=host.getBoundingClientRect();
    var b=mini.box;
    // svg uses meet: compute the letterboxed content area
    var sc=Math.min(r.width/b.w, r.height/b.h);
    var cw=b.w*sc, ch=b.h*sc;
    var ox=(r.width-cw)/2, oy=(r.height-ch)/2;
    var px=(ev.clientX!==undefined?ev.clientX:ev.touches[0].clientX)-r.left-ox;
    var py=(ev.clientY!==undefined?ev.clientY:ev.touches[0].clientY)-r.top-oy;
    return {x:b.x+px/sc, y:b.y+py/sc};
  }
  function miniJump(ev, host){
    var p=miniToWorld(ev, host);
    tween=null;
    viewBox.x=p.x-viewBox.w/2; viewBox.y=p.y-viewBox.h/2;
    applyVB();
  }
  function bindMini(host){
    var down=false;
    host.addEventListener('mousedown', function(ev){ down=true; miniJump(ev,host); ev.preventDefault(); });
    host.addEventListener('mousemove', function(ev){ if(down) miniJump(ev,host); });
    window.addEventListener('mouseup', function(){ down=false; });
    host.addEventListener('touchstart', function(ev){ miniJump(ev,host); }, {passive:true});
    host.addEventListener('touchmove', function(ev){ miniJump(ev,host); ev.preventDefault(); }, {passive:false});
  }

  /* ---------- svg ---------- */
  function buildSVG(){
    var host=document.getElementById('graph-canvas');
    host.innerHTML='';
    var NS='http://www.w3.org/2000/svg';
    svgEl=document.createElementNS(NS,'svg');
    svgEl.setAttribute('width','100%'); svgEl.setAttribute('height','100%');
    viewBox={x:-540,y:-360,w:1080,h:720}; applyVB();
    svgEl.style.display='block'; svgEl.style.cursor='grab';

    var gGlow=document.createElementNS(NS,'g');
    gLinks=document.createElementNS(NS,'g');
    var gHalo=document.createElementNS(NS,'g');
    gNodes=document.createElementNS(NS,'g');
    gLabels=document.createElementNS(NS,'g');
    svgEl.appendChild(gGlow); svgEl.appendChild(gLinks);
    svgEl.appendChild(gHalo); svgEl.appendChild(gNodes); svgEl.appendChild(gLabels);

    model.links.forEach(function(l){
      // the genealogy backbone gets a soft under-glow so it reads as the main structure
      if(l.k==='tree'){
        var gl=document.createElementNS(NS,'line');
        gl.setAttribute('stroke','#C9A227'); gl.setAttribute('stroke-width',16);
        gl.setAttribute('stroke-linecap','round'); gl.setAttribute('opacity',.14);
        l._glow=gl; gGlow.appendChild(gl);
      }
      var ln=document.createElementNS(NS,'line');
      if(l.k==='tree'){ ln.setAttribute('stroke','#E8C557'); ln.setAttribute('stroke-width',5.5); ln.setAttribute('stroke-linecap','round'); }
      else if(l.k==='lin'){ ln.setAttribute('stroke','#C9A227'); ln.setAttribute('stroke-width',0.8); }
      else if(l.k==='tema'){ ln.setAttribute('stroke','#8FA6BC'); ln.setAttribute('stroke-width',1.8); ln.setAttribute('stroke-dasharray','4,4'); }
      else { ln.setAttribute('stroke','#C2564F'); ln.setAttribute('stroke-width',2.2); }
      l._el=ln; gLinks.appendChild(ln);
    });
    model.nodes.forEach(function(n){
      if(n.kind==='hub'){
        var halo=document.createElementNS(NS,'circle');
        halo.setAttribute('r', n.r*1.9); halo.setAttribute('fill','#C9A227');
        halo.setAttribute('opacity',.13); halo.setAttribute('pointer-events','none');
        n._halo=halo; gHalo.appendChild(halo);
      }
      var c=document.createElementNS(NS,'circle');
      c.setAttribute('r',n.r); c.setAttribute('fill',n.color);
      c.setAttribute('stroke', n.kind==='hub'?'#F7F3EB':'rgba(247,243,235,.6)');
      c.setAttribute('stroke-width', n.kind==='hub'?3:1.2);
      c.setAttribute('data-id',n.id);
      c.style.cursor='pointer';
      n._el=c; gNodes.appendChild(c);

      var t=document.createElementNS(NS,'text');
      t.setAttribute('text-anchor','middle');
      t.setAttribute('font-family', n.kind==='hub'?'JetBrains Mono, monospace':'Inter, sans-serif');
      t.setAttribute('font-size', n.kind==='hub'?19:12);
      t.setAttribute('font-weight', n.kind==='hub'?700:600);
      t.setAttribute('fill', n.kind==='hub'?'#F0D375':'#EDF1F3');
      // dark halo around the glyphs keeps labels legible over links
      t.setAttribute('stroke','#0A1F33');
      t.setAttribute('stroke-width', n.kind==='hub'?4.5:3);
      t.setAttribute('paint-order','stroke');
      t.setAttribute('stroke-linejoin','round');
      t.setAttribute('letter-spacing', n.kind==='hub'?'0.8':'0');
      t.setAttribute('pointer-events','none');
      t.textContent = n.label.length>34 ? n.label.slice(0,32)+'…' : n.label;
      n._lbl=t; gLabels.appendChild(t);
    });
    host.appendChild(svgEl);
    bindCanvas();
    buildMini();
  }

  function toWorld(ev){
    var r=svgEl.getBoundingClientRect();
    var px=(ev.clientX!==undefined?ev.clientX:ev.touches[0].clientX)-r.left;
    var py=(ev.clientY!==undefined?ev.clientY:ev.touches[0].clientY)-r.top;
    return {x:viewBox.x+(px/r.width)*viewBox.w, y:viewBox.y+(py/r.height)*viewBox.h};
  }
  function zoomAt(center,factor){
    tween=null;
    var nw=Math.max(150,Math.min(9000,viewBox.w*factor));
    var scale=nw/viewBox.w;
    viewBox.x=center.x-(center.x-viewBox.x)*scale;
    viewBox.y=center.y-(center.y-viewBox.y)*scale;
    viewBox.w=nw; viewBox.h=viewBox.h*scale;
    applyVB();
  }

  function bindCanvas(){
    svgEl.addEventListener('mousemove', function(ev){
      if(dragNode){
        var p=toWorld(ev); dragNode.x=p.x; dragNode.y=p.y; dragNode.vx=0; dragNode.vy=0;
        sim.reheat(); return;
      }
      if(panning){
        var r=svgEl.getBoundingClientRect();
        viewBox.x=vbStart.x-(ev.clientX-panStart.x)/r.width*viewBox.w;
        viewBox.y=vbStart.y-(ev.clientY-panStart.y)/r.height*viewBox.h;
        applyVB(); return;
      }
      var id=ev.target.getAttribute&&ev.target.getAttribute('data-id');
      if(id!==hoverId){ hoverId=id||null; showTip(id,ev); draw(); }
      else if(id) showTip(id,ev);
    });
    svgEl.addEventListener('mousedown', function(ev){
      var id=ev.target.getAttribute&&ev.target.getAttribute('data-id');
      if(id){
        dragNode=model.nodes.find(function(n){return n.id===id;});
        if(dragNode){ dragNode.fixed=true; dragging=false; }
      } else {
        tween=null; panning=true; panStart={x:ev.clientX,y:ev.clientY};
        vbStart={x:viewBox.x,y:viewBox.y}; svgEl.style.cursor='grabbing';
      }
    });
    window.addEventListener('mousemove', function(){ if(dragNode) dragging=true; });
    window.addEventListener('mouseup', function(){
      if(dragNode){
        var wasDrag=dragging, nid=dragNode.id;
        dragNode.fixed=false; dragNode=null; dragging=false;
        if(!wasDrag) activate(nid);
      }
      panning=false;
      if(svgEl) svgEl.style.cursor='grab';
    });
    svgEl.addEventListener('mouseleave', function(){ hoverId=null; hideTip(); draw(); });
    svgEl.addEventListener('wheel', function(ev){
      ev.preventDefault(); zoomAt(toWorld(ev), ev.deltaY>0?1.12:1/1.12);
    }, {passive:false});

    var lastDist=null;
    svgEl.addEventListener('touchstart', function(ev){
      if(ev.touches.length===1){
        tween=null; panning=true;
        panStart={x:ev.touches[0].clientX,y:ev.touches[0].clientY};
        vbStart={x:viewBox.x,y:viewBox.y};
      }
      lastDist=null;
    }, {passive:true});
    svgEl.addEventListener('touchmove', function(ev){
      if(ev.touches.length===2){
        ev.preventDefault();
        var a=ev.touches[0], b=ev.touches[1];
        var dist=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY);
        var mid=toWorld({clientX:(a.clientX+b.clientX)/2, clientY:(a.clientY+b.clientY)/2});
        if(lastDist) zoomAt(mid,lastDist/dist);
        lastDist=dist; panning=false;
      } else if(ev.touches.length===1&&panning){
        ev.preventDefault();
        var r=svgEl.getBoundingClientRect();
        viewBox.x=vbStart.x-(ev.touches[0].clientX-panStart.x)/r.width*viewBox.w;
        viewBox.y=vbStart.y-(ev.touches[0].clientY-panStart.y)/r.height*viewBox.h;
        applyVB();
      }
    }, {passive:false});
    svgEl.addEventListener('touchend', function(){ panning=false; lastDist=null; }, {passive:true});
  }

  /* ---------- tooltip ---------- */
  function showTip(id,ev){
    var tip=document.getElementById('graph-tip');
    if(!id){ tip.style.display='none'; return; }
    var n=model.nodes.find(function(x){return x.id===id;});
    if(!n){ tip.style.display='none'; return; }
    if(n.kind==='hub'){
      tip.innerHTML='<b>'+esc(n.label)+'</b><span>'+esc(n.desc||'')+'</span>'+
        '<span class="tip-cta">'+(n.linId===focusId?'linhagem em foco':'clique para focar esta linhagem')+'</span>';
    } else {
      var ent = ENTRIES.find(function(x){ return x.id===n.id; });
      tip.innerHTML='<div class="tip-row">'+
        (ent ? '<div class="tip-cover">'+coverSVG(ent)+'</div>' : '')+
        '<div class="tip-txt"><b>'+esc(n.full||n.label)+'</b>'+
        '<span>'+esc(n.mediaLabel||'')+(n.year?' · '+n.year:'')+' — '+n.deg+' conexõe'+(n.deg===1?'':'s')+'</span>'+
        '<span class="tip-cta">clique para abrir a ficha</span></div></div>';
    }
    tip.style.display='block';
    var host=document.getElementById('graph-canvas').getBoundingClientRect();
    var x=ev.clientX-host.left+14, y=ev.clientY-host.top+14;
    if(x>host.width-260) x=host.width-260;
    if(y>host.height-90) y=host.height-90;
    tip.style.left=x+'px'; tip.style.top=y+'px';
  }
  function hideTip(){ var t=document.getElementById('graph-tip'); if(t) t.style.display='none'; }

  function activate(id){
    var n=model.nodes.find(function(x){return x.id===id;});
    if(!n) return;
    if(n.kind==='hub'){ setFocus(n.linId, true); return; }
    var entry=ENTRIES.find(function(e){return e.id===n.id;});
    if(entry) openModal(entry.id, entry.kind);
  }

  /* ---------- open / close ---------- */
  function open(linId){
    var ov=document.getElementById('graph-overlay');
    document.body.style.overflow='hidden';
    ov.classList.add('open');

    if(!built){
      model=buildModel();
      sim=makeSim(model);
      buildSVG();
      for(var i=0;i<420;i++) sim.tick();
      built=true;
    }
    if(raf) cancelAnimationFrame(raf);
    focusId=null;
    setFocus(linId, false);
    loop();
  }
  function close(){
    document.getElementById('graph-overlay').classList.remove('open');
    document.body.style.overflow='';
    if(raf) cancelAnimationFrame(raf);
    raf=null; hoverId=null; tween=null; hideTip();
  }

  function bind(){
    document.getElementById('graph-close').addEventListener('click', close);
    document.getElementById('graph-overview').addEventListener('click', function(){ setFocus(null,true); });
    document.getElementById('graph-fit').addEventListener('click', function(){ cameraForFocus(true); });
    document.getElementById('graph-reheat').addEventListener('click', function(){ sim&&sim.reheat(); });
    document.getElementById('graph-nav').addEventListener('click', function(ev){
      var b=ev.target.closest('.gnav-chip');
      if(b) setFocus(b.getAttribute('data-lin'), true);
    });
    var lg=document.getElementById('graph-legend');
    var order=['mitos','literatura','cinema','series','animes','games','ciborgues','transumanismo'];
    lg.innerHTML = order.map(function(m){
      return '<span class="glg"><i style="background:'+MEDIA_COLOR[m]+'"></i>'+CAT_LABEL[m]+'</span>';
    }).join('') + '<span class="glg"><i style="background:'+HUB_COLOR+'"></i>linhagem</span>';
  }

  return {open:open, close:close, bind:bind};
})();

function openGraph(linId){ GRAPH.open(linId); }


/* =========================================================
   INIT
   ========================================================= */
function init(){
  renderFrontiers();
  renderGenealogy();
  renderTimeline();
  renderChips();
  renderCatalog();
  bindCatalogEvents();
  renderThematic();
  renderComputing();
  renderArt();
  renderReality();
  renderUsage();
  bindNav();
  animateStat();
  GRAPH.bind();
}

if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
})();
