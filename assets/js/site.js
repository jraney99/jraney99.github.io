// Light and dark theme. The site is light unless the visitor picks dark;
// the choice is saved for their next visit. A small inline script in each
// page's <head> applies a saved choice before the first paint, so the page
// never flashes the wrong theme.
(function () {
  var root = document.documentElement;
  var button = document.querySelector('.theme-toggle');
  if (!button) return;

  var PAPER = { light: '#f4f1e8', dark: '#0f1612' };
  var bar = document.querySelector('meta[name="theme-color"]');

  function current() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function sync() {
    var next = current() === 'dark' ? 'light' : 'dark';
    button.setAttribute('aria-label', 'Switch to ' + next + ' theme');
    button.setAttribute('title', 'Switch to ' + next + ' theme');
    // A phone's browser bar takes its color from this tag.
    if (bar) bar.setAttribute('content', PAPER[current()]);
  }

  button.addEventListener('click', function () {
    var next = current() === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    sync();
  });

  sync();
})();

// Lets iOS Safari show :active (pressed) styles on tap.
document.addEventListener('touchstart', function () {}, { passive: true });

// Wide tables keep their columns readable; make the sideways scroll discoverable
// and keyboard-accessible only while the table actually exceeds its container.
(function () {
  var wraps = Array.from(document.querySelectorAll('.table-wrap'));
  function update(wrap) {
    var wide = wrap.scrollWidth > wrap.clientWidth + 1;
    wrap.classList.toggle('is-scrollable', wide);
    if (wide) {
      wrap.setAttribute('tabindex', '0');
      wrap.setAttribute('role', 'region');
      wrap.setAttribute('aria-label', 'Scrollable table; use left and right arrow keys to see all columns');
    } else {
      wrap.removeAttribute('tabindex');
      wrap.removeAttribute('role');
      wrap.removeAttribute('aria-label');
    }
  }
  wraps.forEach(update);
  if (typeof ResizeObserver !== 'undefined') {
    var observer = new ResizeObserver(function (entries) {
      entries.forEach(function (entry) { update(entry.target); });
    });
    wraps.forEach(function (wrap) { observer.observe(wrap); });
  } else {
    window.addEventListener('resize', function () { wraps.forEach(update); });
  }
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { wraps.forEach(update); });
  }
})();
