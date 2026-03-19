# -*- coding: utf-8 -*-
import json
import pathlib
import random
import asyncio
from datetime import datetime
from pathlib import Path

from playwright.async_api import Playwright, async_playwright, Page

from conf import BASE_DIR, LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger


def extract_keys_from_json(data):
    """Extract specified keys from the provided JSON data."""
    keys_to_extract = ["SESSDATA", "bili_jct", "DedeUserID__ckMd5", "DedeUserID", "access_token"]
    extracted_data = {}

    if 'cookies' in data and 'cookie_info' not in data:
        for cookie in data['cookies']:
            if cookie['name'] in keys_to_extract:
                extracted_data[cookie['name']] = cookie['value']
    elif 'cookie_info' in data:
        for cookie in data['cookie_info']['cookies']:
            if cookie['name'] in keys_to_extract:
                extracted_data[cookie['name']] = cookie['value']
        if "token_info" in data and "access_token" in data['token_info']:
            extracted_data['access_token'] = data['token_info']['access_token']

    return extracted_data


def read_cookie_json_file(filepath: pathlib.Path):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = json.load(file)
        return content


def random_emoji():
    emoji_list = ["🍏", "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🥥", "🥝",
                  "🍅", "🍆", "🥑", "🥦", "🥒", "🥬", "🌶", "🌽", "🥕", "🥔", "🍠", "🥐", "🍞", "🥖", "🥨", "🥯", "🧀", "🥚", "🍳", "🥞",
                  "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🥙", "🌮", "🌯", "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣",
                  "🍱", "🥟", "🍤", "🍙", "🍚", "🍘", "🍥", "🥮", "🥠", "🍢", "🍡", "🍧", "🍨", "🍦", "🥧", "🍰", "🎂", "🍮", "🍭", "🍬",
                  "🍫", "🍿", "🧂", "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕️", "🍵", "🥤", "🍶", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
                  "🍾", "🥄", "🍴", "🍽", "🥣", "🥡", "🥢"]
    return random.choice(emoji_list)


class BilibiliUploader(object):
    """
    Bilibili视频上传器 - 使用Playwright模拟浏览器操作
    
    Bilibili创作者中心上传页面: https://member.bilibili.com/platform/material/upload
    """
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, tid=160, description=None, thumbnail_path=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.tid = tid  # 视频分区ID
        self.description = description
        self.thumbnail_path = thumbnail_path  # 封面图片路径（可选）
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        # 保存浏览器实例,失败时不关闭
        self.browser = None
        self.context = None
        self.page = None

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def upload(self, playwright: Playwright) -> None:
        """使用Playwright上传视频到Bilibili"""
        # 启动浏览器
        if self.local_executable_path:
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.local_executable_path,
            )
        else:
            self.browser = await playwright.chromium.launch(headless=self.headless)
        
        # 创建浏览器上下文
        self.context = await self.browser.new_context(storage_state=f"{self.account_file}")
        self.context = await set_init_script(self.context)
        self.page = await self.context.new_page()
        
        try:
            bilibili_logger.info(f'[+]正在上传-------{self.title}')
            bilibili_logger.info(f'[-] 正在打开Bilibili创作者中心...')
            
            # 访问Bilibili创作者中心首页
            await self.page.goto("https://member.bilibili.com/platform/home")
            await asyncio.sleep(2)
            
            # 检查是否需要登录
            current_url = self.page.url
            if 'passport.bilibili.com' in current_url:
                bilibili_logger.error('[-] Cookie已失效,需要重新登录')
                print("\n" + "="*50)
                print("Cookie已失效,请查看浏览器页面")
                print("按Enter键继续...")
                input()
                return False
            
            # 等待页面加载完成
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(1)
            
            bilibili_logger.info(f'[-] 页面加载完成,当前URL: {self.page.url}')
            
            # 点击"投稿"按钮进入投稿页面
            contribute_btn = self.page.locator('#nav_upload_btn')
            if await contribute_btn.count():
                bilibili_logger.info(f'[-] 找到"投稿"按钮,点击进入...')
                await contribute_btn.click()
                await asyncio.sleep(2)
                
                # 找到上传区域的input元素
                file_input = self.page.locator('.bcc-upload-wrapper input[type="file"]').first
                if await file_input.count():
                    bilibili_logger.info(f'[-] 找到上传input,点击并上传文件...')
                    # await file_input.click()
                    await file_input.set_input_files(str(self.file_path))
                    await asyncio.sleep(2)
                else:
                    bilibili_logger.warning(f'[-] 未找到上传input')
            # 上传视频文件
            bilibili_logger.info(f'[-] 正在上传视频文件...')
            await asyncio.sleep(3)
            
            # 等待视频上传
            bilibili_logger.info(f'[-] 等待视频上传...')
            
            # 等待上传完成
            max_wait = 300  # 最大等待5分钟
            waited = 0
            while waited < max_wait:
                # 检查上传进度或成功标志
                upload_progress = await self.page.locator('.upload-progress, [class*="progress"]').count()
                upload_success = await self.page.locator('.upload-success, [class*="success"]').count()
                
                if upload_success > 0:
                    bilibili_logger.success('[-] 视频上传完成')
                    break
                
                if upload_progress == 0 and waited > 10:
                    # 没有进度条且已等待一段时间,可能已完成
                    break
                
                await asyncio.sleep(2)
                waited += 2
                if waited % 10 == 0:
                    bilibili_logger.info(f'[-] 上传中... ({waited}s)')
            
            # 等待页面跳转到编辑页面
            await asyncio.sleep(3)
            
            # 选择"自制"类型
            bilibili_logger.info(f'[-] 正在选择视频类型...')
            type_check = self.page.locator('.form-item .type-check .check-radio-v2-container').first
            if await type_check.count():
                bilibili_logger.info(f'[-] 找到"自制"选项,点击选择...')
                await type_check.click()
                await asyncio.sleep(1)
            
            bilibili_logger.info(f'[-] 当前URL: {self.page.url}')
            
            
            
            await asyncio.sleep(2)
            
            # 填写标题
            bilibili_logger.info(f'[-] 正在填写标题...')
            try:
                # 找到标题容器
                title_item = self.page.locator('.form-item').filter(has=self.page.locator('.section-title-container:has-text("标题")'))
                title_input = title_item.locator('input').first
                if await title_input.count():
                    await title_input.click()
                    await self.page.keyboard.press("Control+KeyA")
                    await self.page.keyboard.press("Delete")
                    await title_input.fill(self.title[:80])
                    bilibili_logger.info(f'[-] 已填写标题: {self.title[:80]}')
            except Exception as e:
                bilibili_logger.warning(f'[-] 填写标题失败: {e}')
            
            # 选择分区
            bilibili_logger.info(f'[-] 正在选择分区...')
            try:
                # 找到分区选择器
                partition_item = self.page.locator('.form-item').filter(has=self.page.locator('.section-title-container:has-text("分区")'))
                selector = partition_item.locator('.selector-container')
                if await selector.count():
                    await selector.click()
                    await asyncio.sleep(0.5)
                    # 在下拉列表中选择"三农"
                    drop_list = self.page.locator('.drop-list-v2-content-wrp')
                    if await drop_list.count():
                        sannong_option = drop_list.locator('text=三农').first
                        if await sannong_option.count():
                            await sannong_option.click()
                            bilibili_logger.info(f'[-] 已选择"三农"分区')
                            await asyncio.sleep(0.5)
            except Exception as e:
                bilibili_logger.warning(f'[-] 选择分区失败: {e}')
            
            # 填写标签
            if self.tags:
                bilibili_logger.info(f'[-] 正在填写标签...')
                try:
                    # 找到标签容器
                    tag_item = self.page.locator('.form-item').filter(has=self.page.locator('.section-title-container:has-text("标签")'))
                    tag_container = tag_item.locator('.tag-container')
                    tag_pre_wrp = tag_container.locator('.tag-pre-wrp')
                    
                    # 打印并清空现有标签
                    if await tag_pre_wrp.count():
                        existing_tags = tag_pre_wrp.locator('[class*="label"]')
                        count = await existing_tags.count()
                        bilibili_logger.info(f'[-] 当前有 {count} 个标签')
                        
                        # 打印现有标签内容
                        for i in range(count):
                            try:
                                tag_text = await existing_tags.nth(i).text_content()
                                bilibili_logger.info(f'[-] 现有标签[{i}]: {tag_text}')
                            except:
                                pass
                        
                        # 清空现有标签
                        bilibili_logger.info(f'[-] 开始清空标签...')
                        while True:
                            # 每次重新获取标签列表
                            existing_tags = tag_pre_wrp.locator('[class*="label"]')
                            current_count = await existing_tags.count()
                            if current_count == 0:
                                bilibili_logger.info(f'[-] 标签已全部清空')
                                break
                            
                            try:
                                # 删除第一个标签
                                tag_element = existing_tags.nth(0)
                                # 方式1: 找关闭按钮
                                close_btn = tag_element.locator('[class*="close"], [class*="delete"], .icon-close, .close-icon').first
                                if await close_btn.count():
                                    await close_btn.click()
                                    bilibili_logger.info(f'[-] 通过关闭按钮删除标签')
                                else:
                                    # 方式2: 直接点击标签元素上的x
                                    await tag_element.click()
                                    await self.page.keyboard.press('Delete')
                                    bilibili_logger.info(f'[-] 通过Delete键删除标签')
                                await asyncio.sleep(0.3)
                            except Exception as ex:
                                bilibili_logger.warning(f'[-] 删除标签失败: {ex}')
                                break
                    
                    # 填入新标签
                    tag_input = tag_container.locator('input').first
                    if await tag_input.count():
                        for tag in self.tags[:12]:  # B站最多12个标签
                            await tag_input.fill(tag)
                            await self.page.keyboard.press('Enter')
                            await asyncio.sleep(0.3)
                            bilibili_logger.info(f'[-] 已添加标签: {tag}')
                except Exception as e:
                    bilibili_logger.warning(f'[-] 填写标签失败: {e}')
            
            # 填写简介
            if self.description:
                bilibili_logger.info(f'[-] 正在填写简介...')
                try:
                    # 找到简介容器
                    desc_item = self.page.locator('.form-item').filter(has=self.page.locator('.section-title-container:has-text("简介")'))
                    desc_container = desc_item.locator('.desc-container')
                    desc_text_wrp = desc_container.locator('.desc-text-wrp p').first
                    
                    if await desc_text_wrp.count():
                        await desc_text_wrp.click()
                        await self.page.keyboard.press("Control+KeyA")
                        await self.page.keyboard.type(self.description[:2000])
                        bilibili_logger.info(f'[-] 已填写简介')
                except Exception as e:
                    bilibili_logger.warning(f'[-] 填写简介失败: {e}')
            
            # 上传封面图片（如果提供了）
            # if self.thumbnail_path:
            #     await self.set_thumbnail(self.page, self.thumbnail_path)
            
            # 设置定时发布
            if self.publish_date != 0:
                bilibili_logger.info(f'[-] 正在设置定时发布...')
                await self.set_schedule_time(self.page, self.publish_date)
            
            # 点击发布按钮
            bilibili_logger.info(f'[-] 正在发布视频...')
            await asyncio.sleep(10)
            
            # 方案1: 精确查找"立即投稿"按钮
            bilibili_logger.info(f'[-] 方案1: 精确查找"立即投稿"按钮...')
            try:
                # 尝试多种选择器来定位"立即投稿"按钮
                submit_selectors = [
                    'span.submit-add:has-text("立即投稿")',  # 包含"立即投稿"文本的span
                    'button:has-text("立即投稿")',           # 包含"立即投稿"文本的button
                    '[class*="submit"]:has-text("立即投稿")', # 包含submit和"立即投稿"文本的元素
                    'text="立即投稿"',                       # 精确文本匹配
                ]
                
                submit_btn = None
                for selector in submit_selectors:
                    btn = self.page.locator(selector).first
                    count = await btn.count()
                    bilibili_logger.info(f'[-] 尝试选择器 "{selector}": 找到 {count} 个元素')
                    if count > 0:
                        submit_btn = btn
                        bilibili_logger.info(f'[-] 使用选择器: {selector}')
                        break
                
                if submit_btn:
                    # 检查按钮文本确认是"立即投稿"
                    try:
                        btn_text = await submit_btn.text_content()
                        bilibili_logger.info(f'[-] 按钮文本: {btn_text}')
                        if '立即投稿' not in btn_text:
                            bilibili_logger.warning(f'[-] 按钮文本不包含"立即投稿": {btn_text}')
                            # 继续查找正确的按钮
                            submit_btn = None
                    except Exception as e:
                        bilibili_logger.warning(f'[-] 无法获取按钮文本: {e}')
                
                # 如果没找到,尝试查找所有包含"投稿"的按钮
                if not submit_btn:
                    bilibili_logger.info(f'[-] 尝试查找所有包含"投稿"的按钮...')
                    all_buttons = self.page.locator('button, span, div, a')
                    btn_count = await all_buttons.count()
                    bilibili_logger.info(f'[-] 找到 {btn_count} 个按钮/元素')
                    
                    for i in range(min(btn_count, 20)):  # 只检查前20个
                        try:
                            btn = all_buttons.nth(i)
                            text = await btn.text_content()
                            if text and '投稿' in text:
                                bilibili_logger.info(f'[-] 找到包含"投稿"的元素[{i}]: {text}')
                                if '立即投稿' in text:
                                    submit_btn = btn
                                    bilibili_logger.info(f'[-] 找到"立即投稿"按钮: {text}')
                                    break
                        except:
                            continue
                
                if submit_btn:
                    bilibili_logger.info(f'[-] 找到"立即投稿"按钮,准备点击...')
                    
                    # 检查按钮状态
                    is_visible = await submit_btn.is_visible()
                    is_enabled = await submit_btn.is_enabled()
                    bilibili_logger.info(f'[-] 按钮状态 - visible: {is_visible}, enabled: {is_enabled}')
                    
                    # 获取按钮的完整HTML
                    try:
                        outer_html = await submit_btn.evaluate('el => el.outerHTML')
                        bilibili_logger.info(f'[-] 按钮outerHTML: {outer_html[:200]}...')
                    except Exception as e:
                        bilibili_logger.warning(f'[-] 无法获取outerHTML: {e}')
                    
                    # 检查是否有popover提示
                    try:
                        has_popover = await submit_btn.evaluate('el => el.hasAttribute("data-tooltip") || el.hasAttribute("title") || el.getAttribute("aria-label")')
                        bilibili_logger.info(f'[-] 是否有popover提示: {has_popover}')
                    except Exception as e:
                        bilibili_logger.warning(f'[-] 检查popover失败: {e}')
                    
                    # 尝试点击按钮
                    bilibili_logger.info(f'[-] 尝试点击"立即投稿"按钮...')
                    
                    # 方法1: 直接点击
                    try:
                        await submit_btn.click(timeout=3000)
                        bilibili_logger.info(f'[-] ✓ 直接点击完成')
                    except Exception as e:
                        bilibili_logger.warning(f'[-] 直接点击失败: {e}')
                    
                    await asyncio.sleep(1)
                    
                    # 方法2: 强制点击
                    try:
                        await submit_btn.click(force=True, timeout=3000)
                        bilibili_logger.info(f'[-] ✓ 强制点击完成')
                    except Exception as e:
                        bilibili_logger.warning(f'[-] 强制点击失败: {e}')
                    
                    bilibili_logger.info(f'[-] 方案1执行完毕')
                else:
                    bilibili_logger.warning(f'[-] 未找到"立即投稿"按钮')
            except Exception as e:
                bilibili_logger.warning(f'[-] ✗ 方案1失败: {e}')
            
            await asyncio.sleep(2)
            
            # 方案2: 检查页面状态并尝试提交表单
            # bilibili_logger.info(f'[-] 方案2: 检查页面状态...')
            # try:
            #     # 检查页面是否有错误提示
            #     error_elements = self.page.locator('.error-message, .error-text, .ant-message-error, .ant-alert-error')
            #     error_count = await error_elements.count()
            #     if error_count > 0:
            #         for i in range(error_count):
            #             error_text = await error_elements.nth(i).text_content()
            #             bilibili_logger.warning(f'[-] 页面错误提示[{i}]: {error_text}')
                
            #     # 检查是否有必填项未填
            #     required_fields = self.page.locator('[required], .required, .is-required')
            #     required_count = await required_fields.count()
            #     bilibili_logger.info(f'[-] 必填字段数量: {required_count}')
                
            #     # 检查上传是否完成
            #     upload_status = self.page.locator('.upload-status, .upload-progress, .upload-success')
            #     upload_count = await upload_status.count()
            #     bilibili_logger.info(f'[-] 上传状态元素数量: {upload_count}')
                
            #     # 尝试直接提交表单
            #     bilibili_logger.info(f'[-] 尝试提交表单...')
            #     try:
            #         # 查找表单
            #         forms = self.page.locator('form')
            #         form_count = await forms.count()
            #         bilibili_logger.info(f'[-] 找到 {form_count} 个表单')
                    
            #         for i in range(form_count):
            #             form = forms.nth(i)
            #             # 尝试提交表单
            #             await form.evaluate('form => form.submit()')
            #             bilibili_logger.info(f'[-] ✓ 提交表单 {i+1} 完成')
            #             await asyncio.sleep(1)
            #     except Exception as e:
            #         bilibili_logger.warning(f'[-] 提交表单失败: {e}')
                
            #     # 尝试触发提交事件
            #     bilibili_logger.info(f'[-] 尝试触发提交事件...')
            #     try:
            #         await self.page.evaluate('''
            #             () => {
            #                 // 查找所有表单并触发submit事件
            #                 const forms = document.querySelectorAll('form');
            #                 forms.forEach(form => {
            #                     const event = new Event('submit', { bubbles: true, cancelable: true });
            #                     form.dispatchEvent(event);
            #                 });
                            
            #                 // 查找所有按钮并触发click事件
            #                 const buttons = document.querySelectorAll('button[type="submit"], input[type="submit"], .submit-add, [class*="submit"]');
            #                 buttons.forEach(btn => {
            #                     const event = new MouseEvent('click', { bubbles: true, cancelable: true });
            #                     btn.dispatchEvent(event);
            #                 });
            #             }
            #         ''')
            #         bilibili_logger.info(f'[-] ✓ 触发提交事件完成')
            #     except Exception as e:
            #         bilibili_logger.warning(f'[-] 触发提交事件失败: {e}')
                
            # except Exception as e:
            #     bilibili_logger.warning(f'[-] ✗ 方案2失败: {e}')
            
            # await asyncio.sleep(2)
            
            # # 方案3: 最终尝试 - 检查是否所有信息已填写
            # bilibili_logger.info(f'[-] 方案3: 检查信息完整性...')
            # try:
            #     # 检查标题是否已填写
            #     title_input = self.page.locator('input[placeholder*="标题"], input[name*="title"]')
            #     title_count = await title_input.count()
            #     if title_count > 0:
            #         title_value = await title_input.first.input_value()
            #         bilibili_logger.info(f'[-] 标题输入框值: {title_value}')
                
            #     # 检查分区是否已选择
            #     partition_select = self.page.locator('.selector-container, .ant-select-selection-item')
            #     partition_count = await partition_select.count()
            #     bilibili_logger.info(f'[-] 分区选择器数量: {partition_count}')
                
            #     # 检查标签是否已填写
            #     tag_input = self.page.locator('.tag-container input, [class*="tag"] input')
            #     tag_count = await tag_input.count()
            #     bilibili_logger.info(f'[-] 标签输入框数量: {tag_count}')
                
            #     # 检查上传进度
            #     upload_progress = self.page.locator('.progress-bar, .progress-text, [class*="progress"]')
            #     progress_count = await upload_progress.count()
            #     bilibili_logger.info(f'[-] 上传进度元素数量: {progress_count}')
                
            #     # 如果上传未完成,等待一下
            #     if progress_count > 0:
            #         bilibili_logger.info(f'[-] 检测到上传进度,等待5秒...')
            #         await asyncio.sleep(5)
                
            #     # 最终尝试: 精确查找"立即投稿"按钮
            #     bilibili_logger.info(f'[-] 最终尝试: 精确查找"立即投稿"按钮...')
                
            #     # 查找"立即投稿"按钮
            #     submit_buttons = [
            #         'span.submit-add:has-text("立即投稿")',
            #         'button:has-text("立即投稿")',
            #         'text="立即投稿"',
            #     ]
                
            #     final_submit_btn = None
            #     for selector in submit_buttons:
            #         btn = self.page.locator(selector).first
            #         count = await btn.count()
            #         if count > 0:
            #             final_submit_btn = btn
            #             bilibili_logger.info(f'[-] 使用选择器找到按钮: {selector}')
            #             break
                
            #     if not final_submit_btn:
            #         # 查找"保存草稿"按钮,确保不点到它
            #         draft_btn = self.page.locator('text="保存草稿"').first
            #         draft_count = await draft_btn.count()
            #         bilibili_logger.info(f'[-] 找到"保存草稿"按钮数量: {draft_count}')
                    
            #         # 查找所有按钮,排除"保存草稿"
            #         all_btns = self.page.locator('button, span, div, a')
            #         btn_count = await all_btns.count()
            #         bilibili_logger.info(f'[-] 总按钮数量: {btn_count}')
                    
            #         for i in range(min(btn_count, 30)):  # 只检查前30个
            #             try:
            #                 btn = all_btns.nth(i)
            #                 text = await btn.text_content()
            #                 if text and '投稿' in text and '保存草稿' not in text:
            #                     bilibili_logger.info(f'[-] 找到投稿相关按钮[{i}]: {text}')
            #                     if '立即投稿' in text:
            #                         final_submit_btn = btn
            #                         bilibili_logger.info(f'[-] 找到"立即投稿"按钮: {text}')
            #                         break
            #             except:
            #                 continue
                
            #     if final_submit_btn:
            #         # 确认按钮文本
            #         try:
            #             btn_text = await final_submit_btn.text_content()
            #             bilibili_logger.info(f'[-] 确认按钮文本: {btn_text}')
            #             if '立即投稿' not in btn_text:
            #                 bilibili_logger.warning(f'[-] 警告: 按钮文本不是"立即投稿": {btn_text}')
            #         except Exception as e:
            #             bilibili_logger.warning(f'[-] 无法获取按钮文本: {e}')
                    
            #         bilibili_logger.info(f'[-] 尝试点击"立即投稿"按钮...')
            #         try:
            #             await final_submit_btn.click(force=True, timeout=5000)
            #             bilibili_logger.info(f'[-] ✓ 最终点击完成')
            #         except Exception as e:
            #             bilibili_logger.warning(f'[-] 最终点击失败: {e}')
            #     else:
            #         bilibili_logger.warning(f'[-] 未找到"立即投稿"按钮,可能信息未填写完整或按钮被禁用')
                    
            # except Exception as e:
            #     bilibili_logger.warning(f'[-] ✗ 方案3失败: {e}')
                
                # 确认发布(如果有确认弹窗)
            confirm_btn = self.page.locator('button:has-text("确定"), button:has-text("确认")').first
            if await confirm_btn.count():
                await confirm_btn.click()
            
            # 等待发布完成
            await asyncio.sleep(3)
            
            # 检查发布结果
            current_url = self.page.url
            if 'success' in current_url or 'manage' in current_url or 'material' in current_url:
                bilibili_logger.success(f'[+] {Path(self.file_path).name} 上传成功')
                return True
            else:
                bilibili_logger.warning(f'[-] {Path(self.file_path).name} 发布状态未知')
                print("\n" + "="*50)
                print("发布状态未知,请查看浏览器页面")
                print("当前URL:", current_url)
                print("按Enter键继续...")
                input()
                return True
                
        except Exception as e:
            bilibili_logger.error(f'[-] 上传视频失败: {str(e)}')
            import traceback
            traceback.print_exc()
            print("\n" + "="*50)
            print("上传出错,请查看浏览器页面")
            print("按Enter键继续...")
            input()
            return False

    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        """设置视频封面图片"""
        if not thumbnail_path:
            return
            
        try:
            bilibili_logger.info('  [-] 正在设置视频封面...')
            
            # 尝试多种选择器来定位封面上传区域
            cover_selectors = [
                'div[class*="cover-upload"]',
                'div[class*="thumbnail-upload"]',
                'div[class*="cover"] input[type="file"]',
                'input[type="file"][accept*="image"]',
                'div.cover-uploader',
                'div.upload-cover',
                'div.cover-upload-area',
                'div.upload-area',
                'div[role="button"][aria-label*="封面"]',
                'button:has-text("上传封面")',
                'button:has-text("选择封面")',
                'div:has-text("封面") input[type="file"]'
            ]
            
            cover_found = False
            for selector in cover_selectors:
                try:
                    # 等待页面稳定
                    await page.wait_for_timeout(1000)
                    
                    # 检查元素是否存在
                    locator = page.locator(selector)
                    element_count = await locator.count()
                    if element_count > 0:
                        bilibili_logger.info(f'  [-] 找到封面选择器: {selector}')
                        
                        if 'input[type="file"]' in selector:
                            # 直接是文件输入框
                            await locator.set_input_files(thumbnail_path)
                        else:
                            # 先点击元素，然后上传文件
                            await locator.click()
                            await page.wait_for_timeout(500)
                            
                            # 尝试找到文件输入框
                            file_inputs = await page.locator('input[type="file"]').all()
                            if file_inputs:
                                # 使用第一个文件输入框
                                await file_inputs[0].set_input_files(thumbnail_path)
                            else:
                                # 如果没有找到文件输入框，尝试通过文件选择器
                                async with page.expect_file_chooser() as fc_info:
                                    await locator.click()
                                file_chooser = await fc_info.value
                                await file_chooser.set_files(thumbnail_path)
                        
                        bilibili_logger.info('  [+] 视频封面设置完成！')
                        await page.wait_for_timeout(2000)  # 等待封面处理完成
                        cover_found = True
                        break
                        
                except Exception as e:
                    bilibili_logger.debug(f'  [-] 选择器 {selector} 失败: {e}')
                    continue
            
            if not cover_found:
                bilibili_logger.warning('  [-] 未找到封面上传区域，跳过封面设置')
                
        except Exception as e:
            bilibili_logger.warning(f'  [-] 设置封面失败: {e}，继续发布流程')

    async def set_schedule_time(self, page: Page, publish_date: datetime):
        """设置定时发布时间"""
        try:
            # 点击定时发布选项
            schedule_label = page.locator('label:has-text("定时"), text=定时发布').first
            if await schedule_label.count():
                await schedule_label.click()
                await asyncio.sleep(0.5)
                
                # 设置时间
                time_str = publish_date.strftime("%Y-%m-%d %H:%M")
                time_input = page.locator('input[type="text"][placeholder*="时间"], input[class*="time"]').first
                if await time_input.count():
                    await time_input.click()
                    await page.keyboard.press("Control+KeyA")
                    await time_input.fill(time_str)
                    await page.keyboard.press('Enter')
        except Exception as e:
            bilibili_logger.warning(f'[-] 设置定时发布失败: {e}')

    async def main(self):
        """主入口函数"""
        async with async_playwright() as playwright:
            result = await self.upload(playwright)
            # 只有成功时才关闭浏览器,失败时保持打开让用户可以重试
            if result:
                await self.close()
            return result
