// Every hour of one year at one ERCOT hub, as a carpet plot: a column for each
// day and a row for each hour, colored by that hour's price. Hours priced
// above the shut-off turn yellow and hours below zero are blue. The grid is
// painted once at 365 by 24 pixels and scaled up without smoothing, so each
// hour stays a crisp block at any width.
(function () {
  'use strict';

  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DATA = window.ERCOT || window.ERCOT_2025;
  if (!DATA) return;
  var YEAR = DATA.year;
  var LEAP = (YEAR % 4 === 0 && YEAR % 100 !== 0) || YEAR % 400 === 0;
  // US daylight saving: starts the second Sunday of March, ends the first Sunday of November.
  function nthSunday(month, n) {
    var first = new Date(Date.UTC(YEAR, month, 1)).getUTCDay();
    return 1 + ((7 - first) % 7) + 7 * (n - 1);
  }
  var DST_START = nthSunday(2, 2);
  var DST_END = nthSunday(10, 1);
  var DAYS_IN_MONTH = [31, LEAP ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  var WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var DAYS = LEAP ? 366 : 365;
  var JAN_1_WEEKDAY = new Date(Date.UTC(YEAR, 0, 1)).getUTCDay();

  var monthOfDay = [];
  var dateOfDay = [];
  (function () {
    for (var m = 0; m < 12; m++) {
      for (var d = 1; d <= DAYS_IN_MONTH[m]; d++) { monthOfDay.push(m); dateOfDay.push(d); }
    }
  })();

  // The prices run hour by hour in Central Time. The spring daylight-saving
  // day loses its 2 a.m. hour, so that square is left empty, and the fall day
  // runs 1 a.m. twice, so those two hours are averaged into one.
  var grids = {};
  function grid(hub) {
    if (grids[hub]) return grids[hub];
    var prices = DATA.hubs[hub];
    var cells = new Float64Array(DAYS * 24);
    var i = 0;
    for (var day = 0; day < DAYS; day++) {
      var m = monthOfDay[day];
      var d = dateOfDay[day];
      for (var h = 0; h < 24; h++) {
        if (m === 2 && d === DST_START && h === 2) { cells[day * 24 + h] = NaN; continue; }
        var v = prices[i++];
        if (m === 10 && d === DST_END && h === 1) v = (v + prices[i++]) / 2;
        cells[day * 24 + h] = v;
      }
    }
    grids[hub] = cells;
    return cells;
  }

  // What a site would have saved at this hub by sitting out every hour priced
  // above the cap, per megawatt and as a share of running all year.
  function stats(hub, cap) {
    var prices = DATA.hubs[hub];
    var total = 0;
    var above = 0;
    var hours = 0;
    for (var i = 0; i < prices.length; i++) {
      total += prices[i];
      if (prices[i] > cap) { above += prices[i]; hours++; }
    }
    return { hours: hours, uptime: (prices.length - hours) / prices.length, cut: total ? above / total : 0, perMw: above };
  }

  function rgb(value) {
    var s = String(value).trim().replace('#', '');
    if (s.length === 3) s = s.replace(/(.)/g, '$1$1');
    var n = parseInt(s, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function mix(a, b, t) {
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  }

  function logT(p, lo, hi) {
    var t = (Math.log(p) - Math.log(lo)) / (Math.log(hi) - Math.log(lo));
    return t < 0 ? 0 : t > 1 ? 1 : t;
  }

  function money(v) {
    var s = '$' + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return v < 0 ? '−' + s : s;
  }

  function hourLabel(h) {
    if (h === 0) return 'midnight to 1 a.m.';
    if (h === 11) return '11 a.m. to noon';
    if (h === 12) return 'noon to 1 p.m.';
    if (h === 23) return '11 p.m. to midnight';
    var a = h % 12 || 12;
    var b = (h + 1) % 12 || 12;
    return a + ' to ' + b + (h < 12 ? ' a.m.' : ' p.m.');
  }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }

  function mount(root, options) {
    if (!root || !DATA || !DATA.hubs) return null;
    var state = { hub: options.hub || 'HB_WEST', cap: options.cap == null ? 100 : options.cap };
    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    root.textContent = '';
    var plot = el('div', 'hours__plot');
    var canvas = el('canvas', 'hours__canvas');
    canvas.setAttribute('aria-hidden', 'true');
    plot.appendChild(canvas);
    [[0, '12 a.m.'], [6, '6 a.m.'], [12, 'noon'], [18, '6 p.m.']].forEach(function (tick) {
      var label = el('span', 'hours__y', tick[1]);
      label.style.top = ((tick[0] + 0.5) / 24 * 100).toFixed(2) + '%';
      label.setAttribute('aria-hidden', 'true');
      plot.appendChild(label);
    });
    var tip = el('div', 'hours__tip');
    tip.hidden = true;
    plot.appendChild(tip);
    root.appendChild(plot);

    var axis = el('div', 'hours__x');
    axis.setAttribute('aria-hidden', 'true');
    var start = 0;
    MONTHS.forEach(function (name, m) {
      var label = el('span', '', name);
      label.style.left = (start / DAYS * 100).toFixed(2) + '%';
      axis.appendChild(label);
      start += DAYS_IN_MONTH[m];
    });
    root.appendChild(axis);

    var sheet = document.createElement('canvas');
    sheet.width = DAYS;
    sheet.height = 24;
    var sheetCtx = sheet.getContext('2d');
    var image = sheetCtx.createImageData(DAYS, 24);
    var ctx = canvas.getContext('2d');
    var colors = null;
    var shown = reduced ? DAYS : 0;

    function readColors() {
      var css = getComputedStyle(root);
      colors = {
        run0: rgb(css.getPropertyValue('--h-run-0')), run1: rgb(css.getPropertyValue('--h-run-1')),
        neg0: rgb(css.getPropertyValue('--h-neg-0')), neg1: rgb(css.getPropertyValue('--h-neg-1')),
        off0: rgb(css.getPropertyValue('--h-off-0')), off1: rgb(css.getPropertyValue('--h-off-1'))
      };
    }

    function colorFor(p, cap) {
      if (p < 0) return mix(colors.neg0, colors.neg1, Math.min(1, -p / 20));
      if (p > cap) return mix(colors.off0, colors.off1, logT(p, 60, 1500));
      return mix(colors.run0, colors.run1, logT(Math.max(p, 1), 8, 160));
    }

    function paint() {
      var cells = grid(state.hub);
      var px = image.data;
      for (var day = 0; day < DAYS; day++) {
        for (var h = 0; h < 24; h++) {
          var p = cells[day * 24 + h];
          var k = (h * DAYS + day) * 4;
          if (p !== p) { px[k + 3] = 0; continue; }
          var c = colorFor(p, state.cap);
          px[k] = c[0];
          px[k + 1] = c[1];
          px[k + 2] = c[2];
          px[k + 3] = 255;
        }
      }
      sheetCtx.putImageData(image, 0, 0);
      draw();
    }

    function draw() {
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      var n = Math.round(shown);
      if (n <= 0) return;
      ctx.drawImage(sheet, 0, 0, n, 24, 0, 0, canvas.width * n / DAYS, canvas.height);
    }

    function fit() {
      var box = canvas.getBoundingClientRect();
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = Math.max(1, Math.round(box.width * dpr));
      var h = Math.max(1, Math.round(box.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      draw();
    }

    // The year fills in from January to December the first time the grid
    // comes into view.
    function play() {
      var began = null;
      function step(now) {
        if (began === null) began = now;
        var t = Math.min(1, (now - began) / 1500);
        shown = DAYS * (1 - Math.pow(1 - t, 3));
        draw();
        if (t < 1) window.requestAnimationFrame(step);
      }
      window.requestAnimationFrame(step);
    }

    function hide() { tip.hidden = true; }

    function point(event) {
      var box = canvas.getBoundingClientRect();
      var x = event.clientX - box.left;
      var y = event.clientY - box.top;
      if (x < 0 || y < 0 || x >= box.width || y >= box.height) { hide(); return; }
      var day = Math.min(DAYS - 1, Math.floor(x / box.width * DAYS));
      var h = Math.min(23, Math.floor(y / box.height * 24));
      if (day >= Math.round(shown)) { hide(); return; }
      var p = grid(state.hub)[day * 24 + h];
      var when = WEEKDAYS[(JAN_1_WEEKDAY + day) % 7] + ', ' + MONTHS[monthOfDay[day]] + ' ' + dateOfDay[day] + ', ' + hourLabel(h);
      var what;
      if (p !== p) what = 'Skipped when the clocks moved forward';
      else if (p < 0) what = '<span class="is-neg">' + money(p) + '/MWh, the grid paid buyers</span>';
      else if (p > state.cap) what = '<b>' + money(p) + '/MWh, switched off</b>';
      else what = money(p) + '/MWh';
      tip.innerHTML = when + '<br>' + what;
      tip.hidden = false;
      var half = tip.offsetWidth / 2;
      tip.style.left = Math.max(half - 8, Math.min(box.width - half + 8, x)) + 'px';
      tip.style.top = y + 'px';
    }

    canvas.addEventListener('pointermove', point);
    canvas.addEventListener('pointerdown', point);
    canvas.addEventListener('pointerleave', hide);

    readColors();
    paint();
    fit();

    if ('ResizeObserver' in window) {
      new ResizeObserver(fit).observe(canvas);
    } else {
      window.addEventListener('resize', fit);
    }

    // Repaint when the theme changes, since the colors come from it.
    new MutationObserver(function () { readColors(); paint(); })
      .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    if (!reduced) {
      if ('IntersectionObserver' in window) {
        var seen = new IntersectionObserver(function (entries) {
          for (var i = 0; i < entries.length; i++) {
            if (entries[i].isIntersecting) { seen.disconnect(); play(); return; }
          }
        }, { threshold: 0.25 });
        seen.observe(canvas);
      } else {
        shown = DAYS;
        draw();
      }
    }

    return {
      update: function (next) {
        var changed = false;
        if (next.hub && next.hub !== state.hub) { state.hub = next.hub; changed = true; }
        if (next.cap !== undefined && next.cap !== state.cap) { state.cap = next.cap; changed = true; }
        if (changed) { hide(); paint(); }
      }
    };
  }

  window.Hours = { mount: mount, stats: stats };

  // A grid with a fixed shut-off sets it in its markup and needs no other script.
  Array.prototype.forEach.call(document.querySelectorAll('.hours[data-cap]'), function (node) {
    mount(node, { hub: node.getAttribute('data-hub') || 'HB_WEST', cap: parseFloat(node.getAttribute('data-cap')) });
  });
})();
