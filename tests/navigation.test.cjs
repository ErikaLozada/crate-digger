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

const shelfLinks = {
  musicians: [
    {name: 'Billy Higgins', role: 'Drums', count: 1, records: [{id: 7925345, artist: 'Lee Morgan', title: 'The Sidewinder', year: 1964}]},
    {name: 'Herbie Hancock', role: 'Piano', count: 1, records: [{id: 31430060, artist: 'Wayne Shorter', title: 'Speak No Evil', year: 1966}]},
  ],
  producers: [],
  labels: [{name: 'Blue Note', count: 10, records: [
    {id: 3820432, artist: 'Jutta Hipp With Zoot Sims', title: 'Jutta Hipp With Zoot Sims', year: 1957},
    {id: 5462880, artist: 'Sonny Clark', title: 'The Art Of The Trio', year: 1980},
    {id: 36534199, artist: 'Melissa Aldana', title: 'Filin', year: 2026},
  ]}],
};
const plain = html => html.replace(/<[^>]*>/g, '');

test('shelf connections render from release data before recommendations arrive', async () => {
  const b = browser(), card = b.navigate('#/release/1216425');
  b.respond('/api/release/1216425', {...record(1216425), links: shelfLinks}); await card;
  const markup = b.elements.get('connections').innerHTML;
  assert.match(markup, /Connections on Your Shelf/);
  assert.equal((markup.match(/class="row"/g) || []).length, 3);
  assert.match(plain(markup), /Herbie Hancock · Piano/);
  assert.match(plain(markup), /on Speak No Evil \(Wayne Shorter, 1966\)/);
  assert.match(plain(markup), /10 records you own: Jutta Hipp With Zoot Sims, The Art Of The Trio, Filin and 7 more/);
  for (const entry of [...shelfLinks.musicians, ...shelfLinks.labels]) {
    for (const r of entry.records) assert.ok(markup.includes(`href="#/release/${r.id}">${r.title}</a>`));
  }
  const layout = b.elements.get('app').innerHTML;
  assert.ok(layout.indexOf('id="own"') < layout.indexOf('id="connections"'));
  assert.ok(layout.indexOf('id="connections"') < layout.indexOf('Closest in Your Collection'));
  assert.match(b.elements.get('picks').innerHTML, /Finding the closest/);
});

test('missing or empty connections leave no heading or group', async () => {
  for (const links of [undefined, {musicians: [], producers: [], labels: []}, {artists: [], musicians: [], producers: [], labels: []}]) {
    const b = browser(), card = b.navigate('#/release/A');
    b.respond('/api/release/A', {...record('A'), links}); await card;
    assert.equal(b.elements.get('connections').innerHTML, '');
  }
});

test('connection subtitles handle counts, absent roles and unknown years, and escape text', async () => {
  const b = browser(), card = b.navigate('#/release/A');
  const records = ['A', 'B', 'C'].map((title, i) => ({id: i + 1, title, artist: 'Artist', year: null}));
  b.respond('/api/release/A', {...record('A'), links: {
    musicians: [{name: 'Player', role: '', count: 3, records}, {name: 'Solo', role: '', count: 1, records: [records[0]]}],
    producers: [{name: 'Alfred Lion', count: 5, records}],
    labels: [{name: '<Label>', count: 1, records: [{id: '"<1>', title: '<Title>', artist: '<Artist>', year: '<Year>'}]}],
  }}); await card;
  const markup = b.elements.get('connections').innerHTML, text = plain(markup);
  assert.match(text, /on 3 records: A, B, C/);
  assert.match(text, /on A \(Artist\)/);
  assert.match(text, /Produced by Alfred Lion/);
  assert.match(text, /on 5 records: A, B, C and 2 more/);
  assert.match(text, /1 record you own:/);
  assert.doesNotMatch(text, /Player ·|Solo ·|null/);
  assert.match(markup, /&lt;Label&gt;/);
  assert.match(markup, /&lt;Title&gt;/);
  assert.doesNotMatch(markup, /<Label>|<Title>|href="#\/release\/"/);
});

test('artist connections come first with linked, escaped album titles and count wording', async () => {
  const b = browser(), card = b.navigate('#/release/A');
  const records = ['A', 'B', 'C'].map((title, i) => ({id: i + 1, title, year: 1965}));
  b.respond('/api/release/A', {...record('A'), links: {...shelfLinks, artists: [
    {name: 'Stanley Turrentine', count: 4, records},
    {name: '<Artist>', count: 1, records: [{id: '"<1>', title: '<Title>', year: '<Year>'}]},
    {name: 'Unknown year', count: 1, records: [{id: 9, title: 'Undated', year: null}]},
  ]}}); await card;
  const markup = b.elements.get('connections').innerHTML, text = plain(markup);
  assert.ok(text.indexOf('More by Stanley Turrentine') < text.indexOf('Billy Higgins'));
  assert.match(text, /4 records you own: A, B, C and 1 more/);
  assert.match(markup, /More by &lt;Artist&gt;/);
  assert.match(markup, /href="#\/release\/%22%3C1%3E">&lt;Title&gt;<\/a> \(&lt;Year&gt;\)/);
  assert.match(markup, /href="#\/release\/9">Undated<\/a><\/div>/);
  assert.doesNotMatch(markup, /<Artist>|<Title>|<Year>|null|undefined/);
  for (const r of records) assert.ok(markup.includes(`href="#/release/${r.id}">${r.title}</a>`));
});

test('a lone artist connection shows album and year without repeating the artist', async () => {
  const b = browser(), card = b.navigate('#/release/A');
  b.respond('/api/release/A', {...record('A'), links: {artists: [
    {name: 'Stanley Turrentine', count: 1, records: [{id: 2, title: "Hustlin'", year: 1965}]},
  ]}}); await card;
  const text = plain(b.elements.get('connections').innerHTML);
  assert.match(text, /Connections on Your Shelf/);
  assert.match(text, /Hustlin&#39; \(1965\)/);
  assert.doesNotMatch(text, /on Hustlin|1965,|records you own/);
});

test('late release connections cannot populate a different card or a return to the same card', async () => {
  for (const next of ['A', 'B']) {
    const b = browser(), first = b.navigate('#/release/A');
    b.navigate('#/');
    const second = b.navigate(`#/release/${next}`);
    if (next === 'A') {
      b.respond('/api/release/A', {...record('A'), links: shelfLinks}); await first;
      assert.equal(b.elements.get('connections').innerHTML, '');
      b.respond('/api/release/A', record('A')); await second;
    } else {
      b.respond('/api/release/B', record('B')); await second;
      b.respond('/api/release/A', {...record('A'), links: shelfLinks}); await first;
    }
    assert.equal(b.elements.get('connections').innerHTML, '');
  }
});

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
