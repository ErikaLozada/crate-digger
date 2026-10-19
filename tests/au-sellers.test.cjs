// Run with node --test tests/au-sellers.test.cjs. No browser or network dependencies.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {browser, record} = require('./page-harness.cjs');

async function open(data) {
  const b = browser(), card = b.navigate('#/release/route-id');
  b.respond('/api/release/route-id', data); await card;
  return b.elements.get('price').innerHTML;
}

test('for-sale listings link to this release filtered to Australian sellers', async () => {
  const markup = await open({...record('12345'), market: {for_sale: 2, low: 10}});
  assert.match(markup, /<a class="row" href="https:\/\/www\.discogs\.com\/sell\/release\/12345\?ships_from=Australia" target="_blank" rel="noopener">/);
  assert.match(markup, /Sellers in Australia/);
  assert.match(markup, /<svg class="i chev"[^>]*><path[^>]*><\/svg>\s*<\/a>$/);
});

test('seller link encodes the release id and escapes the completed href', async () => {
  const markup = await open({...record('"<1>'), market: {for_sale: 1}});
  assert.match(markup, /href="https:\/\/www\.discogs\.com\/sell\/release\/%22%3C1%3E\?ships_from=Australia"/);
  assert.doesNotMatch(markup, /href="[^"]*<1>/);
});

test('seller link is absent when no copies are for sale or count is missing', async () => {
  for (const market of [{for_sale: 0}, {}]) {
    const markup = await open({...record('12345'), market});
    assert.doesNotMatch(markup, /Sellers in Australia|sell\/release\//);
  }
});
