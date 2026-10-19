// Run with node --test tests/decisions.test.cjs. The decision buttons on the record card, against a mocked API.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {browser, record, picks, samples, flush} = require('./page-harness.cjs');

const plain = html => html.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
const ENTRY = {id: 'e1', release_id: 'A', action: 'pass', date: '2026-10-12T14:02:11+11:00', artist: 'Artist', title: 'Record A',
  price: null, tracks: [], note: '', discogs: null, undone: null};
const decided = (action, extra = {}) => ({...record('A'), decision: {...ENTRY, action, ...extra}});
async function loadCardExtras(b) {
  b.respond('/api/recommend/A', picks('Jazz'));
  b.respond('/api/samples/A', samples('A'));
  await flush();
}

async function open(data) {
  const b = browser(), card = b.navigate('#/release/A');
  b.respond('/api/release/A', data); await card;
  return b;
}
const box = b => b.elements.get('decide').innerHTML;

test('the four buttons show for a release that is not on the shelf or wanted', async () => {
  const b = await open(record('A'));
  for (const id of ['buy', 'pass', 'explore', 'wishlist']) assert.match(box(b), new RegExp(`id="${id}"`));
  assert.match(box(b), /Explore later/);
});

test('Buy is hidden only for the exact release on the shelf; Wishlist is hidden once wanted', async () => {
  const cases = [
    [{own: {kind: 'same'}}, 'buy', false],
    [{own: {kind: 'other_edition'}}, 'buy', true],
    [{own: {kind: 'apple'}}, 'buy', true],
    [{wanted: true}, 'wishlist', false],
    [{wanted: false}, 'wishlist', true],
  ];
  for (const [extra, id, shown] of cases) {
    const b = await open({...record('A'), ...extra});
    assert.equal(box(b).includes(`id="${id}"`), shown, JSON.stringify(extra));
  }
});

test('a saved decision replaces the buttons with its date and an Undo', async () => {
  const lines = {buy: 'Bought on 12 Oct', pass: 'Passed on 12 Oct', explore: 'Saved to explore on 12 Oct', wishlist: 'Wishlisted on 12 Oct'};
  for (const [action, line] of Object.entries(lines)) {
    const b = await open(decided(action));
    assert.equal(plain(box(b)), `${line} Undo`);
    assert.doesNotMatch(box(b), /id="(buy|pass|explore|wishlist|sticker)"/);
  }
});

test('Buy posts the sticker price as JSON and updates only the decision section', async () => {
  const b = await open(record('A'));
  await loadCardExtras(b);
  b.elements.get('sticker').value = ' 25 ';
  const rest = ['hero', 'picks', 'listen', 'links'].map(id => b.elements.get(id).innerHTML);
  const click = b.elements.get('buy').onclick();
  const sent = b.sent('/api/decision/A');
  assert.equal(sent.method, 'POST');
  assert.equal(sent.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(sent.body), {action: 'buy', price: '25'});
  assert.match(plain(box(b)), /Adding to your collection/);
  assert.doesNotMatch(box(b), /id="buy"/);
  b.respond('/api/decision/A', {decision: {...ENTRY, action: 'buy'}}); await click;
  await flush();
  assert.equal(b.pending('/api/release/A'), 0);
  assert.deepEqual(['hero', 'picks', 'listen', 'links'].map(id => b.elements.get(id).innerHTML), rest);
  assert.match(plain(box(b)), /^Bought on 12 Oct Undo$/);
});

test('Pass and Wishlist send a null price when the sticker field is empty', async () => {
  for (const action of ['pass', 'wishlist']) {
    const b = await open(record('A'));
    const click = b.elements.get(action).onclick();
    assert.deepEqual(JSON.parse(b.sent('/api/decision/A').body), {action, price: null});
    b.respond('/api/decision/A', {decision: ENTRY}); await click;
  }
});

test('Explore later sends the note and only the ticked tracks, and escapes track names', async () => {
  const b = await open({...record('A'), tracks: ['Side A', '<Side B>']});
  b.elements.get('explore').onclick();
  assert.match(b.elements.get('exploreform').innerHTML, /&lt;Side B&gt;/);
  assert.doesNotMatch(b.elements.get('exploreform').innerHTML, /<Side B>/);
  b.elements.get('tr-1').checked = true;
  b.elements.get('note').value = ' Check the bass ';
  b.elements.get('sticker').value = '30';
  const click = b.elements.get('save').onclick();
  assert.deepEqual(JSON.parse(b.sent('/api/decision/A').body),
    {action: 'explore', price: '30', note: 'Check the bass', tracks: ['<Side B>']});
  b.respond('/api/decision/A', {decision: {...ENTRY, action: 'explore'}}); await click;
  await flush();
  assert.equal(b.pending('/api/release/A'), 0);
  assert.match(plain(box(b)), /Saved to explore on 12 Oct/);
});

test('Explore later opens and closes its form with a second tap', async () => {
  const b = await open({...record('A'), tracks: ['Side A']});
  b.elements.get('explore').onclick();
  assert.match(b.elements.get('exploreform').innerHTML, /id="save"/);
  b.elements.get('explore').onclick();
  assert.equal(b.elements.get('exploreform').innerHTML, '');
});

test('Undo deletes the entry as JSON and restores the decision buttons in place', async () => {
  const b = await open(decided('wishlist', {id: 'e9'}));
  await loadCardExtras(b);
  const rest = ['hero', 'picks', 'listen', 'links'].map(id => b.elements.get(id).innerHTML);
  const click = b.elements.get('undo').onclick();
  const sent = b.sent('/api/decision/e9');
  assert.equal(sent.method, 'DELETE');
  assert.equal(sent.headers['Content-Type'], 'application/json');
  b.respond('/api/decision/e9', {decision: {...ENTRY, undone: '2026-10-19'}}); await click;
  await flush();
  assert.equal(b.pending('/api/release/A'), 0);
  assert.deepEqual(['hero', 'picks', 'listen', 'links'].map(id => b.elements.get(id).innerHTML), rest);
  for (const id of ['buy', 'pass', 'explore', 'wishlist']) assert.match(box(b), new RegExp(`id="${id}"`));
});

test('a Discogs error keeps the choice, shows the server message escaped, and keeps the price', async () => {
  const b = await open(record('A'));
  b.elements.get('sticker').value = '25';
  const click = b.elements.get('buy').onclick();
  b.refuse('/api/decision/A', 'Discogs refused <b>the</b> request'); await click;
  assert.match(box(b), /class="banner">Discogs refused &lt;b&gt;the&lt;\/b&gt; request/);
  assert.doesNotMatch(box(b), /<b>the<\/b>/);
  assert.match(box(b), /id="buy"/);
  assert.match(box(b), /value="25"/);
  assert.equal(b.pending('/api/release/A'), 0);
});

test('an undo error leaves the decision and its Undo in place', async () => {
  const b = await open(decided('buy', {id: 'e1'}));
  const click = b.elements.get('undo').onclick();
  b.refuse('/api/decision/e1', 'Discogs is down'); await click;
  assert.match(box(b), /Discogs is down/);
  assert.match(plain(box(b)), /Bought on 12 Oct Undo$/);
  assert.match(box(b), /id="undo"/);
});

test('a late decision answer cannot change a different card, success or failure', async () => {
  for (const fail of [false, true]) {
    const b = await open(record('A'));
    const click = b.elements.get('buy').onclick();
    const next = b.navigate('#/release/B');
    b.respond('/api/release/B', record('B')); await next;
    if (fail) b.refuse('/api/decision/A', 'Old failure'); else b.respond('/api/decision/A', {decision: ENTRY});
    await click;
    assert.equal(b.pending('/api/release/A'), 0);
    assert.match(b.elements.get('hero').innerHTML, /Record B/);
    assert.match(box(b), /id="buy"/);
    assert.doesNotMatch(box(b), /Old failure|Bought/);
  }
});

test('a late decision answer cannot change the same card after returning to it', async () => {
  const b = await open(record('A'));
  const click = b.elements.get('pass').onclick();
  b.navigate('#/');
  b.navigate('#/release/A');
  assert.equal(b.pending('/api/release/A'), 1);
  b.respond('/api/decision/A', {decision: ENTRY}); await click;
  assert.equal(b.pending('/api/release/A'), 1);
  assert.doesNotMatch(box(b), /Passed on|Undo/);
});
