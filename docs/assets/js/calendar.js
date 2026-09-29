// 日历页:月历浏览全部简报,已读变灰(与简报页共享 localStorage 日期集)。
// 数据来源:页面内联注入的 window.__briefs([{date, url}]);外部文件不经 Chirpy compress。
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
  if (!grid || !yearSel || !monthSel) return;

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

  // 默认定位到最新一期简报所在月份(而非当前月,避免空月);无简报回退当前月
  var latest = (window.__briefs && window.__briefs[0] && window.__briefs[0].date) ||
    cur.getFullYear() + '-' + String(cur.getMonth() + 1).padStart(2, '0') + '-01';
  yearSel.value = latest.slice(0, 4);
  monthSel.value = String(+latest.slice(5, 7) - 1);

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
