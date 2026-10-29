import { expect, test } from '@playwright/test';

test('API real: mapa, seleção de base, comparação, reprodução e troca de cidade', async ({ page }) => {
  test.skip(!process.env.KTSP_REAL_API, 'Requer a API Python na porta 8000.');
  test.setTimeout(90000);
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await page.getByLabel('Orçamento (iterações)').fill('100');
  const execute = async (name) => {
    const response = page.waitForResponse('**/api/solve');
    await page.getByRole('button', { name, exact: true }).click();
    const api = await response;
    expect(api.ok()).toBe(true);
    await expect(page.getByRole('button', { name: 'Pausar', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Pausar', exact: true }).click();
    return api.json();
  };
  const first = await execute('Executar algoritmo');
  expect(first.city).toBe('ibirapuita');
  await expect(page.locator('.leaflet-map')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Comparação das bases' })).toBeVisible();
  // Seleciona uma entrega existente como nova base: exige reconciliar as entregas.
  await page.getByLabel('Voltar ao início', { exact: true }).click();
  const base = first.deliveries[first.steps[0].bestOrder[0] - 1];
  await page.locator('.leaflet-marker-icon:not(.stop-base):not(.stop-selected)').first().click();
  await expect(page.getByRole('combobox', { name: 'Vértice da base', exact: true })).toHaveValue(String(base));
  const changed = await execute('Recalcular com nova base');
  expect(changed.base).toBe(base);
  expect(changed.displayBase).toBe(base);
  expect(changed.deliveries).not.toContain(base);
  await page.getByRole('combobox', { name: 'Base exibida no mapa', exact: true }).selectOption('random');
  const random = await execute('Executar algoritmo');
  expect(random.displayBase).not.toBe(base);
  await page.getByLabel('Ver resultado final', { exact: true }).click();
  await page.screenshot({ path: 'test-results/real-map-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/real-map-mobile.png', fullPage: true });
  await page.getByRole('combobox', { name: 'Cidade', exact: true }).selectOption('grid');
  const grid = await execute('Executar algoritmo');
  expect(grid.city).toBe('grid');
  expect(grid.geographic).toBe(false);
  await expect(page.getByRole('heading', { name: 'Grade sintética' })).toBeVisible();
  expect(errors).toEqual([]);
});
