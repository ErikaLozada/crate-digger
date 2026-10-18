import unittest

import library


def album(title, artist='Hiromi'):
    return {'artist': artist, 'album': title, 'n_artist': library.norm(artist),
            'n_album': library.norm(title)}


class AlbumOwnershipTests(unittest.TestCase):
    def test_known_editions_still_match(self):
        pairs = [
            ('Orphée', 'ORPHEE'),
            ("Don't Look Back", 'Don’t Look Back'),
            ('Album - Deluxe Edition', 'Album — Deluxe Edition'),
            ('Tourist', 'Tourist (Remastered) [Deluxe Version]'),
            ('Royal Flush', 'Royal Flush (feat. Herbie Hancock) [Remastered 2014]'),
            ('Speak No Evil', 'Speak No Evil (Rudy Van Gelder Edition)'),
            ('The Blue Notebooks', 'The Blue Notebooks (15 Years)'),
            ('Blue Train: The Complete Masters', 'Blue Train'),
            ('Album: Subtitle', 'Album: Subtitle (Deluxe Edition)'),
            ('Album', 'Album - 2015 Remaster'),
            ("Live At Vidro '77", "Live at Vidro'77"),
        ]
        for target, saved in pairs:
            with self.subTest(target=target, saved=saved):
                entry = album(saved)
                self.assertIs(library.find_album([entry], ['Hiromi'], [target]), entry)

    def test_different_titles_and_recordings_do_not_match(self):
        pairs = [
            ('Out There', 'OUT THERE: Strollin’ (Live at Sony Hall/ 2025) [feat. Sonicwonder] - Single'),
            ('Out There', 'Out There (Live)'),
            ('Out There', 'Out There - Single'),
            ('Out There', 'Out There - EP'),
            ('Out There', 'Out There Again'),
            ('Out There', 'Out There 2'),
            ('Album Volume 1', 'Album Volume 2'),
            ('Album (Part One)', 'Album (Part Two)'),
        ]
        for target, saved in pairs:
            with self.subTest(target=target, saved=saved):
                self.assertIsNone(library.find_album([album(saved)], ['Hiromi'], [target]))
                self.assertIsNone(library.find_album([album(target)], ['Hiromi'], [saved]))

    def test_matching_title_still_requires_artist(self):
        self.assertIsNone(library.find_album([album('Out There')], ['Someone Else'], ['Out There']))

    def test_exact_album_wins_over_similarly_named_single(self):
        single, full = album('Out There - Single'), album('Out There')
        self.assertIs(library.find_album([single, full], ['Hiromi'], ['Out There']), full)


if __name__ == '__main__':
    unittest.main()
