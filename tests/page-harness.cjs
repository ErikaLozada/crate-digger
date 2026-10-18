// Shared by the page tests: runs static/index.html's script in a vm with its element ids and a fetch the test answers by hand.
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
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
  const queue = path => requests.get(path) || [];
  const location = {hash: '#/', replace(hash) { this.hash = hash; }};
  const context = vm.createContext({
    document: {querySelector: selector => elements.get(selector.slice(1)) || null,
      createElement: () => element('')},
    window: {addEventListener() {}, scrollTo() {}}, location,
    localStorage: {getItem: () => null, setItem() {}},
    fetch: (path, opts) => new Promise((resolve, reject) => {
      if (!requests.has(path)) requests.set(path, []);
      requests.get(path).push({resolve, reject, opts});
    }),
  });
  vm.runInContext(script, context);
  const take = path => {
    const request = queue(path).shift();
    assert.ok(request, `Expected request ${path}`);
    return request;
  };
  return {
    elements, location,
    navigate(hash) { location.hash = hash; return vm.runInContext('route()', context); },
    respond(path, data, error = false) {
      const request = take(path);
      if (error) request.reject(new Error(data));
      else request.resolve({ok: true, json: async () => data});
    },
    refuse(path, message, status = 502) {
      take(path).resolve({ok: false, status, json: async () => ({error: message})});
    },
    sent(path) { return queue(path)[0]?.opts; },
    pending(path) { return queue(path).length; },
    refresh() { const button = elements.get('refresh'); return button.onclick({currentTarget: button}); },
  };
}

const record = id => ({id, title: `Record ${id}`, artist: 'Artist', live: true, market: {}});
const picks = style => ({result: {style, sentence: style, picks: []}, seconds: 1});
const samples = id => ({tracks: [], videos: [], youtube: `https://example.test/${id}`});
const flush = () => new Promise(resolve => setImmediate(resolve));

module.exports = {browser, record, picks, samples, flush};
