from conf import LOCAL_CHROME_HEADLESS, LOCAL_CHROME_PATH

def get_browser_options():
    options = {
        'headless': LOCAL_CHROME_HEADLESS,
        'args': [
            '--disable-blink-features=AutomationControlled',
            '--lang=zh-CN',
            '--disable-infobars',
            '--start-maximized',
            '--no-sandbox',
            '--disable-web-security'
        ]
    }
    if LOCAL_CHROME_PATH:
        # 使用系统 Chrome 而不是 Playwright 自带的 Chromium
        options['executable_path'] = LOCAL_CHROME_PATH
        # 添加 channel 参数以确保使用 Chrome 而不是 Chromium
        options['channel'] = 'chrome'
    return options
