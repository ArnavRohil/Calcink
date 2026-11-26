"""
Browser end-to-end test for CalcInk (drives a real Chromium with a fake "hand").

    pip install playwright && playwright install chromium
    python tests/e2e/browser_e2e.py              # starts the dev server itself
    python tests/e2e/browser_e2e.py --shots out/ # also save screenshots

It writes expressions with synthetic mouse strokes (shapes deliberately different
from the bundled model's training templates) and checks the answers on the page,
plus undo/redo, both erasers, scratch-to-erase, plotting, frame timing while
recognising, offline reload via the service worker, and the standalone build.
"""
import math, os, random, subprocess, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PORT = 5199
SHOTS = Path(sys.argv[sys.argv.index('--shots') + 1]) if '--shots' in sys.argv else None
random.seed(3)


def arc(cx, cy, rx, ry, a0, a1, n=18):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / (n - 1))),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / (n - 1)))) for i in range(n)]


SHAPES = {
    '0': [arc(.3, .5, .3, .5, -100, 255)],
    '1': [[(.15, .2), (.38, 0), (.33, 1)]],
    '2': [arc(.3, .28, .28, .26, 200, 380) + [(.5, .45), (.0, 1), (.62, .98)]],
    '3': [arc(.3, .24, .26, .24, 210, 440) + arc(.3, .74, .3, .26, 280, 500)],
    '4': [[(.45, 0), (.02, .62), (.62, .6)], [(.47, .2), (.45, 1)]],
    '5': [[(.12, .02), (.1, .45)] + arc(.3, .7, .3, .28, 220, 470), [(.12, .02), (.6, 0)]],
    '6': [arc(.6, .55, .55, .55, 250, 175) + arc(.33, .72, .28, .27, 175, 535)],
    '7': [[(.02, .03), (.62, 0), (.25, 1)]],
    '8': [[(.3 + .28 * math.sin(2 * t) * .9, .5 - .5 * math.cos(t)) for t in [i * 2 * math.pi / 39 for i in range(40)]]],
    '9': [arc(.3, .28, .27, .28, 10, -350) + [(.57, .3), (.5, 1)]],
    '+': [[(0, .5), (.8, .52)], [(.4, .1), (.42, .9)]],
    '-': [[(0, .5), (.7, .5)]],
    '=': [[(0, .38), (.7, .38)], [(.02, .64), (.72, .64)]],
    'x': [[(0, .25), (.6, .95)], [(.6, .25), (0, .95)]],
    '÷': [[(0, .55), (.7, .55)], [(.35, .25)], [(.35, .85)]],
    '(': [arc(.55, .5, .45, .55, 240, 120)],
    ')': [arc(.0, .5, .45, .55, -60, 60)],
    'y': [[(0, .25), (.3, .7)], [(.6, .25), (.05, 1.2)]],
    '.': [[(.1, .95)]],
}
H, GAP = 34, 10
adv = lambda ch: (H * .25 if ch == '.' else H * .62) + GAP


def draw_strokes(page, strokes):
    for st in strokes:
        page.mouse.move(*st[0]); page.mouse.down()
        if len(st) == 1: page.mouse.move(st[0][0] + .5, st[0][1] + .5)
        for p in st[1:]: page.mouse.move(*p, steps=3)
        page.mouse.up()


def glyph(ch, x, y, h=H):
    return [[(x + px * h + random.gauss(0, .6), y + py * h + random.gauss(0, .6)) for px, py in st] for st in SHAPES[ch]]


def write(page, text, x, y):
    for ch in text:
        draw_strokes(page, glyph(ch, x, y)); x += adv(ch)
    return x


def results(page):
    r = page.evaluate("[...document.querySelectorAll('.res')].map(e => [e.textContent, parseFloat(e.style.top)])")
    return [t for t, _ in sorted(r, key=lambda a: a[1])]


def nstrokes(page):
    return page.evaluate('CalcInk.canvas.strokes.length')


class Check:
    def __init__(self): self.fails = 0
    def __call__(self, name, cond, info=''):
        print(('PASS ' if cond else 'FAIL ') + name + (f'  — {info}' if info else ''))
        self.fails += 0 if cond else 1


def wait_ready(page):
    page.wait_for_function("document.getElementById('mDot').dataset.s === 'ready'", timeout=30000)


SLOW = float(os.environ.get('CALCINK_SLOW', '1'))   # >1 for slow machines / engines


def settle(page, ms=900):
    page.wait_for_timeout(ms * SLOW)


def main():
    check = Check()
    server = subprocess.Popen(['node', 'scripts/serve.js'], cwd=ROOT, env={**os.environ, 'PORT': str(PORT)},
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={'width': 1200, 'height': 760})
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(f'http://localhost:{PORT}/')
            wait_ready(page)
            print('engine:', page.evaluate('CalcInk.recognizer.engine'), '| models:', page.evaluate('CalcInk.recognizer.models'))
            check('symbol images are drawn inside the worker', page.evaluate('CalcInk.recognizer.workerDraws'))

            # ── expressions → answers ─────────────────────────────────────────
            tests = ['18+4x3=', 'x=5', 'x+10=', '7÷0=', '2.5x2=', '-3+1=', '(6-3)÷4=', '9-=']
            want = ['30', '15', 'Undefined', '5', '−2', '0.75', '?']
            for i, t in enumerate(tests): write(page, t, 60, 50 + i * 70)
            settle(page, 1200)
            reads = page.evaluate('CalcInk.lines.map(l => l.text)')
            check('recognition', reads == tests, f'{reads}')
            check('answers next to "="', results(page) == want, f'{results(page)}')
            if SHOTS: page.screenshot(path=str(SHOTS / 'answers.png'))

            # ── reactive edit: replace the 3 in line 1 by a 5 → 38 ────────────
            x3 = 60 + sum(adv(c) for c in '18+4x')
            page.keyboard.press('s')
            page.mouse.move(x3 + 10, 45); page.mouse.down(); page.mouse.move(x3 + 10, 90, steps=8); page.mouse.up()
            page.keyboard.press('p')
            draw_strokes(page, glyph('5', x3, 50))
            settle(page)
            check('reactive re-evaluation', results(page)[0] == '38', f'line 1 now reads {page.evaluate("CalcInk.lines[0].text")} → {results(page)[0]}')

            # ── 60 FPS while recognising ──────────────────────────────────────
            # rAF gaps measure frames; Long Tasks (>50 ms) measure whether the MAIN
            # thread was ever blocked — the thing the worker architecture guarantees.
            page.evaluate("""() => { window.__gaps = []; window.__lt = []; let last = performance.now();
                new PerformanceObserver(l => l.getEntries().forEach(x => __lt.push(Math.round(x.duration)))).observe({ entryTypes: ['longtask'] });
                const tick = t => { __gaps.push(t - last); last = t; if (!window.__stop) requestAnimationFrame(tick); };
                requestAnimationFrame(tick); }""")
            page.mouse.move(700, 700); page.mouse.down()
            for i in range(90):
                page.mouse.move(700 + i * 4, 700 + (i % 2) * 4)
                if i == 2: page.evaluate('CalcInk.recognizer.recognize(CalcInk.canvas.strokes)')
            page.mouse.up()
            page.evaluate('window.__stop = true')
            gaps, longtasks = page.evaluate('__gaps')[2:], page.evaluate('__lt')
            smooth = sum(g <= 20 for g in gaps) / len(gaps)
            check('main thread never blocked while recognising (no long tasks)', not longtasks, f'long tasks: {longtasks}')
            check('≥ 99 % of frames within the 60 FPS budget', smooth >= 0.99,
                  f'{smooth:.1%} of {len(gaps)} frames ≤ 20 ms, median {sorted(gaps)[len(gaps)//2]:.1f} ms, worst {max(gaps):.1f} ms')
            page.keyboard.press('Control+z')

            # ── undo / redo / erasers ─────────────────────────────────────────
            n = nstrokes(page)
            page.keyboard.press('Control+z'); n1 = nstrokes(page)
            page.keyboard.press('Control+y'); n2 = nstrokes(page)
            check('undo / redo', (n1, n2) == (n - 1, n), f'{n} → {n1} → {n2}')
            page.mouse.move(700, 620); page.mouse.down(); page.mouse.move(1100, 620, steps=20); page.mouse.up()
            before = nstrokes(page)
            page.keyboard.press('e')
            page.mouse.move(900, 600); page.mouse.down(); page.mouse.move(900, 640, steps=5); page.mouse.up()
            check('pixel eraser splits a stroke', nstrokes(page) == before + 1)
            page.keyboard.press('Control+z'); page.keyboard.press('p')
            page.click('#bClear'); c0 = nstrokes(page)
            page.keyboard.press('Control+z')
            check('clear + undo', c0 == 0 and nstrokes(page) == before)

            # ── scratch-to-erase: scribble over the "7" of line 4 ─────────────
            settle(page, 600)
            before = nstrokes(page)
            y4 = 50 + 3 * 70
            page.mouse.move(56, y4 + 2); page.mouse.down()
            for k in range(10):
                page.mouse.move(56 + (24 if k % 2 == 0 else 0), y4 + 3 + k * 3.2, steps=4)
            page.mouse.up()
            settle(page)
            check('scratch-to-erase', nstrokes(page) < before and page.evaluate('CalcInk.lines[3].text') == '÷0=',
                  f'strokes {before} → {nstrokes(page)}, line 4 reads {page.evaluate("CalcInk.lines[3].text")}')

            # ── y = f(x) plot ─────────────────────────────────────────────────
            page.click('#bClear')
            write(page, 'y=2x+1', 60, 60)
            settle(page, 1000)
            check('y = f(x) draws a graph', page.evaluate("document.querySelectorAll('canvas.plot').length") == 1,
                  f'reads {page.evaluate("CalcInk.lines.map(l => l.text)")}')
            page.click('#bDark'); settle(page, 300)
            if SHOTS: page.screenshot(path=str(SHOTS / 'plot-dark.png'))
            page.click('#bDark')

            # ── BODMAS Orders: a small raised digit is a power; Steps view ────
            page.click('#bClear')
            draw_strokes(page, glyph('2', 70, 70, 40)); draw_strokes(page, glyph('3', 98, 60, 18))
            x = 125
            for ch in '+1=':
                draw_strokes(page, glyph(ch, x, 72, 36)); x += adv(ch)
            write(page, '9-4=', 600, 70)                                  # a second sum on the same row
            settle(page, 1200)
            check('handwritten power 2³+1 = 9 (BODMAS "O")', '9' in results(page), f'reads {page.evaluate("CalcInk.lines.map(l => l.text)")}')
            check('two sums side by side on one row', sorted(results(page)) == ['5', '9'], f'{results(page)}')
            page.click('#bSteps'); settle(page, 400)
            rules = page.evaluate("[...document.querySelectorAll('.steps .rule')].map(e => e.textContent).join('')")
            check('Steps view shows the BODMAS order', rules.startswith('OA') and 'S' in rules, rules)
            page.click('#bSteps')

            # ── memory: a long session must not keep growing the heap ─────────
            cdp = ctx.new_cdp_session(page)
            def heap_mb():
                cdp.send('HeapProfiler.collectGarbage')
                return cdp.send('Runtime.getHeapUsage')['usedSize'] / 1e6
            def scribble_round(k):
                for i in range(40):
                    x0, y0 = 80 + (i % 10) * 90, 120 + (i // 10) * 90
                    page.mouse.move(x0, y0); page.mouse.down()
                    for j in range(1, 8): page.mouse.move(x0 + j * 6, y0 + 20 * math.sin(j + k))
                    page.mouse.up()
                page.click('#bClear')
            for k in range(8): scribble_round(k)                          # warm up: fill the 300-step history
            settle(page, 600); h1 = heap_mb()
            for k in range(8, 20): scribble_round(k)                      # 480 more strokes
            settle(page, 600); h2 = heap_mb()
            check('no memory growth over a long session', h2 - h1 < 3, f'heap {h1:.1f} MB → {h2:.1f} MB after 480 more strokes')
            page.keyboard.press('Control+z')

            check('no uncaught page errors', not errors, '; '.join(errors))

            # ── offline: reload with the network off (service worker cache) ──
            page.evaluate('navigator.serviceWorker.ready')
            page.wait_for_timeout(500)
            ctx.set_offline(True)
            page.reload(); wait_ready(page)
            write(page, '12÷4=', 60, 60); settle(page, 1000)
            check('works offline after first load', results(page) == ['3'], f'{results(page)} via {page.evaluate("CalcInk.recognizer.engine")}')
            ctx.set_offline(False)

            # ── touch input on a Retina tablet (DPR 2) ────────────────────────
            tctx = browser.new_context(viewport={'width': 820, 'height': 600}, device_scale_factor=2, has_touch=True)
            tp = tctx.new_page()
            tp.goto(f'http://localhost:{PORT}/'); wait_ready(tp)
            tcdp = tctx.new_cdp_session(tp)
            def touch_strokes(strokes):
                for st in strokes:
                    pts = [{'x': st[0][0], 'y': st[0][1]}]
                    tcdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': pts})
                    for (px, py) in (st[1:] or [(st[0][0] + .5, st[0][1] + .5)]):
                        tcdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': px, 'y': py}]})
                    tcdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            def dense(st):                                                  # touch moves are sparse: add points
                out = [st[0]]
                for a, b in zip(st, st[1:]):
                    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 4))
                    out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(1, n + 1)]
                return out
            x = 70
            for ch in '7+2=':
                touch_strokes([dense(s) for s in glyph(ch, x, 80)]); x += adv(ch)
            settle(tp, 1200)
            backing = tp.evaluate("(() => { const c = document.getElementById('ink'); return [c.width, c.getBoundingClientRect().width]; })()")
            check('high-DPI: canvas backing store = CSS size × devicePixelRatio', backing[0] == 2 * round(backing[1]), f'{backing[0]} px for {backing[1]} CSS px')
            check('touch input draws and is recognised', results(tp) == ['9'], f'{results(tp)}, reads {tp.evaluate("CalcInk.lines.map(l => l.text)")}')
            if SHOTS: tp.screenshot(path=str(SHOTS / 'touch-retina.png'))
            tctx.close()

            # ── standalone single file (file://) ──────────────────────────────
            sp = browser.new_page(viewport={'width': 1000, 'height': 500})
            sp.goto((ROOT / 'dist' / 'calcink-standalone.html').as_uri())
            wait_ready(sp)
            write(sp, '6x7=', 60, 60); settle(sp, 1000)
            check('standalone build works from file://', results(sp) == ['42'], f'{results(sp)}')
            browser.close()
    finally:
        server.terminate()
    print(f'\n{"ALL PASSED" if not check.fails else f"{check.fails} FAILED"}')
    sys.exit(1 if check.fails else 0)


if __name__ == '__main__':
    main()
