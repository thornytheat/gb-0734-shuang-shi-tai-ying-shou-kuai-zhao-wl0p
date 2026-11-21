const dayMs = 86400000;
const localClock = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'UTC', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', second: '2-digit',
});

export function localInstant(stamp) {
  const clock = localClock.format(new Date(Date.parse(stamp) + 8 * 3600000)).replace(' ', 'T');
  const fraction = stamp.match(/\.(\d{1,6})(?:Z|[+-]\d\d:\d\d)$/)?.[1].replace(/0+$/, '');
  return fraction ? `${clock}.${fraction}` : clock;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

export function axis(root, kind, marks, selected, pick) {
  if (!selected) return;
  const business = kind === 'effective';
  const caption = business ? '业务有效日' : '知悉时间';
  const label = (stamp) => business ? stamp : localInstant(stamp).replace('T', ' ');
  const current = Date.parse(selected);
  const positions = marks.map((mark) => Date.parse(mark.at));
  const times = positions.concat(current);
  const endToEnd = Math.max(...times) - Math.min(...times);
  const edge = Math.max(endToEnd * 0.027, business ? dayMs : 3600000);
  const start = Math.min(...times) - edge;
  const end = Math.max(...times) + edge;
  const percent = (time) => `${100 * (time - start) / (end - start)}%`;

  const heading = element('div', 'axis-label');
  const control = element('label', 'axis-picker');
  control.append(element('span', '', caption));
  const select = element('select');
  select.setAttribute('aria-label', `选取${caption}刻度`);
  select.append(new Option('选取刻度', ''));
  heading.append(control, element('strong', '', label(selected)));
  control.append(select);
  const track = element('div', 'axis-track');
  const cut = element('span', 'axis-cut');
  cut.setAttribute('aria-hidden', 'true');
  cut.style.setProperty('--at', percent(current));
  track.append(cut);
  marks.forEach((mark, index) => {
    const marker = element('button', 'axis-mark');
    const text = `${label(mark.at)} · ${mark.count} 条`;
    marker.type = 'button';
    marker.title = text;
    marker.setAttribute('aria-label', `取${caption} ${text}`);
    marker.dataset.after = String(business ? mark.at > selected : positions[index] > current ||
      (positions[index] === current && localInstant(mark.at) > localInstant(selected)));
    marker.style.setProperty('--at', percent(positions[index]));
    marker.addEventListener('click', () => pick(mark.at));
    track.append(marker);
    select.append(new Option(text, mark.at));
  });
  select.disabled = marks.length === 0;
  select.addEventListener('change', () => { if (select.value) pick(select.value); });
  const ticks = element('div', 'ticks');
  ticks.setAttribute('aria-hidden', 'true');
  const unit = endToEnd < dayMs * 3 && !business ? 16 : 10;
  for (let i = 0; i <= 4; i += 1) {
    const date = new Date(start + (end - start) * i / 4).toISOString();
    const tick = element('span', 'axis-tick', (business ? date : localInstant(date)).slice(5, unit).replace('T', ' '));
    tick.style.setProperty('--at', `${i * 25}%`);
    ticks.append(tick);
  }
  root.replaceChildren(heading, track, ticks);
}
