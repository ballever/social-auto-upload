# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import xiaohongshu_logger


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=LOCAL_CHROME_HEADLESS, channel="chrome"
        )
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        xiaohongshu_logger.info("[+] 正在验证小红书cookie...")
        await page.goto("https://creator.xiaohongshu.com/publish/publish?target=video")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.wait_for_url("**/publish/publish**", timeout=10000)
            xiaohongshu_logger.info("[+] 页面加载完成，正在检查登录状态...")
        except:
            xiaohongshu_logger.error(
                f"[+] 页面加载超时或URL不匹配，当前URL: {page.url}"
            )
            await context.close()
            await browser.close()
            return False
        if (
            await page.get_by_text("手机号登录").count()
            or await page.get_by_text("扫码登录").count()
        ):
            xiaohongshu_logger.error("[+] cookie 失效，需要重新登录")
            await context.close()
            await browser.close()
            return False
        else:
            xiaohongshu_logger.success("[+] cookie 有效")
            await context.close()
            await browser.close()
            return True


async def xiaohongshu_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        xiaohongshu_logger.info(
            "[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件"
        )
        await xiaohongshu_cookie_gen(account_file)
    return True


async def xiaohongshu_cookie_gen(account_file):
    async with async_playwright() as playwright:
        options = {
            "headless": LOCAL_CHROME_HEADLESS,
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
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class XiaoHongShuVideo(object):
    def __init__(
        self,
        title,
        file_path,
        tags,
        publish_date: datetime,
        account_file,
        thumbnail_path=None,
        description=None,
    ):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = "%Y年%m月%d日 %H:%M"
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.thumbnail_path = thumbnail_path
        self.description = description  # 作品简介（可选）

    async def set_schedule_time_xiaohongshu(self, page, publish_date):
        print("  [-] 正在设置定时发布时间...")
        print(f"publish_date: {publish_date}")

        # 使用文本内容定位元素
        # element = await page.wait_for_selector(
        #     'label:has-text("定时发布")',
        #     timeout=5000  # 5秒超时时间
        # )
        # await element.click()

        # # 选择包含特定文本内容的 label 元素
        label_element = page.locator("label:has-text('定时发布')")
        # # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
        print(f"publish_date_hour: {publish_date_hour}")

        await asyncio.sleep(1)
        await page.locator('.el-input__inner[placeholder="选择日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def handle_upload_error(self, page):
        xiaohongshu_logger.info("视频出错了，重新上传中")
        await page.locator(
            'div.progress-div [class^="upload-btn-input"]'
        ).set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            browser = await playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.local_executable_path,
                channel="chrome",
            )
        else:
            browser = await playwright.chromium.launch(
                headless=self.headless, channel="chrome"
            )
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=f"{self.account_file}",
        )
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/publish/publish?target=video")
        xiaohongshu_logger.info(f"[+]正在上传-------{self.title}.mp4")
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        xiaohongshu_logger.info(f"[-] 正在打开主页...")
        await page.wait_for_url(
            "https://creator.xiaohongshu.com/publish/publish?target=video"
        )
        # 点击 "上传视频" 按钮
        await page.locator(
            "div[class^='upload-content'] input[class='upload-input']"
        ).set_input_files(self.file_path)

        # 等待页面跳转到指定的 URL 2025.01.08修改在原有基础上兼容两种页面
        attempt_count = 0
        while True:
            attempt_count += 1
            print(f"  [=] 开始第 {attempt_count} 次检测上传状态...")
            try:
                # 等待upload-input元素出现
                print(f"  [=] 等待上传输入元素出现 (3秒超时)...")
                upload_input = await page.wait_for_selector(
                    "input.upload-input", timeout=3000
                )
                print(f"  [+] 找到上传输入元素!")

                # 获取下一个兄弟元素
                preview_new = await upload_input.query_selector(
                    'xpath=following-sibling::div[contains(@class, "preview-new")]'
                )

                if preview_new:
                    print(f"  [+] 找到预览元素 preview-new!")

                    # 在preview-new元素中查找包含"上传成功"的stage元素
                    stage_elements = await preview_new.query_selector_all("div.stage")
                    print(f"  [=] 找到 {len(stage_elements)} 个 stage 元素")

                    if len(stage_elements) > 0:
                        upload_success = False
                        for idx, stage in enumerate(stage_elements):
                            text_content = await page.evaluate(
                                "(element) => element.textContent", stage
                            )
                            print(
                                f"  [=] Stage {idx + 1} 文本内容: '{text_content.strip()}'"
                            )

                            # 检测上传成功标识（包括低分辨率但仍成功的情况）
                            low_resolution = "分辨率较低" in text_content
                            if (
                                "检测为高清视频" in text_content
                                or "上传成功" in text_content
                                or low_resolution
                            ):
                                upload_success = True
                                if low_resolution:
                                    print(
                                        f"  [✓] 在 Stage {idx + 1} 中检测到上传成功标识! (但分辨率低于1080P)"
                                    )
                                    xiaohongshu_logger.warning(
                                        "[+] 检测到上传成功，但视频分辨率较低，建议上传1080P及以上分辨率"
                                    )
                                else:
                                    print(
                                        f"  [✓] 在 Stage {idx + 1} 中检测到上传成功标识!"
                                    )
                                break
                            elif "上传中" in text_content:
                                print(f"  [=] Stage {idx + 1} 显示: 上传中")
                            elif "上传失败" in text_content:
                                print(f"  [✗] Stage {idx + 1} 显示: 上传失败")
                            else:
                                print(f"  [?] Stage {idx + 1} 状态未知")

                        if upload_success:
                            xiaohongshu_logger.info("[+] 检测到上传成功标识!")
                            break  # 成功检测到上传成功后跳出循环
                        else:
                            print("  [-] 未找到上传成功标识，继续等待...")
                    else:
                        print("  [-] 未找到任何 stage 元素，继续等待...")
                else:
                    print("  [-] 未找到预览元素 preview-new，继续等待...")

                # 等待一段时间后重新检测
                await asyncio.sleep(1)

            except Exception as e:
                print(f"  [-] 检测过程出错: {str(e)}，重新尝试...")
                print(
                    f"  [i] 注意: 这里的3秒超时是指等待 upload-input 元素出现的时间，不是整个上传过程的时间"
                )
                print(f"  [i] 如果超时，代码会继续循环重试，不会放弃上传")
                await asyncio.sleep(0.5)  # 等待0.5秒后重新尝试

        # 填充标题和话题
        # 检查是否存在包含输入框的元素
        # 这里为了避免页面变化，故使用相对位置定位：作品标题父级右侧第一个元素的input子元素
        await asyncio.sleep(1)
        xiaohongshu_logger.info(f"  [-] 正在填充标题和话题...")

        # 尝试新的DOM结构定位标题输入框
        print(f"  [=] 尝试新的DOM结构定位标题输入框")
        # 新的DOM路径: div.publish-page-content > div.publish-page-content-base > div > div.flex > div.input > div.d-input-wrapper.d-inline-block.c-input_inner > div > input
        title_container = page.locator(
            "div.publish-page-content div.publish-page-content-base div.flex div.input div.d-input-wrapper.d-inline-block.c-input_inner input"
        )
        title_count = await title_container.count()
        print(f"  [=] 找到 {title_count} 个标题输入框")

        if await title_container.count():
            print(f"  [+] 使用新DOM结构填充标题: {self.title[:30]}")
            await title_container.click()  # 先点击输入框
            await asyncio.sleep(0.5)  # 等待输入框激活
            await title_container.fill(self.title[:30])
            print(f"  [+] 标题填充完成")
        else:
            print(f"  [✗] 新DOM结构也无法找到标题输入框！")
            xiaohongshu_logger.error("  [✗] 无法找到标题输入框，发布失败！")
            print(f"  [i] 浏览器保持打开状态，方便观察问题")
            print(f"  [i] 请手动检查页面DOM结构后关闭浏览器")
            # 仅抛出异常，不关闭浏览器
            raise Exception("无法找到标题输入框，发布失败")

        # 填充简介和话题（共用同一个输入框）
        # 新的DOM路径: div.publish-page-content > div.publish-page-content-base > div > div.editor-container > div.editor-content > div > div
        css_selector = "div.publish-page-content div.publish-page-content-base div.editor-container div.editor-content div div"
        print(f"  [=] 尝试定位简介和话题输入框: {css_selector}")
        editor_count = await page.locator(css_selector).count()
        print(f"  [=] 找到 {editor_count} 个输入框")

        if editor_count > 0:
            print(f"  [+] 开始填充简介和话题...")
            # 先点击输入框确保激活
            await page.locator(css_selector).first.click()
            await asyncio.sleep(0.5)  # 等待输入框激活

            # 先输入简介（如果有）
            if self.description:
                print(f"  [=] 输入简介: {self.description[:50]}...")
                await page.type(css_selector, self.description)
                print(f"  [+] 简介输入完成")

            # 输入话题标签
            for index, tag in enumerate(self.tags, start=1):
                print(f"  [=] 添加话题 {index}/{len(self.tags)}: #{tag}")
                # 如果有简介，先换行
                if self.description or index > 1:
                    await page.press(css_selector, "Enter")
                await page.type(css_selector, "#" + tag)
                await page.press(css_selector, "Space")
            xiaohongshu_logger.info(f"总共添加{len(self.tags)}个话题")
        else:
            print(f"  [✗] 无法找到简介和话题输入框！")
            xiaohongshu_logger.error("  [✗] 无法找到简介和话题输入框，发布失败！")
            print(f"  [i] 浏览器保持打开状态，方便观察问题")
            print(f"  [i] 请手动检查页面DOM结构后关闭浏览器")
            # 仅抛出异常，不关闭浏览器
            raise Exception("无法找到简介和话题输入框，发布失败")

        # while True:
        #     # 判断重新上传按钮是否存在，如果不存在，代表视频正在上传，则等待
        #     try:
        #         #  新版：定位重新上传
        #         number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
        #         if number > 0:
        #             xiaohongshu_logger.success("  [-]视频上传完毕")
        #             break
        #         else:
        #             xiaohongshu_logger.info("  [-] 正在上传视频中...")
        #             await asyncio.sleep(2)

        #             if await page.locator('div.progress-div > div:has-text("上传失败")').count():
        #                 xiaohongshu_logger.error("  [-] 发现上传出错了... 准备重试")
        #                 await self.handle_upload_error(page)
        #     except:
        #         xiaohongshu_logger.info("  [-] 正在上传视频中...")
        #         await asyncio.sleep(2)

        # 上传视频封面
        # await self.set_thumbnail(page, self.thumbnail_path)

        # 更换可见元素
        # await self.set_location(page, "青岛市")

        # # 頭條/西瓜
        # third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
        # # 定位是否有第三方平台
        # if await page.locator(third_part_element).count():
        #     # 检测是否是已选中状态
        #     if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
        #         await page.locator(third_part_element).locator('input.semi-switch-native-control').click()

        if self.publish_date != 0:
            await self.set_schedule_time_xiaohongshu(page, self.publish_date)

        # 判断视频是否发布成功
        while True:
            try:
                # 等待包含"定时发布"文本的button元素出现并点击
                if self.publish_date != 0:
                    await page.locator('button:has-text("定时发布")').click()
                else:
                    await page.locator('button:has-text("发布")').click()
                await page.wait_for_url(
                    "https://creator.xiaohongshu.com/publish/success?**", timeout=3000
                )  # 如果自动跳转到作品页面，则代表发布成功
                xiaohongshu_logger.success("  [-]视频发布成功")
                break
            except:
                xiaohongshu_logger.info("  [-] 视频正在发布中...")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

        await context.storage_state(path=self.account_file)  # 保存cookie
        xiaohongshu_logger.success("  [-]cookie更新完毕！")
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()

    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.semi-modal-content:visible")
            await page.click('text="设置竖封面"')
            await page.wait_for_timeout(2000)  # 等待2秒
            # 定位到上传区域并点击
            await page.locator(
                "div[class^='semi-upload upload'] >> input.semi-upload-hidden-input"
            ).set_input_files(thumbnail_path)
            await page.wait_for_timeout(2000)  # 等待2秒
            await page.locator(
                "div[class^='extractFooter'] button:visible:has-text('完成')"
            ).click()
            # finish_confirm_element = page.locator("div[class^='confirmBtn'] >> div:has-text('完成')")
            # if await finish_confirm_element.count():
            #     await finish_confirm_element.click()
            # await page.locator("div[class^='footer'] button:has-text('完成')").click()

    async def set_location(self, page: Page, location: str = "青岛市"):
        print(f"开始设置位置: {location}")

        # 点击地点输入框
        print("等待地点输入框加载...")
        loc_ele = await page.wait_for_selector(
            "div.d-text.d-select-placeholder.d-text-ellipsis.d-text-nowrap"
        )
        print(f"已定位到地点输入框: {loc_ele}")
        await loc_ele.click()
        print("点击地点输入框完成")

        # 输入位置名称
        print(f"等待1秒后输入位置名称: {location}")
        await page.wait_for_timeout(1000)
        await page.keyboard.type(location)
        print(f"位置名称输入完成: {location}")

        # 等待下拉列表加载
        print("等待下拉列表加载...")
        dropdown_selector = (
            "div.d-popover.d-popover-default.d-dropdown.--size-min-width-large"
        )
        await page.wait_for_timeout(3000)
        try:
            await page.wait_for_selector(dropdown_selector, timeout=3000)
            print("下拉列表已加载")
        except:
            print("下拉列表未按预期显示，可能结构已变化")

        # 增加等待时间以确保内容加载完成
        print("额外等待1秒确保内容渲染完成...")
        await page.wait_for_timeout(1000)

        # 尝试更灵活的XPath选择器
        print("尝试使用更灵活的XPath选择器...")
        flexible_xpath = (
            f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
            f'//div[contains(@class, "d-options-wrapper")]'
            f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
            f'//div[contains(@class, "name") and text()="{location}"]'
        )
        await page.wait_for_timeout(3000)

        # 尝试定位元素
        print(f"尝试定位包含'{location}'的选项...")
        try:
            # 先尝试使用更灵活的选择器
            location_option = await page.wait_for_selector(flexible_xpath, timeout=3000)

            if location_option:
                print(f"使用灵活选择器定位成功: {location_option}")
            else:
                # 如果灵活选择器失败，再尝试原选择器
                print("灵活选择器未找到元素，尝试原始选择器...")
                location_option = await page.wait_for_selector(
                    f'//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    f'//div[contains(@class, "d-options-wrapper")]'
                    f'//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    f'/div[1]//div[contains(@class, "name") and text()="{location}"]',
                    timeout=2000,
                )

            # 滚动到元素并点击
            print("滚动到目标选项...")
            await location_option.scroll_into_view_if_needed()
            print("元素已滚动到视图内")

            # 增加元素可见性检查
            is_visible = await location_option.is_visible()
            print(f"目标选项是否可见: {is_visible}")

            # 点击元素
            print("准备点击目标选项...")
            await location_option.click()
            print(f"成功选择位置: {location}")
            return True

        except Exception as e:
            print(f"定位位置失败: {e}")

            # 打印更多调试信息
            print("尝试获取下拉列表中的所有选项...")
            try:
                all_options = await page.query_selector_all(
                    '//div[contains(@class, "d-popover") and contains(@class, "d-dropdown")]'
                    '//div[contains(@class, "d-options-wrapper")]'
                    '//div[contains(@class, "d-grid") and contains(@class, "d-options")]'
                    "/div"
                )
                print(f"找到 {len(all_options)} 个选项")

                # 打印前3个选项的文本内容
                for i, option in enumerate(all_options[:3]):
                    option_text = await option.inner_text()
                    print(f"选项 {i + 1}: {option_text.strip()[:50]}...")

            except Exception as e:
                print(f"获取选项列表失败: {e}")

            # 截图保存（取消注释使用）
            # await page.screenshot(path=f"location_error_{location}.png")
            return False

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
