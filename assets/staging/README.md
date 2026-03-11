CHAKANA staging assets

Purpose:
- temporary output bucket for generated art, audio, previews, and candidate renders
- this folder is for review and validation only

Pipeline position:
- art_references -> scene specs -> staging -> validation -> production

Rules:
- runtime must not depend on staging assets
- candidates should be promoted to production only after validation
- failed or superseded candidates can be archived instead of kept mixed with approved outputs
