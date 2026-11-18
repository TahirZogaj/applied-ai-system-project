# VibeMatch Genre Guide

Custom knowledge base retrieved alongside the song catalog. Each section is one
retrievable document. Fields:

- `type`: `genre` (in the catalog) or `missing` (not in the catalog)
- `moods`: catalog moods that usually go with this genre
- `energy`: typical energy on a 0-1 scale
- `acoustic`: whether the genre is usually acoustic
- `nearest`: (missing genres only) closest catalog genres
- `keywords`: activities, settings and synonyms people use when they want this sound

## lofi
type: genre
moods: chill, focused
energy: 0.40
acoustic: yes
keywords: study, studying, homework, exam, coding, programming, work, working, reading, focus, concentrate, concentration, background, beats, cafe, rainy, rain, late night
Lo-fi hip hop is slow, warm, slightly dusty instrumental music. Its steady beat and lack of lyrics make it the classic soundtrack for studying, coding and other focused work.

## ambient
type: genre
moods: chill, peaceful
energy: 0.25
acoustic: yes
keywords: sleep, sleeping, meditate, meditation, yoga, space, spa, breathe, unwind, background, drone, float
Ambient music is slow, textured and mostly beatless. It fades into the background, which suits sleep, meditation and winding down.

## classical
type: genre
moods: peaceful
energy: 0.20
acoustic: yes
keywords: piano, orchestra, orchestral, violin, sonata, symphony, sleep, reading, dinner, elegant, quiet, instrumental
Classical pieces such as piano sonatas are acoustic, quiet and calm, good for reading, sleeping or a quiet dinner.

## jazz
type: genre
moods: relaxed
energy: 0.40
acoustic: yes
keywords: smooth, coffee, cafe, dinner, cooking, sunday, brunch, saxophone, unwind, evening, lounge, wine
Jazz in this catalog is relaxed, acoustic and mid-tempo, good for coffee shops, cooking, Sunday mornings and unwinding after work.

## r&b
type: genre
moods: romantic
energy: 0.55
acoustic: no
keywords: date, romance, romantic, love, slow jam, jams, smooth, sensual, night, valentine, partner
R&B blends smooth vocals with soft grooves. Slow, romantic R&B is the go-to for date nights.

## folk
type: genre
moods: sad
energy: 0.25
acoustic: yes
keywords: guitar, acoustic, singer, songwriter, rainy, rain, heartbreak, breakup, lonely, cry, reflective, quiet, campfire
Folk is acoustic, guitar-led and lyrical. The folk in this catalog is quiet and sad, suited to rainy days and heartbreak.

## blues
type: genre
moods: melancholic
energy: 0.45
acoustic: yes
keywords: heartbreak, breakup, lonely, guitar, soulful, bar, whiskey, melancholy, down, rainy
Blues is soulful, guitar-driven and melancholic, music for feeling down or working through a breakup.

## country
type: genre
moods: nostalgic
energy: 0.50
acoustic: yes
keywords: road trip, drive, driving, truck, porch, summer, hometown, nostalgia, memories, banjo, southern, highway
Country is story-driven and nostalgic, with acoustic instruments. It's a classic for long drives and back-porch evenings.

## pop
type: genre
moods: happy, intense
energy: 0.85
acoustic: no
keywords: upbeat, catchy, radio, hits, sing along, singalong, road trip, party, dance, cleaning, happy, feel good, mainstream
Pop is catchy, upbeat and polished, built for singing along on road trips, at parties or while cleaning the house.

## indie pop
type: genre
moods: happy
energy: 0.75
acoustic: no
keywords: indie, alternative, quirky, summer, sunny, rooftop, festival, bright, road trip
Indie pop is bright and upbeat but less mainstream than pop, good for sunny days, rooftops and festivals.

## rock
type: genre
moods: intense
energy: 0.90
acoustic: no
keywords: guitar, loud, band, workout, gym, running, run, adrenaline, drive, headbang, stadium
Rock is loud, guitar-driven and intense, great for workouts, running and driving fast.

## metal
type: genre
moods: angry, intense
energy: 0.95
acoustic: no
keywords: heavy, loud, aggressive, angry, rage, gym, workout, lifting, headbang, mosh, scream
Metal is the heaviest, loudest genre in the catalog: aggressive, fast and built for lifting weights or venting anger.

## edm
type: genre
moods: energetic
energy: 0.95
acoustic: no
keywords: electronic, dance, club, rave, festival, party, drop, bass, workout, gym, cardio, techno, house
EDM is fast electronic dance music with big drops, made for clubs, festivals, parties and cardio.

## hip hop
type: genre
moods: confident
energy: 0.75
acoustic: no
keywords: rap, beats, bars, confidence, hype, swagger, gym, walk, street, urban, flex
Hip hop pairs rhythmic rapping with punchy beats. It brings confident, swaggering energy for workouts or walking around the city.

## synthwave
type: genre
moods: moody
energy: 0.75
acoustic: no
keywords: night, drive, driving, city, neon, retro, 80s, eighties, cyberpunk, late night, highway, synth
Synthwave is retro 1980s-style electronic music. Moody and neon-lit, it's the classic late-night city drive soundtrack.

## reggae
type: genre
moods: uplifting
energy: 0.60
acoustic: no
keywords: beach, island, summer, sunny, chill, barbecue, bbq, vacation, tropical, riddim, laid back
Reggae has a laid-back offbeat groove and uplifting feel, perfect for the beach, barbecues and summer vacations.

## latin
type: genre
moods: festive
energy: 0.85
acoustic: no
keywords: salsa, reggaeton, bachata, dance, dancing, party, fiesta, spanish, summer, celebrate, celebration, tropical
Latin music in the catalog is festive and danceable, made for parties, celebrations and dancing.

## k-pop
type: missing
nearest: pop, edm
keywords: kpop, korean, idol, bts, blackpink
K-pop is NOT in this catalog. The closest available sounds are upbeat pop and high-energy EDM.

## afrobeats
type: missing
nearest: latin, reggae
keywords: afrobeat, african, nigerian, amapiano
Afrobeats is NOT in this catalog. The closest available sounds are festive latin and uplifting reggae.

## punk
type: missing
nearest: rock, metal
keywords: punk rock, pop punk, mosh
Punk is NOT in this catalog. The closest available sounds are intense rock and metal.

## soul
type: missing
nearest: r&b, blues
keywords: motown, gospel, funk
Soul is NOT in this catalog. The closest available sounds are romantic r&b and melancholic blues.

## j-pop
type: missing
nearest: pop, indie pop
keywords: jpop, japanese, anime
J-pop is NOT in this catalog. The closest available sounds are pop and indie pop.
