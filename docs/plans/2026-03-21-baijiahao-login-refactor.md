# 百家号登录流程重构实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构百家号登录流程，修复选择器、登录状态检测、验证逻辑等问题

**Architecture:** 修改 `myUtils/login.py` 中的 `baijiahao_cookie_gen` 函数，添加辅助函数实现多选择器尝试，统一 `auth.py` 和 `main.py` 中的验证逻辑

**Tech Stack:** Python, Playwright, asyncio

---

### Task 1: 添加浏览器配置辅助函数

**Files:**
- Modify: `myUtils/login.py:44-62`

**Step 1: 编写 `get_baijiahao_options` 函数**

在 `get_browser_options` 函数后添加：

```python
# 百家号专用浏览器配置
def get_baijiahao_options():
    """百家号专用浏览器配置，基于通用配置"""
    return get_browser_options()
```

**Step 2: 验证函数可用**

运行: `python -c "from myUtils.login import get_baijiahao_options; print(get_baijiahao_options())"`
Expected: 输出浏览器配置字典

**Step 3: 提交**

```bash
git add myUtils/login.py
git commit -m "feat: add baijiahao browser options helper function"
```

---

### Task 2: 添加登录按钮点击辅助函数

**Files:**
- Modify: `myUtils/login.py:488-602`

**Step 1: 编写 `click_baijiahao_login_button` 函数**

在 `baijiahao_cookie_gen` 函数前添加：

```python
async def click_baijiahao_login_button(page):
    """尝试多种方式点击百家号登录按钮"""
    selectors = [
        ("text", "登录/注册百家号"),
        ("text", "登录", {"exact": True}),
        ("role", "link", {"name": "登录"}),
    ]

    for selector_type, *args in selectors:
        try:
            if selector_type == "text":
                await page.get_by_text(*args).click(timeout=5000)
            elif selector_type == "role":
                await page.get_by_role(*args).click(timeout=5000)
            print(f"✅ 成功点击登录按钮 (选择器: {selector_type})")
            return True
        except Exception as e:
            print(f"⚠️ 选择器 {selector_type} 失败: {e}")
            continue

    return False
```

**Step 2: 验证函数语法**

运行: `python -c "import ast; ast.parse(open('myUtils/login.py').read()); print('语法正确')"`
Expected: 输出 "语法正确"

**Step 3: 提交**

```bash
git add myUtils/login.py
git commit -m "feat: add multi-selector login button click function"
```

---

### Task 3: 添加二维码获取辅助函数

**Files:**
- Modify: `myUtils/login.py:488-602`

**Step 1: 编写 `get_baijiahao_qrcode_src` 函数**

在 `click_baijiahao_login_button` 函数后添加：

```python
async def get_baijiahao_qrcode_src(page):
    """获取百家号二维码图片地址"""
    selectors = [
        ".tang-pass-qrcode-img",
        ".qrcode-img img",
        "img[src*='qr']",
        "img[src*='qrcode']",
    ]

    for selector in selectors:
        try:
            img = page.locator(selector)
            if await img.count() > 0:
                src = await img.get_attribute("src", timeout=5000)
                if src:
                    print(f"✅ 获取二维码成功 (选择器: {selector})")
                    return src
        except Exception as e:
            print(f"⚠️ 选择器 {selector} 失败: {e}")
            continue

    return None
```

**Step 2: 验证函数语法**

运行: `python -c "import ast; ast.parse(open('myUtils/login.py').read()); print('语法正确')"`
Expected: 输出 "语法正确"

**Step 3: 提交**

```bash
git add myUtils/login.py
git commit -m "feat: add multi-selector qrcode getter function"
```

---

### Task 4: 添加登录成功等待辅助函数

**Files:**
- Modify: `myUtils/login.py:488-602`

**Step 1: 编写 `wait_baijiahao_login_success` 函数**

在 `get_baijiahao_qrcode_src` 函数后添加：

```python
async def wait_baijiahao_login_success(page, timeout=200):
    """等待百家号登录成功，同时检测安全验证"""
    import time
    start_time = time.time()

    while time.time() - start_time < timeout:
        # 检查安全验证弹窗
        if await page.locator('div.passMod_dialog-container:visible').count():
            raise Exception("出现百度安全验证，请手动处理后重新运行")

        # 检查是否跳转到创作者中心
        if "builder/rc" in page.url:
            print("✅ 检测到跳转到创作者中心")
            return True

        # 检查登录按钮是否消失
        if await page.get_by_text("登录/注册百家号").count() == 0:
            print("✅ 登录按钮已消失，登录成功")
            return True

        await asyncio.sleep(1)

    return False
```

**Step 2: 验证函数语法**

运行: `python -c "import ast; ast.parse(open('myUtils/login.py').read()); print('语法正确')"`
Expected: 输出 "语法正确"

**Step 3: 提交**

```bash
git add myUtils/login.py
git commit -m "feat: add login success detection with security check"
```

---

### Task 5: 重构 `baijiahao_cookie_gen` 函数

**Files:**
- Modify: `myUtils/login.py:488-602`

**Step 1: 备份原函数**

将原 `baijiahao_cookie_gen` 函数重命名为 `_baijiahao_cookie_gen_legacy`

**Step 2: 编写新 `baijiahao_cookie_gen` 函数**

```python
async def baijiahao_cookie_gen(id, status_queue):
    """百家号登录，生成cookie"""
    async with async_playwright() as playwright:
        options = get_baijiahao_options()
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()

        print("✅ 正在访问百家号登录页面...")
        await page.goto("https://baijiahao.baidu.com/builder/theme/bjh/login")
        await page.wait_for_load_state("domcontentloaded")

        # 检查是否需要登录（基于页面内容，不是URL）
        login_button = page.get_by_text("登录/注册百家号")
        if await login_button.count() == 0:
            # 没有登录按钮，检查是否在创作者中心
            if "builder/rc" in page.url:
                print("✅ 已登录，直接保存cookie")
                uuid_v1 = uuid.uuid1()
                cookies_dir = Path(BASE_DIR / "cookiesFile")
                cookies_dir.mkdir(exist_ok=True)
                await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
                result = await check_cookie(6, f"{uuid_v1}.json")
                if not result:
                    status_queue.put("500")
                    await page.close()
                    await context.close()
                    await browser.close()
                    return None
                insert_user_info_if_not_exists(6, f"{uuid_v1}.json", id, 1)
                status_queue.put("200")
                return

        # 需要登录，点击登录按钮
        print("✅ 正在点击登录按钮...")
        if not await click_baijiahao_login_button(page):
            print("❌ 点击登录按钮失败")
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 获取二维码
        print("✅ 正在获取二维码...")
        src = await get_baijiahao_qrcode_src(page)
        if not src:
            print("❌ 获取二维码失败")
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None

        print(f"✅ 二维码地址: {src}")
        status_queue.put(src)

        # 等待登录成功
        print("✅ 等待用户扫码登录...")
        try:
            if not await wait_baijiahao_login_success(page):
                print("❌ 登录超时")
                status_queue.put("500")
                await page.close()
                await context.close()
                await browser.close()
                return None
        except Exception as e:
            print(f"❌ 登录失败: {e}")
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None

        # 保存cookie
        uuid_v1 = uuid.uuid1()
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")

        # 验证cookie
        result = await check_cookie(6, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None

        await page.close()
        await context.close()
        await browser.close()

        # 插入用户信息
        insert_user_info_if_not_exists(6, f"{uuid_v1}.json", id, 1)
        status_queue.put("200")
```

**Step 3: 验证函数语法**

运行: `python -c "import ast; ast.parse(open('myUtils/login.py').read()); print('语法正确')"`
Expected: 输出 "语法正确"

**Step 4: 提交**

```bash
git add myUtils/login.py
git commit -m "refactor: rewrite baijiahao_cookie_gen with helper functions"
```

---

### Task 6: 统一 `auth.py` 中的验证逻辑

**Files:**
- Modify: `myUtils/auth.py:132-157`

**Step 1: 重写 `cookie_auth_baijiahao` 函数**

```python
async def cookie_auth_baijiahao(account_file):
    """验证百家号cookie是否有效"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS, channel="chrome")
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()

        await page.goto("https://baijiahao.baidu.com/builder/rc/home")
        await page.wait_for_timeout(5000)

        # 检查安全验证
        if await page.locator('div.passMod_dialog-container:visible').count():
            baijiahao_logger.error("Cookie失效: 出现安全验证")
            await page.close()
            await context.close()
            await browser.close()
            return False

        # 检查是否有登录按钮
        if await page.get_by_text("登录/注册百家号").count() > 0:
            baijiahao_logger.error("Cookie失效: 需要登录")
            await page.close()
            await context.close()
            await browser.close()
            return False

        # 检查URL是否在创作者中心
        if "builder/rc" not in page.url:
            baijiahao_logger.error(f"Cookie失效: 页面跳转到 {page.url}")
            await page.close()
            await context.close()
            await browser.close()
            return False

        baijiahao_logger.success("[+] cookie 有效")
        await page.close()
        await context.close()
        await browser.close()
        return True
```

**Step 2: 验证函数语法**

运行: `python -c "import ast; ast.parse(open('myUtils/auth.py').read()); print('语法正确')"`
Expected: 输出 "语法正确"

**Step 3: 提交**

```bash
git add myUtils/auth.py
git commit -m "refactor: unify baijiahao cookie auth logic"
```

---

### Task 7: 统一 `main.py` 中的验证逻辑（可选）

**Files:**
- Modify: `uploader/baijiahao_uploader/main.py:39-55`

**Step 1: 重写 `cookie_auth` 函数**

```python
async def cookie_auth(account_file):
    """验证百家号cookie是否有效"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS, channel="chrome")
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()

        await page.goto("https://baijiahao.baidu.com/builder/rc/home")
        await page.wait_for_timeout(5000)

        # 检查安全验证
        if await page.locator('div.passMod_dialog-container:visible').count():
            baijiahao_logger.error("Cookie失效: 出现安全验证")
            return False

        # 检查是否有登录按钮
        if await page.get_by_text("登录/注册百家号").count() > 0:
            baijiahao_logger.error("Cookie失效: 需要登录")
            return False

        # 检查URL是否在创作者中心
        if "builder/rc" not in page.url:
            baijiahao_logger.error(f"Cookie失效: 页面跳转到 {page.url}")
            return False

        baijiahao_logger.success("[+] cookie 有效")
        return True
```

**Step 2: 验证函数语法**

运行: `python -c "import ast; ast.parse(open('uploader/baijiahao_uploader/main.py').read()); print('语法正确')"`
Expected: 输出 "语法正确"

**Step 3: 提交**

```bash
git add uploader/baijiahao_uploader/main.py
git commit -m "refactor: unify baijiahao cookie auth in uploader"
```

---

### Task 8: 集成测试

**Files:**
- Test: 手动测试

**Step 1: 测试登录流程**

```bash
python cli_main.py baijiahao test_account login
```

Expected: 
1. 浏览器打开百家号登录页面
2. 自动点击登录按钮
3. 显示二维码
4. 用户扫码后自动检测登录成功
5. 保存cookie

**Step 2: 测试验证流程**

```bash
python -c "import asyncio; from myUtils.auth import check_cookie; print(asyncio.run(check_cookie(6, 'test_cookie.json')))"
```

Expected: 输出 cookie 有效性

**Step 3: 测试上传流程**

```bash
python examples/upload_video_to_baijiahao.py
```

Expected: 使用已保存的cookie进行视频上传

**Step 4: 最终提交**

```bash
git add .
git commit -m "feat: complete baijiahao login refactor"
git push
```

---

## 验证清单

- [ ] `get_baijiahao_options` 函数正常工作
- [ ] `click_baijiahao_login_button` 函数可以点击登录按钮
- [ ] `get_baijiahao_qrcode_src` 函数可以获取二维码
- [ ] `wait_baijiahao_login_success` 函数可以检测登录成功
- [ ] `baijiahao_cookie_gen` 函数完整流程正常
- [ ] `cookie_auth_baijiahao` 函数验证逻辑正确
- [ ] `cookie_auth` 函数验证逻辑正确
- [ ] 完整登录流程测试通过
- [ ] 完整上传流程测试通过
