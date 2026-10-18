# Crate Digger: Product Requirements

Oct 3, 2026 · @Erika · Revision 7 (18 October 2026: model calls through OpenRouter, key storage, measured cost and speed; see Revision notes)

## Summary

Crate Digger is planned as an iPhone app, but the prototype is an iPhone-usable web app. A few seconds after you identify a record or CD, it tells you whether you already own it (on your shelves or only in Apple Music), says in one sentence what the record is, names the closest things you already listen to, shows where it sits among your labels, musicians and styles, and lets you hear 30-second samples. The prototype tests whether this evidence helps you decide manually: buy, pass, explore later or wishlist. It does not yet record that decision or modify Discogs. The price and Discogs' owner, want and for-sale numbers are context, not a reason to buy.

The first version of this document matched records by Discogs tags and kept the language model out of matching. The Phase 0 test on your own data reversed that: tags are too coarse to say what a record sounds like, and a language model choosing from your Apple Music library and shelf does it well. The bet is unchanged: evidence you can judge yourself ("closest to Tord Gustavsen Trio's The Ground, which is in your library") is more useful in a record bin than a score from the app.

- **Who:** you first, through a private local web app. TestFlight is a later product phase.
- **Prototype priority:** trustworthy decision support comes before action capture. The required evidence is ownership, one main style, and a valid close match or explicit no-match result. Samples and price are optional enrichments.
- **Product priorities after the prototype:** identification, decision evidence, samples, action capture, speed and cost. Price and market numbers remain context. A label that qualifies the price range is parked until you have defined it.
- **Platform:** an iPhone-usable web app for the prototype, backed by a local service; native iPhone remains the planned product platform.

**Phases used in this document.** Phase 0 is a test on your own data, with no app; most of it is done and its results are below. The prototype is a private iPhone-usable web app with a local backend and a deliberately smaller scope than the later product. The later native/TestFlight build takes the deferred P0 product requirements. Phase 2 adds the P1 requirements. Phase 3 is the P2 list, including the App Store and Android.

## Prototype build scope (decisions from the planning review)

The first prototype is a decision-support experiment, not the complete iPhone product described below. Its purpose is to determine whether trustworthy catalogue evidence helps Erika decide what to do with one record faster than the current manual workflow.

### Prototype user flow

The prototype is an iPhone-usable web app backed by a local service running on Erika's computer. The input order is:

1. Scan a barcode.
2. If no barcode is available, scan or enter the catalogue number.
3. If neither is available, type the artist and album title.
4. If the typed search returns multiple editions, show a filtered edition list and require manual selection.

Edition-specific ownership, price and market numbers are shown only after an edition is confirmed. The prototype does not guess an edition.

The prototype card must show:

- the confirmed record and edition;
- ownership against a local snapshot of the Discogs collection;
- one main style family;
- up to three close matches from the local Discogs and Apple Music snapshots, or an explicit "nothing close in your collection or library" result;
- Apple Music samples when available; and
- Discogs price and market data when available.

Style, ownership and close-match/no-match evidence are required for a successful decision. Samples and price data are optional and must be marked unavailable when a service has no result. Buy, Pass, Explore later and Wishlist were added to the prototype on 19 October 2026 (see `docs/decisions.md`): Buy and Wishlist change your Discogs collection and wantlist, each with Undo, and every tap is saved in a local dig history.

### Prototype data and services

Discogs collection data and Apple Music library data are imported into local snapshots through an explicit Refresh action. The Apple Music snapshot includes saved and playlist albums, play counts, and liked/favourite tracks. The inspected Discogs release is looked up live. The browser calls the local backend, not Discogs or the language-model provider directly; credentials stay in the backend environment.

The recommendation request receives the scanned record and the local candidate lists. It must return structured data: one style from the 24 families in `styles.py` or `Other/uncertain`, up to three candidate IDs, and a short reason for each. The app drops IDs not present in the supplied snapshots, permits zero matches, and never turns an unavailable or timed-out result into a guessed match. Model calls go through [OpenRouter](https://openrouter.ai), one API and one key in front of several providers. The primary model is `openai/gpt-5.6-luna` and the fallback is `anthropic/claude-haiku-5.5`; both IDs were checked against OpenRouter's live model list on 18 October 2026 (`check_models.py`). Each request asks OpenRouter to route only to providers that honour the JSON schema and do not keep the request data, and to return the cost of the call. The web app currently calls only the primary; the fallback is run in the harness, so the two can be compared on the same records.

A normal record gets one model run with a 20-second timeout. If the first result's style is `Other/uncertain`, the app runs two more attempts. The majority style wins; matches come from the attempt that produced that majority style. If there is no majority, recommendations are unavailable. A timeout is a recommendation-availability failure, not a false close match.

### Prototype acceptance test

Use a fixed set of 20 records labelled before seeing prototype output. Two independent labels establish the expected style and whether a close match is known; disagreements are resolved before testing. Run the normal one-pass flow, with the uncertainty retry only when triggered.

The prototype passes the decision-support test when:

- the style receives a specific family for at least 18 of 20 records;
- at least 90% of those specific family classifications are correct;
- false close matches occur on no more than 15% of records; a valid no-match result is not a false match;
- the required evidence is available quickly enough to support a manual decision in under 60 seconds per record; and
- the same records take at least 90 seconds per decision in the current manual workflow of looking up Discogs and using an LLM when needed.

The first implementation milestone is the recommendation-quality harness using fixed snapshots and record inputs. Barcode scanning, edition search and the web card are added only after this harness is testable.

## Problem

In a record bin you decide in seconds, with one hand full, and you cannot remember what is on your own shelves or in your Apple Music library. Catalogue apps tell you what a record is and what it sells for. The Discogs app can also tell you whether that exact release is in your collection (*to verify*). None of them connects a record to your Apple Music listening, or shows which things you own are close to it, so the real question ("is this *for me*?") is answered by guesswork, and the cost of a wrong guess is an A$40 record you play once.

**A typical dig:** 40 to 100 records flipped in an hour, about 10 worth a closer look. The bins are an even mix of used vinyl, often with no barcode, and barcoded CDs and newer pressings. You want to see in seconds where each of those 10 sits against what you own, hear a few tracks, and leave with a record of what you decided.

**How you decide** (your description, 4 October 2026): where does it sit in my collection, and what kind of music is it? Then listen to the samples. Like it: buy. Don't like it: pass. Like some of it but not all: note the artist to dig into later. The owner, want and for-sale numbers hint that a record may deserve a closer look, but they do not change whether you buy. At the bin you are mostly capturing information.

## Goals and priorities

The app shows evidence and lets you decide. It does not score whether you will like a record. Targets are proposals for you to adjust; the last column says what Phase 0 measured.

| Priority | Goal | Target | Phase 0 result |
| --- | --- | --- | --- |
| 0. Identification | Know which record, and which edition, you are holding | 9 in 10 records identified to the right album within 5 s without typing; the edition is confirmed before any edition-specific number is shown or anything is added to Discogs | Not tested yet: needs a photographed crate |
| 1. Ownership | Never buy a duplicate by accident | The card says whether you own this release, a different release of it, or only have it in Apple Music | 3 of 3 two-edition albums recognised; 10 of 25 wantlist records found in your library |
| 1. Closest by sound | Name the closest things you already listen to, with the reason | For 9 in 10 records, at least one of up to three picks is one you agree is close | 15 of 15 with picks written by Claude Opus in the session; at least 10 of 15 with Sonnet 5.5; 3 of 15 with the fastest tier |
| 1. Where it sits | Show the labels, musicians and main style that link it to what you own | The main style is right for 9 in 10 records; label and musician lines are facts | Main style ticked right on 13 of 15 |
| 1. Samples | Hear it, because listening is what decides | A 30-second preview or a video listed on Discogs for at least 80% of scanned albums. A YouTube search link is always offered as well, but does not count | 167 of 179 (93%) |
| 2. Capture | Leave the bin with a record of what you decided | Every record you look at closely ends in one tap: Buy, Pass, Explore later or Wishlist | Not tested: needs the app |
| 2. Speed and cost | Quick and affordable | Ownership and the fact lines in 1 s; the full card in 4 s where the model allows; running cost you have agreed to | Prototype models (18 October): picks in a median 5 to 6 s, so the full card misses 4 s; US$0.001 to US$0.007 per record, a few dollars in a heavy month |
| 3. Market context | See price and demand at a glance | The sticker price compared with the lowest listed price once the edition is confirmed, with owners, wants and copies for sale as plain numbers. Context only: no label | Not tested: needs the app |

**Non-goals for v1:** a like/dislike verdict or score, selling, social features, a full music player, price history charts, offline use (a good connection is assumed), Android.

## Later product experience (not the prototype)

The following full card and action flow is the planned native/TestFlight product. The prototype scope above takes precedence for the first build.

The app opens straight to the camera. One scan produces one result card, built to be read in about five seconds. Rating the Phase 0 test cards took you too long, and those cards carried about eleven rows each, so the card below is held to three picks and two or three fact lines.

**Scan flow**

1. Point the camera at the barcode or the cover. Barcode is tried first, then text recognition of the cover. Both run on the phone.
2. If neither identifies the record in about 2 seconds, the cover photo is sent to a vision model, which returns artist and title for a Discogs search (if this passes its Phase 0 test). A search box with artist, album and catalogue number fields is always one tap away.
3. If the match is uncertain, show the artwork and ask "Is this it?". One tap confirms. Never show matches for the wrong record.
4. A Vinyl / CD toggle sets the format you are holding.
5. **Edition.** A barcode usually identifies the exact release. Cover text, typing and the vision model identify only the album. In that case the card shows everything that is true of the album and offers a short list of editions, filtered by the format toggle, to pick from. The catalogue number on the spine or label narrows the list to one.
6. The card fills in layers. Ownership and the fact lines come from data on the phone and appear first. The sentence on what the record is and the closest picks come from one request to the language model and arrive next. Samples, then price and market numbers, follow.
7. Optionally type the sticker price.
8. Tap Buy, Pass, Explore later or Wishlist. Buy and Wishlist change your Discogs account, so both have an Undo and both are disabled until the edition is confirmed. Pass and Explore later work as soon as the album is known.

**Result card, top to bottom**

1. **The record:** artwork, title, artist, year, its one main style and decade (for example "Jazz-funk & fusion · 1970s"), format toggle, and the edition if confirmed.
2. **Do you have it?** One of four answers, set out in the table below. If this release, or another edition of the same album, is on your Discogs wantlist, the card says so here.
3. **Territory line:** one plain sentence on how close the record is to what you own and listen to: familiar, nearby, or new to you, with the strongest reason. It is a description, not a score.
4. **What it is:** one sentence, at most 25 words ("Swedish piano trio album of lyrical, pop-tinged contemporary jazz").
5. **Closest by sound:** up to three picks from your Apple Music library and your shelf, each with a short reason and, for library albums, your plays and liked tracks. The picks stay in the same sub-style; if fewer than three are truly close, fewer are shown.
6. **Where it sits:** two or three fact lines, such as "You own 9 records on Blue Note", "Isao Suzuki plays on records you own" and "9 Salsa & Cuban records on your shelf, 175 albums in your library".
7. **Listen:** 30-second previews of three tracks from Apple Music. One tap on a track marks it as one you liked. If the album is not on Apple Music, a button opens the video listed on Discogs, or a YouTube search, in the YouTube app. Nothing from YouTube is fetched until you tap it.
8. **Price and market numbers:** once the edition is confirmed, the lowest listed price in AUD and, if you typed a sticker price, the difference. Owners, wants and copies for sale are shown as plain numbers. This panel is context, so it always sits below Listen.
9. **Facts:** country and label.
10. **Buy, Pass, Explore later, Wishlist.**

The order follows how you decide: do I have it, where does it sit, what kind of music is it, how does it sound. It is the same for every record.

**What each tap does**

| What you think | Tap | What the app does |
| --- | --- | --- |
| I like it | Buy | Adds this release to your Discogs collection and logs the sticker price |
| I don't like it | Pass | Logs the pass in the dig history |
| I like some of it, and the artist is worth digging into | Explore later | Saves the artist, this record, the tracks you marked as liked and an optional note to an Explore later list in the app. Nothing is sent to Discogs |
| I want this record, but not today or not this copy | Wishlist | Adds this release to your Discogs wantlist |
| I already own it, and it is not in Discogs yet | I own this (on the ownership line) | Adds this release to your Discogs collection without logging a purchase |

Wishlist is about one record and lives in Discogs. Explore later is about an artist and lives in the app. Every tap is saved in the dig history with the date, the store's sticker price if you typed one, and the tracks you sampled.

**Ownership answers.** Apple Music does not mean you own the record, so it is reported separately from your shelf.

| Situation | What the card says | Why it matters |
| --- | --- | --- |
| This release is in your Discogs collection | "You own this", with format and year | Prevents a duplicate |
| Another release of the same album is in your collection | "You own a different release", naming its format, year, country and label | A CD and an LP, or an original and a reissue, can both be worth owning, and you decide |
| Not in your collection, but the album is in your Apple Music library | "In your Apple Music library, not on your shelf", with plays and liked tracks | You listen to it, so a physical copy may be worth buying |
| Neither | No ownership line |  |

A "different release" means the same Discogs master release in another format, pressing or edition. The Apple Music check compares artist and album title on the phone; it needs no call to Discogs. In Phase 0 it found 10 of your 25 wantlist records in your library, which fits how you use the wantlist: you listen first, then want the record.

**Wishlist.** There is one wishlist: your Discogs wantlist. Tapping Wishlist on a card adds the release to it, and tapping Buy on a wantlist record moves it from the wantlist to your collection. A wantlist entry is one specific edition (15 of your 25 are reissues), and the copy in the bin is often another, so the card matches the wantlist at album level and names the edition you listed. In Phase 2 the app also suggests additions: albums in your Apple Music library with several liked tracks or heavy plays that are not in your Discogs collection or wantlist, most-listened first. One tap adds the album's main release to your wantlist; you can choose a different edition first if you care which one.

**States to design:** no match found (manual search), several editions (pick one from a list filtered by format), album identified but edition not yet picked (album-level card; Buy, Wishlist and I own this disabled), compilations and box sets, no preview available (video link or search link), the model slow or unavailable (the card is complete without sections 4 and 5, and says so), and a service that is down (show the sections that did load).

## Functional requirements for the later product

These requirements are not all prototype requirements. Items explicitly marked Prototype are in the first web build; action capture, history and Discogs mutations are deferred to the later native build.

For the later product roadmap, P0 is the first native/TestFlight version after this prototype. P1 follows once P0 feels right in a real store. P2 is the wider release, including the App Store and Android.

| ID | Requirement | Priority |
| --- | --- | --- |
| F1 | Identify a release by barcode scan, on the phone | P0 |
| F2 | Identify an album by cover text recognition (on the phone) and by typed artist, album or catalogue number | P0 |
| F3 | Import your Discogs collection (154 items on 3 October 2026) and wantlist (25 items) into a local snapshot, with an explicit Refresh action. For each collection item, also fetch its credits, labels, styles, barcode and master release once | Prototype |
| F4 | Import an Apple Music library snapshot: saved albums and playlist albums, with play counts and liked/favourite tracks (1,327 albums in the export of 4 October 2026). The Library.xml export is the input for the prototype | Prototype |
| F5 | Ownership answers: this release is in your collection; a different release of the album is in your collection; only in your Apple Music library; neither. Also: this release, or another edition of the album, is on your wantlist | P0 |
| F6 | Closest by sound: up to three picks from your library and shelf, each with a short reason. Chosen by the configured primary model from the record's details and your two lists. Every returned ID is checked against your lists, and an ID that is not in them is dropped; zero picks is valid | Prototype |
| F12 | What it is: one sentence of at most 25 words, from the same request as F6 | Prototype |
| F24 | Where it sits: fact lines for labels you own, musicians who play on your records, and how many records and library albums share the main style; plus the territory line (familiar, nearby, new to you) | P0 |
| F25 | One main style per record: a family built from Discogs styles, with tags too broad to mean anything ignored. Where the styles conflict or are missing, the model names the family or it is left blank. Assigned once per shelf record at import and once per scanned record | P0 |
| F7 | 30-second Apple Music previews of three tracks; if the album is not on Apple Music, a button that opens the Discogs video link, or a YouTube search, in the YouTube app | Prototype, optional evidence |
| F8 | Main style and decade in the card header; country and label lower down | P0 |
| F9 | Lowest listed price in AUD, and owners, wants and copies for sale as plain numbers, all returned with the release. Shown only once the edition is confirmed, below Listen, as optional context | Prototype, optional evidence |
| F10 | Buy, Pass and Wishlist actions saved in a dig history. Buy adds the release to your Discogs collection; Wishlist adds it to your Discogs wantlist. Both have Undo and both need a confirmed edition. "I own this" adds a record you already have without logging a purchase | Later native build |
| F23 | Explore later: saves the artist, the record, the tracks you marked as liked and an optional note to a list in the app, with a simple screen to read the list | Later native build |
| F13 | Cover recognition by a vision model when barcode and text recognition fail, with "Is this it?" confirmation. Ships in Phase 1 only if it passes its Phase 0 test | P0, conditional |
| F19 | Edition list: when only the album is known, show its editions filtered by the format toggle, narrowed by catalogue number, for one-tap confirmation | P0 |
| F20 | Sticker price field (optional): the card compares it with the lowest listed price and saving it in dig history is deferred | Prototype, optional evidence |
| F21 | Matching each library album to Discogs | Dropped: the by-sound picks no longer need Discogs styles for library albums, and the library ownership check runs on the phone |
| F22 | Price-range label on the card | Parked: you like the idea and want to think about it before it is defined |
| F26 | A cheaper way to make the picks: label every library album with a precise sub-style once, then let a small model choose from a short list on each scan. Built only if it passes the same test Sonnet passed | P1 |
| F11 | Wantlist suggestions from your Apple Music library: albums with several liked tracks or heavy plays that are not in your collection or wantlist, most-listened first | P1 |
| F14 | Browse all past digs, including passes | P1 |
| F15 | Richer price: suggested price by condition, price history | P2 |
| F16 | Sonic similarity from preview audio compared with your liked songs | P2 |
| F17 | App Store release: Discogs sign-in, backend, accounts, terms review | P2 |
| F18 | Android client | P2 |

## Matching: closest by sound, and where it sits

The card answers two different questions, and Phase 0 showed they need two different methods.

| Question | Method | What Phase 0 showed |
| --- | --- | --- |
| What is this record like, among things I already listen to? | A language model picks from your library and shelf (method A in the test) | You ticked a pick on all 15 records you rated |
| Where does it sit: which of my labels, musicians and styles does it touch? | Rules over Discogs credits and one main style (method B in the test) | Useful as facts; poor as a list of "similar records" |

The app still does not predict whether you will like a record. Your earlier library analysis is why: artist, genre, era and length alone separate liked from not-liked at an AUC of about 0.72 (0.5 is a coin flip), which is too weak to trust as a score.

### Closest by sound

On each scan the app sends one request to the configured language model. The request holds your shelf list, your library list with plays and liked/favourite tracks, the scanned record's artist, title, year, label and Discogs styles, and the task. The model returns one sentence on what the record is, its main style, and up to three picks with a short reason each. In the prototype, the primary model is `openai/gpt-5.6-luna` with `anthropic/claude-haiku-5.5` as fallback, both called through OpenRouter (see Prototype data and services). The full request for Seven Days of Falling is in the file "Seven Days of Falling - request to the model.txt", sent to you in the chat on 4 October: 1,497 lines, about 130,000 characters, almost all of it the library list.

Rules for the request, from what you ticked and what you left:

- **At most three picks.** Picks I wrote beyond the first three were ticked 25% of the time (10 of 40), against 62% for the first three (28 of 45).
- **Same sub-style, not a neighbour.** You left the looser picks: Havana D'Primera for a mambo big band, Anri for Japanese fusion, Bobby Caldwell for city pop. If fewer than three are truly close, the model returns fewer; if none is, the card says so.
- **Closest, not most played.** Plays and liked tracks are shown beside each pick, but they do not decide the pick.
- **Only things you have.** The model may only return ids from your two lists, and the app drops any id that is not in them. This is the guard against invented albums.
- **Never the record itself.** If the scanned album is already in your library, the ownership line says so and the pick list leaves it out.

**Phase 0 model evidence.** The earlier request was run three ways, scored against the 15 wantlist records you rated. That evidence informed the original app plan, but the prototype uses the configured primary and fallback models above and evaluates them separately.

| Model | Records with a pick you ticked | Picks | Notes |
| --- | --- | --- | --- |
| Claude Opus, writing the picks in the working session | 15 of 15 | 38 of 85 ticked | Four to eight picks per record, more than the three the card will show |
| Claude Sonnet 5.5 | at least 10 of 15 | 13 ticked, 9 seen and left, 21 new to you | No invented ids. The 21 new picks are unrated, many of them albums you added after rating, so 10 is a floor |
| The fastest tier on your Claude plan (model not named) | 3 of 15 | 4 ticked; 5 invented ids across the 25 records, dropped | At least 12 plainly wrong albums, such as Minutemen for Tatsuro Yamashita. About 3 s per record (2 to 8 s) |

Sonnet 5.5 was the model in the earlier Phase 0 comparison. That result is historical evidence only; the prototype uses the configured primary model and evaluates the primary and fallback separately. The prototype uses one request per record and measures the 20-second timeout.

The fastest tier returned ids that were not in the 1,480-line list and picked albums from unrelated styles. Whether a small model does better when it chooses from a short list has not been tested. F26 is the design that would test it: label the library once with precise sub-styles, then give a small model a short list to choose from.

### Where it sits

These lines are facts from Discogs and your library, shown without a list of "similar records":

- **Same artist:** "You own 2 other records by this artist", or "You listen to this artist in Apple Music".
- **Musicians:** "Isao Suzuki plays on records you own". Matching uses Discogs artist ids and the credits of each release, because the printed credit hides shared players: "Ryo Fukui" and "Ryo Fukui Trio" are different Discogs artists. Design, liner-note and engineering credits are ignored, and on records with a large line-up only featured players count.
- **Label:** "You own 9 records on Blue Note". Labels too broad to say anything, such as Columbia or Sony Music, are ignored. A label line is a fact about your shelf and is not offered as a reason the music is similar: on its own it was ticked for 2 of 7 matches.
- **Main style:** "9 Salsa & Cuban records on your shelf". Where Apple's genre is about as narrow as the style, the library count is added ("175 albums filed under Música tropical or Cuban"). Where Apple's genre is much broader, as with "Jazz", it is left out.

**One main style per record.** Discogs lists many styles per release, often contradictory: St Germain's 2015 album carries African, Deep House, Downtempo and Future Jazz. The app reduces them to one family:

- Discogs styles are grouped into 24 families, such as "Hard bop, post-bop & soul-jazz", "Jazz-funk & fusion", "City pop & AOR", "Salsa & Cuban", "Bossa nova & MPB" and "Film & TV score". The full table is in `styles.py` in the CrateDigger folder.
- Tags too broad to mean anything are ignored: Contemporary Jazz, Vocal, Ballad, Easy Listening, and classical form words such as Symphony and Concerto.
- A record gets the family most of its styles point to. Where there is no clear majority, the model names the family, or it is left blank.
- The period is the decade the album was first released. For classical families the decade is dropped, since the family already names the era.

In Phase 0, 5 of 179 records were left blank and 50 were named by Claude in the session. You ticked the main style as right on 13 of 15 cards; the two you left were Return to Forever as "Jazz-funk & fusion" and The Awakening as "Hard bop, post-bop & soul-jazz".

**Territory line.** One sentence, from the first rule that applies:

| Territory | Rule |
| --- | --- |
| Familiar | You own another record by the artist; or the album, or the artist with 5 or more plays or a liked track, is in your library; or you own a record on the same specific label; or a lead artist of one record plays on the other; or two or more of its musicians play on records you own; or you own three or more records in its main style |
| Nearby | You own one or two records in its main style; or your library holds 10 or more albums in a matching narrow genre; or one of its musicians plays on a record you own; or the model's picks include two or more things you have played or own |
| New to you | None of the above |

On your wantlist this gave 21 familiar, 3 nearby and 1 new. The one "new" call was wrong: Konoma, where you ticked a pick as close. The territory line has not been tested on records you did not choose.

**Shelf details.** The Discogs collection list does not include credits, styles, barcodes or master releases, so each shelf record needs one release call to fetch them. For 154 records this took a few minutes, and it runs again only for records added since.

**What your Discogs data showed** (collection of 154 and wantlist of 25):

| Finding | Number | What it means |
| --- | --- | --- |
| Artists with only one record on the shelf | 115 of 130 | "Same artist" rarely fires from the shelf alone |
| Wantlist records whose artist is on your shelf | 1 of 25 by exact credit, 4 of 25 by person | For records you already want, the link is almost never the artist, which is why the by-sound picks carry the card |
| Wantlist records already in your Apple Music library | 10 of 25 | You listen first, then want the record |
| Records with more than one label listed | 41 of 154 | A label line checks every label on the release |
| Records with no release year | 9 of 154 | The period falls back to the master release year |
| Vinyl records marked as reissues or repressings | 51 of 91 | The edition in your hand is often not the original |

## Price and market numbers

The Discogs release call that returns credits and styles also returns four market numbers (checked against the API documentation): how many collectors own the release, how many want it, how many copies are for sale now, and the lowest listed price. The card shows them as they are. It does not turn them into a label.

These numbers are context. By your description they do not change whether you buy; the want count in particular is a hint that other collectors are looking for the record, so it may deserve a closer look.

| Number | What it tells you | Caveat |
| --- | --- | --- |
| Lowest listed price | What the cheapest copy costs today | An asking price in any condition, so one worn copy can pull it down. Shipping from overseas sellers is extra. Empty when no copies are listed |
| Owners | How widely owned this edition is | Older releases have had longer to collect owners. The count belongs to one edition, so a new reissue has few owners however well known the album is |
| Wants | How much demand there is for this edition | Hyped records can attract wants faster than owners |
| Copies for sale | Supply today | Counted worldwide, not in Australia. It is marketplace data, so it falls under the stricter Discogs terms |

- The lowest listed price is returned in AUD on request (checked against the API documentation). The sticker price comparison says "lowest listed, any condition, plus shipping" beside the number.
- The numbers describe second-hand copies. For a new release still in print, the store's price is the price.
- Before the edition is confirmed, the card shows only the lowest listed price across all editions of the album, labelled as such.

**Price-range label: parked (4 October 2026)**

The Common, Rare and Collector tiers are removed from the first build. You like the idea of a label that qualifies the price range of a record, and want to think about it before it is defined. Until then the card shows the price and the plain numbers.

Your examples, kept for when you come back to it:

| You called it | Record | What is on your shelf or wantlist |
| --- | --- | --- |
| Rare | Ryo Fukui, Scenery | LP, limited reissue, 2026 |
| Rare | Jiro Inagaki & Soul Media, Funky Stuff | Wantlist: LP, reissue, 2023 |
| Rare | Tsuyoshi Yamamoto Trio, Misty (Three Blind Mice) | LP, limited reissue, 2024, and CD, reissue, 2019 |
| Rare | The Bill Evans Trio, Portrait In Jazz: you meant the first pressing | Your collection lists an LP reissue from 1976 |
| Rare | You & The Explosion Band, Lupin III original soundtrack | LP, 1978 |
| Common | Rosalía, Lux | 2xLP, 2025 |
| Common | Willie Colón & Rubén Blades, Siembra | LP, reissue, 2021 |
| Common | Portishead, Portishead | 2xLP, reissue, 2017 |
| Common | Classical records | Deutsche Grammophon, Decca, Sony Classical and others |
| Common | Massive Attack, Mezzanine | On your shelf, not yet added to Discogs |
| Collector | None | You own nothing you would call Collector |

What the examples show, read from the exports alone (owner and want counts were not fetched):

- **Sometimes it is the album.** Scenery, Funky Stuff and Misty are reissues from 2023 to 2026, and you still call them rare. Four of the five "rare" records are Japanese jazz or Japanese releases, and the "common" ones are records most shops stock.
- **Sometimes it is the pressing.** For Portrait In Jazz you mean the first pressing, not the album.
- **Price covers both.** A hard-to-find album and a sought-after pressing both show up as a higher price, which the owner count of one edition does not capture. That supports your instinct to label the price range and not the rarity.
- **Collector cannot be tuned.** With no Collector records on your shelf, there is nothing to set that cut-off against.

Questions to settle when you return to it:

- Which price does the label describe: the cheapest copy of the edition in your hand, or the typical price across all editions of the album? The second needs more calls than one release returns.
- What are the ranges, in dollars, and what would you call them?
- The lowest listed price is one asking price in any condition. Is that good enough, or does the label need Discogs' suggested price by condition (F15, which needs your seller settings filled in)?

## Data sources

A scan joins three services: Discogs, Apple Music and a language model reached through OpenRouter. Items marked *to verify* have not been checked; the rest were checked against official documentation on 3 and 4 October 2026, and the OpenRouter row on 18 October 2026.

| Source | Provides | Cost | Limits and terms | Role |
| --- | --- | --- | --- | --- |
| On-device iPhone scanning | Barcode and cover text recognition | Free |  | Identify the record (F1, F2) |
| Apple Music API / MusicKit | Catalogue match (including lookup by UPC), artwork, 30 s previews; your library with permission, including plays per song | Apple Developer Program, [US$99 a year](https://developer.apple.com/programs/); AU price shown at enrolment | The printed barcode often differs from the digital UPC, so lookup falls back to artist and title. Whether liked tracks and playlist contents are exposed the way the Library.xml export shows them is *to verify* | Previews, library import, ownership check |
| [Discogs](https://www.discogs.com/developers) (your account) | Your collection and wantlist (read, and add on Buy or Wishlist); search by barcode, catalogue number, artist and title; one release call returns credits, styles, country, label, owner and want counts, copies for sale, lowest price and linked videos; the list of editions of an album | Free | 60 requests a minute with authentication; prices in AUD on request | Identification, collection, credits, styles, price and market numbers, video links |
| YouTube (link only) | Opens the linked video or a search in the YouTube app when you tap Sample, for records that are not on Apple Music | Free | No API call and no key | Sampling fallback (F7) |
| [OpenRouter](https://openrouter.ai) | What the record is, its main style and the closest picks: `openai/gpt-5.6-luna` (primary) or `anthropic/claude-haiku-5.5` (fallback). Reading a cover the phone could not is not yet assigned a model | Pay per call from prepaid credit. OpenRouter's list price on 18 October 2026: luna US$0.10 in / US$0.60 out per million tokens; Haiku 5.5 US$0.10 in / US$0.50 out. Measured cost per record is under Speed and cost | Requests are routed only to providers that support the JSON schema and do not keep the data. The library list makes each request large, so cost depends on caching | Matching and wording |

**What this means for price.** Discogs shows what sellers are asking and how many collectors own and want a record, not what it sold for. The card shows the counts as plain numbers and labels any price as "lowest listed".

**Discogs terms.** The [Discogs API terms](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use) apply from Phase 1, not only at the App Store:

- **Attribution.** "Data provided by Discogs", with a link to the Discogs page, sits next to any Discogs data on the card.
- **Your collection now goes to the model.** The terms class a user's collection and wantlist as restricted data that may not be passed to third parties. The by-sound request sends your shelf list (artist, title, year and styles of records you own) through OpenRouter to the model's provider. For a personal app using your own data this is a small risk that you are accepting; it must be settled with Discogs, or the shelf left out of the request, before any public release. Marketplace data (prices, copies for sale) is never put in a request.
- **Freshness.** Data may not be shown if it is more than 6 hours older than the live site, and may not be stored longer than needed. Release data is fetched live on each scan and your collection is refreshed when the app opens.
- **Fees.** The terms prohibit charging for an app where Discogs offers the same access free, without written permission. A paid app may not be allowed.

## Speed and cost budget

The by-sound request sends your whole library on every scan, so it is the only step with a real running cost. Earlier revisions estimated US$0.01 to US$0.11 per scan with Sonnet 5.5. The prototype models are far cheaper. The figures below are measured: four harness runs on 18 October 2026, 20 records each, with the cost OpenRouter reported for each call (`data/runs/`).

**Measured request size.** The full request is about 24,400 input tokens as luna counts them and about 39,400 as Haiku counts them, against the 45,000 estimated earlier. The answer is about 400 to 500 output tokens from luna and about 900 from Haiku.

**Cost per scan (measured)**

| Step | Runs on | Cost |
| --- | --- | --- |
| Barcode or text recognition, ownership check, fact lines, territory | Your phone | US$0 |
| Apple Music and Discogs lookups, including price | The backend, calling the services directly | US$0 per call |
| What it is, main style and picks, library list read from the cache | `gpt-5.6-luna` | median US$0.0011 (US$0.0009 to US$0.0037) |
| The same, library list not cached | `gpt-5.6-luna` | median US$0.0066 (US$0.0065 to US$0.0082) |
| The same, on the fallback (no cache hits were reported) | `claude-haiku-5.5` | median US$0.0044 (US$0.0040 to US$0.0130) |
| Vision fallback when barcode and text recognition fail | Not chosen yet | not measured |

The top of each range is a record whose first answer was `Other/uncertain`, which triggers the two extra attempts. Caching is up to the provider: in one luna run nearly every request was read from the cache; in the other, minutes later, none was. Haiku requests did not use the cache, because the request does not yet mark the library list for caching, which Anthropic requires.

**Cost per month (average cost per record in each run, extra attempts included)**

| Case | 100 scans | 500 scans |
| --- | --- | --- |
| luna, cache hits as in the first run | about US$0.12 | about US$0.60 |
| luna, no cache hits | about US$0.70 | about US$3.40 |
| Haiku fallback | about US$0.50 | about US$2.40 |

Your typical dig is about 10 closer looks, so 500 scans a month is a heavy month. Even the worst case is a few dollars a month, which leaves F26 (a cheaper way to make the picks) without a cost reason; it would matter only if a small model on a short list picked better or faster.

**Fixed costs and upkeep**

- Apple Developer Program: US$99 a year.
- OpenRouter credit, topped up in advance; at the measured rates a few dollars lasts months.
- The prototype backend runs on your own Linux laptop rather than a hosted server, so there is no hosting cost. The later native product needs a hosted backend before wider distribution.
- The later product uses TestFlight, so updates install over the air. Builds expire after 90 days, so a fresh build is uploaded at least every three months.
- Build effort: not estimated.

**Controls on the model request (requirements)**

- Ownership, the fact lines, the territory rules and price never call the language model.
- One request per scanned album returns the sentence, the main style and the picks together. The answer is stored, so a record scanned twice costs nothing the second time.
- The lists come first in the request and the record last, so the long part is identical from scan to scan and can be cached.
- The request holds your shelf and library lists and the record's catalogue facts. It never holds prices, owner or want counts, or your wantlist.
- The vision model runs only after barcode and text recognition fail, on a downscaled image, and returns artist and title only.

**Speed (proposed; times are from the start of the scan)**

| Stage | Done by | Notes |
| --- | --- | --- |
| Barcode or text read | 0.3 s | On the phone |
| Ownership, fact lines and territory | 1 s after the record is identified | Your collection and library are on the phone |
| Catalogue match and previews | 1.5 s | Apple Music |
| Credits, price and market numbers | 3 s | Discogs search then release |
| What it is, and the picks | 5 to 6 s median after the record is confirmed | Measured in the harness on 18 October 2026: median 5.3 to 5.9 s for luna and 5.5 to 6.2 s for Haiku. The slowest single attempt was 11.5 s; records that needed the two extra attempts took 12 to 23 s in total. This misses the 4-second target for the full card. The card is usable without this section and fills it in when it arrives |
| Vision fallback, when used | adds 2 to 3 s | Starts after barcode and text recognition give up at about 2 s |

A good connection is assumed. If a service fails or is slow, the card shows the sections that arrived and marks the rest as loading.

## Platform and architecture

The prototype is an iPhone-usable web app with a local backend running on your computer. This is deliberately different from the later native iPhone product: the prototype is for validating decision support, not distribution through TestFlight.

- **Browser client:** responsive web UI with barcode/photo input where browser support permits, plus catalogue-number and typed artist/title fallback.
- **Local backend:** handles Discogs and model requests, imports and refreshes local snapshots, validates model IDs, and serves the evidence card.
- **Secrets:** the OpenRouter key is kept in an environment file on the server machine (`~/.config/crate-digger/env`, readable only by your user account), which only the backend service loads. The Discogs token is in `discogs_token.txt` in the project folder, also readable only by you and never committed. Neither is ever sent to browser JavaScript. On the Mac, the scripts can instead read the OpenRouter key from the macOS Keychain.
- **Where it runs:** the backend runs on your Linux laptop and listens only on that machine; Tailscale makes it reachable from your phone and Mac over your private network, and it is not exposed to the public internet.
- **Local data:** imported Discogs collection data and Apple Music library data are stored in snapshots. The Apple Music snapshot includes saved/playlist albums, play counts and liked/favourite tracks.
- **Live data:** the inspected Discogs release is looked up live. Samples and market data are shown when available and are optional for the prototype pass.
- **Model request:** built by the backend from the two snapshots and the inspected record; the response is structured and checked so only IDs from the supplied snapshots can be shown.
- **Later product:** a native Swift iPhone app, TestFlight distribution, Discogs sign-in, a backend suitable for other users, privacy/terms review and eventually Android.

The rules and test files from Phase 0 are in your CrateDigger folder: `engine.py` (fact lines, territory, ownership), `styles.py` (main style families), `library.py` (library import and ownership check) and `sound_picks.py` (the picks you rated).

## Privacy and data handling

For the prototype, the browser connects over Tailscale to the backend on your Linux laptop. Imported snapshots and live lookups are sent only to the services required by the prototype, and model credentials remain on the backend. The later native product will need the fuller privacy and terms review described below. The shelf and library lists go through OpenRouter to the model's provider on each recommendation request; requests are routed only to providers that do not keep the data.

- The prototype's Discogs token and OpenRouter key are stored on the backend machine in files only your user account can read (see Platform and architecture), not in browser JavaScript. They are used to refresh snapshots, look up releases and request recommendations; prototype actions do not modify Discogs.
- The Apple Music Library.xml export is uploaded to the local backend and refreshed explicitly; direct on-device MusicKit access is deferred to the native product.
- Scans send the required identifier to the local backend, which calls Discogs. A barcode is preferred, followed by catalogue number and typed artist/title.
- Each recommendation request sends the configured model the shelf list, library list (including plays and liked/favourite tracks), and inspected record details. Prices, market data, wantlist data and dig history are not sent.
- The prototype stores snapshots and temporary results locally. It does not store decisions, dig history or an Explore later list.
- If a cover image is used, the local backend may send a downscaled image only to the configured vision service; this is not required for the first recommendation harness.
- Discogs data carries the attribution their terms require.
- The App Store version adds a privacy policy, account deletion and a review of how other users' Discogs and library data is handled.

## Risks and open questions

The biggest risks are that records are not identified quickly or to the right edition, that the by-sound request is too slow or too costly at one request per scan, and that the model's picks drift when it is run the way the app will run it.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Used records with no barcode, stylised or abstract covers | Slow or failed identification | Cover text, then vision fallback, then typed search including catalogue number; the crate test |
| Album identified but not the edition | Wrong price, wrong facts, wrong release added to Discogs | No edition-specific numbers and no Buy or Wishlist until the edition is confirmed |
| Sonnet was tested with 15 records in one request, not one per scan | Picks may differ in the app | Re-run through the API, one record per request, before the build |
| The by-sound request is slow | The card's most useful section arrives late | Cache the lists; show the card without it and fill it in; measure before the build |
| Cost per scan is cents, not fractions of a cent | A heavy month costs up to about US$45 | Cache the lists; set a spend limit on the key; build F26 if the cost bothers you |
| The model picks something that is not close, or invents an album | A wrong reason to buy | Returned ids are checked against your lists; at most three picks; the reason is shown so you can judge it |
| The model does not know an obscure record | A vague sentence and loose picks | The card says when the model is unsure; Konoma was the one case in the test |
| Main style families are too wide for jazz | "26 Hard bop, post-bop & soul-jazz records" says little | Split the families once you say which distinctions matter; you left two of 15 unticked |
| The period is the release decade | A 2026 record in a 1950s style reads "2020s" | Shown beside the style, not used to exclude; the model's sentence carries the real character |
| Records on your shelf that are not in Discogs yet (Massive Attack's Mezzanine is one) | The card shows no ownership line for a record you own | The Apple Music line may still catch it; "I own this" adds it on the spot |
| Four actions on a card read in five seconds | A slower or wrong tap | Buy and Pass are the large buttons; test the layout in the first build |
| Price is the cheapest asking price in any condition, and excludes shipping | The sticker comparison flatters or condemns the store unfairly | Label it "lowest listed, any condition, plus shipping" |
| Not on Apple Music, or no preview (Three Blind Mice and similar labels) | Cannot hear it in the app | Open the video Discogs lists, otherwise a YouTube search. In Phase 0, 3 of 14 Three Blind Mice records were found on Apple and all 14 had a Discogs video |
| Discogs terms: your collection in a model request, the 6-hour data limit, attribution, no fees on API apps | Complicates a public or paid release | Personal token and live fetches in TestFlight; settle the terms before the App Store |
| Apple Music library access may not expose liked tracks or playlist contents (*to verify*) | A thinner library list | Import the Library.xml export |
| The OpenRouter key sits on your laptop, and the app has no login | Anyone who reaches the app can spend your credit | The key never leaves the backend; the app is reachable only over your Tailscale network, not the public internet; set a credit limit on the key in OpenRouter; add accounts before any wider release |

**Decided for the later product unless superseded by the prototype scope above**

- Bins are an even mix of used vinyl and barcoded releases, so cover text, catalogue number and the edition list are part of the main path.
- A good connection is assumed and offline is a non-goal.
- The Wishlist is your Discogs wantlist. Apple Music albums you do not own appear as suggestions to add.
- A sticker price field is included for the later product. MusicBrainz is dropped. The later native product uses a secure backend for the model key; the prototype uses its local backend.
- Sample opens the YouTube app for records that are not on Apple Music.
- Distribution of the later product is TestFlight.
- The rarity tiers are removed. A price-range label is parked. Owners, wants and copies for sale stay on the card as plain numbers.
- You decide on three things: where the record sits, what kind of music it is, and how the samples sound. The card is ordered that way.
- Explore later is a fourth outcome.
- Decided in this revision: the closest records are picked by sound by a language model, from your library and shelf, at most three. Sonnet 5.5 is the model. Labels, musicians and one main style are shown as facts, not as a list of similar records. Each record gets one main style, or none where it is unclear.

**Open questions for you**

- **Cost.** Is roughly US$10 to US$45 for a heavy month acceptable for the first build, or should F26 be built and tested first?
- **Jazz families.** Which distinctions matter to you inside "Hard bop, post-bop & soul-jazz" and "Jazz-funk & fusion"? Piano trio, organ soul-jazz and Japanese jazz are the ones your ratings suggest.
- **Sonnet's new picks.** Ticking the 21 unrated picks on the Model tab would turn "at least 10 of 15" into a real number. Optional.
- **Explore later.** Is artist, record, liked tracks and an optional note the right information to capture? Should the tap also add the album to an Apple Music playlist?
- **Four buttons.** Buy, Pass, Explore later and Wishlist: is that the right set, and are those the right names?
- **Portrait In Jazz.** Your collection lists the 1976 reissue. Is that the copy you own?
- **Uncatalogued records.** Mezzanine needs adding to Discogs. Are there others?
- **Price-range label, when you return to it.** The three questions at the end of Price and market numbers.

## Success measures and roadmap

The prototype works if it supplies trustworthy ownership, style and close-match/no-match evidence quickly enough for you to make a manual decision. It does not yet need to keep what you decided or change Discogs.

**Phase 0 so far**

| Test | Result | Status |
| --- | --- | --- |
| Ownership: albums held in two editions | 3 of 3 read "You own a different release" | Passed |
| Library ownership | 10 of 25 wantlist and 27 of 154 shelf records found in your library | Measured; one false match was found and fixed |
| Samples | 167 of 179 (93%) have an Apple catalogue match or a Discogs video. Apple alone: at least 129 (72%). Discogs video: 153 (85%) | Passed, against a target of 80% |
| Closest by sound, picks written by Claude Opus | 15 of 15 rated records with a pick you ticked | Passed, on 15 records |
| Closest by sound, Sonnet 5.5 | at least 10 of 15 | Promising; 21 picks unrated; run as one request |
| Closest by sound, fastest tier | 3 of 15 | Failed |
| Where it sits, as a list of similar shelf records | 9 of 12 records, 14 of 36 matches | Dropped as a list; kept as fact lines |
| Main style | 13 of 15 ticked right; 5 of 179 left blank | Close to target; jazz families may be too wide |
| Territory line | 1 wrong call in 15 | Not yet tested on records you did not choose |
| Shelf records as if not owned | 154 prepared, none rated | Not needed for the decision; skipped |

Fifteen records is a small sample. A result of 15 of 15 is consistent with a true rate anywhere from about 80% upward, and 10 of 15 with roughly 40% to 85%, so these results choose a direction and do not prove a target.

**Still to do before the prototype**

| Test | What it settles |
| --- | --- |
| Verify the OpenAI and Anthropic model IDs and structured-output support | Whether the configured primary and fallback models can be called as planned |
| Build the one-pass recommendation harness against fixed snapshots | Style coverage/accuracy, false close matches, no-match behavior and 20-second timeout behavior |
| One photographed crate, about 50 records (after the harness passes) | Barcode and catalogue-number input, edition selection and the fallback path in a realistic setting |

**Prototype measures**

| Measure | Target | How it is measured |
| --- | --- | --- |
| Style coverage | A specific style family for at least 18 of 20 records | Fixed 20-record set; `Other/uncertain` may occupy at most two records |
| Style accuracy | At least 90% of specific family classifications are correct | Two independent labels, with disagreements resolved before testing |
| False close matches | No more than 15% of records | A clearly unrelated returned match counts as false; an explicit no-match result does not |
| Required evidence | Style, ownership and close-match/no-match result are available | Inspect the card for each record; unavailable recommendations fail availability but are not false matches |
| Decision speed | Required evidence supports a manual decision in under 60 seconds | Time from submitted input to the user's decision |
| Baseline | The same decisions take at least 90 seconds manually | Time the current Discogs lookup plus optional LLM workflow |
| Optional evidence | Samples and price/market data are shown when available | Missing optional data is marked unavailable and does not fail the prototype |
| Model timeout | 20 seconds | Timeout produces `recommendations unavailable` |
| Uncertainty retry | Three attempts only when the first style is `Other/uncertain` | Majority style wins; matches come from the run producing that style; no majority means unavailable |

**Roadmap.** No dates are set; the pace is yours.

| Phase | What happens | Gate to pass before the next phase |
| --- | --- | --- |
| 0. Data test, no app | Done: ownership, samples, library, main style, and the picks on three models. Remaining: Sonnet through the API one record at a time, and the crate | Sonnet's picks hold up one record per request, at a speed and cost you accept; identification reaches 9 in 10 on the crate |
| 1. Prototype web app | Recommendation harness, local snapshots, live inspected-release lookup, evidence card and barcode/catalogue-number/typed input | The 20-record decision-support test passes, including the under-60-second target |
| 2. First native/TestFlight build | Product P0 requirements that were deferred from the prototype: Apple Music integration, action capture, Discogs Buy/Wishlist mutations, Explore later and richer failure handling | Real-store testing confirms identification, evidence, samples, capture, cost and terms targets |
| 3. Wider release | P1/P2 requirements: cheaper picks, wantlist suggestions, dig history, richer price, sonic similarity, App Store backend/accounts and Android |  |

## Revision notes

Revision 7, 18 October 2026:

- Model calls go through OpenRouter. Primary `openai/gpt-5.6-luna` and fallback `anthropic/claude-haiku-5.5` were verified on OpenRouter's live model list; requests go only to providers that honour the JSON schema and do not keep the data. The web app calls the primary; the fallback is compared in the harness.
- Key storage written down: the OpenRouter key in an environment file on the backend machine, the Discogs token in an uncommitted file, both readable only by your account. The backend runs on your Linux laptop, reachable only over Tailscale.
- Cost and speed now measured: about US$0.001 to US$0.007 per record with luna depending on caching, about US$0.004 to US$0.005 with Haiku, so a heavy month is a few dollars. The picks take a median of 5 to 6 s, over the 4-second target.
- F26 no longer has a cost reason.

Revision 6, prototype scope review:

- Decision support is the prototype's sole outcome: the user decides manually; action buttons, history and Discogs mutations are deferred.
- The prototype is an iPhone-usable web app with a local backend, not a TestFlight/native app.
- Identification proceeds barcode, catalogue number, typed artist/title, then a manual edition selection when needed; the prototype never guesses an edition.
- Discogs and Apple Music are imported as local snapshots with an explicit Refresh action; the inspected Discogs release is live.
- Required evidence is style, ownership and a valid close match or explicit no-match. Samples and price are optional.
- The prototype uses a 20-record acceptance test: 18/20 style coverage, at least 90% accuracy among assigned families, no more than 15% false close matches, and under 60 seconds versus a 90-second manual baseline.
- Model evaluation uses one run normally, three runs when the first style is `Other/uncertain`, a 20-second timeout, and separate evaluation of the primary and fallback models.
- The primary and fallback model identifiers are provisional and must be verified before implementation.

Revision 5, 4 October 2026:

- Matching rewritten after the Phase 0 test. The closest records are now picked by sound by a language model from your Apple Music library and shelf (F6), at most three, with a one-sentence description from the same request (F12, moved from P1 to P0). The earlier rule that the language model plays no part in similarity is reversed.
- Sonnet 5.5 chosen for the picks, from a three-way test: picks written by Claude Opus (15 of 15 rated records), Sonnet 5.5 (at least 10 of 15) and the fastest tier (3 of 15).
- The tag-and-credit rules become "Where it sits": fact lines for labels, musicians and one main style (F24, F25). Their list of similar shelf records is dropped.
- One main style per record replaces the Discogs style list, with broad tags ignored and unclear cases left blank.
- The territory line now counts what you play in Apple Music and falls back on the model's picks.
- The Apple Music library is imported from your export of 4 October 2026 (1,327 albums). The job that matched library albums to Discogs is dropped (F21).
- Cost and speed rewritten: a scan now costs an estimated US$0.01 to US$0.11, not US$0.0025. A cheaper design is added as F26.
- Privacy and Discogs terms updated: your shelf and library lists now go to the Claude API on each scan, and your library no longer goes to Discogs.
- The card is shortened to three picks and two or three fact lines, because rating the longer test cards took too long.
- Phase 0 results recorded, and the two tests still to do named.

Revision 4, 4 October 2026:

- How you decide is written into the Problem section: where the record sits, what kind of music it is, then the samples.
- Goals reordered to match. Samples move up to priority 1, a Capture goal is added, and price becomes market context at priority 3.
- Card changed: genre and style move from Facts into the header; the price panel no longer moves up for records that are new to you; tracks can be marked as liked.
- Explore later added as a fourth outcome (F23), with a table of what each tap does. "I own this" added for records on your shelf that are not in Discogs.
- Owners, wants and copies for sale confirmed on the card as plain numbers.
- The parked label is now a price-range label, not a rarity label (F22). Misty and Portrait In Jazz confirmed, with the first pressing noted for Portrait In Jazz; Massive Attack is Mezzanine, owned but not yet in Discogs.
- Risks added for uncatalogued records and for four actions on one card.

Revision 3, 4 October 2026:

- Rarity label parked. The Common, Rare and Collector tiers, their draft rules and the A$100 line are removed from Phase 1, the success measures and the roadmap gate. Your examples and what they suggest are recorded under Price and market numbers. F9 is now price and plain market numbers; the label is F22, parked.
- Collection size corrected from "about 120" to 154 (91 vinyl, 63 CDs), and the wantlist (25 records) added, both from your Discogs exports of 3 October 2026.
- Findings from the exports added to the Similarity engine section: few repeat artists, credits that hide shared musicians, multi-label releases, name variants, missing years, and classical and film music.
- Two Phase 0 tests added that need no store visit: the engine run on your 25 wantlist records, and an ownership test on the three albums you hold in two editions.
- The wantlist is matched at album level, so a different edition of a wanted album is flagged.

Revision 2, changes from the first version, all on 3 October 2026 (the rarity changes listed here are superseded by Revision 3):

- Identification added as the top priority, with its own target, Phase 0 test and success measure. Catalogue number search and an edition list added (F2, F19). Rarity, Buy and Wishlist now wait for a confirmed edition.
- Vision cover recognition (F13) moved from P1 to P0, conditional on a Phase 0 test.
- Problem statement no longer mentions poor signal, since a good connection is assumed.
- Wishlist redefined as the Discogs wantlist; Apple Music albums become suggestions (F10, F11).
- Sticker price field added (F20).
- Library matching job added and sized (F21); library-to-shelf matching now uses artist and title, not barcode. Privacy section corrected to say that library album names are sent to Discogs.
- MusicBrainz removed. Call budget restated per path.
- Rarity rules given a minimum want count and a stricter "Rare" rule; tested on a crate as well as your own records. "Collector" now also needs a lowest listed price of A$100 or more, since you defined it as hard to find and expensive.
- Open questions answered: library size (500 to 1,500 albums), YouTube opens in its own app, wantlist suggestions add the main release, distribution is TestFlight.
- Phase 0 gate redesigned: leave-one-out on your collection plus a photographed crate, marked before seeing output.
- Samples target counts only previews and Discogs-listed videos, lowered from 90% to 80% because a search link no longer counts.
- Proxy removed; Claude key kept in the Keychain. Monthly cost restated as expected and upper-bound figures. TestFlight expiry and unestimated build effort noted.
- Discogs terms section now applies from Phase 1: attribution beside data, restricted data kept out of language-model prompts, caching limits noted.
- Items verified against documentation: counts, price and videos arrive with the Discogs release call; AUD is supported; the 60-a-minute limit; Apple Music lookup by UPC; song play counts in the library; Haiku 4.5 prices.
- The two embedded diagrams (architecture, roadmap) are replaced by text, because they could not be edited here.
