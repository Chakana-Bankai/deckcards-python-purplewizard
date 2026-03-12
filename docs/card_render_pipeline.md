# Card Render Pipeline

## Canonical flow

`generate_art()` -> `load_frame(rarity)` -> `compose_card()` -> `export_card()`

## Rules

- Art generation must output frameless art.
- Outer frames and rarity treatments are applied only during card render stage.
- The canonical overlay owner is `game/render/frame_renderer.py`.
- Supported frame rarities are `common`, `rare`, `epic`, and `legendary`.
- Art modules may use composition guides, lighting, vignette, and subject separation, but must not bake decorative outer frames into exported card art.

## Active modules

- Frameless art generation: `game/art/gen_card_art32.py`, `game/art/gen_card_art_advanced.py`, `game/content/card_art_generator.py`
- Frame overlay: `game/render/frame_renderer.py`
- Card composition/runtime render: `game/ui/components/card_renderer.py`
- Portrait border styling: `game/visual/portrait_pipeline.py`

## Notes

- `game/art/frame_engine.py` is compatibility glue only and delegates to the render-stage frame system.
- If an asset already contains an outer decorative frame, it should be treated as legacy and cleaned before production use.
- Rarity identity should be expressed once through overlay frames, not duplicated inside art generation.
