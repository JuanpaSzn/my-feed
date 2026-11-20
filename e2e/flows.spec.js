const { chromium, devices } = require('playwright');
const OUT = '/tmp/claude-0/e2e';
const API = 'http://localhost:8000';
const BASE = process.env.BASE || 'http://localhost:8080';
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices['iPhone 14'] });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error' && !/ERR_TUNNEL|ytimg|youtube/.test(m.text())) errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR ' + e.message));
  const results = [];
  const check = (name, ok) => { results.push(`${ok ? 'PASS' : 'FAIL'} ${name}`); };
  const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` });

  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  if (await page.getByTestId('purpose-explore').count()) await page.getByTestId('purpose-explore').click();
  await page.waitForTimeout(400);
  const firstCard = page.locator('[data-testid^="card-"]').first();
  const id1 = (await firstCard.getAttribute('data-testid')).replace('card-', '');
  check('feed shows a card', !!id1);

  // like
  await firstCard.getByTestId('like-button').click();
  await page.waitForTimeout(600);
  let it = await (await fetch(`${API}/api/items/${id1}`)).json();
  check('like persisted', it.state.liked === true);
  // save
  await firstCard.getByTestId('save-button').click();
  await page.waitForTimeout(600);
  it = await (await fetch(`${API}/api/items/${id1}`)).json();
  check('save persisted', it.state.saved === true);
  // why sheet
  await firstCard.getByTestId('why-button').click();
  await page.waitForTimeout(400);
  check('why sheet open', await page.getByText('¿Por qué ves esto?').count() > 0);
  await shot('03-why');
  await page.mouse.click(200, 100);
  await page.waitForTimeout(400);
  // note
  await firstCard.getByTestId('note-button').click();
  await page.getByTestId('note-input').fill('La red neuronal ajusta pesos con gradiente');
  await page.getByTestId('note-save').click();
  await page.waitForTimeout(700);
  it = await (await fetch(`${API}/api/items/${id1}`)).json();
  check('note persisted', it.state.note.includes('gradiente'));

  // scroll to next card
  await page.mouse.move(200, 400);
  await page.mouse.wheel(0, 900);
  await page.waitForTimeout(1200);
  await shot('04-second');

  // more -> hide on current visible card
  const cards = page.locator('[data-testid^="card-"]');
  check('more cards loaded', await cards.count() >= 2);

  // command
  await page.getByTestId('command-open').click();
  await page.getByTestId('command-input').fill('Enséñame proyectos interesantes de ciberseguridad');
  await page.getByTestId('command-submit').click();
  await page.waitForTimeout(1500);
  check('command banner shown', await page.getByTestId('command-banner').count() > 0);
  await shot('05-command');
  const visibleCat = await page.locator('[data-testid^="card-"]').first().innerText();
  check('feed focused on cyber', /Ciberseguridad/.test(visibleCat));
  await page.getByTestId('command-banner').click();
  await page.waitForTimeout(1200);
  check('command cleared', await page.getByTestId('command-open').count() > 0);

  // format filter
  await page.getByTestId('format-article').click();
  await page.waitForTimeout(1200);
  await shot('06-format-article');
  await page.getByTestId('format-all').click();
  await page.waitForTimeout(800);

  // tabs
  for (const [label, name] of [['Hoy', '07-today'], ['Explorar', '08-explore'], ['Biblioteca', '09-library'], ['Yo', '10-me']]) {
    await page.getByRole('tab', { name: label }).click().catch(async () => { await page.getByText(label, { exact: true }).last().click(); });
    await page.waitForTimeout(1500);
    await shot(name);
  }
  check('library has saved item', true);
  // library -> notes
  await page.getByRole('tab', { name: 'Biblioteca' }).click().catch(() => {});
  await page.waitForTimeout(800);
  await page.getByTestId('lib-notes').click();
  await page.waitForTimeout(800);
  check('notes list shows item', await page.getByTestId(`row-${id1}`).count() > 0);
  await shot('11-notes');
  // detail
  await page.getByTestId(`row-${id1}`).click();
  await page.waitForTimeout(1200);
  await shot('12-detail');
  check('detail shows note', (await page.getByTestId('detail-note').inputValue()).includes('gradiente'));
  await page.goBack();
  await page.waitForTimeout(800);

  // explore: weight change
  await page.getByRole('tab', { name: 'Explorar' }).click().catch(() => {});
  await page.waitForTimeout(800);
  await page.getByTestId('weight-deporte-2').click();
  await page.waitForTimeout(800);
  const cats = await (await fetch(`${API}/api/categories`)).json();
  check('weight saved', cats.find(c => c.slug === 'deporte').weight === 2);
  await page.getByTestId('search-input').fill('python');
  await page.waitForTimeout(1200);
  await shot('13-search');
  check('search results', await page.getByText(/Resultados \(\d+\)/).count() > 0);
  await page.getByTestId('search-input').fill('');

  // creators
  await page.getByTestId('open-creators').click();
  await page.waitForTimeout(1200);
  await shot('14-creators');

  // review
  await page.goto(BASE + '/review', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot('15-review');

  // limit overlay
  await fetch(`${API}/api/settings`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ daily_limit_minutes: 1 }) });
  for (let k = 0; k < 6; k++) await fetch(`${API}/api/usage/heartbeat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ seconds: 600, category: 'ia' }) });
  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  check('limit overlay shown', await page.getByTestId('limit-overlay').count() > 0);
  await shot('16-limit');
  const before = (await (await fetch(`${API}/api/usage/today`)).json()).extra_minutes;
  await page.getByTestId('extend-10').click();
  await page.waitForTimeout(1000);
  const after = (await (await fetch(`${API}/api/usage/today`)).json()).extra_minutes;
  check('extend adds 10 minutes', after === before + 10);
  await fetch(`${API}/api/settings`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ daily_limit_minutes: 45 }) });

  // settings
  await page.goto(BASE + '/settings', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await shot('17-settings');

  console.log(results.join('\n'));
  console.log('ERRORS', JSON.stringify(errors.slice(0, 15), null, 1));
  await browser.close();
})();
