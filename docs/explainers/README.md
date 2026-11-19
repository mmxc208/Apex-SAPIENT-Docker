# Explainer pages

These pages give the background of the work in this repository. Each one is an HTML page. Open it in a browser from your clone, for example with `open docs/explainers/sapient/sapient_explainer.html` on a Mac. A code hosting site shows only the source of an HTML file.

| Page | Content | Written |
|---|---|---|
| [`sapient/sapient_explainer.html`](sapient/sapient_explainer.html) | SAPIENT, explained: the standard, the Apex middleware, and where the Stone Soup tracker could fit | 2026-10-25 |
| [`zenoh/overview.html`](zenoh/overview.html) | SAPIENT over Zenoh in plain terms, with no code | 2026-11-08 |
| [`zenoh/architecture.html`](zenoh/architecture.html) | SAPIENT over Zenoh: the technical design note | 2026-11-08 |
| [`goatcore/overview.html`](goatcore/overview.html) | goat in plain language: what the goat network is | 2026-11-11 |
| [`goatcore/architecture.html`](goatcore/architecture.html) | goatcore: the technical note on its architecture | 2026-11-11 |
| [`goat-step1/index.html`](goat-step1/index.html) | Step 1 of the goat work, for a new team member. It is interactive. | 2026-11-12 |
| [`goat-step4/index.html`](goat-step4/index.html) | Step 4 of the goat work: what goatlite is and how the goatnet `cuaslab` was stood up with it, the step 1 rig on that goatnet, what was tested, and what was learned. It is interactive. | 2026-11-19 |
| [`goat-step4b/index.html`](goat-step4b/index.html) | Step 4b of the goat work: the host on its own VM, so pod, goatnet and host are on three machines; a task hop by hop, the clock difference set on purpose, the link cuts, what was tested, the fit with goat's ADRs and what was left. Its numbers come from `docs/acceptance-goat4b.md`. It is interactive. | 2026-11-19 |
| [`goat-hierarchy/index.html`](goat-hierarchy/index.html) | Hierarchy, echelon and how step 4b fits goat's ADRs: mesh peer and fabric identity, a level-by-level hierarchy, ADRs 1165 and 1205, echelon and slot, and the ingress gateway and edge router. It is interactive. | 2026-11-19 |

## How to read them

- **The first five pages are studies.** They were written before the work that they describe was built, from the standard and from source code. `README.md`, `README-goat.md` and the acceptance records say what was built and measured later. Where a study and a record disagree, the record is right.
- **The step 1, step 4 and step 4b pages describe finished work.** The numbers of the step 1 page come from `docs/acceptance-goat1.md`. Those of the step 4 page come from `docs/acceptance-goat4.md`; its goatlite part comes from the stand-up session of 2026-11-18, which has no record in this repository. Those of the step 4b page come from `docs/acceptance-goat4b.md`.
- **The hierarchy page is a reading note.** It comes from goatcore's ADRs read at `5c5aee66` and from this repository's step 4b design; nothing was run for it. Its Markdown version is `docs/goat-hierarchy.md`.
- **No video.** The originals of the first five pages have narrated videos. The videos are large and are not in this repository. The pages here are complete without them. The files that only exist to make the videos (slides, narration text, posters and the build script) are not here either.
- **The pictures** of the Zenoh and goatcore pages are the `.svg` files beside them.
