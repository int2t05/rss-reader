// 简报页已读标记(日期为键):与日历页共享 localStorage 已读日期集。
// 外部文件不经 Chirpy compress 压缩,可安全使用行注释。
(function () {
  'use strict';

  var STORE_KEY = 'rss-reader.read-dates'; // 已读日期集(YYYY-MM-DD 数组),与日历页共享
  var PAGE_RE = /\/posts\/(\d{4})\/(\d{2})\/(\d{2})\/daily-briefing\/?$/;

  /** 读取已读日期集;存储损坏回退空集,绝不阻断页面。 */
  function load() {
    try {
      var arr = JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
      return new Set(Array.isArray(arr) ? arr : []);
    } catch (e) { return new Set(); }
  }

  /** 写回已读日期集,失败静默(隐私模式不阻塞交互)。 */
  function save(set) {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(Array.from(set))); } catch (e) { /* 静默 */ }
  }

  /** 装配:简报页正文前插「标记已读」按钮,日期取自 URL,h1 签名双保险。 */
  function init() {
    var m = PAGE_RE.exec(location.pathname);
    var content = document.querySelector('.content');
    var h1 = content && content.querySelector('h1');
    if (!m || !h1 || !/^每日简报 · \d{4}-\d{2}-\d{2}$/.test(h1.textContent.trim())) return;

    var date = m[1] + '-' + m[2] + '-' + m[3];

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'brief-read-btn';
    btn.addEventListener('click', function () {
      var set = load();
      if (set.has(date)) { set.delete(date); } else { set.add(date); }
      save(set);
      paint(set.has(date));
    });

    var row = document.createElement('div');
    row.className = 'brief-read-row';
    row.appendChild(btn);
    content.insertBefore(row, content.firstChild);

    function paint(isRead) {
      btn.textContent = isRead ? '已读 ✓' : '标记已读';
      btn.classList.toggle('is-read', isRead);
    }
    paint(load().has(date));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
