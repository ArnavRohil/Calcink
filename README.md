# CalcInk ✍️ = 🧮

### ✨ [Live Demo: Try CalcInk](https://calcink.netlify.app/)

A handwritten mathematics calculator that turns digital ink into mathematical expressions and solves them.


**Created by Arnav Rohil.**

**An on-device handwritten math calculator.** Write `18 + 4 × 3 =` with a mouse, stylus or finger, and the answer appears on the paper right after the `=`. Erase a digit and write another, and the answer updates. All of it runs in your browser and keeps working with no network.

> Inter IIT Tech Meet 15.0 Bootcamp · Software Development PS · Digital Ink, HCI & Edge ML

---

## Features

| Area | What you get |
|---|---|
| **Ink canvas** | Mouse, stylus and touch (Pointer Events). Smooth curves with **pen-like ink**: stroke ends taper, and with a stylus the line gets thicker when you press harder. Pen, highlighter, **pixel eraser** (actually cuts strokes), **stroke eraser**, clear, stroke width and opacity, 300-step undo/redo, high-DPI/Retina rendering (`devicePixelRatio`), palm rejection, dark mode, PNG export |
| **Recognition** | Digits `0–9`, `+ − × ÷ =`, decimal point `.`, plus `( )`, `x`, `y`. ONNX Runtime Web in a **Web Worker**, so drawing never stutters |
| **Evaluation** | Shunting Yard parser (no `eval()`) with **full BODMAS**: **B**rackets, **O**rders (powers, written as small raised digits like 2³), **D**ivision/**M**ultiplication left to right, **A**ddition/**S**ubtraction left to right. Multi-digit numbers, decimals, negatives (`−2² = −4`), implicit multiplication `2(3+4)`, **Undefined** for ÷ 0, `?` for unreadable input. It never throws |
| **Projection** | The answer is placed next to the `=`, sized to your handwriting, in a different font and colour from your ink, and it "writes itself in" from left to right. Editing a line re-evaluates only that line. Several sums can sit side by side on one row |
| **Creative extras** | **Scratch-to-erase** (scribble over ink; it turns red, then fades out), **variables** (`x = 5`, then `x + 10 =` → 15), **function plots** (`y = 2x + 1` draws a mini graph), **BODMAS Steps** view (`[M] 4 × 3 = 12 → [A] 18 + 12 = 30`), confidence indicators (dotted underline + tooltip), haptic tick + optional sound when an answer appears, "Show reads" debug view, paper grain and margin line, first-visit hint, preferences remembered |
| **Offline** | A service worker caches every file plus ONNX Runtime, so the app works in airplane mode after the first visit. A single-file build works from a double-click |

## Run locally

Requirements: **Node.js 18 or newer** and npm.

After cloning the repository:

```bash
git clone https://github.com/USERNAME/calcink.git
cd calcink
npm ci             # installs the pinned dependency and prepares vendor/ort/
npm run dev        # open http://localhost:5173
```

Replace `USERNAME` with your GitHub username. No framework or bundler is required; the app uses plain HTML, CSS and JavaScript.

Other scripts:

| Command | Does |
|---|---|
| `npm test` | Unit tests (parser, geometry, gestures, both models vs onnxruntime, build checks). Uses Node's built-in runner, no extra installs |
| `npm run build` | Writes `dist/site/` (upload this) and `dist/calcink-standalone.html` (one self-contained file) |
| `npm run preview` | Serves the production build |
| `python tests/e2e/browser_e2e.py` | Browser end-to-end test that draws with a simulated hand (requires Playwright and Chromium) |

Install the browser-test requirements and run it with:

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/e2e/browser_e2e.py
```

### The pre-trained model is already included

`models/pretrained.onnx` is the [altynbk](https://github.com/altynbk/handwritten-math-recognition) CNN (MIT), converted from its original Keras file. To reproduce the conversion (no TensorFlow needed, just Python + NumPy):

```bash
pip install numpy opencv-python onnxruntime        # onnxruntime/opencv only for the self-checks
python tools/convert_pretrained.py path/to/handwritten-math-recognition-main.zip
```

The converter reads the Keras weights with a tiny built-in HDF5 reader (`tools/minih5.py`), writes the same network as ONNX, and checks the result against an independent NumPy implementation of the Keras layers.

## How to use

- **Write** an expression and finish it with `=`. The answer appears after a short pause.
- **Variables:** write `x = 5` on one line and use `x` on the lines below it.
- **Graphs:** write `y = 2x + 1` while `x` has no value, and a graph appears.
- **Powers:** write the exponent small and raised, like 2³. It is read as `2^3`.
- **Steps:** press **Steps** (T) to see the BODMAS order used for each answer.
- **Two sums on one row:** leave a clear gap between them; each gets its own answer.
- **Erase:** use the Eraser (E) or the Stroke eraser (S), or just **scribble over** ink.
- **Shortcuts:** `P` pen · `H` highlighter · `E` pixel eraser · `S` stroke eraser · `[` `]` size · `R` show what the model read · `T` BODMAS steps · `Ctrl+Z` / `Ctrl+Y` undo/redo.
- Highlighter ink is never read by the recogniser, so you can use it for notes.

## Model attribution

CalcInk runs **two small CNNs** through ONNX Runtime Web:

| | Primary: pre-trained recogniser | Supplementary: bundled CalcInk model |
|---|---|---|
| **Source** | [altynbk/handwritten-math-recognition](https://github.com/altynbk/handwritten-math-recognition), "CNN (augmented)" | This repo: [`tools/bundled-model/`](tools/bundled-model) |
| **Licence** | MIT © Altynbek Kabiyev | MIT (this project) |
| **Architecture** | 4 × [Conv3×3 → BatchNorm → MaxPool] (32/64/128/256) → GlobalAvgPool → Dropout → Dense(15, softmax) | Conv3×3(16) → Pool → Conv3×3(32) → Pool → Dense(128) → Dense(18, softmax), about 210k parameters, 0.8 MB |
| **Input** | 64×64×1 (NHWC), light ink on dark, 0–1 | 28×28 (NCHW), white ink on black, 0–1 |
| **Classes** | 0–9, + − × ÷ = | 0–9, + − x ÷ = ( ) y |
| **Trained on** | 8,036 real handwritten symbol images (deduplicated), with stroke / occlusion / photometric augmentation | synthetic strokes (templates with random slant, wobble and pen width) |
| **Reported accuracy** | 99.44 % clean test, 98.45 % augmented test (1,608 held-out images, from the repo's `results/metrics.json`) | 100 % on its own synthetic validation set; 25/25 on hand-drawn test strokes |
| **Role** | Reads every symbol | Adds `( ) y` when it is ≥ 85 % sure (the pre-trained model can't output them) |
| **File** | `models/pretrained.onnx` (1.5 MB) + `models/pretrained.json` (input contract) | `models/calcink_symbols.onnx` (0.8 MB) |

Why these, and what else was considered: see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#3-model-choice).

Runtime: [ONNX Runtime Web](https://github.com/microsoft/onnxruntime) 1.20.1 (MIT © Microsoft), WebAssembly backend.

## Project structure

```
index.html                  page markup; loads the scripts below in order
src/styles.css              digital-paper theme (light + dark)
src/core/calcink-core.js    pure logic, no DOM: segmentation, Shunting Yard parser,
                            evaluator, variables, scratch detection, plotting  ← unit-tested
src/app/canvas.js           Phase 1: ink canvas, erasers, undo/redo, scratch-to-erase
src/app/recognizer.js       Phase 2: symbol rasterisation, model loading, worker messaging
src/worker/inference-worker.js  ONNX Runtime Web on a separate thread (+ a small built-in ONNX interpreter as offline fallback)
src/app/projection.js       Phase 4: answers, graphs, debug labels, PNG export layer
src/app/main.js             wiring: scheduling, keyboard, service-worker registration
sw.js                       offline cache
models/                     pretrained.onnx (+ .json input contract), calcink_symbols.onnx
scripts/                    dev server, ONNX Runtime vendoring, build (all zero-dependency)
tools/                      Keras→ONNX converter (no TensorFlow), mini HDF5 reader, bundled-model training scripts
tests/                      node:test unit tests + Playwright end-to-end test
docs/ARCHITECTURE.md        design document
```

## Publish this project on GitHub

1. Create a new **public** repository named `calcink` on GitHub. Leave the options to add a README, `.gitignore`, or license unchecked because those files are already included here.
2. From this project folder, initialise Git and make the first commit:

   ```bash
   git init -b main
   git config user.name "Arnav Rohil"
   git config user.email "YOUR_GITHUB_EMAIL"
   git add .
   git commit -m "chore: prepare CalcInk for GitHub"
   ```
3. Connect the local folder to your GitHub repository and push:

   ```bash
   git remote add origin https://github.com/USERNAME/calcink.git
   git push -u origin main
   ```

   Replace `USERNAME` with your GitHub username and `YOUR_GITHUB_EMAIL` with the email associated with your GitHub account (or your GitHub-provided no-reply address). GitHub may ask you to authenticate in your browser.
4. Open the repository's **Actions** tab and wait for **Deploy to GitHub Pages** to finish. Then go to **Settings → Pages** and confirm that the source is set to **GitHub Actions**. Your live site URL will appear in the Pages section and in the deployment details.

## Deploy

- **GitHub Pages:** push to `main`. [`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs the tests, builds, and publishes `dist/site/`. In the repo, go to *Settings → Pages → Source* and choose **GitHub Actions**.
- **Vercel / Netlify:** build command `npm run build`, output directory `dist/site` (already set in `vercel.json` / `netlify.toml`).

After deploying, open the site once, then turn on airplane mode and reload. It keeps working.

## Known limitations

- The pre-trained model was trained on a small set of writers, so unusual handwriting can still be misread. "Show reads" (R) shows what was recognised (and which model read each symbol), and a dotted underline marks answers that contain low-confidence symbols.
- A handwritten `x` and `×` look the same. Between two numbers (`3x5`) it means multiply; anywhere else it is the variable `x`.
- Fractions written vertically (one number over another) and roots are out of scope. Powers must be written clearly smaller and raised.

## How the rubric is covered

| Rubric item | Where it is met | Proof |
|---|---|---|
| Smooth drawing, undo/redo, both erasers, clear, width, display scaling | `src/app/canvas.js` | e2e: undo/redo, pixel split, stroke erase, clear+undo, DPR-2 backing store, touch drawing |
| Recognition of 0–9, + − × ÷, `.`, `=` with a pre-trained model | `models/pretrained.onnx` (altynbk, MIT), `src/app/recognizer.js` | 99.44 % reported test accuracy; e2e reads 8 mixed lines (sizes 22–56 px, slanted, tight spacing) correctly |
| BODMAS/PEMDAS, multi-digit, decimals, negatives | `src/core/calcink-core.js` | `tests/core.test.js`: precedence table, powers, unary minus, decimals, fuzzing |
| Automated tests (parser, ÷0, coordinates) | `tests/` | 33 unit tests (`npm test`) + 20-check browser test |
| Architecture document, model justification, stroke → tensor pipeline | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | sections 1–5 |
| 60 FPS, non-blocking inference | Web Worker + OffscreenCanvas (`src/worker/`) | e2e: zero main-thread long tasks; 100 % of frames ≤ 20 ms while recognising |
| 100 % on-device, offline | `sw.js`, vendored ONNX Runtime, built-in ONNX interpreter | e2e: reload with network off still works; no remote API calls exist |
| Memory stability | immutable stroke list, capped history, nodes freed | e2e: heap unchanged (3.5 MB → 3.5 MB) after 480 more strokes |
| `eval()` forbidden, graceful errors | parser only | build test scans for `eval`/`new Function`; fuzz test: 5,000 random inputs never throw |
| Paper aesthetic, micro-interactions, creative extensions | `src/styles.css`, `src/app/projection.js`, `src/app/main.js` | pressure ink, grain, write-in answers, haptics/sound, scratch-to-erase, variables, plots, Steps |

## How we work (Git)

- `main` is always deployable: the Pages workflow runs `npm test` before publishing.
- Each change goes on a branch (`feat/…`, `fix/…`, `docs/…`) and into `main` through a pull request that says *what* changed, *why*, and *how it was tested* (`npm test`, plus the e2e test for UI changes).
- Commit messages follow `type(scope): summary`, e.g. `feat(core): powers as raised digits`.

## Author

**Arnav Rohil** — creator and maintainer of CalcInk.

## License

The CalcInk project code is licensed under the MIT License; see [LICENSE](LICENSE). The primary pre-trained model is separately attributed to Altynbek Kabiyev under MIT; see [models/LICENSE-pretrained-altynbk.txt](models/LICENSE-pretrained-altynbk.txt). ONNX Runtime Web is also MIT-licensed by Microsoft.
