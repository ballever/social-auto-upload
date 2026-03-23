import asyncio
import sqlite3

from playwright.async_api import async_playwright

from myUtils.auth import check_cookie
from utils.base_social_media import set_init_script
import uuid
from pathlib import Path
from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH


# 检查并插入用户信息（避免重复创建）
def insert_user_info_if_not_exists(type_val, file_path, user_name, status_val):
    """检查是否已存在相同用户名和平台的记录，如果不存在则插入"""
    with sqlite3.connect(Path(BASE_DIR / "db" / "database.db")) as conn:
        cursor = conn.cursor()
        # 检查是否已存在相同用户名和平台的记录
        cursor.execute(
            "SELECT id FROM user_info WHERE type = ? AND userName = ?",
            (type_val, user_name),
        )
        existing_record = cursor.fetchone()

        if existing_record:
            print(
                f"⚠️  用户 '{user_name}' (平台类型: {type_val}) 已存在，更新cookie和状态"
            )
            cursor.execute(
                "UPDATE user_info SET filePath = ?, status = ? WHERE type = ? AND userName = ?",
                (file_path, status_val, type_val, user_name),
            )
            conn.commit()
            return existing_record[0]  # 返回已存在记录的ID

        # 不存在则插入新记录
        cursor.execute(
            "INSERT INTO user_info (type, filePath, userName, status) VALUES (?, ?, ?, ?)",
            (type_val, file_path, user_name, status_val),
        )
        conn.commit()
        print(f"✅ 用户 '{user_name}' (平台类型: {type_val}) 创建成功")
        return cursor.lastrowid  # 返回新插入记录的ID


# 统一获取浏览器启动配置（防风控+引入本地浏览器）
def get_browser_options():
    options = {
        "headless": LOCAL_CHROME_HEADLESS,
        "args": [
            "--disable-blink-features=AutomationControlled",  # 核心防爬屏蔽：去掉 window.navigator.webdriver 标签
            "--lang=zh-CN",
            "--disable-infobars",
            "--start-maximized",
        ],
    }
    # 如果用户在 conf.py 里配置了本地 Chrome，就用本地的，这样成功率极高
    if LOCAL_CHROME_PATH:
        options["executable_path"] = LOCAL_CHROME_PATH

    # 使用 Chrome 而不是 Chromium
    options["channel"] = "chrome"

    return options


# 百家号专用浏览器配置
def get_baijiahao_options():
    """百家号专用浏览器配置，基于通用配置"""
    return get_browser_options()


async def click_baijiahao_login_button(page):
    """尝试多种方式点击百家号登录按钮，带详细调试信息"""
    selectors = [
        ("text", "登录/注册百家号"),
        ("text", "登录", {"exact": True}),
        ("role", "link", {"name": "登录"}),
    ]

    for selector_type, *args in selectors:
        try:
            print(f"🔍 尝试选择器: {selector_type}, 参数: {args}")

            if selector_type == "text":
                element = page.get_by_text(*args)
                count = await element.count()
                print(f"   找到 {count} 个匹配元素")

                if count > 0:
                    # 打印第一个元素的文本内容
                    first_text = await element.first.text_content()
                    print(f"   第一个元素文本: '{first_text}'")

                    # 打印元素位置
                    bbox = await element.first.bounding_box()
                    print(f"   元素位置: {bbox}")

                await element.first.click(timeout=5000)

            elif selector_type == "role":
                element = page.get_by_role(*args)
                count = await element.count()
                print(f"   找到 {count} 个匹配元素")
                await element.first.click(timeout=5000)

            print(f"✅ 成功点击登录按钮 (选择器: {selector_type})")

            # 等待模态窗口出现
            print("⏳ 等待模态窗口出现...")
            await page.wait_for_timeout(3000)

            # 检查当前页面状态
            current_url = page.url
            print(f"   当前URL: {current_url}")

            # 检查是否有模态窗口
            modal_selectors = [
                "div[class*='modal']:visible",
                "div[class*='dialog']:visible",
                "div[class*='popup']:visible",
                "div[class*='qrcode']:visible",
                ".tang-pass-qrcode:visible",
            ]

            print("🔍 检查模态窗口...")
            for modal_sel in modal_selectors:
                modal_count = await page.locator(modal_sel).count()
                print(f"   {modal_sel}: {modal_count} 个")
                if modal_count > 0:
                    print(f"✅ 检测到模态窗口 (选择器: {modal_sel})")
                    return True

            print("⚠️ 未检测到模态窗口，但点击成功")
            return True

        except Exception as e:
            print(f"⚠️ 选择器 {selector_type} 失败: {e}")
            continue

    return False


async def get_baijiahao_qrcode_src(page):
    """获取百家号二维码图片地址，带详细调试信息"""
    selectors = [
        "div[class*='modal'] img[src*='qr']",
        "div[class*='dialog'] img[src*='qr']",
        "div[class*='popup'] img[src*='qr']",
        "div[class*='qrcode'] img",
        ".tang-pass-qrcode img",
        ".qrcode-img img",
        "img[src*='qr']",
        "img[src*='qrcode']",
    ]

    print("🔍 开始查找二维码图片...")
    for selector in selectors:
        try:
            img = page.locator(selector)
            count = await img.count()
            print(f"   选择器 '{selector}': 找到 {count} 个元素")

            if count > 0:
                src = await img.first.get_attribute("src", timeout=5000)
                print(f"   第一个元素src: {src}")

                if src:
                    print(f"✅ 获取二维码成功 (选择器: {selector})")
                    return src
        except Exception as e:
            print(f"   选择器 '{selector}' 失败: {e}")
            continue

    print("❌ 所有选择器都失败")
    return None


async def wait_baijiahao_login_success(page, timeout=200):
    """等待百家号登录成功，同时检测安全验证"""
    import time

    start_time = time.time()

    while time.time() - start_time < timeout:
        # 检查安全验证弹窗
        if await page.locator("div.passMod_dialog-container:visible").count():
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
                user_id = insert_user_info_if_not_exists(6, f"{uuid_v1}.json", id, 1)
                print(f"✅ 用户ID: {user_id}")
                status_queue.put(f"200:{user_id}")
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
        user_id = insert_user_info_if_not_exists(6, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")


# 抖音登录
async def douyin_cookie_gen(id, status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/")
        original_url = page.url
        img_locator = page.get_by_role("img", name="二维码")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on(
            "framenavigated",
            lambda frame: (
                asyncio.create_task(on_url_change())
                if frame == page.main_frame
                else None
            ),
        )
        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(
                url_changed_event.wait(), timeout=200
            )  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(3, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()
        # 使用辅助函数插入用户信息（避免重复创建）
        user_id = insert_user_info_if_not_exists(3, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")


# 视频号登录
async def get_tencent_cookie(id, status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        original_url = page.url

        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on(
            "framenavigated",
            lambda frame: (
                asyncio.create_task(on_url_change())
                if frame == page.main_frame
                else None
            ),
        )

        # 等待 iframe 出现（最多等 60 秒）
        iframe_locator = page.frame_locator("iframe").first

        # 获取 iframe 中的第一个 img 元素
        img_locator = iframe_locator.get_by_role("img").first

        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        print("✅ 图片地址:", src)
        status_queue.put(src)

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(
                url_changed_event.wait(), timeout=200
            )  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(2, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        # 使用辅助函数插入用户信息（避免重复创建）
        user_id = insert_user_info_if_not_exists(2, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")


# 快手登录
async def get_ks_cookie(id, status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            "args": ["--lang en-GB"],
            "headless": LOCAL_CHROME_HEADLESS,  # Set headless option here
            "channel": "chrome",
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")

        # 定位并点击“立即登录”按钮（类型为 link）
        await page.get_by_role("link", name="立即登录").click()
        await page.get_by_text("扫码登录").click()
        img_locator = page.get_by_role("img", name="qrcode")
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on(
            "framenavigated",
            lambda frame: (
                asyncio.create_task(on_url_change())
                if frame == page.main_frame
                else None
            ),
        )

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(
                url_changed_event.wait(), timeout=200
            )  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(4, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        # 使用辅助函数插入用户信息（避免重复创建）
        user_id = insert_user_info_if_not_exists(4, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")


# 小红书登录
async def xiaohongshu_cookie_gen(id, status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = {
            "args": ["--lang en-GB"],
            "headless": LOCAL_CHROME_HEADLESS,  # Set headless option here
            "channel": "chrome",
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://creator.xiaohongshu.com/")
        await page.locator("img.css-wemwzq").click()

        img_locator = page.get_by_role("img").nth(2)
        # 获取 src 属性值
        src = await img_locator.get_attribute("src")
        original_url = page.url
        print("✅ 图片地址:", src)
        status_queue.put(src)
        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on(
            "framenavigated",
            lambda frame: (
                asyncio.create_task(on_url_change())
                if frame == page.main_frame
                else None
            ),
        )

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(
                url_changed_event.wait(), timeout=200
            )  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            status_queue.put("500")
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            return None
        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(1, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        # 使用辅助函数插入用户信息（避免重复创建）
        user_id = insert_user_info_if_not_exists(1, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")


# Bilibili登录
async def bilibili_cookie_gen(id, status_queue):
    url_changed_event = asyncio.Event()

    async def on_url_change():
        # 检查是否是主框架的变化
        if page.url != original_url:
            url_changed_event.set()

    async with async_playwright() as playwright:
        options = get_browser_options()
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://member.bilibili.com/platform/home")
        original_url = page.url

        # 等待页面加载完成
        await page.wait_for_load_state("networkidle")

        # 检查是否已经登录
        current_url = page.url
        if "passport.bilibili.com" not in current_url:
            # 已经登录，直接保存cookie
            uuid_v1 = uuid.uuid1()
            print(f"UUID v1: {uuid_v1}")
            cookies_dir = Path(BASE_DIR / "cookiesFile")
            cookies_dir.mkdir(exist_ok=True)
            await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
            result = await check_cookie(5, f"{uuid_v1}.json")
            if not result:
                status_queue.put("500")
                await page.close()
                await context.close()
                await browser.close()
                return None
            await page.close()
            await context.close()
            await browser.close()
            # 使用辅助函数插入用户信息（避免重复创建）
            user_id = insert_user_info_if_not_exists(5, f"{uuid_v1}.json", id, 1)
            status_queue.put(f"200:{user_id}")
            return

        # 需要登录，获取二维码
        try:
            # 等待二维码出现
            await page.wait_for_selector(".qrcode-img", timeout=10000)
            img_locator = page.locator(".qrcode-img img")
            src = await img_locator.get_attribute("src")
            print("✅ 图片地址:", src)
            status_queue.put(src)
        except Exception as e:
            print(f"获取二维码失败: {e}")
            # 尝试其他选择器
            try:
                img_locator = page.get_by_role("img").first
                src = await img_locator.get_attribute("src")
                if src and "qr" in src.lower():
                    print("✅ 图片地址(备用):", src)
                    status_queue.put(src)
                else:
                    status_queue.put("500")
                    await page.close()
                    await context.close()
                    await browser.close()
                    return None
            except:
                status_queue.put("500")
                await page.close()
                await context.close()
                await browser.close()
                return None

        # 监听页面的 'framenavigated' 事件，只关注主框架的变化
        page.on(
            "framenavigated",
            lambda frame: (
                asyncio.create_task(on_url_change())
                if frame == page.main_frame
                else None
            ),
        )

        try:
            # 等待 URL 变化或超时
            await asyncio.wait_for(
                url_changed_event.wait(), timeout=200
            )  # 最多等待 200 秒
            print("监听页面跳转成功")
        except asyncio.TimeoutError:
            print("监听页面跳转超时")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None

        uuid_v1 = uuid.uuid1()
        print(f"UUID v1: {uuid_v1}")
        # 确保cookiesFile目录存在
        cookies_dir = Path(BASE_DIR / "cookiesFile")
        cookies_dir.mkdir(exist_ok=True)
        await context.storage_state(path=cookies_dir / f"{uuid_v1}.json")
        result = await check_cookie(5, f"{uuid_v1}.json")
        if not result:
            status_queue.put("500")
            await page.close()
            await context.close()
            await browser.close()
            return None
        await page.close()
        await context.close()
        await browser.close()

        # 使用辅助函数插入用户信息（避免重复创建）
        user_id = insert_user_info_if_not_exists(5, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")


# 百家号登录（旧版，保留备用）
async def _baijiahao_cookie_gen_legacy(id, status_queue):
    async with async_playwright() as playwright:
        options = {
            "args": ["--lang en-GB"],
            "headless": LOCAL_CHROME_HEADLESS,
            "channel": "chrome",
        }
        browser = await playwright.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://baijiahao.baidu.com/builder/theme/bjh/login")

        # 等待页面DOM加载完成
        await page.wait_for_load_state("domcontentloaded")

        # 检查当前URL,如果被重定向说明cookie有效
        current_url = page.url
        if "login" not in current_url:
            # URL不包含login,说明已被重定向到创作者中心,cookie有效
            print("✅ 检测到cookie有效,页面已自动跳转到创作者中心")
            uuid_v1 = uuid.uuid1()
            print(f"UUID v11: {uuid_v1}")
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
            # await page.close()
            # await context.close()
            # await browser.close()
            # 使用辅助函数插入用户信息（避免重复创建）
            user_id = insert_user_info_if_not_exists(6, f"{uuid_v1}.json", id, 1)
            status_queue.put(f"200:{user_id}")
            return

        # 需要登录，先点击登录按钮
        print("✅ 百家号需要登录，点击登录按钮")
        try:
            # 点击"注册/登录百家号"按钮
            await page.get_by_text("注册/登录百家号").click()
            print("✅ 已点击登录按钮")

            # 等待二维码出现
            await page.wait_for_selector(".qrcode-img", timeout=10000)
            print("✅ 二维码已出现")

            # 获取二维码图片
            img_locator = page.locator(".qrcode-img img")
            src = await img_locator.get_attribute("src")
            print("✅ 图片地址:", src)
            status_queue.put(src)
        except Exception as e:
            print(f"获取二维码失败: {e}")
            # 尝试其他选择器
            try:
                img_locator = page.get_by_role("img").first
                src = await img_locator.get_attribute("src")
                if src and "qr" in src.lower():
                    print("✅ 图片地址(备用):", src)
                    status_queue.put(src)
                else:
                    status_queue.put("500")
                    await page.close()
                    await context.close()
                    await browser.close()
                    return None
            except:
                status_queue.put("500")
                await page.close()
                await context.close()
                await browser.close()
                return None

        # 等待登录成功：等待"注册/登录百家号"文本消失（表示已登录）
        try:
            print("等待用户扫码登录...")
            await page.wait_for_function(
                "document.body.innerText.indexOf('注册/登录百家号') === -1",
                timeout=200000,
            )
            print("检测到登录成功")
        except Exception as e:
            print(f"监听登录状态失败: {e}")
            await page.close()
            await context.close()
            await browser.close()
            status_queue.put("500")
            return None

        uuid_v1 = uuid.uuid1()
        print(f"UUID v12: {uuid_v1}")
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
        await page.close()
        await context.close()
        await browser.close()

        # 使用辅助函数插入用户信息（避免重复创建）
        user_id = insert_user_info_if_not_exists(6, f"{uuid_v1}.json", id, 1)
        status_queue.put(f"200:{user_id}")
