// Run with node --test tests/navigation.test.cjs. No browser or network dependencies.
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const vm = require('node:vm');

const html = readFileSync(`${__dirname}/../static/index.html`, 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];

function browser() {
  const elements = new Map(), dynamic = new Set(), requests = new Map();
  function element(id) {
    let content = '';
    return {
      id, style: {setProperty() {}}, classList: {toggle() {}, add() {}, remove() {}},
      value: '', textContent: '', querySelectorAll: () => [], after() {},
      get innerHTML() { return content; },
      set innerHTML(value) {
        content = value;
        if (id === 'app') {
          for (const key of dynamic) elements.delete(key);
          dynamic.clear();
        }
        for (const match of value.matchAll(/id="([^"]+)"/g)) {
          elements.set(match[1], element(match[1]));
          dynamic.add(match[1]);
        }
      },
    };
  }
  for (const match of html.split('<script>')[0].matchAll(/id="([^"]+)"/g)) {
    elements.set(match[1], element(match[1]));
  }
  const location = {hash: '#/', replace(hash) { this.hash = hash; }};
  const context = vm.createContext({
    document: {querySelector: selector => elements.get(selector.slice(1)) || null,
      createElement: () => element('')},
    window: {addEventListener() {}, scrollTo() {}}, location,
    localStorage: {getItem: () => null, setItem() {}},
    fetch: path => new Promise((resolve, reject) => {
      if (!requests.has(path)) requests.set(path, []);
      requests.get(path).push({resolve, reject});
    }),
  });
  vm.runInContext(script, context);
  return {
    elements, location,
    navigate(hash) { location.hash = hash; return vm.runInContext('route()', context); },
    respond(path, data, error = false) {
      const request = requests.get(path)?.shift();
      assert.ok(request, `Expected request ${path}`);
      if (error) request.reject(new Error(data));
      else request.resolve({ok: true, json: async () => data});
    },
    refresh() { const button = elements.get('refresh'); return button.onclick({currentTarget: button}); },
  };
}

const record = id => ({id, title: `Record ${id}`, artist: 'Artist', live: true, market: {}});
const picks = style => ({result: {style, sentence: style, picks: []}, seconds: 1});
const samples = id => ({tracks: [], videos: [], youtube: `https://example.test/${id}`});
const flush = () => new Promise(resolve => setImmediate(resolve));

test('late release response cannot replace the selected record', async () => {
  const b = browser();
  const first = b.navigate('#/release/A'), second = b.navigate('#/release/B');
  b.respond('/api/release/B', record('B')); await second;
  b.respond('/api/release/A', record('A')); await first;
  assert.match(b.elements.get('hero').innerHTML, /Record B/);
});

test('returning to the same URL still invalidates the first request', async () => {
  const b = browser();
  const first = b.navigate('#/release/A');
  b.navigate('#/');
  const second = b.navigate('#/release/A');
  b.respond('/api/release/A', {...record('A'), title: 'Old response'}); await first;
  assert.doesNotMatch(b.elements.get('hero').innerHTML, /Old response/);
  b.respond('/api/release/A', {...record('A'), title: 'Current response'}); await second;
  assert.match(b.elements.get('hero').innerHTML, /Current response/);
});

test('late release errors cannot replace home', async () => {
  const b = browser(), first = b.navigate('#/release/A');
  b.navigate('#/');
  const home = b.elements.get('app').innerHTML;
  b.respond('/api/release/A', 'Old failure', true); await first;
  assert.equal(b.elements.get('app').innerHTML, home);
});

test('late recommendations and samples cannot change the next card', async () => {
  const b = browser(), first = b.navigate('#/release/A');
  b.respond('/api/release/A', record('A')); await first;
  const second = b.navigate('#/release/B');
  b.respond('/api/release/B', record('B')); await second;
  b.respond('/api/recommend/B', picks('Current style'));
  b.respond('/api/samples/B', samples('B')); await flush();
  b.respond('/api/recommend/A', picks('Stale style'));
  b.respond('/api/samples/A', samples('A')); await flush();
  assert.match(b.elements.get('tags').innerHTML, /Current style/);
  assert.match(b.elements.get('links').innerHTML, /example.test\/B/);
  assert.match(b.elements.get('picks').innerHTML, /Current style/);
});

test('late search results cannot redirect, and late failures cannot replace the card', async () => {
  for (const fail of [false, true]) {
    const b = browser(), search = b.navigate('#/search/q/old');
    const card = b.navigate('#/release/B');
    b.respond('/api/release/B', record('B')); await card;
    b.respond('/api/search?q=old', fail ? 'Old failure' : {results: [{id: 'A'}]}, fail);
    await search;
    assert.equal(b.location.hash, '#/release/B');
    assert.match(b.elements.get('hero').innerHTML, /Record B/);
  }
});

test('refresh completion does not replace a card opened while refreshing', async () => {
  for (const fail of [false, true]) {
    const b = browser(), refresh = b.refresh(), card = b.navigate('#/release/B');
    b.respond('/api/release/B', record('B')); await card;
    b.respond('/api/refresh', fail ? 'Old failure' : {shelf: 160, library: 587, added: 0, failed: []}, fail);
    await refresh;
    assert.match(b.elements.get('hero').innerHTML, /Record B/);
    assert.equal(b.elements.get('refresh').disabled, false);
  }
});
