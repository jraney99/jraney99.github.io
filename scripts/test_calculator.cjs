// Exercise the actual calculator with a small DOM stand-in and independently summed prices.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('assets/js/calculator.js', 'utf8');
const dataContext = {window: {}};
vm.runInNewContext(fs.readFileSync('assets/data/ercot.js', 'utf8'), dataContext);
const data = dataContext.window.ERCOT || dataContext.window.ERCOT_2025;
function boot(query = '', loaded = true) {
  const nodes = {};
  function node(id) {
    return nodes[id] ||= {value: '', textContent: '', innerHTML: '', attrs: {}, events: {},
      setAttribute(k, v) { this.attrs[k] = v; },
      addEventListener(k, fn) { this.events[k] = fn; },
      querySelector(sel) { return node(id + sel); }};
  }
  const form = node('calc-form');
  const radios = Object.keys(data.hubs).map(value => ({value, checked: value === 'HB_WEST', addEventListener(){}}));
  form.querySelector = sel => sel.includes(':checked') ? radios.find(r => r.checked) : radios.find(r => sel.includes(r.value));
  form.querySelectorAll = () => radios;
  const window = {ERCOT: loaded ? data : null, location: {search: query, pathname: '/calculator'},
    history: {replaceState(a,b,url) { window.url = url; }}};
  vm.runInNewContext(source, {window, document: {getElementById: node}, URLSearchParams, navigator: {}});
  return {nodes, node, window, radios};
}
const fmt = n => Math.round(n).toLocaleString('en-US');
let cases = 0;
for (const hub of Object.keys(data.hubs)) {
  for (const cap of [50,75,100,150,200,300,500,1000,2000,Infinity]) {
    const app = boot();
    app.radios.forEach(r => r.checked = r.value === hub);
    app.node('cap').value = [50,75,100,150,200,300,500,1000,2000,Infinity].indexOf(cap);
    app.node('cap').events.input();
    const above = Array.from(data.hubs[hub]).filter(p => p > cap);
    const total = above.reduce((a,b) => a+b,0);
    assert.ok(app.node('f-hours').innerHTML.startsWith(fmt(above.length) + '<small>'));
    assert.equal(app.node('f-permw').innerHTML, '$' + fmt(total) + '<small>a year</small>');
    assert.equal(app.node('cap').attrs['aria-valuetext'], Number.isFinite(cap) ? '$' + fmt(cap) + ' per megawatt-hour' : 'Never shut off');
    cases++;
  }
}
for (const [input, expected] of [['100.6',101],['6000',5000],['',1],['-5',1],['2500',2500]]) {
  const app = boot();
  app.node('mw').value = input;
  app.node('mw').events.change();
  assert.equal(Number(app.node('mw').value), expected);
  assert.equal(Number(app.node('mw-range').value), expected);
  assert.ok(app.window.url.includes('mw=' + expected + '&'));
  const reopened = boot(app.window.url.split('?')[1]);
  assert.equal(reopened.node('f-always').textContent, app.node('f-always').textContent);
}
assert.match(boot('',false).node('summary').textContent, /didn’t load/);
const invalid = boot('?hub=invalid&mw=NaN&cap=wrong');
assert.ok(invalid.window.url.includes('hub=west&mw=100&cap=100'));
console.log(`${cases} hub/shut-off scenarios, input boundaries, share round trips and missing data passed.`);
