const assert = require('node:assert/strict');
const {test} = require('node:test');
const {browser, record} = require('./page-harness.cjs');

const result = {shelf: 160, wantlist: 25, library: 587, added: 2, failed: [],
  sync: {collection: 160, wantlist: 25, synced_at: '2026-10-28T12:00:00+11:00'}, sync_error: null};

test('Refresh reports Discogs counts, last success and the separate Apple import', async () => {
  const b = browser(), refresh = b.refresh();
  assert.match(b.elements.get('app').innerHTML, /Syncing your Discogs collection and wantlist/);
  assert.equal(b.sent('/api/refresh').method, 'POST');
  b.respond('/api/refresh', result); await refresh;
  const html = b.elements.get('app').innerHTML;
  assert.match(html, /Synced Discogs: 160 shelf records, 25 wanted/);
  assert.match(html, /Apple library: 587 albums \(local import\)/);
  assert.match(html, /Last successful Discogs sync: 2026-10-28 12:00:00\+11:00/);
  assert.match(html, /2 new records downloaded/);
  assert.equal(b.elements.get('refresh').disabled, false);
});

test('offline Refresh identifies cached lists and previous success without claiming a new sync', async () => {
  const b = browser(), refresh = b.refresh();
  b.respond('/api/refresh', {...result, added: 0, sync_error: 'Could not reach Discogs'}); await refresh;
  const html = b.elements.get('app').innerHTML;
  assert.match(html, /Discogs sync failed: Could not reach Discogs/);
  assert.match(html, /Using cached lists: 160 shelf records, 25 wanted/);
  assert.match(html, /Last successful Discogs sync/);
  assert.doesNotMatch(html, /Synced Discogs:/);
});

test('initial sync failures and detail failures are distinguished and escaped', async () => {
  const b = browser(), refresh = b.refresh();
  b.respond('/api/refresh', {...result, sync: null, sync_error: '<token error>', failed: ['3 (<detail error>)']}); await refresh;
  const html = b.elements.get('app').innerHTML;
  assert.match(html, /No successful Discogs sync recorded/);
  assert.match(html, /Could not download details for 3 \(&lt;detail error&gt;\)/);
  assert.match(html, /&lt;token error&gt;/);
  assert.doesNotMatch(html, /<token error>|<detail error>/);
});

test('a successful empty account is shown as zero records', async () => {
  const b = browser(), refresh = b.refresh();
  b.respond('/api/refresh', {...result, shelf: 0, wantlist: 0, added: 0}); await refresh;
  assert.match(b.elements.get('app').innerHTML, /Synced Discogs: 0 shelf records, 0 wanted/);
});

test('cached sync response cannot replace a card opened while syncing', async () => {
  const b = browser(), refresh = b.refresh(), card = b.navigate('#/release/3');
  b.respond('/api/release/3', record(3)); await card;
  b.respond('/api/refresh', {...result, sync_error: 'offline'}); await refresh;
  assert.match(b.elements.get('hero').innerHTML, /Record 3/);
  assert.equal(b.elements.get('refresh').disabled, false);
});
