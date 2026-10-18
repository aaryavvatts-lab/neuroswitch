# DIRECTION SHEET — The printed annual
seed 1447503330 · drawn 2026-10-18 · sector health
Brief: neuroswitch: does the brain rewire after a hand injury; fMRI of 25 nerve-injury patients and 46 controls drawing with each hand, a per-person brain network, four tests built to break the result, still running at 18 of about 66 people

| | |
| --- | --- |
| Direction | The printed annual |
| Hero | Narrow talk, wide headline |
| Type | kept from the brand |
| Colour | kept from the brand |
| Sections | intro (Lead line over four columns) → how-it-works (Run-in column) → stats (One figure owns the screen) → showcase (One row, three states) → list (Statement, table pushed right) → footer (Name first, places under it) |
| Motion | Masked headline |
| Photographs | the "People" set, as atmosphere |

This is the direction for this build. Adopt it. Do not blend it with the layout you would have made anyway,
and do not redraw because it is unfamiliar: unfamiliar is the point. Redraw a slot only when it conflicts
with a stated brand constraint or needs an asset that does not exist, and say why in your report.

The parts of this sheet were written separately and will disagree in small ways. Settle every disagreement in this order:
**house rules** (including type no smaller than 13px and body text of 16px or more) → **the direction** (the idea, the composition habits, where the
one accent goes) → **the type system and the palette** (which face does which job, the five size steps, which colour is the ground and where the
accent goes) → **the hero blueprint** → **the section blueprints**. Under each blueprint below, "Adjusted for this page" lists where it disagrees.
In practice: take geometry from blueprints (columns, proportions, what sits where) and take everything else from above them. Map every size a
blueprint names onto one of your five type steps instead of adding a sixth. Use one button shape, one corner radius and one pair of page margins on
the whole page, whatever individual blueprints say. If a blueprint names a kind of typeface (a light serif, a heavy grotesk), use the dealt face.

## 1. The idea
Lay the page out like a well-designed printed report or magazine feature: a masthead image, a tight oversized title, text held to a strict column line, and colour used in solid blocks the way a two-colour print job would. It gives weight and authority to subjects that are really about content: findings, a manifesto, a programme, a serious product. The reader should feel that someone edited this.

Before anything else, write one sentence in your notes: "On this page, <the subject's own material> becomes <the device>."
Fill the first blank from your inventory of what only this client has (its name and what it means, its street, its numbers, its
constraint), then put the nearest competitor in the sentence: if it still works, the idea is the category's, not the client's.
Then name the one live thing the visitor can do on the page (SKILL.md step 4).

## 2. Composition
A fixed vertical axis at about 42% of the viewport width organises everything: headings begin on it, body columns hang from it, and the 0–42% zone holds small side notes, figures or stays empty. Masthead: a wide image band (photographic mosaic or a single crop) across the top 45% of the first screen; below it the title at 7–9vw starting on the axis, with a two-sentence standfirst at 20–24px. Sections alternate between text pages (title on the axis, body in one or two columns of 34–40ch to its right) and full-bleed colour pages carrying one large figure, quotation or image mosaic. Mosaics are gutterless: photographs and flat colour tiles butted together in a 4- or 6-cell grid. Page numbers, running heads and other print furniture are left out.

## 3. Type
Kept from the brand. A tight heavy grotesk or a sharp serif for titles; an excellent text face for reading at 18–20px with leading near 1.5. Headings in sentence case, tracked tight.

## 4. Colour
Kept from the brand. Paper, ink and two or three solid block colours. A colour page is a whole section in one flat colour.

## 5. Imagery
**The project has no photographs of its own yet.** First choice: **real pictures of the subject's world from the open collections**: its city and street in old postcards and photographs, an old map of the neighbourhood, its materials up close, its trade in engravings, museum objects of its kind (references/imagery.md §3). Start with `node /Users/aaryav-sharma/.claude/skills/design-taste-frontend/scripts/assets.mjs "injury"`, then queries from your inventory (its street, its materials, its trade's tools and history). Download what you use into the project with `--get` and credit every one on the page (`--credits` prints the footer line). They show the world around the client, never the client's own room, dish, product, person or team. Second, for what no honest picture exists of: draw the subject's own things in code, large, in one flat graphic language and the palette's real colours (its tiles, its windows, its objects; references/imagery.md §8). Third: the dealt photographs, only where an honestly generic picture fits (the sea, the weather, a material), never one a visitor could take for the thing itself and never an unrelated scene. One treatment for all of them. If this direction is built on photographs, plan the set before building (four to six pictures of one family) and reuse them at different crops and scales instead of finding or drawing a new picture for every slot; keep drawings as `<symbol>` + `<use>` or generate them with a small script so the page stays light. List every found picture (with its source and licence), every dealt photograph and every drawing that stands in for photography in your report.

Photographs used as blocks in mosaics alongside flat colour tiles; mixed subjects are fine if cropped tight and converted to one treatment.

**Floor (the inspector checks it):** at least four real pictures on the page, usually six to twelve; SVG drawings do not count. One moving picture where an honest clip exists: `node <skill>/scripts/assets.mjs --video "<query>"`, used as a muted loop with a poster frame. Whatever this direction says about pictures, it is carried out with real ones.

Photographs dealt for this build, from the "People" set (figures, silhouettes and portraits, mostly unposed)
Order of preference for imagery: (1) the project's own photographs and product shots; (2) images you generate, if an image tool is
available; (3) real pictures of the subject's world found in the open collections (assets.mjs, downloaded and credited on the page);
(4) drawings of the subject in code; (5) these. They are real photographs (Unsplash licence, served by picsum.photos) of places, light and
texture. They are atmosphere, never a stand-in for a specific product, dish, person or interface. List the ones you use in your report so
they can be replaced.
Treatment: Give all photographs in a mosaic one treatment: greyscale via `filter: grayscale(1) contrast(1.05)`, or all full colour. Do not mix.
- `https://picsum.photos/id/338/1600/1000` — Person in a hooded coat seen from behind facing a misty sea · mid tone · slate blue, grey, charcoal · calm area: left · native landscape · photo: Patryk Sobczak
- `https://picsum.photos/id/669/1600/1000` — Person in a mustard jacket and grey beanie seen from behind in fog · light tone · mustard, pale grey, white · calm area: left · native landscape · photo: Luke Pamer
- `https://picsum.photos/id/726/1600/1000` — Person in a red jacket standing in a snowy, misty landscape · light tone · white, pale grey, red · calm area: bottom · native landscape · photo: Caleb George
- `https://picsum.photos/id/1006/1600/1000` — Person sitting on a rocky overlook above misty forested hills · mid tone · dusky purple, olive green, grey · calm area: top · native landscape · photo: Vladimir Kudinov
- `https://picsum.photos/id/768/1600/1000` — Person sitting alone on a bench facing sandy dunes · light tone · sand beige, pale blue, soft white · calm area: top · native landscape · photo: Mikael Kristenson
- `https://picsum.photos/id/1005/1600/1000` — Person in a scarf seen from behind, looking at the sea at dusk · mid tone · warm sand, dark brown, pale peach · calm area: left · native landscape · photo: Matthew Wiebe
- `https://picsum.photos/id/473/1600/1000` — Person in dark clothes standing on a jetty facing misty mountains · mid tone · slate blue, black, pale grey · calm area: right · native landscape · photo: Todd Quackenbush
- `https://picsum.photos/id/91/1600/1000` — Person in dark jacket holding a vintage twin-lens camera, monochrome · mid tone · grey, black · black-and-white · native landscape · photo: Jennifer Trovato
The last two path numbers are width and height: request the exact crop you render (`/1200/1500` for a 4:5 portrait, `/2400/1350` for a hero) and
add `?grayscale` to desaturate. Use three to six of them, not all eight. Always set `width`, `height`, `alt` and `loading="lazy"` (not on the hero image).
Other sets that fit this brief: fog-and-quiet, coast, water, interior-and-table — `node draw.mjs --photos <set>` prints one in full; `--photos list` shows all sets. Taking photographs from another set is your call and is not a redraw; keep them to one light and one treatment.

## 6. Hero — Narrow talk, wide headline
An asymmetric sheet on one flat paper-grey ground, divided at 34% of the width by alignment only. Left column (columns 1-4, 32px margin): the wordmark top-left; then, starting at 30% of the height, one supporting sentence at 22px with leading 1.35, max 24ch; under it the single action, a solid ink rectangle with square corners. The column's lower third is empty. Right column (columns 5-12): four text links at 15px on its top edge, the first aligned exactly to the 34% line. Beneath them the headline in a very heavy grotesk at clamp(88px, 9.8vw, 150px), two lines, line-height 0.82, tracking -0.04em, flush left on the 34% line and filling the column width. A square-cornered photograph the full width of the right column starts at 68% of the viewport height and is cropped by the bottom edge. A solid accent block 260px wide, carrying one real figure at 40px and one line of text, overlaps the photograph's top-left corner by half its own height using a negative top margin.

On a phone: One column on 20px margins. The wordmark and a menu word share the top row. The headline comes first at 15vw on two lines, heavy, line-height 0.85. The supporting sentence follows at 18px, then the action at full width. The photograph runs full bleed below at 4:3, with the accent block overlapping its top-left corner at 60% of the screen width.
Headline: A 2-4 word statement in the heaviest weight, at most 20 characters, one or two words per line.

Adjusted for this page:
- It names a kind of typeface: use the brand faces.
- It names colours (grey): map them onto this palette's roles (ground `--bg`, panels `--surface` and the fields, text `--ink`/`--muted`, the accent `--accent` on the primary action only).

## 7. Sections, in order
Each is a composition to rebuild with this project's content. Keep the geometry; change the subject. Re-order or drop a
section when the argument of the page needs it (see references/copy.md), never to fall back to a card grid.

### 1. intro — Lead line over four columns (grid)
Two parts on one 12-column grid with 20px margins. First, a lead paragraph of 30–40 words spans all 12 columns at clamp(22px, 2.2vw, 32px), regular weight, leading 1.2: three lines that read as the opening of a text, with no heading before it. 72px below, four equal columns (three grid columns each, 24px gutters) carry small text at 14–15px with leading 1.45. Each column is one paragraph of 40–70 words that opens with a bold run-in phrase of two or three words in full ink, the rest continuing on the same line in the soft ink. Columns top-align and end ragged at different depths. No cards, icons or dividers; the bold run-ins are the only markers. The four columns answer four plain questions: who, what, where, how to reach them. Padding is modest, 96px top and bottom, so a sheet of images can start straight after.
On a phone: The lead paragraph at 20px, full width. The four columns become a two-by-two grid with a 20px gutter and 40px row gap at 14px; if any paragraph exceeds 60 words, switch to one column with 32px between paragraphs. Run-in phrases stay bold.

### 2. how-it-works — Run-in column (list)
The quietest sequence: one reading column and good typography. A single column 520–600px wide starts at about 30% of the viewport width (or sits on the page's text axis). The heading is a two-to-five-word question or statement at 28–32px, 48px above the first paragraph. Three to five paragraphs follow at 17–18px with line-height 1.6. Each opens with a bold run-in phrase in full ink that names its moment ('To begin,', 'Within a day,', 'After that,', 'From then on,') while the rest of the paragraph runs in the soft ink; there are no subheads, bullets or markers. After each paragraph, 20px lower, comes one small piece of evidence exactly as wide as the column: a cropped interface fragment, a photograph at 16:9, or a row of three small frames 96px tall. 72px separates stages. Nothing in the section is wider than the column, and the space to its left stays empty.
On a phone: The column fills the width between 20px margins. Type stays at 17px. Evidence pieces keep the column width; the row of three frames becomes a single sideways-scrolling row 88px tall. 56px between stages. The heading drops to 24px.

### 3. stats — One figure owns the screen (statement)
One number, one screen. A flat field at least 90svh tall. At the top-left, starting on the page's main axis, a one-line claim of two to five words at 36–44px: this is the heading. Then a long gap of 22–28vh. At the bottom-left on the same edge, a single figure at clamp(180px, 23vw, 380px), leading 0.8, tight tracking, with its unit (a percent sign, 'x', 'hrs') set as a superscript one third of the figure's size and aligned to the figure's cap height. Directly beneath, flush with the figure's left edge, a caption of three lines at 16–17px, 32ch wide, saying exactly what was measured and when. The right half of the field stays empty; resist filling it. The figure is static text in lining numerals and does not animate. A source line, if needed, sits at the bottom-right at 15px.
On a phone: The claim sits at the top at 28px. The figure is 46vw, flush left, with its superscript unit; if it has four characters or more, drop it to 34vw so it stays on one line. The caption follows at 16px across 80% of the width. Minimum height 80svh.

### 4. showcase — One row, three states (stack)
The product's central row (a task, a transaction, a message, a deploy) is shown three times, one directly beneath the other, in three states: as it arrives, with the pointer on it and its actions revealed, and finished. Each copy is built at true size, 640px wide, with real names, amounts and times, its root marked data-ui; inside it the product's own control borders and radii apply. The copies sit in columns 4–9 with 56px between them and nothing framing them. In columns 1–3, right-aligned and level with each copy, one word at 22px in the soft ink names its state. Columns 10–12 stay empty. The middle copy is live: its checkbox or button works and turns it into the third state. The heading, two to four words at 28–32px, sits on column 4's left edge, 96px above the first copy, with no supporting line.
On a phone: Copies stack at full width with 16px margins and stay at true size; a row wider than the screen is cropped at its right end, never shrunk. Each state word sits beneath its copy at 17px in the soft ink, 10px away. 48px separates the three groups. Heading at 26px.

Adjusted for this page:
- It sets text at 10px: use your small step (13px or more) instead.
- It draws lines or borders: keep them only inside a table, a form or a `data-ui` fragment; elsewhere separate with space or a change of ground.

### 5. list — Statement, table pushed right (table)
A heading of four to six words spans the full width on two lines at clamp(40px, 4.5vw, 68px), left-aligned with its first line indented 3vw and leading 0.98. 96px below, the table is pushed into the right-hand five columns (8–12) and the left stays open. One plain word naming the table (offices, hours, rates) hangs at 14px in column 7, top-aligned with the first row. Each row is a three-part line at 15–16px with 26px between rows: the kind or day in the soft ink at the left of the measure, the place or service at 30%, and the address, time or price right-aligned, with a small arrow where the row links. Rows are separated by space only; every fourth row has 44px above it to form groups. In columns 1–4, bottom-aligned with the last row, one 4:5 photograph 22vw wide may sit alone. Holds 5–14 rows.
On a phone: Heading at 9.5vw without the indent. The table takes the full width at 16px; each row stacks the kind above the place, with the value right-aligned on the first line. The naming word is dropped because the heading already says it. The photograph follows at 60% width on the right margin.

### 6. footer — Name first, places under it (list)
The wordmark opens the footer instead of closing it. On a full-bleed field in the page's inverse or final chapter colour, the name spans the full content width as the first thing, its cap line pushed 8% above the footer's top edge so the tops of the letters are sliced off by the section (`overflow: hidden` and a negative top margin in `em`). 72px beneath, a two-part row: columns 1–5 list the places or ways to reach the studio (cities, or email and telephone), one per line at 32–36px in the accent ink, each a link; columns 7–12 hold three columns of small links at 15px, top-aligned with the first place. A final row 96px lower carries the legal line at the left and a back-to-top text link at the right, both 13px. The field is about 90svh tall, and nothing sits between the wordmark and the row but space.
On a phone: The sliced wordmark stays at the top, fitted to the width. Places follow as a list at 26px, then the link columns two across at 15px. Legal line and back-to-top link share the last row at 12px, at opposite margins.

Adjusted for this page:
- It sets text at 12px: use your small step (13px or more) instead.
- It crops letters along their top: the inspector fails that (jurors read it as broken). Crop at the bottom edge or a side instead.

## 8. Motion — Masked headline
On load, each line of the headline rises from behind its own baseline, about 900ms with a strong ease-out, the second line 110ms after the first; the supporting sentence and the action then fade up together. Nothing else on the page performs. Because headlines are two lines at most, you author the line breaks and wrap each line yourself. Recipe: 'Masked line reveal' in references/motion.md.
This is the signature move, the one loud moment. Around it the page still needs the rest of the motion layer (SKILL.md step 9): an entrance for the parts of every section, feedback on every control, and one moving picture. The inspector fails a page that barely moves. Recipes: references/motion.md.

## 9. Where the richness comes from
The column line, the mosaics and whole pages of colour give structure and variety without ornaments.

## 10. How this direction goes wrong
The axis must be exact and reused everywhere or it reads as random indentation. Keep paragraphs to a real reading measure. On a phone the axis collapses to the left margin and side notes move inline above their paragraph.

## 11. Real references
Studied sites that work this way. Take the principle, never the specifics: no names, copy, images or signature assets of theirs.
- **Ai in Design Report 2026** (Awwwards Site of the Day, studied score 8.4) `aww-ai-in-design-report-2026`
  Idea: A research report laid out like a colour-blocked print annual: a thermal-blurred video collage on top, an oversized tight grotesk title, and flat orange, lilac, sage and black blocks carrying stats, quotes and chapters.
  Hero: The top 53% is a full-width video band: blurred, heat-map-like abstract footage in orange, lilac and sage, overlaid with four or five hard-edged rectangles of the same footage in grey or green, two tagged with tiny mono labels in white boxes. The header sits flush on top: a black logo block at far left, an orange link tab running to 40% of the width, two plain links at right. Below the band, on white: a two-line deck at about 1.4vw on a 1% left margin, and from 42% across a two-line title at 8.3vw, medium weight, tracking -0.06em. Bottom row: mono credit left, scroll cue and arrow aligned to the title column.
  Worth taking: Start most headings and text at a fixed column line about 42% across, leaving the left for small decks, credits and chapter numbers.
- **Applied Imagination** (One Page Love, studied score 8.3) `opl-applied-imagination`
  Idea: An essay conceived on a flight is read as a descent: an altimeter ticks from 30,000 ft to zero while you scroll down through halftone clouds to mountains at ground level.
  Hero: A pale blue sky fading to warm cream fills the viewport, with white clouds shaded in halftone dots. A tiny serif logotype sits top-centre; no nav. The title, two centred lines of black wedge-serif at 8.9vw, occupies the middle half of the screen and about 73% of its width; a cloud layer passes in front of the second line's baseline so the feet of the letters dissolve into dots. A two-line centred deck at 24px sits beneath. A mono byline strip is centred on the bottom edge with a scroll cue bottom-right. On the left edge at mid-height, a short vertical rule carries a two-line mono altitude readout.
  Worth taking: Tie a persistent numeric readout to scroll position (altitude falling to zero) so the reader's progress becomes part of the story.
- **Zara Webb** (One Page Love, studied score 8) `opl-zara-webb`
  Idea: A one-woman newborn-care practice presented like a hand-made keepsake: a mascot rabbit, scalloped and flower-shaped cut-outs, candid film photographs.
  Hero: Split exactly in half. Left, on cream: two-line mono caps nav stacks sit at the column's top-left and top-right with a handwritten script logo centred between them. Centred below, a five-line headline in a condensed serif, each line broken to one to three words so the block forms a ragged lozenge; then a three-line 16px sans paragraph and an outlined pill button in mono caps. A line-drawn rabbit on a skateboard rides a hairline at the column's bottom-right. Right: a candid flash photograph bleeds off the top and right edges and stops at 92% height; a lilac pill button and a round chat icon overlay its top-right corner.
  Worth taking: Mask photographs into soft custom shapes (a four-petal flower, a scalloped egg) and let their container crop them.
Full notes on any of them: `node draw.mjs --site <id>`.

## Always
Headlines two lines or fewer at every width. No eyebrow labels, no monospace, no 01/02/03, no thin rules, no gradients, no shadows at rest,
no cream-and-terracotta, no violet. `inspect.mjs` measures all of it.

Saved to /Users/aaryav-sharma/neuroswitch/.taste-skill/direction.json · reprint with `node draw.mjs --show`
