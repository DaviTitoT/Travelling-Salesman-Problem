import { expect, test } from '@playwright/test';

// Resposta com o contrato real da API; sem depender do tempo do solver.
const path = [0, 1, 2, 6, 10, 9, 8, 4, 0];
const result = {
  city: 'grid', cityName: 'Grade sintética', geographic: false, unit: 'unidades', boundary: [], attribution: '',
  size: 4, seed: 42, k: 2, tabuTenure: 0, base: 0, displayBase: 0, deliveries: [2, 10],
  positions: Array.from({ length: 16 }, (_, i) => [-Math.floor(i / 4), i % 4]),
  routeBase: 'selected', randomSeed: 43,
  comparisons: ['selected', 'random'].map((strategy, i) => ({ strategy, base: i, initialCost: 100, bestCost: 80, improvementPct: 20 })),
  edges: path.slice(1).map((point, i) => [path[i], point]),
  initialCost: 100, bestCost: 80, optimumCost: 80, iterations: 100, foundAt: 50,
  bestVisits: [2, 10], bestVertexPath: [0, 1, 2, 6, 10, 9, 8, 4, 0],
  steps: Array.from({ length: 101 }, (_, iteration) => ({
    iteration, temperature: 100 * 0.9 ** iteration,
    currentCost: iteration < 50 ? 100 : 80, bestCost: iteration < 50 ? 100 : 80,
    bestOrder: [1, 2], currentPath: path, bestPath: path,
  })),
};

test('reprodução automática, pausa, velocidade, navegação, nova execução e erro', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/api/solve', (route) => route.fulfill({ json: result }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Executar algoritmo' }).click();
  await expect(page.getByRole('button', { name: 'Pausar', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Pausar', exact: true }).click();
  const slider = page.getByRole('slider', { name: 'Iteração', exact: true });
  const paused = await slider.inputValue();
  await page.waitForTimeout(200);
  expect(await slider.inputValue()).toBe(paused);
  await page.getByLabel('Próximo passo', { exact: true }).click();
  expect(Number(await slider.inputValue())).toBe(Number(paused) + 1);
  await page.getByLabel('Velocidade de reprodução').selectOption('4');
  await page.getByRole('button', { name: 'Continuar', exact: true }).click();
  await expect.poll(async () => Number(await slider.inputValue())).toBeGreaterThan(Number(paused) + 1);
  await page.getByLabel('Ver resultado final', { exact: true }).click();
  await expect(slider).toHaveValue('100');
  await expect(page.getByText('REPRODUÇÃO CONCLUÍDA', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Rever', exact: true }).click();
  await expect.poll(async () => Number(await slider.inputValue())).toBeLessThan(100);
  await page.getByRole('button', { name: 'Executar algoritmo' }).click();
  await expect(page.getByRole('button', { name: 'Pausar', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Pausar', exact: true }).click();
  await page.screenshot({ path: 'test-results/react-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/react-mobile.png', fullPage: true });
  await page.route('**/api/solve', (route) => route.fulfill({ status: 400, json: { error: 'Falha de teste' } }));
  await page.getByRole('button', { name: 'Executar algoritmo' }).click();
  await expect(page.getByRole('alert')).toContainText('Falha de teste');
  await expect(page.locator('.leaflet-map')).toBeVisible();
  expect(errors).toEqual([]);
});

test('cronômetro durante a requisição e resposta com um único passo', async ({ page }) => {
  let respond;
  await page.route('**/api/solve', async (route) => {
    await new Promise((resolve) => { respond = resolve; });
    await route.fulfill({ json: { ...result, k: 1, iterations: 0, steps: [result.steps[0]] } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Executar algoritmo' }).click();
  await expect(page.getByRole('status')).toContainText('Calculando a rota');
  await expect.poll(async () => await page.getByRole('status').innerText()).not.toContain('0 s');
  respond();
  await expect(page.getByRole('button', { name: 'Rever', exact: true })).toBeDisabled();
  await expect(page.getByRole('status')).toHaveCount(0);
});
