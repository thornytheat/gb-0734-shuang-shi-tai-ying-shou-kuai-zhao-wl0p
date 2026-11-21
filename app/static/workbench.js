import { axis, localInstant } from './axis.js';
import * as view from './views.js';

const { $ } = view;
const state = {source: null, page: 'snapshot', cut: null, runs: [], selected: null, token: 0, busy: false, exact: {}};
const pages = [...document.querySelectorAll('[data-page]')];
const links = [...document.querySelectorAll('nav a')];
const form = $('cuts');
const zone = document.body.dataset.zone;

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `请求失败 · HTTP ${response.status}`);
  }
  return response.json();
}

function feedback(message = '', level = '') {
  const target = $('feedback');
  target.hidden = !message;
  target.textContent = message;
  target.dataset.level = level;
  $('status').parentElement.dataset.level = level;
}

function controls() {
  $('sample').disabled = state.busy;
  $('archive-run').disabled = state.busy || !state.source;
  $('rerun').disabled = state.busy || !state.selected;
  $('upload').querySelector('button').disabled = state.busy;
  const link = $('export');
  if (state.selected) {
    link.href = `/api/archive/${state.selected.run_id}/export`;
    link.removeAttribute('aria-disabled');
  } else {
    link.removeAttribute('href');
    link.setAttribute('aria-disabled', 'true');
  }
}

function formCut() {
  const values = Object.fromEntries(new FormData(form));
  for (const name of ['open_known', 'known']) {
    const exact = state.exact[name];
    values[name] = exact?.value === values[name] ? exact.stamp : `${values[name]}${zone}`;
  }
  return values;
}

function setSelection(run) {
  state.selected = run;
  $('run-meta').textContent = run?.run_id.slice(0, 12) ?? '未归档';
  $('time-meta').textContent = run ? localInstant(run.generated_at).slice(0, 19).replace('T', ' ') : '—';
  controls();
  if (state.page === 'archive') view.history(state.runs, run, setSelection);
}

function pick(name, stamp) {
  const input = form.elements.namedItem(name);
  if (name === 'known') {
    input.value = localInstant(stamp).replace(/(\.\d{3})\d+$/, '$1');
    state.exact[name] = {value: input.value, stamp};
  } else {
    input.value = stamp;
  }
  form.requestSubmit();
}

function switchPage() {
  state.page = pages.some((page) => `#${page.dataset.page}` === location.hash) ? location.hash.slice(1) : 'snapshot';
  for (const section of pages) section.hidden = section.dataset.page !== state.page;
  for (const link of links) {
    if (link.hash.slice(1) === state.page) {
      $('crumb').textContent = link.textContent;
      link.setAttribute('aria-current', 'page');
    } else link.removeAttribute('aria-current');
  }
}

async function refresh() {
  if (!state.source || !state.cut) return;
  const token = ++state.token;
  const page = state.page;
  const cut = state.cut;
  const query = new URLSearchParams({source_id: state.source.source_id, ...cut});
  $('status').textContent = '正在读取截面';
  try {
    if (page === 'snapshot') {
      const [data, age] = await Promise.all([request(`/api/snapshot?${query}`), request(`/api/aging?${query}`)]);
      if (token !== state.token) return;
      view.snapshot(data, age);
      axis($('axis-effective'), 'effective', state.source.axis.effective, data.cut.effective, (stamp) => pick('effective', stamp));
      axis($('axis-known'), 'known', state.source.axis.known, data.cut.known, (stamp) => pick('known', stamp));
    } else if (page === 'intake') {
      view.intake(state.source);
    } else {
      const data = await request(`/api/${page}?${query}`);
      if (token !== state.token) return;
      if (page === 'archive') {
        state.runs = data.runs;
        view.history(state.runs, state.selected, setSelection);
      } else {
        view[page](data);
      }
    }
    $('status').textContent = `${$('crumb').textContent} · 已更新`;
  } catch (error) {
    if (token === state.token) {
      feedback(error.message, 'bad');
      $('status').textContent = '读取失败';
    }
  }
}

async function act(operation) {
  if (state.busy) return;
  state.busy = true;
  feedback();
  $('status').textContent = '正在处理';
  controls();
  try {
    await operation();
  } catch (error) {
    feedback(error.message, 'bad');
    $('status').textContent = '操作失败';
  } finally {
    state.busy = false;
    controls();
  }
}

function validate(cut) {
  if (cut.open_effective >= cut.effective || Date.parse(cut.open_known) > Date.parse(cut.known)) {
    feedback('请检查期间切点顺序', 'bad');
    return false;
  }
  return true;
}

async function setSource(source) {
  state.source = source;
  state.runs = [];
  setSelection(null);
  $('source-meta').textContent = source.source_id.slice(0, 12);
  await refresh();
}

async function loadSample() {
  await setSource(await request('/api/intake/sample'));
}

form.addEventListener('input', (event) => { delete state.exact[event.target.name]; });
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const cut = formCut();
  if (['backfill', 'bridge', 'archive'].includes(state.page) && !validate(cut)) return;
  feedback();
  state.cut = cut;
  $('heading-period').textContent = cut.open_effective < cut.effective ? `${cut.open_effective} → ${cut.effective}` : `有效日 ${cut.effective}`;
  setSelection(null);
  refresh();
});
$('sample').addEventListener('click', () => act(async () => {
  form.reset();
  state.exact = {};
  state.cut = formCut();
  $('heading-period').textContent = `${state.cut.open_effective} → ${state.cut.effective}`;
  await loadSample();
}));
$('upload').addEventListener('submit', (event) => {
  event.preventDefault();
  const upload = new FormData(event.currentTarget);
  act(async () => {
    const data = await request('/api/intake', {method: 'POST', body: upload});
    await setSource(data);
    feedback(`收件 ${data.counts.input} 条，隔离 ${data.counts.quarantine} 条`);
  });
});
$('bucket-filter').addEventListener('change', refresh);
$('archive-run').addEventListener('click', () => act(async () => {
  const cut = formCut();
  if (!form.reportValidity() || !validate(cut)) return;
  const data = await request('/api/archive', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...cut, source_id: state.source.source_id})});
  state.cut = cut;
  $('heading-period').textContent = cut.open_effective < cut.effective ? `${cut.open_effective} → ${cut.effective}` : `有效日 ${cut.effective}`;
  setSelection(data.manifest);
  await refresh();
  feedback(data.created ? '快照已归档' : '已复用同一归档');
}));
$('rerun').addEventListener('click', () => act(async () => {
  const data = await request(`/api/archive/${state.selected.run_id}/rerun`, {method: 'POST'});
  setSelection(data.manifest);
  refresh();
  feedback('重跑一致，归档批次号不变');
}));
window.addEventListener('hashchange', () => { switchPage(); feedback(); refresh(); });
switchPage();
state.cut = formCut();
act(loadSample);
