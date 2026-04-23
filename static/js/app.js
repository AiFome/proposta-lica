// ═══════════════════════════════════════════════════
// PropostaLic — app.js
// ═══════════════════════════════════════════════════

// Flash messages — auto-fechar após 5 segundos
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    });
  }, 5000);

  // Fechar flash ao clicar
  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const flash = btn.closest('.flash');
      if (flash) flash.remove();
    });
  });

  // Confirmar ações destrutivas
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      if (!confirm(el.dataset.confirm)) e.preventDefault();
    });
  });

  // Tooltips simples
  document.querySelectorAll('[title]').forEach(el => {
    el.style.cursor = 'help';
  });
});

// Chat flutuante (disponível em proposta, produtos, documentação)
(function() {
  const chatPages = ['/proposta', '/produtos', '/documentacao', '/dashboard'];
  const isChat = chatPages.some(p => location.pathname.includes(p));
  if (!isChat) return;

  // Criar botão flutuante
  const fab = document.createElement('button');
  fab.className = 'chat-fab';
  fab.title = 'Assistente IA';
  fab.innerHTML = '💬';
  document.body.appendChild(fab);

  // Criar painel de chat
  const panel = document.createElement('div');
  panel.className = 'chat-float closed';
  panel.innerHTML = `
    <div class="chat-float-header">
      💬 Assistente IA
      <button class="chat-float-close" onclick="toggleChatFloat()">✕</button>
    </div>
    <div class="chat-float-msgs" id="chatFloatMsgs">
      <div style="text-align:center;padding:20px;color:#aaa;font-size:13px">
        <div style="font-size:32px;margin-bottom:8px">🤖</div>
        Olá! Posso ajudar com dúvidas sobre licitações, propostas ou documentação.
      </div>
    </div>
    <div class="chat-float-input">
      <textarea id="chatFloatInput" placeholder="Digite sua pergunta..." rows="1"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChatFloat()}"></textarea>
      <button onclick="sendChatFloat()" id="chatFloatBtn">➤</button>
    </div>
  `;
  document.body.appendChild(panel);

  let chatOpen = false;
  let chatHistory = [];

  fab.addEventListener('click', toggleChatFloat);

  window.toggleChatFloat = function() {
    chatOpen = !chatOpen;
    panel.classList.toggle('closed', !chatOpen);
    if (chatOpen) document.getElementById('chatFloatInput')?.focus();
  };

  window.sendChatFloat = async function() {
    const inp = document.getElementById('chatFloatInput');
    const btn = document.getElementById('chatFloatBtn');
    const msgs = document.getElementById('chatFloatMsgs');
    const msg = inp.value.trim();
    if (!msg) return;

    inp.value = ''; inp.style.height = 'auto';
    btn.disabled = true;

    // Remove empty state
    const empty = msgs.querySelector('div[style*="text-align:center"]');
    if (empty) empty.remove();

    // Add user message
    const userDiv = document.createElement('div');
    userDiv.className = 'msg u';
    userDiv.textContent = msg;
    msgs.appendChild(userDiv);
    msgs.scrollTop = msgs.scrollHeight;
    chatHistory.push({ role: 'user', content: msg });

    // Thinking
    const thinking = document.createElement('div');
    thinking.className = 'msg a';
    thinking.textContent = 'Pensando...';
    thinking.style.opacity = '.6';
    msgs.appendChild(thinking);
    msgs.scrollTop = msgs.scrollHeight;

    try {
      const resp = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: chatHistory,
          system: 'Você é um assistente especializado em licitações públicas brasileiras. Responda de forma clara e objetiva em português.'
        })
      });
      const data = await resp.json();
      thinking.remove();

      if (data.erro) {
        const errDiv = document.createElement('div');
        errDiv.className = 'msg a';
        errDiv.textContent = '❌ ' + data.erro;
        msgs.appendChild(errDiv);
      } else {
        const aiDiv = document.createElement('div');
        aiDiv.className = 'msg a';
        aiDiv.textContent = data.resposta;
        msgs.appendChild(aiDiv);
        chatHistory.push({ role: 'assistant', content: data.resposta });
      }
    } catch(e) {
      thinking.remove();
      const errDiv = document.createElement('div');
      errDiv.className = 'msg a';
      errDiv.textContent = '❌ Erro de conexão.';
      msgs.appendChild(errDiv);
    }

    msgs.scrollTop = msgs.scrollHeight;
    btn.disabled = false;
    inp.focus();
  };

  document.getElementById('chatFloatInput')?.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 90) + 'px';
  });
})();

// Utilitários globais
window.fmtBytes = function(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
};

window.showFlash = function(msg, type = 'info') {
  const container = document.querySelector('.flash-container') || (() => {
    const c = document.createElement('div');
    c.className = 'flash-container';
    document.querySelector('.main-content')?.prepend(c);
    return c;
  })();
  const el = document.createElement('div');
  el.className = `flash flash-${type}`;
  el.innerHTML = `<span>${msg}</span><button class="flash-close" onclick="this.parentElement.remove()">✕</button>`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 400); }, 5000);
};
