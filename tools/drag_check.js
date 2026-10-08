/*
 * Browser check for the drag-paint interaction on the note grid.
 * The coordinate mapping (canvas cell -> song[x][y]), the stroke mode and the
 * per-stroke cell de-duplication are easy to break by accident, so this drives
 * a real Chromium and asserts the resulting song state.
 *
 * Needs the dev server running and Playwright available:
 *     uv run python app.py &
 *     npm i playwright && npx playwright install chromium
 *     node tools/drag_check.js
 */
const { chromium } = require('playwright');
const { existsSync, readdirSync } = require('fs');
const { homedir } = require('os');
const { join } = require('path');

const URL = process.env.GT_URL || 'http://127.0.0.1:5000/';
const CELL = 32;

// prefer a browser already in the Playwright cache (any build) over a fresh download
function cachedChromium() {
  const root = join(homedir(), '.cache', 'ms-playwright');
  if (!existsSync(root)) return undefined;
  for (const dir of readdirSync(root).filter(d => /^chromium-\d+$/.test(d)).sort().reverse()) {
    const bin = join(root, dir, 'chrome-linux64', 'chrome');
    if (existsSync(bin)) return bin;
  }
  return undefined;
}

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.GT_CHROME || cachedChromium(),
    args: ['--autoplay-policy=no-user-gesture-required', '--mute-audio'],
  });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  const problems = [];
  page.on('pageerror', e => problems.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') problems.push('console: ' + m.text()); });
  page.on('response', r => { if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`); });

  await page.goto(URL);
  await page.waitForFunction('window.filesLoaded === true', null, { timeout: 60000 });
  console.log('assets loaded, overlay removed:', await page.locator('#loading').count() === 0);

  const box = await page.locator('#loadout').boundingBox();
  const at = (col, row) => ({ x: box.x + col * CELL + CELL / 2, y: box.y + row * CELL + CELL / 2 });
  const pixel = (px, py) => page.evaluate(([x, y]) => {
    const d = document.getElementById('loadout').getContext('2d').getImageData(x, y, 1, 1).data;
    return [d[0], d[1], d[2]].join(',');
  }, [px, py]);
  const spritePixel = (name, x, y) => page.evaluate(([n, x, y]) => {
    const cv = document.createElement('canvas');
    cv.width = cv.height = 32;
    const cx = cv.getContext('2d');
    const e = window.imgdata[n];           // gear is a bare Image, instruments are {off, on}
    cx.drawImage(e.off || e, 0, 0);
    const d = cx.getImageData(x, y, 1, 1).data;
    return [d[0], d[1], d[2], d[3]].join(',');
  }, [name, x, y]);
  const cells = () => page.evaluate(() => {
    const out = [];
    song.forEach((col, x) => col.forEach((n, y) => { if (n) out.push(`${x}:${y}:${n}`); }));
    return out;
  });
  const press = async (button, from, to) => {
    await page.mouse.move(from.x, from.y);
    await page.mouse.down({ button });
    await page.mouse.move(to.x, to.y, { steps: 40 });
    await page.mouse.up({ button });
  };
  const check = (ok, label, detail) => {
    console.log((ok ? 'ok   ' : 'FAIL ') + label + (ok ? '' : ' -> ' + detail));
    if (!ok) process.exitCode = 1;
  };

  // sweep left to right paints one note per crossed cell
  await page.click('img[onclick*="note(0"]');
  await press('left', at(1, 1), at(8, 1));
  let got = await cells();
  const xs = got.map(s => +s.split(':')[0]).join(',');
  check(got.length === 8 && xs === '0,1,2,3,4,5,6,7', 'sweep paints 8 cells at x=0..7', xs);
  check(got[0] && got[0].split(':')[1] === '14', 'top note row maps to song y=14', got[0]);

  // sweeping back over the same instrument erases (seed cell decides the mode)
  await press('left', at(8, 1), at(1, 1));
  check((await cells()).length === 0, 'sweep back over same note erases', JSON.stringify(await cells()));

  // right button always erases
  await press('left', at(1, 2), at(8, 2));
  const placed = (await cells()).length;
  await press('right', at(8, 2), at(1, 2));
  check(placed === 8 && (await cells()).length === 0, 'right-drag erases', `${placed} -> ${(await cells()).length}`);

  // plain clicks still place, and clicking the same note still removes it
  await page.mouse.click(at(12, 1).x, at(12, 1).y);
  const one = (await cells()).length;
  await page.mouse.click(at(12, 1).x, at(12, 1).y);
  check(one === 1 && (await cells()).length === 0, 'click still toggles one cell', `${one} -> ${(await cells()).length}`);

  // bottom note row, and never more notes than cells touched
  await press('left', at(1, 14), at(4, 14));
  got = await cells();
  check(got.length === 4 && got.every(s => s.split(':')[1] === '1'), 'bottom row maps to song y=1', got.join(' '));

  // dragging an icon out of the picker and dropping it on a cell
  await press('left', at(1, 14), at(4, 14)); // clear the row again
  await page.dragAndDrop('img[data-note="3"]', '#loadout', { targetPosition: { x: 20 * CELL + 16, y: 3 * CELL + 16 } });
  got = await cells();
  check(got.length === 1 && got[0].startsWith('19:12:D'), 'drop from picker places one drum at x=19,y=12', got.join(' '));
  check(await page.evaluate(() => state) === 3, 'drop also selects the dragged instrument', await page.evaluate(() => state));

  check(problems.length === 0, 'no console errors / failed requests', JSON.stringify(problems));

  // the atlas must blit real sprite pixels, and transparent sprite pixels must keep
  // the tile colour (this caught alpha:false on the atlas + gear not being drawn)
  await page.click('img[data-note="0"]'); // the drop test above left the drum selected
  await press('left', at(1, 1), at(4, 1));
  const sprite = await spritePixel('piano', 16, 16);
  check((await pixel(1 * CELL + 16, 1 * CELL + 16)) + ',255' === sprite, 'placed note renders the sprite pixel', `${await pixel(1 * CELL + 16, 1 * CELL + 16)} vs ${sprite}`);
  // skip x/y 0-1: renderGrid strokes a black line along the top and left cell edges
  const clear = await page.evaluate(() => {
    const cv = document.createElement('canvas');
    cv.width = cv.height = 32;
    const cx = cv.getContext('2d');
    cx.drawImage(window.imgdata.gear, 0, 0);
    const d = cx.getImageData(0, 0, 32, 32).data;
    for (let i = 0; i < d.length; i += 4) {
      const x = (i / 4) % 32, y = Math.floor(i / 4 / 32);
      if (d[i + 3] === 0 && x > 1 && y > 1) return [x, y];
    }
    return null;
  });
  if (clear) {
    const got = await pixel(2 * CELL + clear[0], clear[1]);
    check(got === '149,218,250', `transparent gear pixel at ${clear} keeps the tile colour`, got);
  } else {
    console.log('skip transparent-sprite check: gear.png has no transparent pixels');
  }
  console.log(process.exitCode ? '\nFAILED' : '\nall drag checks passed');
  await page.screenshot({ path: '/tmp/gtmusic-drag.png' });
  await browser.close();
})();
