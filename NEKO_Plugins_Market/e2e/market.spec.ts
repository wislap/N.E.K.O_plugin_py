import { expect, type Page, test } from '@playwright/test';

async function loginFrontend(page: Page, username: string, password: string, next = '/my/plugins') {
  await page.goto(`/#/login?next=${encodeURIComponent(next)}`);
  await page.getByPlaceholder('用户名或邮箱').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  await page.locator('main form').first().locator('button[type="submit"]').click();
  await expect(page).toHaveURL(new RegExp(next.replace(/\//g, '\\/')));
}

async function loginAdmin(page: Page, username: string, password: string) {
  await page.goto('/#/admin/login');
  await page.getByPlaceholder('请输入用户名').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  await page.getByRole('button', { name: '登录' }).click();
  await expect(page).toHaveURL(/\/admin(?!\/login)/);
}

test('marketplace only shows approved seeded plugins', async ({ page }) => {
  await page.goto('/#/plugins');

  await expect(page.getByRole('heading', { name: '所有插件' })).toBeVisible();
  await expect(page.getByText('天气提醒助手')).toBeVisible();
  await expect(page.getByText('游戏资料查询')).toBeVisible();

  await expect(page.getByText('音乐点歌面板')).toHaveCount(0);
  await expect(page.getByText('不安全命令执行测试')).toHaveCount(0);
  await expect(page.getByText('旧版翻译助手')).toHaveCount(0);
});

test('root admin is forced to change the initial password', async ({ page }) => {
  await loginAdmin(page, 'root', 'password');

  await expect(page).toHaveURL(/\/admin\/change-password/);
  await expect(page.getByText('首次登录需要修改密码')).toBeVisible();
});

test('alice can see owned plugins and seeded notifications', async ({ page }) => {
  await loginFrontend(page, 'alice', 'password123');

  await expect(page.getByRole('heading', { name: '我的插件' })).toBeVisible();
  await expect(page.getByText('天气提醒助手')).toBeVisible();
  await expect(page.getByText('音乐点歌面板')).toBeVisible();
  await expect(page.getByText('待审核').first()).toBeVisible();

  await page.getByLabel('打开通知').click();
  await expect(page.getByText('天气提醒助手已通过审核')).toBeVisible();
  await expect(page.getByText('音乐点歌面板正在等待审核')).toBeVisible();
});

test('reviewer can access the plugin review panel and see pending submissions', async ({ page }) => {
  await loginAdmin(page, 'reviewer', 'password123');
  await page.goto('/#/admin/plugins');

  await expect(page.getByRole('heading', { name: '插件审核' }).last()).toBeVisible();
  await expect(page.getByText('音乐点歌面板')).toBeVisible();
  await expect(page.getByText('待审核').first()).toBeVisible();
});
