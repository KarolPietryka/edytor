const API_URL = 'http://localhost:3000/api/draft';
const COMMENT_API_URL = 'http://localhost:3000/api/comment';
const AI_API_URL = 'http://localhost:3000/api/ai';

const draftInput = document.getElementById('draft');
const draftClearBtn = document.getElementById('draft-clear-btn');
const wytyczneInput = document.getElementById('wytyczne');
const sendBtn = document.getElementById('send-btn');
const aiBtn = document.getElementById('ai-btn');
const statusEl = document.getElementById('status');
const terminalTitle = document.getElementById('terminal-title');
const commentPopup = document.getElementById('comment-popup');
const commentPopupQuote = document.getElementById('comment-popup-quote');
const commentInput = document.getElementById('comment-input');
const commentSendBtn = document.getElementById('comment-send-btn');
const commentsList = document.getElementById('comments-list');
const textareaMirror = document.getElementById('textarea-mirror');

let currentSelection = null;
let currentDraftFile = null;

const DRAWER_WIDTH = 320;
const VIEWPORT_GAP = 10;
const DEFAULT_TERMINAL_TITLE = 'ICE_BYPASS // mem:draft_01 // ♪';
const SELECT_ALL_LABEL = '<all>';
const SELECT_ALL_PAYLOAD = '<Wszystko>';

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = 'status' + (type ? ' status--' + type : '');
}

function setDraftPath(path) {
  terminalTitle.textContent = path || DEFAULT_TERMINAL_TITLE;
}

function syncDraftClearBtn() {
  if (!draftClearBtn) {
    return;
  }
  draftClearBtn.disabled = !draftInput.value.length;
}

function clearDraftBuffer() {
  if (!draftInput.value.length) {
    return;
  }
  draftInput.value = '';
  syncDraftClearBtn();
  hideCommentPopup();
  draftInput.focus();
}

function getWytycznePayload() {
  if (!wytyczneInput) {
    return { wytyczne: '' };
  }
  return { wytyczne: wytyczneInput.value.trim() };
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
      body: JSON.stringify(Object.assign({ text: text }, getWytycznePayload())),
    });

    if (!response.ok) {
      throw new Error('HTTP ' + response.status);
    }

    const data = await response.json();
    currentDraftFile = data.file;
    setDraftPath(data.draft_path);
    setStatus('[OK] transmission complete // ' + data.file, 'success');
  } catch (err) {
    setStatus('[ERR] uplink failed // ' + err.message, 'error');
  } finally {
    sendBtn.disabled = false;
  }
}

async function sendAi() {
  aiBtn.disabled = true;
  setStatus('[..] AI loop in progress...', 'info');

  try {
    const response = await fetch(AI_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(getWytycznePayload()),
    });

    if (!response.ok) {
      const errData = await response.json().catch(function () {
        return {};
      });
      var msg = errData.error || 'HTTP ' + response.status;
      if (errData.steps && errData.steps.length) {
        msg += ' // ' + errData.steps[errData.steps.length - 1].comment_id;
      }
      throw new Error(msg);
    }

    const data = await response.json();
    const done = (data.steps || []).filter(function (s) { return s.status === 'done'; }).length;
    const total = data.total || 0;

    if (data.text) {
      draftInput.value = data.text;
      syncDraftClearBtn();
    }
    if (data.draft_file) {
      currentDraftFile = data.draft_file;
    }
    setDraftPath(data.draft_path);

    clearCommentsDrawer();
    hideCommentPopup();

    setStatus('[OK] AI loop done // ' + data.draft_file + ' (' + done + '/' + total + ' comments)', 'success');
  } catch (err) {
    setStatus('[ERR] AI uplink failed // ' + err.message, 'error');
  } finally {
    aiBtn.disabled = false;
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
  textareaMirror.style.height = draftInput.clientHeight + 'px';
  textareaMirror.style.maxHeight = draftInput.clientHeight + 'px';

  const value = draftInput.value;
  const before = value.substring(0, position);
  const after = value.substring(position);

  textareaMirror.textContent = '';
  textareaMirror.appendChild(document.createTextNode(before));

  const marker = document.createElement('span');
  if (!after.length) {
    marker.textContent = '.';
  } else if (after[0] === '\n') {
    textareaMirror.appendChild(document.createTextNode('\n'));
    marker.textContent = '\u200b';
  } else {
    marker.textContent = after[0];
  }
  textareaMirror.appendChild(marker);

  textareaMirror.scrollTop = draftInput.scrollTop;
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

function getSelectionText(start, end) {
  return draftInput.value.substring(start, end).replace(/^\s+|\s+$/g, '');
}

function isFullDraftSelection(start, end) {
  const len = draftInput.value.length;
  return len > 0 && start === 0 && end === len;
}

function showCommentPopup() {
  const start = draftInput.selectionStart;
  const end = draftInput.selectionEnd;

  if (start === end) {
    if (!commentPopup.hidden && currentSelection) {
      return;
    }
    hideCommentPopup();
    return;
  }

  if (isFullDraftSelection(start, end)) {
    currentSelection = {
      text: SELECT_ALL_PAYLOAD,
      label: SELECT_ALL_LABEL,
      start: start,
      end: end,
    };
    commentPopupQuote.textContent = SELECT_ALL_LABEL;
    positionCommentPopup(getSelectionAnchor(start, end));
    commentInput.focus();
    return;
  }

  const text = getSelectionText(start, end);

  if (!text) {
    hideCommentPopup();
    return;
  }

  currentSelection = { text: text, label: text, start: start, end: end };

  const preview = text.length > 100 ? text.slice(0, 100) + '…' : text;
  commentPopupQuote.textContent = preview;

  positionCommentPopup(getSelectionAnchor(start, end));
  commentInput.focus();
}

function debounce(fn, ms) {
  var timer;
  return function () {
    clearTimeout(timer);
    timer = setTimeout(fn, ms);
  };
}

function looksLikeMarkdown(text) {
  return /^(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|```)/m.test(text);
}

function inlineToMarkdown(node) {
  var result = '';
  node.childNodes.forEach(function (child) {
    if (child.nodeType === Node.TEXT_NODE) {
      result += child.textContent;
      return;
    }
    if (child.nodeType !== Node.ELEMENT_NODE) {
      return;
    }
    var tag = child.tagName.toLowerCase();
    var inner = inlineToMarkdown(child);
    if (tag === 'strong' || tag === 'b') {
      result += '**' + inner + '**';
    } else if (tag === 'em' || tag === 'i') {
      result += '*' + inner + '*';
    } else if (tag === 'code') {
      result += '`' + inner + '`';
    } else if (tag === 'a') {
      var href = child.getAttribute('href') || '';
      result += href ? '[' + inner + '](' + href + ')' : inner;
    } else if (tag === 'br') {
      result += '\n';
    } else {
      result += inner;
    }
  });
  return result;
}

function directElements(node, tagName) {
  var items = [];
  node.childNodes.forEach(function (child) {
    if (child.nodeType === Node.ELEMENT_NODE && child.tagName.toLowerCase() === tagName) {
      items.push(child);
    }
  });
  return items;
}

function indentMarkdown(text, spaces) {
  var pad = new Array(spaces + 1).join(' ');
  return text.split('\n').map(function (line) {
    return pad + line;
  }).join('\n');
}

function listToMarkdown(listNode, ordered) {
  var items = [];
  var index = 1;
  directElements(listNode, 'li').forEach(function (li) {
    var prefix = ordered ? index + '. ' : '- ';
    var clone = li.cloneNode(true);
    directElements(clone, 'ul').concat(directElements(clone, 'ol')).forEach(function (nested) {
      nested.remove();
    });
    var line = prefix + inlineToMarkdown(clone).trim();
    directElements(li, 'ul').forEach(function (nested) {
      line += '\n' + indentMarkdown(listToMarkdown(nested, false), 2);
    });
    directElements(li, 'ol').forEach(function (nested) {
      line += '\n' + indentMarkdown(listToMarkdown(nested, true), 2);
    });
    items.push(line);
    index += 1;
  });
  return items.join('\n');
}

function blockToMarkdown(node) {
  var parts = [];
  node.childNodes.forEach(function (child) {
    if (child.nodeType === Node.TEXT_NODE) {
      var text = child.textContent.replace(/\s+/g, ' ').trim();
      if (text) {
        parts.push(text);
      }
      return;
    }
    if (child.nodeType !== Node.ELEMENT_NODE) {
      return;
    }
    var tag = child.tagName.toLowerCase();
    if (tag === 'p' || tag === 'div') {
      parts.push(inlineToMarkdown(child).trim());
    } else if (tag === 'br') {
      parts.push('');
    } else if (/^h[1-6]$/.test(tag)) {
      var level = parseInt(tag.charAt(1), 10);
      parts.push(new Array(level + 1).join('#') + ' ' + inlineToMarkdown(child).trim());
    } else if (tag === 'ul') {
      parts.push(listToMarkdown(child, false));
    } else if (tag === 'ol') {
      parts.push(listToMarkdown(child, true));
    } else if (tag === 'blockquote') {
      parts.push(blockToMarkdown(child).trim().split('\n').map(function (line) {
        return '> ' + line;
      }).join('\n'));
    } else if (tag === 'pre') {
      parts.push('```\n' + child.textContent.replace(/\r\n/g, '\n').trim() + '\n```');
    } else if (tag === 'li') {
      parts.push(inlineToMarkdown(child).trim());
    } else {
      parts.push(blockToMarkdown(child));
    }
  });
  return parts.filter(function (part) {
    return part !== '';
  }).join('\n\n');
}

function htmlToMarkdown(html) {
  if (!html || !html.trim()) {
    return '';
  }
  var container = document.createElement('div');
  container.innerHTML = html;
  return blockToMarkdown(container).replace(/\n{3,}/g, '\n\n').trim();
}

function insertTextAtSelection(textarea, text) {
  var start = textarea.selectionStart;
  var end = textarea.selectionEnd;
  var before = textarea.value.substring(0, start);
  var after = textarea.value.substring(end);
  textarea.value = before + text + after;
  var pos = start + text.length;
  textarea.setSelectionRange(pos, pos);
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
}

function getPasteMarkdown(event) {
  var clipboard = event.clipboardData;
  if (!clipboard) {
    return null;
  }
  var plain = clipboard.getData('text/plain').replace(/\r\n/g, '\n');
  var html = clipboard.getData('text/html');
  if (plain && looksLikeMarkdown(plain)) {
    return plain;
  }
  if (html && html.trim()) {
    var md = htmlToMarkdown(html);
    if (md) {
      return md;
    }
  }
  return null;
}

function handleMarkdownPaste(event) {
  var text = getPasteMarkdown(event);
  if (!text) {
    return;
  }
  event.preventDefault();
  insertTextAtSelection(event.target, text);
  syncDraftClearBtn();
}

function handleSelection() {
  requestAnimationFrame(showCommentPopup);
}

var repositionPopup = debounce(function () {
  if (!commentPopup.hidden && currentSelection) {
    positionCommentPopup(getSelectionAnchor(currentSelection.start, currentSelection.end));
  }
}, 80);

function clearCommentsDrawer() {
  commentsList.innerHTML = '';
  const empty = document.createElement('p');
  empty.className = 'drawer__empty';
  empty.textContent = 'Brak komentarzy. Zaznacz fragment w buforze.';
  commentsList.appendChild(empty);
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

function clearDraftSelection() {
  const pos = draftInput.selectionEnd;
  draftInput.setSelectionRange(pos, pos);
}

async function sendComment() {
  if (!currentSelection) {
    return;
  }

  const selectionText = currentSelection.text;
  const selectionLabel = currentSelection.label || selectionText;
  const commentText = commentInput.value.trim();
  if (!commentText) {
    commentInput.focus();
    return;
  }

  const text = draftInput.value.trim();
  const payload = Object.assign({
    comment: commentText,
    selection: selectionText,
  }, getWytycznePayload());

  if (currentDraftFile) {
    payload.file = currentDraftFile;
  }

  if (text) {
    payload.text = text;
  } else if (!currentDraftFile) {
    setStatus('[ERR] buffer empty // brak tekstu do utworzenia draftu', 'error');
    return;
  }

  commentSendBtn.disabled = true;

  try {
    let response = await fetch(COMMENT_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (response.status === 404 && payload.file && text) {
      currentDraftFile = null;
      delete payload.file;
      response = await fetch(COMMENT_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
    }

    if (!response.ok) {
      const errData = await response.json().catch(function () {
        return {};
      });
      throw new Error(errData.error || 'HTTP ' + response.status);
    }

    const data = await response.json();
    currentDraftFile = data.file;
    setDraftPath(data.draft_path);
    if (data.created) {
      setStatus('[OK] draft + comment // ' + data.file, 'success');
    }

    addCommentToDrawer(selectionLabel, commentText);
    commentInput.value = '';
    clearDraftSelection();
    hideCommentPopup();
    draftInput.focus();
  } catch (err) {
    setStatus('[ERR] comment uplink failed // ' + err.message, 'error');
  } finally {
    commentSendBtn.disabled = false;
  }
}

sendBtn.addEventListener('click', sendDraft);
aiBtn.addEventListener('click', sendAi);

if (draftClearBtn) {
  draftClearBtn.addEventListener('click', clearDraftBuffer);
}

draftInput.addEventListener('input', syncDraftClearBtn);
draftInput.addEventListener('paste', handleMarkdownPaste);
if (wytyczneInput) {
  wytyczneInput.addEventListener('paste', handleMarkdownPaste);
}
draftInput.addEventListener('keydown', function (e) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault();
    sendDraft();
  }
});

draftInput.addEventListener('mouseup', handleSelection);
draftInput.addEventListener('select', handleSelection);
draftInput.addEventListener('keyup', function (e) {
  if (e.ctrlKey && (e.key === 'a' || e.key === 'A')) {
    handleSelection();
    return;
  }
  if (e.shiftKey || e.key === 'Shift' || e.key.startsWith('Arrow')) {
    handleSelection();
  }
});

draftInput.addEventListener('scroll', repositionPopup);

commentSendBtn.addEventListener('click', sendComment);

commentInput.addEventListener('keydown', function (e) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault();
    e.stopPropagation();
    sendComment();
    return;
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

window.addEventListener('resize', repositionPopup);

syncDraftClearBtn();
