"""真实页面的翻页选择器检测：uv run python test_next_page.py。"""

import argparse

from DrissionPage import Chromium, ChromiumOptions

from main import CARD_SELECTOR, EDUCODER_URL, NEXT_PAGE_SELECTOR


def inspect_next_page(tab):
    print('\n========== 翻页选择器检测 ==========')
    print('页面标题：', tab.title)
    print('页面 URL：', tab.url)
    print('Tab ID：', tab.tab_id)
    print('主脚本选择器：', NEXT_PAGE_SELECTOR)

    next_page = tab.ele(NEXT_PAGE_SELECTOR, timeout=10)
    print('next_page =', next_page)

    if next_page:
        print('下一页元素 HTML：\n', next_page.html)
        print('aria-disabled：', repr(next_page.attr('aria-disabled')))
        print('class：', repr(next_page.attr('class')))

        button = next_page.ele('css:button', timeout=2)
        print('button =', button)
        if button:
            disabled_attr = button.attr('disabled')
            disabled = (
                disabled_attr is not None
                or next_page.attr('aria-disabled') == 'true'
                or 'ant-pagination-disabled' in (
                    next_page.attr('class') or ''
                ).split()
            )
            print('button HTML：\n', button.html)
            print('disabled 属性：', repr(disabled_attr))
            print('按钮是否启用：', button.states.is_enabled)
            print('按钮是否显示：', button.states.is_displayed)
            print('主脚本判断：', '已禁用，结束翻页' if disabled else '可翻页')
        else:
            print('找到了下一页元素，但其中没有 button。')
    else:
        print('主选择器没有匹配到元素。')

    # 放宽标签名和 title 条件，输出实际 DOM 供比较。
    for selector in (
        'css:li.ant-pagination-next',
        'css:.ant-pagination-next',
        'css:[title="下一页"]',
        'css:.ant-pagination',
    ):
        elements = tab.eles(selector, timeout=1)
        print(f'\n{selector} -> 匹配 {len(elements)} 个元素')
        for index, element in enumerate(elements, start=1):
            print(f'[{index}] {element.html}')

    css_selector = NEXT_PAGE_SELECTOR.removeprefix('css:')
    js_count = tab.run_js(
        'return document.querySelectorAll(arguments[0]).length;',
        css_selector
    )
    print('\nJavaScript 查询相同选择器的匹配数：', js_count)
    print('当前页视频卡片数量：', len(tab.eles(CARD_SELECTOR, timeout=1)))

    frames = tab.get_frames(timeout=1)
    print('iframe/frame 数量：', len(frames))
    for index, frame in enumerate(frames, start=1):
        try:
            print(f'\nframe #{index} URL：', frame.url)
            elements = frame.eles(NEXT_PAGE_SELECTOR, timeout=1)
            print('frame 内主选择器匹配数：', len(elements))
            for element in elements:
                print(element.html)
        except Exception as exc:
            print(f'读取 frame #{index} 失败：{type(exc).__name__}: {exc}')

    print('\n========== 检测结束 ==========')


def select_list_tab(browser):
    tabs = browser.get_tabs()
    if not tabs:
        raise RuntimeError('当前浏览器没有可检测的标签页。')

    print('\n请选择视频列表所在的标签页：')
    for index, tab in enumerate(tabs, start=1):
        print(f'[{index}] {tab.title}\n    {tab.url}\n    Tab ID: {tab.tab_id}')

    while True:
        choice = input('输入标签页编号（默认 1）：').strip() or '1'
        if choice.isdigit() and 1 <= int(choice) <= len(tabs):
            return tabs[int(choice) - 1]
        print('编号无效，请重新输入。')


def main():
    parser = argparse.ArgumentParser(description='在真实页面中检测下一页选择器。')
    parser.add_argument(
        '--address',
        help='连接已启动的调试浏览器，例如 127.0.0.1:9222；默认启动独立浏览器。'
    )
    args = parser.parse_args()

    options = ChromiumOptions()
    if args.address:
        options.set_address(args.address)
    else:
        options.auto_port()

    browser = Chromium(options)
    print('浏览器调试地址：', browser.address)
    if not args.address:
        browser.latest_tab.get(EDUCODER_URL)

    input('请手动登录并打开视频列表页面，准备好后按回车：')
    tab = select_list_tab(browser)

    while True:
        try:
            inspect_next_page(tab)
        except Exception as exc:
            print(f'检测失败：{type(exc).__name__}: {exc}')

        command = input('\n回车再次检测，t 重新选择标签页，q 退出：').strip().lower()
        if command == 'q':
            break
        if command == 't':
            tab = select_list_tab(browser)

    # 保留浏览器，方便手动翻页后继续检查。
    print('脚本退出，浏览器保持打开。')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n已停止检测，浏览器保持打开。')
