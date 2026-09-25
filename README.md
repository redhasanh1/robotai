# robotai

An open-source AI home-helper robot, built by students in Toronto over 16 weeks.
Phase 1 is two 3D-printed robotic hands. Phase 2 is a two-arm mobile robot that learns chores from demonstrations, with a fast multimodal model on Cerebras doing the planning.

**Live site:** served from this repo on Railway, and every push to `main` redeploys it.

## Update the site
| What | Edit | Then |
|---|---|---|
| Parts / prices | `data/bom.json` | `python tools/build_bom.py` to rebuild `robotai_BOM.xlsx` |
| Roadmap progress | `data/roadmap.json` (`"done": true`) | nothing |
| Research | `research/*.md` | new files: add to `DOCS` in `site/app.js` |

Run locally: `npm start`, then open http://localhost:3000
