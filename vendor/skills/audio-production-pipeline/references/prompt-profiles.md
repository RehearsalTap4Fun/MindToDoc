# Prompt Profiles

Do not directly translate planner descriptions. First map the intent into an acoustic profile, then write a short generation prompt with explicit avoids.

## Default Generation Policy

- Use company API, not personal keys.
- Output WAV.
- Generate full/non-combined candidates by default.
- Do not default to mp3.
- Do not default to raw stems.
- Do not default to combined/stem-mixed outputs.
- Combined is planner opt-in only.

## Prompt Shape

Recommended prompt shape:

```text
short primitive-fantasy mobile SLG UI SFX for <bank/module>.
<intent profile in acoustic language>.
Avoid <known failure modes>.
```

Avoid lore-heavy prose. The model needs acoustic cues, not story paragraphs.

## Validated Profiles

### `ssr_premium_card_reveal`

Use for SSR/premium card reveals.

Acoustic direction:

- warm golden bloom
- wide soft radiant shine
- rounded low-frequency impact
- mellow/luxurious reward chime
- thick low-mid body
- polished mobile UI readability

Avoid:

- sharp metal
- bright clang
- piercing sparkle
- harsh highs
- electric buzz
- long music phrase

### `sr_card_reveal`

Use for SR card reveals.

Acoustic direction:

- lighter than SSR
- soft silver-violet glow
- gentle shimmer
- clean short UI accent

Avoid piercing bells, metal scrape, sci-fi sparkle.

### `free_card_refresh_paper_shuffle`

Use for free card refresh/reroll.

Acoustic direction:

- pure light paper-card shuffle
- two or three quick card flutters
- soft paper tap
- tiny muted magic dust only at the end
- low intensity, tactile, not a reward

Avoid:

- casino
- slot machine
- coins
- reward chime
- bell
- metal
- mechanical click
- bright sparkle
- big whoosh
- melody
- voice
- music
- sci-fi

### `negative_choice_dismiss`

Use for giving up, declining, or sad/negative choices.

Acoustic direction:

- sad low muted failure tone
- soft dark breath
- gentle dissipating fade
- low pitch
- matte and quiet

Avoid metal, clang, bell, bright pitch, success reward, impact, horror sting.

### `slot_spin_loop`

Use for fantasy slot/rolling loops.

Acoustic direction:

- seamless loop
- primitive/fantasy wooden or stone mechanism
- soft repeating motion
- readable rhythm, not noisy

Avoid casino jackpot, electronic hum, harsh metal, bright bells.

### `slot_stop`

Use for rolling result lock/settle.

Acoustic direction:

- soft wooden clack
- rounded mechanical settle
- clear finality

Avoid sharp metal hit, casino bell, jackpot cue.

### `revive_crisis`

Use for revive popup when danger/failure is near.

Acoustic direction:

- low muted tension
- short pressure swell
- serious but not horror
- pause/crisis UI readability

Avoid alarm siren, metal clang, high pitch, gore/horror.

### `revive_confirm`

Use for successful revive.

Acoustic direction:

- warm rising magical energy
- hopeful pulse
- rounded impact
- short clean mobile fantasy feedback

Avoid choir, long music, sci-fi, harsh metal.

## Retry Notes

When a generated result is wrong, write the retry note as a correction to the sound, not a complaint.

Good:

```text
Make it a pure light paper-card shuffle: quick card flutters, soft paper tap, tiny muted magic dust only, no casino, no reward chime, no metal, no big whoosh.
```

Bad:

```text
This does not sound like free refresh.
```
