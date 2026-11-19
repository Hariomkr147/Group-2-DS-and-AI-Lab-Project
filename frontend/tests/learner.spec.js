import { expect, test } from '@playwright/test';

async function signIn(page) {
  await page.goto('/');
  await page.getByLabel('Username').fill('browser-tester');
  await page.getByLabel('Password').fill('browser-test-fixture');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Where are you stuck?' })).toBeVisible();
}

test('opens a saved chat after starting a new one', async ({ page }) => {
  await signIn(page);
  const topic = 'Help me study division again';
  await page.getByLabel('Your question or answer').fill(topic);
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByLabel('Tutor conversation').locator('article')).toHaveCount(2);
  const history = page.getByRole('button', { name: 'Previous chats', exact: true });
  await history.click();
  await page.keyboard.press('Escape');
  await expect(history).toBeFocused();
  await history.click();
  await page.getByRole('button', { name: 'New chat in this lesson' }).click();
  await expect(page.getByText('Where are you stuck?')).toBeVisible();
  await history.click();
  for (const width of [375, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 820 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.getByRole('dialog').getByRole('button', { name: new RegExp(topic) }).click();
  await expect(page.getByLabel('Tutor conversation').getByText(topic)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Tutor conversation').locator('article')).toHaveCount(2);
});

test('switches topics, preserves working on retry, and restores progress after reload', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await signIn(page);
  if (!(await page.getByRole('button', { name: /^Percentages/ }).isVisible())) await page.getByText('Concepts', { exact: true }).click();
  await page.getByRole('button', { name: /^Percentages/ }).click();
  await expect(page.getByRole('button', { name: /^Percentages/ })).toHaveAttribute('aria-current', 'true');
  await page.getByRole('button', { name: /^Division/ }).click();
  await expect(page.getByRole('button', { name: /^Division/ })).toHaveAttribute('aria-current', 'true');
  await page.getByRole('button', { name: 'Ask for a hint' }).click();
  await expect(page.getByText('Hint', { exact: true })).toBeVisible();

  const messagePath = '**/api/sessions/*/messages';
  let requestId;
  await page.route(messagePath, async (route) => {
    requestId = route.request().postDataJSON().request_id;
    const saved = await route.fetch();
    expect(saved.ok()).toBe(true);
    await route.abort();
  }, { times: 1 });
  await page.route('**/progress?*', (route) => route.fulfill({ status: 503, json: { detail: 'Fixture outage' } }));
  const working = '100 / 20 = 5\nAnswer: 5';
  await page.getByRole('textbox', { name: 'Your question or answer' }).fill(working);
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  const retry = page.waitForRequest((request) => request.url().endsWith('/messages'));
  await page.getByRole('button', { name: 'Retry message' }).click();
  expect((await retry).postDataJSON()).toMatchObject({ text: working, request_id: requestId });
  await expect(page.getByText('Progress is temporarily unavailable.')).toBeVisible();
  await expect(page.getByText('Awaiting confirmation')).toHaveCount(0);
  await page.unroute('**/progress?*');
  await page.reload();
  await expect(page.getByText(working)).toBeVisible();
  await expect(page.getByLabel('Tutor conversation').locator('article')).toHaveCount(8);
  await expect(page.getByText('1/1', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Practice', exact: true }).click();
  await page.getByRole('button', { name: 'Start practice' }).click();
  await page.getByLabel('Your answer').fill('5');
  await page.getByRole('button', { name: 'Check answer' }).click();
  await expect(page.getByText('Correct.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'See results' }).click();
  await expect(page.getByText('1 / 1 correct')).toBeVisible();
  await page.getByRole('button', { name: 'Diagnostic', exact: true }).click();
  await page.getByRole('button', { name: 'Start diagnostic' }).click();
  await expect(page.getByText('Question 1 of 4')).toBeVisible();
  expect(errors).toEqual([]);
});

test('recovers from session verification and course-list outages', async ({ page }) => {
  await signIn(page);
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 503, json: {} }), { times: 1 });
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Couldn’t check your sign-in' })).toBeVisible();
  await page.route('**/api/courses', (route) => route.fulfill({ status: 503, json: {} }), { times: 1 });
  await page.getByRole('button', { name: 'Try again' }).click();
  await page.getByRole('button', { name: 'Retry loading courses' }).click();
  await expect(page.getByRole('heading', { name: 'Where are you stuck?' })).toBeVisible();
});

test('opens a scoped textbook lesson, searches sources, and renders maths in dark mode on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await signIn(page);
  await page.getByRole('combobox', { name: 'Course', exact: true }).selectOption('ncert');
  await page.getByRole('combobox', { name: 'Subject', exact: true }).selectOption('science');
  await page.getByRole('combobox', { name: 'Chapter', exact: true }).selectOption({ label: 'Chapter 11 · jesc1' });
  await page.getByRole('button', { name: 'Open lesson' }).click();
  await page.getByText('Chapter topics', { exact: true }).click();
  await page.getByRole('button', { name: 'Electric current', exact: true }).click();
  const source = page.getByRole('link', { name: /Electric current.*Page 8/ });
  await expect(source).toHaveAttribute('href', /#page=8$/);
  await expect(page.getByText('Explanation', { exact: true })).toBeVisible();
  await expect(page.getByText(/Electric current measures the flow/)).toBeVisible();
  await page.getByRole('button', { name: 'Ask for a hint' }).click();
  await expect(page.getByText('Hint', { exact: true })).toBeVisible();
  await page.getByRole('textbox', { name: 'Your question or answer' }).fill('Just give me the answer');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(page.getByText('Redirect', { exact: true })).toBeVisible();
  await expect(page.locator('article').last().getByRole('link')).toHaveCount(0);
  await page.getByText('Search course sources', { exact: true }).click();
  await page.getByLabel('Topic or keyword').fill('electric current');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.locator('.search-hit summary').click();
  await expect(page.locator('.search-hit').getByRole('link')).toHaveAttribute('href', /#page=8$/);
  await page.getByLabel('Color theme').selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByText('Maths tools', { exact: true }).click();
  await expect(page.locator('.math-tools math')).toBeVisible();
  await page.getByRole('combobox', { name: 'Visual', exact: true }).selectOption('graph');
  await expect(page.getByText(/Point \(3, 3\)/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('combobox', { name: 'Course', exact: true }).selectOption('ncert-maths');
  await page.getByRole('button', { name: 'Previous chats', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: /Help me understand Electric current/ }).click();
  await expect(page.getByRole('combobox', { name: 'Chapter', exact: true })).toHaveValue('0');
  await expect(page.getByLabel('Tutor conversation').getByRole('link', { name: /Electric current.*Page 8/ }).last()).toBeVisible();
});
