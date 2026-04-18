# Sputnik

Offline receiver web app and broadcast pipeline layout.

## Repository layout

```
broadcast/
  latest/          # canonical daily package (JSON + audio/)
  archive/         # older days (optional)
config/
  projects.json    # named “project stars” for the receiver map
pipeline/
  seed/ … broadcast_package/
  run.py           # CLI entry (stages to be wired)
web/
  public/
    broadcast/     # copy of broadcast/latest for static hosting (Vite dev & Pages)
    config/        # copy of config/ (e.g. projects.json)
  src/
  index.html
  package.json
  vite.config.ts
```

- **Source of truth** for a day’s broadcast: `broadcast/latest/`.
- **Receiver static assets**: duplicate into `web/public/broadcast/` and `web/public/config/` (or automate sync in CI). Paths used at runtime: `broadcast/*.json`, `config/projects.json` (under `import.meta.env.BASE_URL`).

## Web

```bash
cd web && npm install && npm run dev
```

Build: `npm run build` (set `VITE_BASE` for GitHub Pages, e.g. `/Sputnik/`).

## Pipeline

Python package placeholders under `pipeline/`; entrypoint stub: `python -m pipeline.run` (after wiring `run.py`).

## License

Font assets under `web/src/assets/fonts/` follow their bundled OFL files where applicable.
