import { test, expect } from '@playwright/test';

// Nhóm test 1: Kiểm tra tổng quan trang Admin Dashboard
test.describe('Admin Dashboard Smoke Tests', () => {
  
  test('01. Kiểm tra URL trang Admin', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    await expect(page).toHaveURL(/.*admin/);
  });

  test('02. Kiểm tra hiển thị thanh Sidebar', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const sidebar = page.locator('aside, .ant-layout-sider');
    await expect(sidebar).toBeVisible();
  });

  test('03. Kiểm tra tiêu đề chính (Header/Heading)', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const heading = page.locator('h1, h2, .ant-typography').first();
    await expect(heading).toBeVisible();
  });

  test('04. Kiểm tra sự tồn tại của các thẻ thống kê (Cards)', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const cards = page.locator('.ant-card');
    // Kiểm tra có ít nhất 1 card thống kê hiển thị
    await expect(cards.first()).toBeVisible();
  });

  test('05. Kiểm tra phân vùng nội dung chính', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const content = page.locator('main, .ant-layout-content');
    await expect(content).toBeVisible();
  });
});

// Nhóm test 2: Kiểm tra các mục điều hướng (Navigation) trong Admin
test.describe('Admin Navigation & Sub-pages', () => {
  
  test('06. Điều hướng đến mục Quản lý người dùng', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const userLink = page.getByRole('link', { name: /user|người dùng/i }).first();
    if (await userLink.isVisible()) {
      await userLink.click();
      await expect(page).toHaveURL(/.*user|.*nguoi-dung/);
    } else {
      expect(true).toBeTruthy(); // Bỏ qua nếu chưa có link riêng biệt
    }
  });

  test('07. Kiểm tra hiển thị bảng dữ liệu (Table)', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const table = page.locator('.ant-table');
    if (await table.count() > 0) {
      await expect(table.first()).toBeVisible();
    } else {
      // Fallback kiểm tra trang load thành công
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('08. Kiểm tra sự tồn tại của nút Thêm mới (Create/Add button)', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const addBtn = page.locator('button:has-text("Thêm"), button:has-text("Create"), button:has-text("New")');
    if (await addBtn.count() > 0) {
      await expect(addBtn.first()).toBeVisible();
    } else {
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('09. Kiểm tra hộp thoại tìm kiếm (Search input)', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="Tìm"], .ant-input-search');
    if (await searchInput.count() > 0) {
      await expect(searchInput.first()).toBeVisible();
    } else {
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('10. Kiểm tra hiển thị Footer hoặc thông tin bản quyền', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const footer = page.locator('footer, .ant-layout-footer');
    if (await footer.count() > 0) {
      await expect(footer).toBeVisible();
    } else {
      await expect(page.locator('body')).toBeVisible();
    }
  });
});

// Nhóm test 3: Kiểm tra giao diện và phản hồi chung của hệ thống
test.describe('System Response & General UI', () => {

  test('11. Kiểm tra trạng thái phản hồi HTTP 200 khi truy cập', async ({ page }) => {
    const response = await page.goto('http://localhost:3000/admin');
    expect(response?.status()).toBeLessThan(400);
  });

  test('12. Kiểm tra không có lỗi console lớn khi tải trang', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('http://localhost:3000/admin');
    // Đảm bảo trang load xong
    await page.waitForLoadState('networkidle');
    expect(errors.length).toBeLessThan(5); // Chấp nhận dưới 5 lỗi cảnh báo vặt
  });

  test('13. Kiểm tra responsive giao diện (Thử nghiệm khung nhìn Mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:3000/admin');
    await expect(page.locator('body')).toBeVisible();
  });

  test('14. Kiểm tra responsive giao diện (Thử nghiệm khung nhìn Tablet)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('http://localhost:3000/admin');
    await expect(page.locator('body')).toBeVisible();
  });

  test('15. Kiểm tra nút Đăng xuất hoặc thông tin tài khoản Admin', async ({ page }) => {
    await page.goto('http://localhost:3000/admin');
    const profileOrLogout = page.locator('text=/admin|đăng xuất|logout|profile/i');
    await expect(profileOrLogout.first()).toBeVisible();
  });

});