const assert = require('node:assert/strict');
const {test} = require('node:test');
const {browser, flush} = require('./page-harness.cjs');

const ENTRY = {id: 'e1', release_id: '123', action: 'explore', date: '2026-10-12T14:02:11+11:00',
  artist: 'Artist', title: 'Record A', price: null, tracks: [], note: '', discogs: null, undone: null};
const plain = html => html.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();

async function openExplore(entries) {
  const b = browser();
  b.respond('/api/explore', {entries: []}); await flush();
  const view = b.navigate('#/explore');
  b.respond('/api/explore', {entries});
  await view;
  return b;
}

test('Explore Later renders escaped entry fields and links to its release', async () => {
  const b = await openExplore([{...ENTRY, artist: '<Artist>', title: 'A & B', note: 'Look <closely>',
    tracks: ['Side A', '<Side B>']}]);
  const html = b.elements.get('explore-list').innerHTML;
  assert.match(html, /<b>&lt;Artist&gt;<\/b>/);
  assert.match(html, /A &amp; B/);
  assert.match(html, /Look &lt;closely&gt;/);
  assert.match(html, /Side A · &lt;Side B&gt;/);
  assert.match(html, /12 Oct/);
  assert.doesNotMatch(html, /<Artist>|Look <closely>|<Side B>/);
  assert.match(html, /href="#\/release\/123"/);
  assert.match(b.elements.get('app').innerHTML, /<h1 class="large-title">Explore Later<\/h1>/);
});

test('Explore Later shows a short empty state', async () => {
  const b = await openExplore([]);
  assert.match(plain(b.elements.get('explore-list').innerHTML),
    /Nothing saved yet\. Tap Explore later on a record card\./);
});

test('home shows the Explore Later count only for a nonempty list', async () => {
  const b = browser();
  assert.equal(b.pending('/api/explore'), 1);
  b.respond('/api/explore', {entries: [ENTRY, {...ENTRY, id: 'e2'}]}); await flush();
  assert.match(b.elements.get('explore-link').innerHTML, /Explore Later · 2/);
  assert.match(b.elements.get('explore-link').innerHTML, /href="#\/explore"/);
  assert.ok(b.elements.get('app').innerHTML.indexOf('</form>') < b.elements.get('app').innerHTML.indexOf('id="explore-link"'));

  const empty = browser();
  empty.respond('/api/explore', {entries: []}); await flush();
  assert.equal(empty.elements.get('explore-link').innerHTML, '');
});

test('home hides Explore Later when the request fails', async () => {
  const b = browser();
  b.respond('/api/explore', 'offline', true); await flush();
  assert.equal(b.elements.get('explore-link').innerHTML, '');
});

test('late Explore Later list response cannot render into another view', async () => {
  const b = browser();
  b.respond('/api/explore', {entries: []}); await flush();
  b.navigate('#/explore');
  b.respond('/api/explore', {entries: [ENTRY]}); await flush();
  assert.match(b.elements.get('explore-list').innerHTML, /Record A/);

  const delayed = browser();
  delayed.respond('/api/explore', {entries: []}); await flush();
  delayed.navigate('#/explore');
  delayed.navigate('#/release/B');
  delayed.respond('/api/explore', {entries: [ENTRY]}); await flush();
  assert.doesNotMatch(delayed.elements.get('app').innerHTML, /Record A|Nothing saved yet/);
});

test('Explore Later row target resolves to the release card', async () => {
  const b = await openExplore([ENTRY]);
  const link = b.elements.get('explore-list').innerHTML.match(/href="(#\/release\/123)"/);
  assert.ok(link);
  b.navigate(link[1]);
  assert.equal(b.pending('/api/release/123'), 1);
});
