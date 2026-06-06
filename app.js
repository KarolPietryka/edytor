const API_URL = 'http://localhost:3000/api/draft';

const draftInput = document.getElementById('draft');
const sendBtn = document.getElementById('send-btn');
const statusEl = document.getElementById('status');

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = 'status' + (type ? ' status--' + type : '');
}

async function sendDraft() {
  const text = draftInput.value.trim();

  if (!text) {
    setStatus('[ERR] buffer empty // no data to transmit', 'error');
    return;
  }

  sendBtn.disabled = true;
  setStatus('[..] uplink in progress...', 'info');

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error('HTTP ' + response.status);
    }

    setStatus('[OK] transmission complete', 'success');
  } catch (err) {
    setStatus('[ERR] uplink failed // ' + err.message, 'error');
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener('click', sendDraft);
