// Navbar scroll effect
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 60);
});

// Intersection Observer for reveal animations
const revealItems = document.querySelectorAll('[data-reveal]');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

revealItems.forEach(item => observer.observe(item));

// Also observe valor-item, block-item, format-card, process-step
const animItems = document.querySelectorAll('.valor-item, .block-item, .format-card, .process-step');
animItems.forEach(item => observer.observe(item));

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
