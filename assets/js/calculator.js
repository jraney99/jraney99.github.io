// ERCOT power cost calculator.
// Replays every hour of 2025 at one hub for a site of a given size that sits
// out any hour priced above its shut-off price. All of the math runs on the
// hourly prices in assets/data/ercot-2025.js.
(function () {
  'use strict';

  var data = window.ERCOT_2025;
  var summary = document.getElementById('summary');

  if (!data || !data.hubs) {
    summary.textContent = 'The 2025 price data didn’t load, so the calculator can’t run. Reload the page to try again.';
    return;
  }

  var HUB_NAMES = { HB_WEST: 'West', HB_NORTH: 'North', HB_HOUSTON: 'Houston', HB_SOUTH: 'South' };
  var HUB_SLUGS = { west: 'HB_WEST', north: 'HB_NORTH', houston: 'HB_HOUSTON', south: 'HB_SOUTH' };
  var STOPS = [50, 75, 100, 150, 200, 300, 500, 1000, 2000, Infinity];
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  var DEFAULTS = { hub: 'HB_WEST', mw: 100, stop: 2 };

  // The chart's price window. A handful of hours sit above it; the chart says so.
  var YMAX = 500;
  var YMIN = -50;

  var form = document.getElementById('calc-form');
  var mwInput = document.getElementById('mw');
  var mwRange = document.getElementById('mw-range');
  var capInput = document.getElementById('cap');
  var capOut = document.getElementById('cap-out');
  var curve = document.getElementById('curve');
  var curveNote = document.getElementById('curve-note');
  var months = document.getElementById('months');
  var monthsNote = document.getElementById('months-note');
  var shareLink = document.getElementById('share-link');
  var shareNote = document.getElementById('share-note');
  var keyCap = document.getElementById('key-cap');
  var keyCapText = document.getElementById('key-cap-text');
  var keyFill = document.getElementById('key-fill');
  var hoursTitle = document.getElementById('hours-title');
  var hoursBox = document.getElementById('hours');
  var hoursKeyOff = document.getElementById('hours-key-off');
  var hoursGrid = window.Hours ? window.Hours.mount(hoursBox, { hub: DEFAULTS.hub, cap: STOPS[DEFAULTS.stop] }) : null;
  var fig = {
    always: document.getElementById('f-always'),
    withShut: document.getElementById('f-with'),
    saved: document.getElementById('f-saved'),
    hours: document.getElementById('f-hours'),
    perMw: document.getElementById('f-permw'),
    avg: document.getElementById('f-avg')
  };

  // ---------- data prep, once per hub ----------

  // 2025 in Central Time: every day has 24 hours except March 9 (23) and November 2 (25).
  var dayOfHour = (function () {
    var out = [];
    for (var m = 0; m < 12; m++) {
      for (var d = 1; d <= DAYS_IN_MONTH[m]; d++) {
        var len = 24;
        if (m === 2 && d === 9) len = 23;
        if (m === 10 && d === 2) len = 25;
        for (var h = 0; h < len; h++) out.push(m * 100 + d);
      }
    }
    return out;
  })();

  var cache = {};

  function prep(hub) {
    if (cache[hub]) return cache[hub];
    var prices = data.hubs[hub];
    var n = prices.length;
    var sorted = Array.prototype.slice.call(prices).sort(function (a, b) { return b - a; });
    var prefix = new Float64Array(n + 1);
    var maxIndex = 0;
    for (var i = 0; i < n; i++) {
      prefix[i + 1] = prefix[i] + sorted[i];
      if (prices[i] > prices[maxIndex]) maxIndex = i;
    }
    var stamp = dayOfHour.length === n ? dayOfHour[maxIndex] : null;
    cache[hub] = {
      prices: prices,
      sorted: sorted,
      prefix: prefix,
      n: n,
      total: prefix[n],
      max: prices[maxIndex],
      maxDate: stamp ? MONTH_NAMES[Math.floor(stamp / 100)] + '\u00a0' + (stamp % 100) : null,
      ranks: sampleRanks(n)
    };
    return cache[hub];
  }

  // Ranks to draw on a log scale: every one of the first 30, then evenly spaced in log terms.
  function sampleRanks(n) {
    var seen = {};
    var out = [];
    function add(r) { if (r >= 1 && r <= n && !seen[r]) { seen[r] = true; out.push(r); } }
    for (var r = 1; r <= 30; r++) add(r);
    for (var k = 0; k <= 220; k++) add(Math.round(30 * Math.pow(n / 30, k / 220)));
    add(n);
    return out.sort(function (a, b) { return a - b; });
  }

  // Number of hours priced strictly above the cap (the list is sorted high to low).
  function countAbove(sorted, cap) {
    var lo = 0;
    var hi = sorted.length;
    while (lo < hi) {
      var mid = (lo + hi) >> 1;
      if (sorted[mid] > cap) lo = mid + 1; else hi = mid;
    }
    return lo;
  }

  // ---------- formatting ----------

  function int(v) { return Math.round(v).toLocaleString('en-US'); }

  function moneyShort(v) {
    var a = Math.abs(v);
    var sign = v < 0 ? '−' : '';
    if (a >= 1e9) return sign + '$' + (a / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return sign + '$' + (a / 1e6).toFixed(a >= 1e8 ? 0 : 1) + 'M';
    if (a >= 1e4) return sign + '$' + int(a / 1e3) + 'K';
    return sign + '$' + int(a);
  }

  // Rounded for sentences: nobody reads "$764,769" next to "$4.6 million".
  function moneyWords(v) {
    var a = Math.abs(v);
    if (a >= 1e9) return '$' + (a / 1e9).toFixed(2) + ' billion';
    if (a >= 1e6) return '$' + (a / 1e6).toFixed(1) + ' million';
    if (a >= 1e4) return 'about $' + int(Math.round(a / 1e3) * 1e3);
    return '$' + int(a);
  }

  function pct(x) {
    var p = x * 100;
    return (p >= 99.5 && p < 100 ? p.toFixed(2) : p.toFixed(1)) + '%';
  }

  function rate(v) { return '$' + v.toFixed(2); }

  function capLabel(cap) { return isFinite(cap) ? '$' + int(cap) + '/MWh' : 'Never'; }

  // ---------- state ----------

  function readState() {
    var hub = form.querySelector('input[name="hub"]:checked').value;
    var mw = parseFloat(mwInput.value);
    if (!isFinite(mw) || mw < 1) mw = 1;
    if (mw > 5000) mw = 5000;
    var stop = parseInt(capInput.value, 10);
    return { hub: hub, mw: mw, stop: stop, cap: STOPS[stop] };
  }

  function applyQuery() {
    var q;
    try { q = new URLSearchParams(window.location.search); } catch (e) { return; }
    var hub = HUB_SLUGS[(q.get('hub') || '').toLowerCase()];
    if (hub) form.querySelector('input[value="' + hub + '"]').checked = true;
    var mw = parseFloat(q.get('mw'));
    if (isFinite(mw) && mw >= 1 && mw <= 5000) mwInput.value = Math.round(mw);
    var cap = (q.get('cap') || '').toLowerCase();
    var idx = cap === 'never' ? STOPS.length - 1 : STOPS.indexOf(parseFloat(cap));
    if (idx >= 0) capInput.value = idx;
  }

  function scenarioUrl(state) {
    var slug = HUB_NAMES[state.hub].toLowerCase();
    var cap = isFinite(state.cap) ? state.cap : 'never';
    return window.location.pathname + '?hub=' + slug + '&mw=' + Math.round(state.mw) + '&cap=' + cap;
  }

  // ---------- charts ----------

  function f1(v) { return (Math.round(v * 10) / 10).toString(); }

  function renderCurve(s, state, k) {
    var cap = state.cap;
    var logn = Math.log10(s.n);
    function xr(r) { return Math.log10(r) / logn * 1000; }
    function yv(v) { v = Math.max(YMIN, Math.min(YMAX, v)); return (YMAX - v) / (YMAX - YMIN) * 1000; }

    var svg = '<svg class="plot__svg" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">';
    [100, 200, 300, 400, 500].forEach(function (v) {
      svg += '<line class="grid" x1="0" x2="1000" y1="' + f1(yv(v)) + '" y2="' + f1(yv(v)) + '" vector-effect="non-scaling-stroke"/>';
    });
    svg += '<line class="zero" x1="0" x2="1000" y1="' + f1(yv(0)) + '" y2="' + f1(yv(0)) + '" vector-effect="non-scaling-stroke"/>';

    if (isFinite(cap) && k > 0) {
      var pts = [];
      for (var i = 0; i < s.ranks.length && s.ranks[i] <= k; i++) {
        var r = s.ranks[i];
        pts.push(f1(xr(r)) + ' ' + f1(yv(s.sorted[r - 1])));
      }
      pts.push(f1(xr(k)) + ' ' + f1(yv(s.sorted[k - 1])));
      var xc = xr(k);
      if (k < s.n) {
        var a = s.sorted[k - 1];
        var b = s.sorted[k];
        var t = a === b ? 0 : (a - cap) / (a - b);
        xc = xr(k) + t * (xr(k + 1) - xr(k));
      }
      var cy = f1(yv(cap));
      svg += '<path class="fill-signal" d="M' + pts.join(' L') + ' L' + f1(xc) + ' ' + cy + ' L0 ' + cy + ' Z"/>';
    }

    if (isFinite(cap) && cap <= YMAX) {
      svg += '<line class="cap" x1="0" x2="1000" y1="' + f1(yv(cap)) + '" y2="' + f1(yv(cap)) + '" vector-effect="non-scaling-stroke"/>';
    }

    var d = s.ranks.map(function (r, i) {
      return (i ? 'L' : 'M') + f1(xr(r)) + ' ' + f1(yv(s.sorted[r - 1]));
    }).join(' ');
    svg += '<path class="line" vector-effect="non-scaling-stroke" d="' + d + '"/></svg>';

    var labels = '';
    [0, 100, 200, 300, 400, 500].forEach(function (v) {
      labels += '<span class="plot__y" style="top:' + (yv(v) / 10).toFixed(2) + '%">$' + v + '</span>';
    });
    if (s.max > YMAX) {
      labels += '<span class="plot__tag" style="left:0;top:-1.55rem">↑ Top hour: $' + int(s.max) + (s.maxDate ? ' on ' + s.maxDate : '') + '</span>';
    }

    curve.querySelector('.plot__area').innerHTML = svg + labels;

    // The shut-off is named in the legend rather than on the plot, where a
    // label would sit on the curve at low prices or on a narrow screen.
    keyCap.hidden = !isFinite(cap);
    keyCapText.textContent = isFinite(cap) ? '$' + int(cap) + ' shut-off' + (cap > YMAX ? ', above the chart' : '') : '';
    keyFill.hidden = !(isFinite(cap) && cap <= YMAX && k > 0);

    var ticks = [[1, '1', 'is-start'], [10, '10', ''], [100, '100', ''], [1000, '1,000', ''], [s.n, int(s.n), 'is-end']];
    curve.querySelector('.plot__x').innerHTML = ticks.map(function (t) {
      return '<span' + (t[2] ? ' class="' + t[2] + '"' : '') + ' style="left:' + (xr(t[0]) / 10).toFixed(2) + '%">' + t[1] + '</span>';
    }).join('');

    var hubName = HUB_NAMES[state.hub];
    curve.setAttribute('aria-label', 'Hourly prices at the ' + hubName + ' hub in 2025, ranked from most to least expensive on a log scale. ' +
      (isFinite(cap) ? k + ' hours were priced above the $' + int(cap) + ' shut-off.' : 'No shut-off price is set.'));

    var above = countAbove(s.sorted, YMAX);
    var low = s.sorted[s.n - 1];
    curveNote.textContent = 'Source: ERCOT real-time prices at the ' + hubName + ' hub, hourly averages. ' +
      (above ? above + (above === 1 ? ' hour ran' : ' hours ran') + ' above $' + YMAX + ' and ' + (above === 1 ? 'is' : 'are') + ' cut off at the top of the chart. ' : '') +
      (low < 0 ? 'The lowest hour was −$' + Math.abs(low).toFixed(2) + ', when the grid paid buyers to take power.' : 'The lowest hour was ' + rate(low) + '.');
  }

  function niceCeil(v) {
    if (v <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v)));
    var steps = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
    for (var i = 0; i < steps.length; i++) if (steps[i] * p >= v) return steps[i] * p;
    return 10 * p;
  }

  function renderMonths(s, state) {
    var saved = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    var hours = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    var mapped = dayOfHour.length === s.n;
    if (isFinite(state.cap) && mapped) {
      for (var i = 0; i < s.n; i++) {
        var p = s.prices[i];
        if (p > state.cap) {
          var m = Math.floor(dayOfHour[i] / 100);
          saved[m] += p * state.mw;
          hours[m] += 1;
        }
      }
    }
    var top = Math.max.apply(null, saved);
    var best = saved.indexOf(top);
    var ymax = niceCeil(top * 1.08);
    var slot = 1000 / 12;
    var svg = '<svg class="plot__svg" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">';
    var labels = '';
    // With nothing avoided there is no scale to show, so the axis stays bare.
    if (top > 0) {
      svg += '<line class="grid" x1="0" x2="1000" y1="0" y2="0" vector-effect="non-scaling-stroke"/>';
      svg += '<line class="grid" x1="0" x2="1000" y1="500" y2="500" vector-effect="non-scaling-stroke"/>';
      saved.forEach(function (v, i) {
        if (v <= 0) return;
        var h = v / ymax * 1000;
        svg += '<rect class="bar' + (i === best ? ' bar--signal' : '') + '" x="' + f1(i * slot + slot * 0.18) + '" width="' + f1(slot * 0.64) + '" y="' + f1(1000 - h) + '" height="' + f1(h) + '"/>';
      });
      labels = '<span class="plot__y" style="top:0%">' + moneyShort(ymax) + '</span>' +
        '<span class="plot__y" style="top:50%">' + moneyShort(ymax / 2) + '</span>' +
        '<span class="plot__y" style="top:100%">$0</span>';
    }
    svg += '</svg>';
    months.querySelector('.plot__area').innerHTML = svg + labels;
    months.querySelector('.plot__x').innerHTML = MONTHS.map(function (name, i) {
      return '<span style="left:' + ((i + 0.5) * 100 / 12).toFixed(2) + '%">' + name + '</span>';
    }).join('');

    if (!isFinite(state.cap)) {
      monthsNote.textContent = 'With no shut-off price, the site runs every hour and avoids nothing. Move the slider left to see when the savings would come.';
      months.setAttribute('aria-label', 'No cost avoided in any month, because no shut-off price is set.');
      return;
    }
    if (top <= 0) {
      monthsNote.textContent = 'No hour at this hub went above $' + int(state.cap) + ' in 2025, so this shut-off price would never have kicked in.';
      months.setAttribute('aria-label', 'No cost avoided in any month at this shut-off price.');
      return;
    }
    monthsNote.textContent = 'The biggest month was ' + MONTH_NAMES[best] + ': the site sat out ' + hours[best] +
      (hours[best] === 1 ? ' hour' : ' hours') + ' and avoided ' + moneyWords(top) + '.';
    months.setAttribute('aria-label', 'Cost avoided by month. ' + MONTHS.map(function (name, i) {
      return name + ' ' + moneyShort(saved[i]);
    }).join(', ') + '.');
  }

  // The grid of every hour, by day and time of day.
  function renderHours(state, k, hubName) {
    if (!hoursGrid) return;
    hoursGrid.update({ hub: state.hub, cap: state.cap });
    hoursTitle.textContent = 'Every hour of 2025 at the ' + hubName + ' hub, by day and time of day';
    hoursKeyOff.hidden = !isFinite(state.cap) || k === 0;
    hoursBox.setAttribute('aria-label', 'A grid of every hour of 2025 at the ' + hubName + ' hub, with a column for each day and a row for each hour, colored by price. ' +
      (isFinite(state.cap) && k > 0
        ? 'The ' + int(k) + (k === 1 ? ' hour' : ' hours') + ' priced above $' + int(state.cap) + ' are marked as switched off.'
        : 'No hours are switched off.'));
  }

  // ---------- main ----------

  function render() {
    var state = readState();
    var s = prep(state.hub);
    var cap = state.cap;
    var k = isFinite(cap) ? countAbove(s.sorted, cap) : 0;
    var aboveSum = s.prefix[k];
    var always = s.total * state.mw;
    var withShut = (s.total - aboveSum) * state.mw;
    var saved = aboveSum * state.mw;
    var running = s.n - k;
    var avgAlways = s.total / s.n;
    var avgPaid = running ? (s.total - aboveSum) / running : 0;
    var hubName = HUB_NAMES[state.hub];
    var mwText = int(state.mw) + ' MW';

    capOut.textContent = capLabel(cap);
    if (parseFloat(mwRange.value) !== Math.min(state.mw, 1000)) mwRange.value = Math.min(state.mw, 1000);

    var lead = 'A ' + mwText + ' site at the ' + hubName + ' hub, running every hour of 2025, would have paid ' +
      moneyWords(always) + ' for energy, an average of ' + rate(avgAlways) + '/MWh. ';
    if (!isFinite(cap)) {
      var top1 = Math.round(s.n * 0.01);
      summary.textContent = lead + 'Never shutting off means paying for every spike: the ' + top1 + ' most expensive hours alone cost ' +
        moneyWords(s.prefix[top1] * state.mw) + ', ' + pct(s.prefix[top1] / s.total) + ' of the year’s bill.';
    } else if (k === 0) {
      summary.textContent = lead + 'No hour at the ' + hubName + ' hub went above $' + int(cap) + ', so this shut-off price would never have kicked in.';
    } else {
      summary.textContent = lead + 'Shutting off whenever the price topped $' + int(cap) + ' would have meant ' + int(k) +
        (k === 1 ? ' hour' : ' hours') + ' off (' + pct(running / s.n) + ' uptime) and saved ' + moneyWords(saved) +
        ', or ' + pct(aboveSum / s.total) + ' of the bill.';
    }

    fig.always.textContent = moneyShort(always);
    fig.withShut.textContent = moneyShort(withShut);
    fig.saved.innerHTML = moneyShort(saved) + '<small>' + pct(s.total ? aboveSum / s.total : 0) + ' of the bill</small>';
    fig.hours.innerHTML = int(k) + '<small>' + pct(running / s.n) + ' uptime</small>';
    fig.perMw.innerHTML = '$' + int(aboveSum) + '<small>a year</small>';
    fig.avg.innerHTML = rate(avgPaid) + '<small>vs. ' + rate(avgAlways) + ' always on</small>';

    renderCurve(s, state, k);
    renderMonths(s, state);
    renderHours(state, k, hubName);

    try { window.history.replaceState(null, '', scenarioUrl(state)); } catch (e) {}
    shareNote.textContent = '';
  }

  mwRange.addEventListener('input', function () {
    mwInput.value = mwRange.value;
    render();
  });

  mwInput.addEventListener('input', function () {
    var v = parseFloat(mwInput.value);
    if (isFinite(v) && v >= 1) render();
  });

  mwInput.addEventListener('change', function () {
    var v = parseFloat(mwInput.value);
    if (!isFinite(v) || v < 1) mwInput.value = 1;
    if (v > 5000) mwInput.value = 5000;
    render();
  });

  capInput.addEventListener('input', render);

  Array.prototype.forEach.call(form.querySelectorAll('input[name="hub"]'), function (radio) {
    radio.addEventListener('change', render);
  });

  form.addEventListener('submit', function (e) { e.preventDefault(); });

  shareLink.addEventListener('click', function (e) {
    e.preventDefault();
    var url = window.location.href;
    function fallback() { shareNote.textContent = url; }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        shareNote.textContent = 'Copied.';
      }, fallback);
    } else {
      fallback();
    }
  });

  mwInput.value = DEFAULTS.mw;
  capInput.value = DEFAULTS.stop;
  applyQuery();
  render();
})();
