/* Contagem de acesso (dashboard do admin). Expõe window.vTrack para o resto do arquivo.
   A landing roda dentro de um iframe no app Vue, então a base da API vem de ?apiBase= — a
   mesma convenção já usada pelos materiais, prompts e leads. */
(function trackerBoot() {
  function apiUrl(path) {
    var params = new URLSearchParams(window.location.search);
    var fromQuery = params.get('apiBase');
    if (fromQuery && fromQuery.length) {
      return fromQuery.replace(/\/$/, '') + path;
    }
    return path;
  }

  window.vTrack = function vTrack(resourceKey) {
    if (!resourceKey) return;
    try {
      fetch(apiUrl('/api/public/track'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resource_key: resourceKey }),
        credentials: 'include',
        keepalive: true
      }).catch(function () {});
    } catch (e) {
      // Telemetria nunca pode quebrar a landing
    }
  };

  window.vTrack('plataforma.landing');

  // Delegação: os cards de material e os prompts são renderizados depois, via API.
  document.addEventListener('click', function (ev) {
    var el = ev.target && ev.target.closest ? ev.target.closest('[data-track-key]') : null;
    if (el) window.vTrack(el.getAttribute('data-track-key'));
  });
})();

/* Materiais da landing: carrega primeiro e isolado — não pode ficar preso em "Carregando…". */
(function loadLandingMaterialsBoot() {
  function materialsApiUrl() {
    var params = new URLSearchParams(window.location.search);
    var fromQuery = params.get('apiBase');
    if (fromQuery && fromQuery.length) {
      return fromQuery.replace(/\/$/, '') + '/api/public/landing-materials';
    }
    return '/api/public/landing-materials';
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function isHtmlUrl(url) {
    if (!url) return false;
    var path = String(url).split('?')[0].split('#')[0].toLowerCase();
    return path.endsWith('.html') || path.endsWith('.htm');
  }

  function renderMaterialLinks(item) {
    var trackAttr = ' data-track-key="material:' + escapeHtml(item.id) + '"';
    if (isHtmlUrl(item.material_url)) {
      return (
        '<div class="material-card-links">' +
          '<a class="material-link"' + trackAttr + ' href="' + escapeHtml(item.material_url) + '" target="_blank" rel="noopener noreferrer">Acessar aqui →</a>' +
        '</div>'
      );
    }
    return (
      '<div class="material-card-links">' +
        '<a class="material-link"' + trackAttr + ' href="' + escapeHtml(item.material_url) + '" target="_blank" rel="noopener noreferrer">Baixar material →</a>' +
        '<a class="material-link"' + trackAttr + ' href="' + escapeHtml(item.summary_url) + '" target="_blank" rel="noopener noreferrer">Resumo executivo →</a>' +
      '</div>'
    );
  }

  function renderMaterialCard(item) {
    var audio = item.audio_url
      ? '<audio class="material-audio" controls preload="none" src="' + escapeHtml(item.audio_url) + '">Seu navegador não suporta áudio.</audio>'
      : '';
    return (
      '<article class="material-card">' +
        '<h3 class="material-card-title">' + escapeHtml(item.title) + '</h3>' +
        '<p class="material-card-desc">' + escapeHtml(item.description) + '</p>' +
        renderMaterialLinks(item) +
        audio +
      '</article>'
    );
  }

  function setTrackHtml(html) {
    var track = document.getElementById('materials-track');
    if (track) track.innerHTML = html;
  }

  function loadLandingMaterials() {
    var track = document.getElementById('materials-track');
    if (!track) return;

    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (ctrl) ctrl.abort();
    }, 12000);

    var opts = ctrl ? { signal: ctrl.signal } : {};
    fetch(materialsApiUrl(), opts)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (items) {
        if (!Array.isArray(items) || items.length === 0) {
          setTrackHtml('<p class="materials-empty">Em breve: materiais gratuitos para download.</p>');
          return;
        }
        setTrackHtml(items.map(renderMaterialCard).join(''));
      })
      .catch(function () {
        setTrackHtml('<p class="materials-empty">Não foi possível carregar os materiais agora.</p>');
      })
      .then(function () {
        clearTimeout(timer);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadLandingMaterials);
  } else {
    loadLandingMaterials();
  }

  // Se o script externo falhar parcialmente, não deixar "Carregando…" para sempre
  setTimeout(function () {
    var track = document.getElementById('materials-track');
    if (!track) return;
    if (/Carregando materiais/i.test(track.textContent || '')) {
      setTrackHtml('<p class="materials-empty">Não foi possível carregar os materiais agora.</p>');
    }
  }, 15000);
})();

/* Prompts da landing: lista dinâmica via API (mesmo padrão dos materiais). */
(function loadLandingPromptsBoot() {
  function promptsApiUrl() {
    var params = new URLSearchParams(window.location.search);
    var fromQuery = params.get('apiBase');
    if (fromQuery && fromQuery.length) {
      return fromQuery.replace(/\/$/, '') + '/api/public/landing-prompts';
    }
    return '/api/public/landing-prompts';
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderPromptItem(item) {
    var meta = item.meta_label
      ? '<span class="prompt-link-meta">' + escapeHtml(item.meta_label) + '</span>'
      : '';
    return (
      '<li>' +
        '<a class="prompt-link" data-track-key="prompt:' + escapeHtml(item.id) + '" href="' + escapeHtml(item.prompt_url) + '" target="_blank" rel="noopener noreferrer">' +
          meta +
          '<span class="prompt-link-title">' + escapeHtml(item.title) + '</span>' +
          '<span class="prompt-link-desc">' + escapeHtml(item.description) + '</span>' +
        '</a>' +
      '</li>'
    );
  }

  function setPromptsHtml(html) {
    var list = document.getElementById('prompts-list');
    if (list) list.innerHTML = html;
  }

  function loadLandingPrompts() {
    var list = document.getElementById('prompts-list');
    if (!list) return;

    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (ctrl) ctrl.abort();
    }, 12000);

    var opts = ctrl ? { signal: ctrl.signal } : {};
    fetch(promptsApiUrl(), opts)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (items) {
        if (!Array.isArray(items) || items.length === 0) {
          setPromptsHtml('<li class="prompts-empty">Em breve: prompts úteis para download.</li>');
          return;
        }
        setPromptsHtml(items.map(renderPromptItem).join(''));
      })
      .catch(function () {
        setPromptsHtml('<li class="prompts-empty">Não foi possível carregar os prompts agora.</li>');
      })
      .then(function () {
        clearTimeout(timer);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadLandingPrompts);
  } else {
    loadLandingPrompts();
  }

  setTimeout(function () {
    var list = document.getElementById('prompts-list');
    if (!list) return;
    if (/Carregando prompts/i.test(list.textContent || '')) {
      setPromptsHtml('<li class="prompts-empty">Não foi possível carregar os prompts agora.</li>');
    }
  }, 15000);
})();

try {
  // Navbar scroll effect
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 60);
    });
  }

  // Intersection Observer for reveal animations
  const revealItems = document.querySelectorAll('[data-reveal]');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -5% 0px' });

  revealItems.forEach(item => observer.observe(item));

  // Also observe valor-item, block-item, format-card, process-step
  const animItems = document.querySelectorAll('.valor-item, .block-item, .format-card, .process-step');
  animItems.forEach(item => observer.observe(item));

  // Itens já no viewport (iframe / reload) às vezes não disparam o observer
  function revealIfInView(el) {
    var rect = el.getBoundingClientRect();
    var vh = window.innerHeight || document.documentElement.clientHeight;
    if (rect.top < vh * 0.95 && rect.bottom > 0) {
      el.classList.add('visible');
      observer.unobserve(el);
    }
  }
  revealItems.forEach(revealIfInView);
  animItems.forEach(revealIfInView);
} catch (e) {
  // Animações não devem quebrar a landing
}

// Form submission: envia dados para a API e exibe mensagem de sucesso
var successHtml = '<div style="text-align:center; padding:3rem 1rem;">' +
  '<div style="width:60px;height:60px;border:2px solid #B8962E;display:flex;align-items:center;justify-content:center;margin:0 auto 1.5rem;font-size:1.5rem;color:#B8962E;">✓</div>' +
  '<h3 style="font-family:\'Cormorant Garamond\',serif;font-size:1.6rem;color:#F4F1EB;margin-bottom:0.75rem;">Aplicação Recebida</h3>' +
  '<p style="color:#8A9BB5;font-size:0.9rem;line-height:1.7;">Entraremos em contato em até 24 horas úteis para agendar a Sessão de Triagem.<br><br>Você pode também nos contatar diretamente via WhatsApp.</p>' +
  '<a href="https://wa.me/+5581982579870" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:2rem;padding:0.8rem 2rem;background:#B8962E;color:#0C1827;font-family:\'Barlow Condensed\',sans-serif;font-weight:600;letter-spacing:0.15em;text-transform:uppercase;font-size:0.82rem;text-decoration:none;">WhatsApp →</a>' +
  '</div>';

function refreshCaptcha() {
  var wrap = document.getElementById('lead-captcha-wrap');
  var s1 = document.getElementById('captcha-n1');
  var s2 = document.getElementById('captcha-n2');
  var inp = document.getElementById('lead-captcha');
  if (!wrap || !s1 || !s2) return;
  var n1 = Math.floor(Math.random() * 10);
  var n2 = Math.floor(Math.random() * 10);
  wrap.dataset.n1 = n1;
  wrap.dataset.n2 = n2;
  s1.textContent = n1;
  s2.textContent = n2;
  if (inp) inp.value = '';
}

(function initCaptcha() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', refreshCaptcha);
  } else {
    refreshCaptcha();
  }
})();

function leadsApiUrl() {
  var params = new URLSearchParams(window.location.search);
  var fromQuery = params.get('apiBase');
  if (fromQuery && fromQuery.length) {
    return fromQuery.replace(/\/$/, '') + '/api/public/leads';
  }
  return '/api/public/leads';
}

function detailFromErrorBody(body) {
  if (!body || typeof body !== 'object') return 'Erro ao enviar';
  var d = body.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map(function (e) { return (e && e.msg) ? e.msg : String(e); }).join(' ');
  }
  return 'Erro ao enviar';
}

function handleSubmit() {
  var btn = document.getElementById('btn-submit');
  var nome = document.getElementById('lead-nome');
  var cargo = document.getElementById('lead-cargo');
  var empresa = document.getElementById('lead-empresa');
  var faturamento = document.getElementById('lead-faturamento');
  var email = document.getElementById('lead-email');
  var contexto = document.getElementById('lead-contexto');
  var wrap = document.getElementById('lead-captcha-wrap');
  var captchaInp = document.getElementById('lead-captcha');
  if (!nome || !email || !btn) return;
  var n1 = wrap && wrap.dataset.n1 !== undefined ? parseInt(wrap.dataset.n1, 10) : 0;
  var n2 = wrap && wrap.dataset.n2 !== undefined ? parseInt(wrap.dataset.n2, 10) : 0;
  var answer = captchaInp ? parseInt(captchaInp.value.trim(), 10) : NaN;
  if (answer !== n1 + n2) {
    alert('Verificação incorreta. Calcule a soma dos dois números e tente novamente.');
    if (captchaInp) { captchaInp.focus(); captchaInp.select(); }
    refreshCaptcha();
    return;
  }
  var payload = {
    nome_completo: nome.value.trim(),
    cargo: (cargo && cargo.value.trim()) || '',
    empresa: (empresa && empresa.value.trim()) || '',
    faturamento_anual: (faturamento && faturamento.value) || '',
    email: email.value.trim(),
    contexto_ia: (contexto && contexto.value.trim()) || null,
    num1: n1,
    num2: n2,
    captcha_answer: answer
  };
  btn.textContent = 'Enviando...';
  btn.disabled = true;
  fetch(leadsApiUrl(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function (res) {
      if (res.ok) {
        document.getElementById('form-block').innerHTML = successHtml;
        return;
      }
      return res.text().then(function (text) {
        var msg = 'Erro ao enviar';
        if (text) {
          try {
            msg = detailFromErrorBody(JSON.parse(text));
          } catch (parseErr) {
            msg = text.length > 200 ? text.slice(0, 200) + '…' : text;
          }
        } else {
          msg = 'HTTP ' + res.status;
        }
        throw new Error(msg);
      });
    })
    .catch(function (err) {
      btn.textContent = 'Solicitar Aplicação →';
      btn.disabled = false;
      refreshCaptcha();
      var msg = (err && err.message) ? err.message : 'Não foi possível enviar.';
      if (msg === 'Failed to fetch' || msg === 'Load failed' || msg === 'NetworkError when attempting to fetch resource.') {
        msg = 'Não foi possível conectar ao servidor. Tente novamente em instantes ou fale conosco pelo WhatsApp.';
      }
      alert(msg + ' Você também pode falar conosco pelo WhatsApp.');
    });
}

// Link "Entrar": usar loginBase da query (passado pelo app Vue no iframe) para evitar cross-origin
(function() {
  var a = document.querySelector('a.nav-login');
  if (!a) return;
  var params = new URLSearchParams(window.location.search);
  var loginBase = params.get('loginBase');
  if (loginBase) {
    a.href = loginBase.replace(/\/$/, '') + '/login';
    a.setAttribute('target', '_top');
  }
})();
