# 百家号登录流程重构设计文档

## 1. 背景

### 问题描述
百家号登录流程存在以下问题：
1. 选择器文本顺序错误（代码使用"注册/登录百家号"，实际页面显示"登录/注册百家号"）
2. 登录状态判断逻辑错误（依赖URL判断，但页面会自动重定向）
3. 浏览器配置缺少防风控参数
4. 验证逻辑不一致（`auth.py` 和 `main.py` 使用不同判断方式）
5. 没有安全验证检测机制

### 错误日志分析
```
获取二维码失败: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for get_by_text("注册/登录百家号")
    - navigated to "https://baijiahao.baidu.com/builder/rc/home"
```
- 选择器找不到元素导致超时
- 页面自动重定向到创作者中心首页

## 2. 设计目标

1. 使用正确的选择器文本和实际页面元素
2. 基于页面内容判断登录状态，不依赖URL
3. 添加多选择器备选方案，提高鲁棒性
4. 统一 `auth.py` 和 `main.py` 的验证逻辑
5. 添加安全验证检测和处理

## 3. 详细设计

### 3.1 浏览器配置

**位置**：`myUtils/login.py`

**设计**：复用通用防风控配置

```python
def get_baijiahao_options():
    """百家号专用浏览器配置，基于通用配置"""
    options = get_browser_options()  # 复用通用防风控配置
    # options["args"].append("--lang=zh-CN")  # 可选：覆盖语言设置
    return options
```

**理由**：
- 复用 `--disable-blink-features=AutomationControlled` 等防风控参数
- 保持与其他平台配置的一致性
- 便于后续维护

### 3.2 登录状态检测

**位置**：`myUtils/login.py:489-528`

**设计**：基于页面内容判断，不依赖URL

```python
# 检查是否需要登录（基于页面内容）
login_button = page.get_by_text("登录/注册百家号")
if await login_button.count() == 0:
    # 没有登录按钮，检查是否在创作者中心
    if "builder/rc" in page.url:
        print("✅ 已登录，直接保存cookie")
        # 保存逻辑
        return
```

**理由**：
- URL判断不可靠（页面会自动重定向）
- 页面内容更稳定

### 3.3 登录按钮点击

**位置**：`myUtils/login.py:530-566`

**设计**：多选择器尝试

```python
async def click_login_button(page):
    """尝试多种方式点击登录按钮"""
    selectors = [
        ("text", "登录/注册百家号"),      # 主选择器
        ("role", {"name": "登录"}),       # 备选1: role选择器
        ("text", "登录", {"exact": True}), # 备选2: 精确文本匹配
    ]

    for selector_type, *args in selectors:
        try:
            if selector_type == "text":
                await page.get_by_text(*args).click(timeout=5000)
            elif selector_type == "role":
                await page.get_by_role(*args).click(timeout=5000)
            print(f"✅ 成功点击登录按钮 (选择器: {selector_type})")
            return True
        except Exception:
            continue

    return False
```

**理由**：
- 单一选择器容易因页面变化而失败
- 多选择器提高鲁棒性
- 缩短单次尝试的超时时间（5秒），加快失败反馈

### 3.4 二维码获取

**位置**：`myUtils/login.py:537-545`

**设计**：多选择器 + 合理超时

```python
async def get_qrcode_src(page):
    """获取二维码图片地址"""
    selectors = [
        ".tang-pass-qrcode-img",              # 主选择器 (用户确认)
        ".qrcode-img img",                    # 备选1
        "img[src*='qr']",                     # 备选2: src包含qr
    ]

    for selector in selectors:
        try:
            img = page.locator(selector)
            if await img.count() > 0:
                src = await img.get_attribute("src", timeout=5000)
                if src:
                    return src
        except Exception:
            continue

    return None
```

**理由**：
- 用户确认实际选择器是 `.tang-pass-qrcode-img`
- 添加备选选择器应对页面变化

### 3.5 登录成功检测

**位置**：`myUtils/login.py:568-582`

**设计**：多条件检测 + 安全验证检测

```python
async def wait_for_login_success(page, timeout=200):
    """等待登录成功，同时检测安全验证"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        # 检查安全验证弹窗
        if await page.locator('div.passMod_dialog-container:visible').count():
            raise Exception("出现百度安全验证，请手动处理")

        # 检查是否跳转到创作者中心
        if "builder/rc" in page.url:
            return True

        # 检查登录按钮是否消失
        if await page.get_by_text("登录/注册百家号").count() == 0:
            return True

        await asyncio.sleep(1)

    return False
```

**理由**：
- 单一条件（等待文本消失）容易卡住
- 多条件检测更可靠
- 安全验证检测避免无限等待

### 3.6 验证逻辑统一

**位置**：`myUtils/auth.py:132-157` 和 `uploader/baijiahao_uploader/main.py:39-55`

**设计**：统一使用页面内容判断

```python
async def cookie_auth_baijiahao(account_file):
    """统一的百家号cookie验证逻辑"""
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

**理由**：
- `auth.py` 和 `main.py` 使用不同判断方式可能导致不一致
- 统一逻辑便于维护和调试

## 4. 涉及文件

| 文件 | 修改内容 |
|------|---------|
| `myUtils/login.py` | 重构 `baijiahao_cookie_gen` 函数 |
| `myUtils/auth.py` | 更新 `cookie_auth_baijiahao` 函数 |
| `uploader/baijiahao_uploader/main.py` | 更新 `cookie_auth` 函数（可选） |

## 5. 测试计划

1. **单元测试**：验证各个辅助函数（`click_login_button`, `get_qrcode_src`）
2. **集成测试**：完整登录流程测试
   - 无cookie情况下扫码登录
   - 有有效cookie情况下自动跳转
   - 安全验证出现时的处理
3. **验证测试**：cookie验证逻辑测试

## 6. 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 页面结构变化 | 选择器失效 | 多选择器备选方案 |
| 安全验证频繁 | 登录失败 | 检测并提示用户手动处理 |
| Cookie过期 | 上传失败 | 统一验证逻辑，提前检测 |
