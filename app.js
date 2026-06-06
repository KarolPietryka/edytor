const API_URL = 'http://localhost:3000/api/draft';

const draftInput = document.getElementById('draft');
const sendBtn = document.getElementById('send-btn');
const statusEl = document.getElementById('status');
const commentPopup = document.getElementById('comment-popup');
const commentPopupQuote = document.getElementById('comment-popup-quote');
const commentInput = document.getElementById('comment-input');
const commentSendBtn = document.getElementById('comment-send-btn');
const commentsList = document.getElementById('comments-list');
const textareaMirror = document.getElementById('textarea-mirror');

let currentSelection = null;

const DRAWER_WIDTH = 320;
const VIEWPORT_GAP = 10;

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

function syncMirrorStyles() {
  const style = window.getComputedStyle(draftInput);
  const props = [
    'boxSizing', 'width', 'fontFamily', 'fontSize', 'fontWeight', 'fontStyle',
    'letterSpacing', 'textTransform', 'textIndent', 'paddingTop', 'paddingRight',
    'paddingBottom', 'paddingLeft', 'borderTopWidth', 'borderRightWidth',
    'borderBottomWidth', 'borderLeftWidth', 'lineHeight', 'textAlign', 'wordSpacing',
  ];
  props.forEach(function (prop) {
    textareaMirror.style[prop] = style[prop];
  });
}

function getCaretCoordinates(position) {
  syncMirrorStyles();
  const rect = draftInput.getBoundingClientRect();
  textareaMirror.style.width = rect.width + 'px';

  const value = draftInput.value;
  const before = value.substring(0, position);
  const after = value.substring(position) || '.';

  textareaMirror.textContent = '';
  textareaMirror.appendChild(document.createTextNode(before));
  const marker = document.createElement('span');
  marker.textContent = after[0];
  textareaMirror.appendChild(marker);

  textareaMirror.style.top = rect.top + 'px';
  textareaMirror.style.left = rect.left + 'px';

  const markerRect = marker.getBoundingClientRect();
  return {
    top: markerRect.top,
    bottom: markerRect.bottom,
    left: markerRect.left + markerRect.width / 2,
  };
}

function getSelectionAnchor(start, end) {
  const startCoords = getCaretCoordinates(start);
  const endCoords = getCaretCoordinates(end);
  return {
    top: Math.min(startCoords.top, endCoords.top),
    bottom: Math.max(startCoords.bottom, endCoords.bottom),
    left: (startCoords.left + endCoords.left) / 2,
  };
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function positionCommentPopup(anchor) {
  commentPopup.hidden = false;
  commentPopup.style.visibility = 'hidden';

  const maxW = Math.min(440, window.innerWidth - DRAWER_WIDTH - VIEWPORT_GAP * 2);
  commentPopup.style.width = maxW + 'px';

  const vh = window.innerHeight;
  const spaceAbove = anchor.top - VIEWPORT_GAP * 2;
  const spaceBelow = vh - anchor.bottom - VIEWPORT_GAP * 2;
  const below = spaceBelow >= spaceAbove;

  var top;
  var height;
  if (below) {
    top = anchor.bottom + VIEWPORT_GAP;
    height = vh - VIEWPORT_GAP - top;
  } else {
    top = VIEWPORT_GAP;
    height = anchor.top - VIEWPORT_GAP * 2;
  }

  height = Math.max(140, height);

  commentPopup.style.height = height + 'px';
  commentPopup.style.maxHeight = height + 'px';

  const popupW = commentPopup.offsetWidth;
  let left = anchor.left - popupW / 2;
  left = clamp(
    left,
    VIEWPORT_GAP,
    window.innerWidth - DRAWER_WIDTH - VIEWPORT_GAP - popupW
  );

  commentPopup.style.left = left + 'px';
  commentPopup.style.top = top + 'px';
  commentPopup.style.visibility = '';
}

function hideCommentPopup() {
  commentPopup.hidden = true;
  commentPopup.style.width = '';
  commentPopup.style.height = '';
  commentPopup.style.maxHeight = '';
  commentPopup.style.top = '';
  commentPopup.style.left = '';
  currentSelection = null;
}

function showCommentPopup() {
  const start = draftInput.selectionStart;
  const end = draftInput.selectionEnd;
  const text = draftInput.value.substring(start, end).trim();

  if (!text) {
    hideCommentPopup();
    return;
  }

  currentSelection = { text: text, start: start, end: end };

  const preview = text.length > 100 ? text.slice(0, 100) + '…' : text;
  commentPopupQuote.textContent = preview;

  positionCommentPopup(getSelectionAnchor(start, end));
}

function handleSelection() {
  requestAnimationFrame(showCommentPopup);
}

function addCommentToDrawer(selectionText, commentText) {
  const empty = commentsList.querySelector('.drawer__empty');
  if (empty) {
    empty.remove();
  }

  const card = document.createElement('article');
  card.className = 'comment-card';

  const quote = document.createElement('blockquote');
  quote.className = 'comment-card__quote';
  quote.textContent = selectionText;

  const body = document.createElement('p');
  body.className = 'comment-card__body';
  body.textContent = commentText;

  const time = document.createElement('time');
  time.className = 'comment-card__time';
  time.textContent = new Date().toLocaleString('pl-PL');

  card.appendChild(quote);
  card.appendChild(body);
  card.appendChild(time);
  commentsList.appendChild(card);
  commentsList.scrollTop = commentsList.scrollHeight;
}

function sendComment() {
  if (!currentSelection) {
    return;
  }

  const commentText = commentInput.value.trim();
  if (!commentText) {
    commentInput.focus();
    return;
  }

  addCommentToDrawer(currentSelection.text, commentText);
  commentInput.value = '';
  hideCommentPopup();
}

sendBtn.addEventListener('click', sendDraft);

draftInput.addEventListener('keydown', function (e) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault();
    sendDraft();
  }
});

draftInput.addEventListener('mouseup', handleSelection);
draftInput.addEventListener('keyup', function (e) {
  if (e.shiftKey || e.key === 'Shift' || e.key.startsWith('Arrow')) {
    handleSelection();
  }
});

draftInput.addEventListener('scroll', function () {
  if (!commentPopup.hidden) {
    showCommentPopup();
  }
});

commentSendBtn.addEventListener('click', sendComment);

commentInput.addEventListener('keydown', function (e) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault();
    sendComment();
  }
  e.stopPropagation();
});

commentPopup.addEventListener('mousedown', function (e) {
  e.stopPropagation();
});

document.addEventListener('mousedown', function (e) {
  if (commentPopup.hidden) {
    return;
  }
  if (!commentPopup.contains(e.target) && e.target !== draftInput) {
    hideCommentPopup();
  }
});

window.addEventListener('resize', function () {
  if (!commentPopup.hidden) {
    showCommentPopup();
  }
});
