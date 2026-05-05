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

test('root admin can change the initial password and enter the dashboard', async ({ page }) => {
  await loginAdmin(page, 'root', 'password');

  await expect(page).toHaveURL(/\/admin\/change-password/);
  await expect(page.getByText('首次登录需要修改密码')).toBeVisible();
  await page.getByLabel('当前密码').fill('password');
  await page.getByLabel('新密码', { exact: true }).fill('new-password');
  await page.getByLabel('确认新密码').fill('new-password');
  await page.getByRole('button', { name: '修改密码并进入后台' }).click();

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole('heading', { name: '仪表盘' })).toBeVisible();
});

test('alice starts with an empty submission queue after fresh reset', async ({ page }) => {
  await loginFrontend(page, 'alice', 'password123');

  await expect(page.getByRole('heading', { name: '我的插件申请' })).toBeVisible();
  await expect(page.getByText('还没有提交插件申请')).toBeVisible();
});

test('upload creates a review submission visible in admin workspace', async ({ page }) => {
  const suffix = Date.now().toString(36);
  const pluginName = `E2E Plugin ${suffix}`;

  await loginFrontend(page, 'alice', 'password123', '/upload');
  await page.getByLabel('仓库 URL').fill(`https://github.com/wislap/n.e.k.o_plugin_e2e_${suffix}`);
  await page.getByLabel('插件名称').fill(pluginName);
  await page.getByLabel('简介').fill('End to end submission for the fresh review workspace.');
  await page.getByRole('combobox').click();
  await page.getByRole('option', { name: '功能区' }).click();
  await page.getByRole('button', { name: '工具' }).click();
  await page.getByRole('button', { name: '提交审核申请' }).click();

  await expect(page).toHaveURL(/\/my\/plugins\?submission=\d+/);
  await expect(page.getByRole('heading', { name: '我的插件申请' })).toBeVisible();
  await expect(page.getByRole('heading', { name: pluginName })).toBeVisible();
  await expect(page.getByText('刚刚提交')).toBeVisible();
  await page.getByRole('button', { name: '查看详情' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByRole('heading', { name: '审核意见' })).toBeVisible();
  await expect(page.getByRole('dialog').getByText(`https://github.com/wislap/n.e.k.o_plugin_e2e_${suffix}`)).toBeVisible();

  await loginAdmin(page, 'reviewer', 'password123');
  await page.goto('/#/admin/review/workspace');

  await expect(page.getByRole('heading', { name: '审核工作区' })).toBeVisible();
  await expect(page.getByRole('heading', { name: pluginName })).toBeVisible();
  await expect(page.getByText('待审核').first()).toBeVisible();
});
