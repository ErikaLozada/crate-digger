"""Crate Digger, Phase 0: one main style per record.

Discogs lists many styles per release, often contradictory. This file groups Discogs styles
into families, ignores the ones too broad to mean anything, and gives each record ONE main
style family. If the styles point to several families and there is no clear majority, the
main style is left blank unless MAIN_STYLE names it (in the app, the language model would
make that call once per record)."""
FAMILIES = {
 'Hard bop, post-bop & soul-jazz': ['Hard Bop', 'Bop', 'Soul-Jazz', 'Cool Jazz', 'Modal', 'Post Bop'],
 'Free & spiritual jazz': ['Free Jazz', 'Spiritual Jazz', 'Avant-garde Jazz', 'Free Improvisation'],
 'Jazz-funk & fusion': ['Jazz-Funk', 'Fusion', 'Jazz-Rock', 'Smooth Jazz', 'Acid Jazz'],
 'Swing & big band': ['Swing', 'Big Band'],
 'Latin jazz': ['Latin Jazz', 'Afro-Cuban Jazz'],
 'Salsa & Cuban': ['Salsa', 'Mambo', 'Son', 'Guaguancó', 'Boogaloo', 'Cha-Cha', 'Descarga', 'Rumba', 'Cubano',
                   'Afro-Cuban', 'Son Montuno', 'Guajira', 'Guaracha', 'Plena', 'Merengue', 'Bolero'],
 'Bossa nova & MPB': ['Bossa Nova', 'Bossanova', 'MPB', 'Samba'],
 'City pop & AOR': ['City Pop', 'AOR', 'Kayōkyoku'],
 'Soul, funk & disco': ['Soul', 'Funk', 'Neo Soul', 'Rhythm & Blues', 'Contemporary R&B', 'Disco'],
 'Trip hop & downtempo': ['Trip Hop', 'Downtempo'],
 'House-jazz': ['Future Jazz'],
 'House & dance': ['House', 'Deep House', 'Euro House', 'Garage House', 'Hip-House', 'Trance', 'Drum n Bass', 'Electro'],
 'Ambient & modern classical': ['Ambient', 'Modern Classical', 'Neo-Classical', 'Dark Ambient'],
 'Film & TV score': ['Soundtrack', 'Score', 'Theme'],
 'Anime music': ['Anison'],
 'Romantic & Impressionist classical': ['Romantic', 'Late Romantic', 'Neo-Romantic', 'Impressionist'],
 'Baroque & Classical-era': ['Baroque'],
 '20th-century classical': ['Modern', 'Contemporary'],
 'Choral & opera': ['Choral', 'Motet', 'Opera'],
 'Classical guitar & flamenco': ['Classical Guitar', 'Flamenco'],
 'Pop rock': ['Pop Rock', 'Soft Rock', 'Power Pop', 'Classic Rock', 'Britpop', 'Indie Pop', 'Europop', 'Synth-pop',
              'New Wave', 'Alt-Pop', 'Latin Pop', 'Reggae-Pop'],
 'Alternative & indie rock': ['Alternative Rock', 'Indie Rock', 'Post Rock', 'Pop Punk'],
 'Hard rock & metal': ['Hard Rock', 'Heavy Metal', 'Arena Rock', 'Glam'],
 'Prog & art rock': ['Prog Rock', 'Art Rock', 'Symphonic Rock', 'Space Rock', 'Psychedelic Rock'],
 'Folk & country': ['Folk', 'Folk Rock', 'Country'],
}
# Too broad, or describing form and not sound: never used for matching.
IGNORED = ['Contemporary Jazz', 'Vocal', 'Easy Listening', 'Ballad', 'Orchestra', 'Symphony', 'Concerto', 'Piano',
           'Theme With Variations', 'Tone Poem', 'Suite', 'Dances', 'Ballet', 'Dialogue', 'Spoken Word', 'Light Music',
           'Psychedelic', "Min'yō", 'African', 'Classical', 'Guarania', 'Lovers Rock', 'Industrial', 'Experimental', 'Abstract']
FAMILY_OF = {s: f for f, ss in FAMILIES.items() for s in ss}

# Apple Music genres that correspond to a family, for counting what is in the library.
APPLE_GENRES = {
 'Salsa & Cuban': ['Música tropical', 'Cuban', 'Salsa y Tropical'],
 'Bossa nova & MPB': ['MPB', 'Bossa Nova', 'Brazilian', 'Samba'],
 'Latin jazz': ['Latin Jazz'],
 'Hard bop, post-bop & soul-jazz': ['Jazz', 'Bop', 'Hard Bop', 'Mainstream Jazz'],
 'Free & spiritual jazz': ['Jazz', 'Avant-Garde Jazz'],
 'Jazz-funk & fusion': ['Jazz', 'Fusion', 'Crossover Jazz', 'Contemporary Jazz', 'Funk'],
 'Swing & big band': ['Jazz', 'Big Band'],
 'City pop & AOR': ['J-Pop'],
 'Soul, funk & disco': ['R&B/Soul', 'Soul', 'Funk', 'Contemporary R&B'],
 'Trip hop & downtempo': ['Electronic', 'Downtempo', 'Electronica'],
 'House-jazz': ['Electronic', 'Dance', 'Jazz'],
 'House & dance': ['Dance', 'Electronic', 'House'],
 'Ambient & modern classical': ['Ambient', 'Classical Crossover', 'New Age'],
 'Film & TV score': ['Soundtrack', 'Original Score', 'TV Soundtrack', 'Video Game'],
 'Anime music': ['Anime'],
 'Romantic & Impressionist classical': ['Classical'], 'Baroque & Classical-era': ['Classical'],
 '20th-century classical': ['Classical'], 'Choral & opera': ['Classical', 'Opera'],
 'Classical guitar & flamenco': ['Classical', 'Flamenco'],
 'Pop rock': ['Pop', 'Rock', 'Pop/Rock'], 'Alternative & indie rock': ['Alternative', 'Indie Rock', 'Rock'],
 'Hard rock & metal': ['Rock', 'Hard Rock', 'Metal'], 'Prog & art rock': ['Rock', 'Prog-Rock/Art Rock'],
 'Folk & country': ['Folk', 'Singer/Songwriter', 'Country', 'Alternative Folk', 'Traditional Folk'],
}
# Families whose Apple genre is much broader than the family: the card says so.
BROAD_APPLE = {'Hard bop, post-bop & soul-jazz', 'Free & spiritual jazz', 'Jazz-funk & fusion', 'Swing & big band',
               'City pop & AOR', 'Trip hop & downtempo', 'House-jazz', 'House & dance', 'Romantic & Impressionist classical',
               'Baroque & Classical-era', '20th-century classical', 'Choral & opera', 'Classical guitar & flamenco',
               'Pop rock', 'Alternative & indie rock', 'Hard rock & metal', 'Prog & art rock', 'Folk & country',
               'Soul, funk & disco'}

# Families that Discogs has no style for; they are only ever assigned by name below.
NAMED_ONLY = ['ECM & European contemporary jazz', 'Vocal jazz', 'Classical crossover']
APPLE_GENRES.update({'ECM & European contemporary jazz': ['Jazz', 'Contemporary Jazz'], 'Vocal jazz': ['Jazz', 'Vocal Jazz'],
                     'Classical crossover': ['Classical Crossover']})
BROAD_APPLE |= {'ECM & European contemporary jazz', 'Vocal jazz'}

# One line per family for the model's prompt, written with the user. Examples avoid the
# records in data/eval_set.json, so the definitions don't hand the test its answers.
DEFINITIONS = {
 'Hard bop, post-bop & soul-jazz': 'acoustic small-group jazz from the bop lineage, 1950s on: swinging Blue Note/Prestige-style dates, blues and modal playing, organ soul-jazz grooves',
 'Free & spiritual jazz': 'jazz that puts devotion or freedom ahead of swing: modal drones, harp, chant, mystic or raga-like moods, open-form or collective improvisation',
 'Jazz-funk & fusion': 'electric jazz on funk or rock rhythms: electric piano, synths, electric bass, backbeat grooves; includes smooth jazz and acid jazz',
 'Swing & big band': 'swing-era jazz and large-ensemble arrangements, 1930s-50s and in that manner',
 'Latin jazz': 'jazz improvisation over Afro-Cuban or other Latin rhythms, where the jazz soloing leads',
 'ECM & European contemporary jazz': 'spacious, lyrical jazz with chamber-like interplay and a European feel, acoustic or with electric piano, on ECM or in its manner (Keith Jarrett, Jan Garbarek, Tord Gustavsen)',
 'Vocal jazz': 'jazz led by a singer: standards, ballads, scat',
 'Salsa & Cuban': 'Cuban and Caribbean dance music led by the clave and the song: son, mambo, salsa, boogaloo, bolero; Latin funk goes under Soul, funk & disco',
 'Bossa nova & MPB': 'Brazilian popular music (bossa nova, samba, MPB, tropicalia), including its funk- and pop-leaning 70s-80s records',
 'City pop & AOR': 'polished late-70s/80s Japanese pop and its West Coast AOR models: glossy studio sound, smooth funk-tinged arrangements',
 'Soul, funk & disco': 'soul, R&B, funk, Latin funk and disco, from 60s soul to neo-soul, where the groove and the vocal lead rather than jazz soloing',
 'Trip hop & downtempo': 'slow, atmospheric, beat-based electronic music, often sampled with jazz or soul textures, made for listening rather than the dance floor',
 'House-jazz': 'house rhythms played or sampled with jazz: live horns, keys and percussion at a relaxed tempo between the club and the listening room (nu-jazz, future jazz)',
 'House & dance': 'club music made for dancing: house, deep house, trance, drum and bass, electro',
 'Ambient & modern classical': 'minimal, textural or slowly unfolding music, electronic or acoustic, from ambient to post-classical piano and strings (Max Richter)',
 'Film & TV score': 'music written for live-action film, TV or games',
 'Anime music': 'soundtracks and songs from anime and animated films',
 'Romantic & Impressionist classical': 'concert music of about 1820-1920 (Chopin, Brahms, Rachmaninoff, Debussy, Ravel)',
 'Baroque & Classical-era': 'concert music of about 1600-1820 (Bach, Vivaldi, Handel, Mozart, Haydn)',
 '20th-century classical': 'concert music after about 1910: modernism, minimalism, holy minimalism (Stravinsky, Barber, Part, Reich)',
 'Choral & opera': 'classical works led by voices: choral music, masses, opera',
 'Classical guitar & flamenco': 'solo or small-ensemble classical guitar and flamenco',
 'Classical crossover': 'classical voices or repertoire packaged for a pop audience (Andrea Bocelli)',
 'Pop rock': 'melodic mainstream pop and rock, from classic and soft rock to new wave, synth-pop and Latin pop',
 'Alternative & indie rock': 'guitar rock outside the mainstream, 1980s on: alternative, grunge, indie, post-rock, pop punk',
 'Hard rock & metal': 'heavy, riff-driven rock: hard rock, arena rock, glam, heavy metal',
 'Prog & art rock': 'rock with long forms, unusual structures or experimental textures: progressive, art, symphonic, space and psychedelic rock',
 'Folk & country': 'acoustic song traditions and what grew from them: folk, folk rock, singer-songwriter, country',
}

# Main style named record by record, where Discogs styles conflict, are missing or mislead.
# Written by Claude in the working session, standing in for the one-time call the app would
# make to a language model. None means "not clear: leave blank".
J, F, H = 'Jazz-funk & fusion', 'Film & TV score', 'Hard bop, post-bop & soul-jazz'
E, P, X = 'ECM & European contemporary jazz', 'Pop rock', 'Classical crossover'
MAIN_STYLE = {
 8276381: P, 13682715: 'Alternative & indie rock', 4812238: J, 15706565: P, 1866293: J,
 21263395: 'Trip hop & downtempo', 789623: J, 23556914: X, 36737404: 'Ambient & modern classical',
 2259338: E, 9985337: E, 3197708: E, 12596028: E, 1516744: 'Soul, funk & disco', 6881609: 'Baroque & Classical-era',
 8981764: 'House & dance', 8852277: P, 10261281: P, 4017977: P, 2544111: P, 14823982: 'Vocal jazz',
 8328639: 'Choral & opera', 34457932: None, 10739269: 'Romantic & Impressionist classical',
 3589286: 'Trip hop & downtempo', 5928749: 'House-jazz', 7564034: 'House-jazz', 6273953: '20th-century classical',
 33243735: H, 31069463: H, 7118739: H, 4468845: H, 24676892: H, 33376985: None, 16150865: F, 16150880: F, 10522015: F,
 15966187: F, 22369048: X, 2867602: X, 10951449: X, 4833717: 'Bossa nova & MPB', 5277949: 'Swing & big band',
 11690428: 'Classical guitar & flamenco', 7633364: 'Romantic & Impressionist classical', 26948018: 'City pop & AOR',
 28753711: J, 34921262: 'Free & spiritual jazz', 16030720: None, 2499163: J, 35896225: None, 31167839: J,
 7021131: 'Romantic & Impressionist classical', 9345009: 'Classical guitar & flamenco',
}
# For these the family already names the period of the music; the recording year adds nothing.
NO_PERIOD = {'Romantic & Impressionist classical', 'Baroque & Classical-era', '20th-century classical', 'Choral & opera',
             'Classical guitar & flamenco', 'Classical crossover'}

def main_family(styles, genres, rid=None):
    """(family or None, how): one main style family for a record."""
    if rid in MAIN_STYLE: return MAIN_STYLE[rid], 'named'
    votes = {}
    for s in styles:
        f = FAMILY_OF.get(s)
        if f == '20th-century classical' and 'Classical' not in genres: f = None
        if f == 'Baroque & Classical-era' and 'Classical' not in genres: f = None
        if f: votes[f] = votes.get(f, 0) + 1
    if not votes: return None, 'no usable style'
    top = sorted(votes.items(), key=lambda x: -x[1])
    if len(top) == 1: return top[0][0], 'only family'
    if top[0][1] > top[1][1]: return top[0][0], 'majority'
    return None, 'conflict'
