"""Changes to the user's Discogs account: Buy adds to the collection, Wishlist to the wantlist, and both can be undone.
After a successful call the local export (data/collection.csv, data/wantlist.csv) is updated to match.
CD_DISCOGS_DRY=1: no network and no file changes; calls return made-up ids. Workers and tests must use it.
Stub from the lead (task 0); the discogs-writes task fills in the bodies and keeps these signatures."""
import os

DRY = os.environ.get('CD_DISCOGS_DRY') == '1'

class DiscogsError(Exception):
    """A Discogs call failed; the message is safe to show on the card."""

def buy(rid):
    """Adds release rid to collection folder 1 (Uncategorized). Returns {'folder_id': 1, 'instance_id': int}."""
    raise NotImplementedError

def unbuy(rid, folder_id, instance_id):
    """Removes that collection instance again."""
    raise NotImplementedError

def want(rid):
    """Adds release rid to the wantlist. Returns {}."""
    raise NotImplementedError

def unwant(rid):
    """Removes release rid from the wantlist."""
    raise NotImplementedError
