# Card Art Foreground Prompt V2

## Objetivo
Generar arte de carta legible, con sujeto real, objeto real y fondo claro.

No buscamos ruido abstracto.
No buscamos lineas y circulos como protagonista.
Buscamos ilustracion pixel-fantasy con lectura inmediata.

## Prompt maestro
Generate a fantasy card artwork for a roguelike deckbuilder.

Canvas work size: 1024x1024 minimum.
Final game export: readable at small card size.

The image must follow this order:
1. BACKGROUND
2. SCENE SUPPORT
3. PRIMARY SUBJECT
4. SECONDARY OBJECT
5. MAGICAL EFFECT
6. FINAL COLOR GRADING
7. CARD FRAME SEPARATED FROM THE ART

Rules:
- clear readable silhouette
- strong subject in foreground
- strong secondary object
- minimal visual noise
- no abstract geometry over the center
- sacred geometry only in borders, distant architecture or ritual accents
- scene must feel hand-illustrated, not random procedural noise
- pixel-fantasy readability
- soft 2D/2.5D depth

Foreground dominance:
- primary subject occupies 80-85% of useful height
- focus object occupies 35-45% of useful width
- subject must be closer than the architecture
- background must not compete with subject

Lighting:
- single clear main light
- local shadow under the subject
- subject darker or stronger than the background
- object brighter than subject body when needed

Effects:
- less than 15% of frame
- use only subtle glow, particles, short streaks, soft aura, sparse runes
- never cover face, torso or main object

Style target:
- readable fantasy illustration
- pixel art game asset
- strong silhouette
- limited noise
- strong composition

## Prompt template
Background: {environment}
Scene support: distant architecture or terrain that supports the lore of {set_name}
Primary subject: {subject}
Primary subject kind: {subject_kind}
Primary subject reference: {subject_ref}
Secondary object: {object}
Secondary object kind: {object_kind}
Secondary object reference: {object_ref}
Energy effect: {effects}
Environment kind: {environment_kind}
Environment reference: {environment_ref}
Palette: {palette}
Lighting: {lighting}
Lore mood: {lore_tokens}

Important:
- the primary subject must be unmistakable
- the secondary object must be readable without guessing
- the background must stay behind
- the artwork must never look like circles, lines or blocks pretending to be a subject

## Set direction
### Base
- Chakana sanctuary
- Gaia
- ritual heroism
- gold, violet, turquoise

### Hiperborea
- polar citadel
- frozen observatory
- marble and ice
- white, silver, pale blue

### Arconte
- dark throne realm
- malignant monument
- oppressive void
- black, crimson, toxic green

## Rejection rules
Reject if:
- subject is not obvious
- object is not obvious
- center is occupied by geometry instead of scene
- image reads as abstract noise
- silhouette collapses at small size
- background is stronger than foreground
