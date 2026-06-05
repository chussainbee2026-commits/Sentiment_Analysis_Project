// ── Current mode: 'single' or 'multi' ──
let currentMode = 'single';

// ── Character counter ──
const ta = document.getElementById('review_text');
ta.addEventListener('input', () => {
  document.getElementById('char-count').textContent = ta.value.length;
});

// ── Switch between Single and Bulk mode ──
function setMode(mode) {
  currentMode = mode;

  // Toggle button styles
  document.getElementById('btn-single').classList.toggle('active', mode === 'single');
  document.getElementById('btn-multi').classList.toggle('active', mode === 'multi');

  // Update hint text
  const hints = {
    single: 'Analyze one review at a time',
    multi:  'Paste one review per line — get an overall product verdict'
  };
  document.getElementById('mode-hint').textContent = hints[mode];

  // Update label and placeholder
  const labels = {
    single: 'Enter your review:',
    multi:  'Paste all reviews (one review per line):'
  };
  const placeholders = {
    single: 'e.g. This product is amazing! Arrived quickly and works perfectly.',
    multi:  'Paste each review on a new line, e.g.\nGreat product, very happy!\nBroke after one week, terrible quality.\nDelivery was fine, nothing special.'
  };
  document.getElementById('input-label').textContent    = labels[mode];
  document.getElementById('review_text').placeholder    = placeholders[mode];
  document.getElementById('review_text').rows           = mode === 'multi' ? 8 : 5;

  // Toggle sample cards
  document.querySelectorAll('.single-sample').forEach(el =>
    el.classList.toggle('hidden', mode === 'multi'));
  document.querySelectorAll('.bulk-sample').forEach(el =>
    el.classList.toggle('hidden', mode === 'single'));

  // Update samples title
  document.getElementById('samples-title').textContent =
    mode === 'single' ? '📌 Try a sample review' : '📌 Try a bulk sample';

  // Clear results
  clearAll();
}

// ── Main analyze dispatcher ──
function analyze() {
  if (currentMode === 'single') analyzeSingle();
  else analyzeMulti();
}

// ══════════════════════════════════════════
//  SINGLE REVIEW ANALYSIS
// ══════════════════════════════════════════
async function analyzeSingle() {
  const text = ta.value.trim();
  if (!text) { showError('Please enter a review first.'); return; }

  hideAll();
  show('loading');

  try {
    const form = new FormData();
    form.append('review_text', text);
    const res  = await fetch('/analyze', { method: 'POST', body: form });
    const data = await res.json();
    hide('loading');
    if (data.error) { showError(data.error); return; }
    displaySingle(data);
  } catch (e) {
    hide('loading');
    showError('Could not connect. Is Flask running?');
  }
}

function displaySingle(data) {
  const card = document.getElementById('result-single');
  card.className = 'card result ' + data.final_color;
  show('result-single');

  document.getElementById('result-emoji').textContent = data.final_emoji;
  const lbl = document.getElementById('result-label');
  lbl.textContent = data.final_label;
  lbl.className   = data.final_color;

  document.getElementById('vader-score').textContent = data.vader.compound_score;
  document.getElementById('tb-score').textContent    = data.textblob.polarity;

  setTimeout(() => {
    setBar('pos', Math.round(data.vader.positive_score * 100));
    setBar('neg', Math.round(data.vader.negative_score * 100));
    setBar('neu', Math.round(data.vader.neutral_score  * 100));
  }, 80);

  card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ══════════════════════════════════════════
//  BULK / PRODUCT REVIEW ANALYSIS
// ══════════════════════════════════════════
async function analyzeMulti() {
  const raw = ta.value.trim();
  if (!raw) { showError('Please paste at least one review.'); return; }

  // Split by newline — each non-empty line = one review
  const reviews = raw.split('\n').map(r => r.trim()).filter(r => r.length > 0);

  if (reviews.length < 2) {
    showError('Please paste at least 2 reviews (one per line) for bulk analysis.');
    return;
  }

  hideAll();
  show('loading');
  document.getElementById('loading-text').textContent =
    `Analyzing ${reviews.length} reviews...`;

  try {
    // Send all reviews to the backend bulk endpoint
    const res  = await fetch('/analyze-bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviews })
    });
    const data = await res.json();
    hide('loading');
    if (data.error) { showError(data.error); return; }
    displayBulk(data);
  } catch (e) {
    hide('loading');
    showError('Could not connect. Is Flask running?');
  }
}

function displayBulk(data) {
  // ── Overall card ──
  const overall = document.getElementById('overall-card');
  overall.className = 'card result ' + data.overall_color;

  document.getElementById('overall-emoji').textContent = data.overall_emoji;
  const lbl = document.getElementById('overall-label');
  lbl.textContent = data.overall_label;
  lbl.className   = data.overall_color;
  document.getElementById('overall-desc').textContent = data.overall_desc;

  // Count chips
  document.getElementById('count-total').textContent = data.total;
  document.getElementById('count-pos').textContent   = data.count_pos;
  document.getElementById('count-neg').textContent   = data.count_neg;
  document.getElementById('count-neu').textContent   = data.count_neu;

  // Aggregate bars
  setTimeout(() => {
    setOvBar('pos', data.pct_pos);
    setOvBar('neg', data.pct_neg);
    setOvBar('neu', data.pct_neu);
  }, 80);

  // ── Per-review breakdown ──
  const list = document.getElementById('breakdown-list');
  list.innerHTML = '';
  data.results.forEach((r, i) => {
    const cls   = { Positive: 'bd-pos', Negative: 'bd-neg', Neutral: 'bd-neu' }[r.label];
    const emoji = { Positive: '😊', Negative: '😞', Neutral: '😐' }[r.label];
    const short = r.text.length > 120 ? r.text.slice(0, 120) + '…' : r.text;
    list.innerHTML += `
      <div class="breakdown-item">
        <span class="breakdown-num">#${i + 1}</span>
        <span class="breakdown-text">${short}</span>
        <span class="breakdown-badge ${cls}">${emoji} ${r.label}</span>
      </div>`;
  });

  show('result-bulk');
  document.getElementById('result-bulk').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Bar helpers ──
function setBar(name, pct) {
  document.getElementById('bar-' + name).style.width    = pct + '%';
  document.getElementById('pct-' + name).textContent    = pct + '%';
}
function setOvBar(name, pct) {
  document.getElementById('ov-bar-' + name).style.width = pct + '%';
  document.getElementById('ov-pct-' + name).textContent = Math.round(pct) + '%';
}

// ── Load single sample ──
function loadSample(el) {
  ta.value = el.querySelector('p').textContent;
  document.getElementById('char-count').textContent = ta.value.length;
  ta.scrollIntoView({ behavior: 'smooth', block: 'center' });
  ta.style.borderColor = '#7c3aed';
  setTimeout(() => { ta.style.borderColor = ''; }, 1200);
}

// ── Load bulk sample ──
function loadBulkSample() {
  const sample = [
    "Absolutely love this product! Works perfectly and arrived super fast. Would buy again.",
    "Terrible quality. Broke after just 3 days of use. Very disappointed.",
    "Decent product for the price. Does the job but nothing extraordinary.",
    "Amazing! Exceeded all my expectations. Best purchase I've made this year!",
    "Packaging was damaged and customer service took forever to respond.",
    "It's okay. Not as good as described but not terrible either.",
    "Five stars! Exactly what I needed. Perfect fit and great build quality.",
    "Do not buy! Stopped working after one week and return process is a nightmare."
  ].join('\n');

  ta.value = sample;
  document.getElementById('char-count').textContent = ta.value.length;
  ta.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ── Clear all ──
function clearAll() {
  ta.value = '';
  document.getElementById('char-count').textContent = '0';
  hideAll();
}

// ── UI helpers ──
function show(id)  { document.getElementById(id).classList.remove('hidden'); }
function hide(id)  { document.getElementById(id).classList.add('hidden'); }
function hideAll() {
  hide('result-single');
  hide('result-bulk');
  hide('loading');
  hide('error-msg');
}
function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg;
  show('error-msg');
}

// ── Ctrl+Enter shortcut ──
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') analyze();
});