---
layout: page
title: 日历
icon: fas fa-calendar-days
order: 1
---

<!-- 月历浏览全部简报:已读变灰(与简报页共享 localStorage 日期集),复刻自 auto-trend。 -->
<script>
  // 简报日期与 URL 注入(来自 site.posts,url 已含 baseurl)
  window.__briefs = [
    {%- for p in site.posts %}
    { date: '{{ p.date | date: "%Y-%m-%d" }}', url: '{{ p.url | relative_url }}' }{% unless forloop.last %},{% endunless %}
    {%- endfor %}
  ];
</script>

<div class="cal-card">
  <div class="cal-header">
    <button class="cal-nav" id="cal-prev" type="button" aria-label="上一月">‹</button>
    <div class="cal-title">
      <select id="cal-year" class="cal-select" aria-label="年"></select> 年
      <select id="cal-month" class="cal-select" aria-label="月"></select> 月
    </div>
    <button class="cal-nav" id="cal-next" type="button" aria-label="下一月">›</button>
  </div>
  <div class="cal-weekdays">
    <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
  </div>
  <div class="cal-grid" id="cal-grid"></div>
  <div class="cal-legend">
    <span class="cal-dot"></span><span>未读</span>
    <span class="cal-dot is-read"></span><span>已读</span>
    <button class="cal-mark-all" id="cal-mark-all" type="button">全部标为已读</button>
  </div>
</div>

<style>
  /* 日历卡片:配色用 Chirpy 变量随明暗模式自适应 */
  .cal-card {
    max-width: 420px; margin: 1.5rem 0 2rem; padding: 1.25rem 1.5rem;
    background: var(--card-bg); border: 1px solid var(--main-border-color); border-radius: 1rem;
  }
  .cal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .cal-title { display: flex; align-items: center; gap: .25rem; font-weight: 600; }
  .cal-select {
    font: inherit; font-weight: 600; color: var(--text-color);
    background: transparent; border: 1px solid var(--main-border-color);
    border-radius: .5rem; padding: .1rem .4rem; cursor: pointer;
  }
  .cal-nav {
    width: 2rem; height: 2rem; border: none; border-radius: .5rem;
    background: transparent; color: var(--text-muted-color);
    font-size: 1.2rem; cursor: pointer;
  }
  .cal-nav:hover { color: var(--text-color); box-shadow: 0 0 0 1px var(--main-border-color); }
  .cal-weekdays {
    display: grid; grid-template-columns: repeat(7, 1fr); text-align: center;
    font-size: .72rem; color: var(--text-muted-color); margin-bottom: .4rem;
  }
  .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: .2rem; }
  .cal-day {
    aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
    border-radius: .5rem; font-size: .9rem; color: var(--text-muted-color);
  }
  .cal-day.in-month { color: var(--text-color); }
  .cal-day.has-post { background: var(--link-color); color: var(--card-bg); font-weight: 600; cursor: pointer; }
  .cal-day.has-post:hover { text-decoration: none; filter: brightness(1.1); }
  .cal-day.has-post.is-read { background: transparent; color: var(--text-muted-color); font-weight: 400; box-shadow: inset 0 0 0 1px var(--main-border-color); }
  .cal-day.today { box-shadow: inset 0 0 0 2px var(--link-color); }
  .cal-day.has-post.today:not(.is-read) { box-shadow: inset 0 0 0 2px var(--card-bg), 0 0 0 2px var(--link-color); }
  .cal-day.empty { visibility: hidden; }
  .cal-legend {
    display: flex; align-items: center; gap: .4rem; margin-top: 1rem; padding-top: 1rem;
    border-top: 1px solid var(--main-border-color); font-size: .8rem; color: var(--text-muted-color);
  }
  .cal-dot { width: .6rem; height: .6rem; border-radius: 50%; background: var(--link-color); flex-shrink: 0; }
  .cal-dot.is-read { background: transparent; box-shadow: inset 0 0 0 1px var(--main-border-color); }
  .cal-mark-all {
    margin-left: auto; font: inherit; font-size: .8rem; cursor: pointer;
    color: var(--text-muted-color); background: transparent;
    border: 1px solid var(--main-border-color); border-radius: 980px; padding: .15rem .6rem;
  }
  .cal-mark-all:hover { color: var(--link-color); border-color: var(--link-color); }
</style>

<script>
(function () {
  'use strict';

  var STORE_KEY = 'rss-reader.read-dates'; // 与简报页共享的已读日期集
  var briefMap = {}; // 日期 → 简报 URL
  var years = [];
  (window.__briefs || []).forEach(function (b) {
    briefMap[b.date] = b.url;
    var y = b.date.slice(0, 4);
    if (years.indexOf(y) < 0) years.push(y);
  });
  years.sort();

  var grid = document.getElementById('cal-grid');
  var yearSel = document.getElementById('cal-year');
  var monthSel = document.getElementById('cal-month');

  // 年份选项从实际简报推导(无简报时回退当前年);月份固定 1-12
  var cur = new Date();
  if (!years.length) years.push(String(cur.getFullYear()));
  years.forEach(function (y) {
    var opt = document.createElement('option');
    opt.value = y;
    opt.textContent = y;
    yearSel.appendChild(opt);
  });
  for (var m = 1; m <= 12; m++) {
    var opt = document.createElement('option');
    opt.value = m - 1;
    opt.textContent = m;
    monthSel.appendChild(opt);
  }
  yearSel.value = +years[0] <= cur.getFullYear() && cur.getFullYear() <= +years[years.length - 1]
    ? String(cur.getFullYear()) : years[years.length - 1];
  monthSel.value = cur.getMonth();

  /** 读取已读日期集;存储损坏回退空集。 */
  function load() {
    try {
      var arr = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
      return new Set(Array.isArray(arr) ? arr : []);
    } catch (e) { return new Set(); }
  }

  /** 写回已读日期集,失败静默。 */
  function save(set) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(Array.from(set))); } catch (e) { /* 静默 */ }
  }

  function todayStr() {
    var t = new Date();
    return t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0');
  }

  /** 渲染当前年月网格:周一为首,有简报的天为链接,已读变灰,今日描边。 */
  function render() {
    var year = +yearSel.value;
    var month = +monthSel.value;
    var readSet = load();
    var today = todayStr();
    grid.innerHTML = '';

    var startDow = (new Date(year, month, 1).getDay() + 6) % 7; // 周一为首的偏移
    var daysInMonth = new Date(year, month + 1, 0).getDate();

    for (var i = 0; i < startDow; i++) {
      var pad = document.createElement('span');
      pad.className = 'cal-day empty';
      grid.appendChild(pad);
    }

    var _loop = function (d) {
      var dateStr = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      var cell = document.createElement(briefMap[dateStr] ? 'a' : 'span');
      if (briefMap[dateStr]) {
        cell.href = briefMap[dateStr];
        cell.className = 'cal-day in-month has-post';
        if (readSet.has(dateStr)) cell.classList.add('is-read');
      } else {
        cell.className = 'cal-day in-month';
      }
      cell.textContent = d;
      if (dateStr === today) cell.classList.add('today');
      grid.appendChild(cell);
    };
    for (var d = 1; d <= daysInMonth; d++) _loop(d);
  }

  function shiftMonth(delta) {
    var m = +monthSel.value + delta;
    if (m < 0) { m = 11; yearSel.value = +yearSel.value - 1; }
    else if (m > 11) { m = 0; yearSel.value = +yearSel.value + 1; }
    monthSel.value = m;
    render();
  }

  document.getElementById('cal-prev').addEventListener('click', function () { shiftMonth(-1); });
  document.getElementById('cal-next').addEventListener('click', function () { shiftMonth(1); });
  yearSel.addEventListener('change', render);
  monthSel.addEventListener('change', render);

  // 全部标为已读:所有简报日期全量写入已读集
  document.getElementById('cal-mark-all').addEventListener('click', function () {
    var set = load();
    Object.keys(briefMap).forEach(function (date) { set.add(date); });
    save(set);
    render();
  });

  render();
})();
</script>
