---
layout: page
title: 日历
icon: fas fa-calendar-days
order: 1
permalink: /calendar/
---

<div class="calendar-card">
  <div class="calendar-header">
    <button class="cal-nav-btn" id="cal-prev" aria-label="上一月">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M11.25 13.5L6.75 9L11.25 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
    <div class="cal-title">
      <select id="cal-year" class="cal-select"></select>
      <span class="cal-sep">年</span>
      <select id="cal-month" class="cal-select"></select>
      <span class="cal-sep">月</span>
    </div>
    <button class="cal-nav-btn" id="cal-next" aria-label="下一月">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M6.75 13.5L11.25 9L6.75 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>
  </div>
  <div class="calendar-weekdays">
    <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
  </div>
  <div class="calendar-grid" id="cal-grid"></div>
  <div class="calendar-legend">
    <span class="legend-dot"></span><span>有日报</span>
    <span class="legend-dot legend-today"></span><span>今天</span>
  </div>
</div>

<style>
.calendar-card { max-width: 460px; background: var(--chip-bg, #f8f9fa); border: 1px solid var(--main-border, #dee2e6); border-radius: 16px; padding: 28px; box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 4px 16px rgba(0,0,0,.04); }
.calendar-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.cal-title { display: flex; align-items: center; gap: 6px; font-size: 17px; font-weight: 600; }
.cal-select { font: inherit; font-weight: 600; background: var(--chip-bg, #f1f3f5); border: 1px solid transparent; border-radius: 10px; padding: 5px 10px; cursor: pointer; outline: none; }
.cal-select:focus { border-color: var(--btn-border, #2a8df1); }
.cal-sep { user-select: none; opacity: .6; }
.cal-nav-btn { display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border: none; border-radius: 10px; background: transparent; color: var(--text-muted, #6c757d); cursor: pointer; }
.cal-nav-btn:hover { background: var(--chip-bg, #f1f3f5); }
.calendar-weekdays { display: grid; grid-template-columns: repeat(7,1fr); text-align: center; margin-bottom: 10px; }
.calendar-weekdays span { font-size: 11px; font-weight: 600; opacity: .6; padding: 6px 0; }
.calendar-grid { display: grid; grid-template-columns: repeat(7,1fr); gap: 4px; }
.cal-day { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; font-size: 15px; border-radius: 10px; text-decoration: none; transition: all .15s; position: relative; }
.cal-day.in-month { opacity: .85; }
.cal-day.has-report { color: #fff; background: var(--btn-bg, #2a8df1); font-weight: 600; box-shadow: 0 1px 3px rgba(42,141,241,.25); }
.cal-day.has-report:hover { transform: scale(1.08); filter: brightness(.92); }
.cal-day.today { box-shadow: inset 0 0 0 2px var(--btn-bg, #2a8df1); }
.cal-day.empty { visibility: hidden; }
.calendar-legend { display: flex; align-items: center; gap: 8px; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--main-border, #dee2e6); font-size: 12px; opacity: .7; }
.legend-dot { width: 10px; height: 10px; border-radius: 5px; background: var(--btn-bg, #2a8df1); display: inline-block; }
.legend-dot.legend-today { background: transparent; box-shadow: inset 0 0 0 2px var(--btn-bg, #2a8df1); }
</style>

<script>
(function() {
  var reportSet = new Set({% assign posts = site.posts | sort: 'date' | reverse %}[{% for p in site.posts %}"{{ p.date | date: '%Y-%m-%d' }}"{% unless forloop.last %},{% endunless %}{% endfor %}]);
  var grid = document.getElementById('cal-grid');
  var yearSel = document.getElementById('cal-year');
  var monthSel = document.getElementById('cal-month');
  var now = new Date();
  var todayStr = now.toISOString().slice(0,10);
  for (var y = 2026; y <= now.getFullYear()+1; y++) { var o=document.createElement('option'); o.value=y; o.textContent=y; yearSel.appendChild(o); }
  for (var m = 1; m <= 12; m++) { var o=document.createElement('option'); o.value=m-1; o.textContent=m; monthSel.appendChild(o); }
  yearSel.value = now.getFullYear(); monthSel.value = now.getMonth();
  function reportUrl(d) { return '{{ "/posts/" | relative_url }}' + d.replace(/-/g,'/') + '/daily-briefing/'; }
  function render() {
    var y = parseInt(yearSel.value), m = parseInt(monthSel.value);
    grid.innerHTML = '';
    var startDow = (new Date(y, m, 1).getDay() + 6) % 7;
    var dim = new Date(y, m+1, 0).getDate();
    for (var i = 0; i < startDow; i++) { var c = document.createElement('span'); c.className='cal-day empty'; grid.appendChild(c); }
    for (var d = 1; d <= dim; d++) {
      var ds = y + '-' + String(m+1).padStart(2,'0') + '-' + String(d).padStart(2,'0');
      var cell;
      if (reportSet.has(ds)) { cell = document.createElement('a'); cell.href = reportUrl(ds); cell.className='cal-day in-month has-report'; }
      else { cell = document.createElement('span'); cell.className='cal-day in-month'; }
      cell.textContent = d;
      if (ds === todayStr) cell.classList.add('today');
      grid.appendChild(cell);
    }
  }
  yearSel.addEventListener('change', render); monthSel.addEventListener('change', render);
  document.getElementById('cal-prev').onclick = function(){ var m=+monthSel.value,y=+yearSel.value; if(m===0){monthSel.value=11;yearSel.value=y-1;}else{monthSel.value=m-1;} render(); };
  document.getElementById('cal-next').onclick = function(){ var m=+monthSel.value,y=+yearSel.value; if(m===11){monthSel.value=0;yearSel.value=y+1;}else{monthSel.value=m+1;} render(); };
  render();
})();
</script>
