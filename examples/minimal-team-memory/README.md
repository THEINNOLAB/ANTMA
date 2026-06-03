# Minimal Team Memory Example

Create a sample workspace:

```bash
antma init ./team-memory
antma sanitize ./team-memory
antma index ./team-memory --db ./team-memory/.antma/index.db
antma search "truth" --db ./team-memory/.antma/index.db
```

The generated files are synthetic and public-safe by design.

For a fuller synthetic workspace with product, research, source-of-truth,
curation, and evidence examples, see `examples/product-team-memory/`.
