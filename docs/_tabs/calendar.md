---
layout: page
title: 日历
icon: fas fa-calendar-days
order: 1
---

<!-- 月历浏览全部简报:已读变灰(与简报页共享 localStorage 日期集),复刻自 auto-trend。
     内联脚本不得使用 // 行注释:Chirpy compress 把整个文档压成一行,行注释会吞掉后续代码。 -->
<script>
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

<script src="{{ '/assets/js/calendar.js' | relative_url }}" defer></script>
