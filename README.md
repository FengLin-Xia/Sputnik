# Sputnik

Offline receiver web app and broadcast pipeline: generate a daily **broadcast package** (score + audio + meta), serve it from static hosting, and play it in the receiver UI with a shared star map.

## Repository layout

```
broadcast/
  latest/          # canonical daily package (JSON + audio/)
  archive/         # older days (optional)
composition_output/  # default output for `compose` (e.g. score.json)
config/
  projects.json    # named “project stars” for the receiver map
pipeline/
  composition/     # score.json generation (mock or Ollama)
  render/          # score.json → WAV
  broadcast_package/  # assemble broadcast/latest
  run.py           # CLI entry for pipeline subcommands
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

## Python environment

Use a venv (optional path: `backend/.venv`) and install dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Render and packaging need **numpy**. Composition with **`--provider mock`** only imports the score schema and can run without numpy in many setups; **`render`** and **`all`** require numpy.

**Run all `python -m pipeline…` commands from the repository root** so the `pipeline` package resolves (`cd` to the repo root, not `web/`).

## Pipeline

End-to-end flow: **compose** (optional) → **render** (score → WAV) → **package** (write `broadcast/latest/`). Seed/drift layers are reserved for later work.

Unified CLI:

```bash
python -m pipeline.run compose --provider mock
python -m pipeline.run render --score composition_output/score.json --out broadcast/audio/rendered.wav
python -m pipeline.run package --repo . --score composition_output/score.json --audio broadcast/audio/rendered.wav --out broadcast/latest
python -m pipeline.run all --score pipeline/render/demo_score.json
```

(`all` runs render then package with the given score; adjust paths to match your files.)

Direct modules (same root-directory rule):

```bash
python -m pipeline.composition --provider mock
python -m pipeline.render --score composition_output/score.json --out out.wav
python -m pipeline.broadcast_package --help
```

For **Ollama**, use `compose --provider ollama` (local Ollama must be running; set `--model` and optionally `OLLAMA_BASE_URL` / `--ollama-url`). See `Composition_v0.1_PR.md` for scope and behaviour.

### Score format

Authoritative description: **`Sputnik_Score_Spec_PrV01.md`**. Validation logic lives in `pipeline/render/schema.py`.

## Design docs (PR notes)

Feature-level goals and scope are in the repo root, e.g. `Composition_v0.1_PR.md`, `RenderV01.pr.md`, `Broadcast_PackageV01.pr.md`, `frontend_broadcast_package_integration_PRnotev01.md`, and `Sputnik_主架构与前端PR规划.md`. The README stays short; use those for rationale and detailed requirements.

## License

Font assets under `web/src/assets/fonts/` follow their bundled OFL files where applicable.
