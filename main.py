import time

from DrissionPage import Chromium
from DrissionPage import Chromium, ChromiumOptions
import traceback

# ============================================================
# 配置
# ============================================================

EDUCODER_URL = 'https://www.educoder.net/'

# 每隔多少秒检查一次视频时间
CHECK_INTERVAL = 3

# 打开视频页后，等待播放器初始化
PLAYER_LOAD_WAIT = 3

# 视频结束后，给网页一点时间提交进度
AFTER_VIDEO_WAIT = 3

# 点击下一页后，等待视频列表更新
PAGE_LOAD_WAIT = 3


# ============================================================
# 视频列表页面元素
# ============================================================

# 每个视频卡片
CARD_SELECTOR = 'css:.ant-card-body'

# 视频完成百分比
PROGRESS_SELECTOR = 'css:.ant-progress-text'

# 视频列表的下一页按钮（翻页不会打开新 Tab）
NEXT_PAGE_SELECTOR = 'css:li.ant-pagination-next[title="下一页"]'


# ============================================================
# 视频播放器元素
# ============================================================

# <button data-title="播放/暂停" id="play"></button>
PLAY_SELECTOR = 'css:#play'

# <time id="time-elapsed">00:00</time>
VIDEO_CURRENT_SELECTOR = 'css:#time-elapsed'

# <time id="duration">07:34</time>
VIDEO_DURATION_SELECTOR = 'css:#duration'


# ============================================================
# 时间转换
# ============================================================

def parse_time(text):
    """
    将播放器中的时间转换成秒。

    例如：

        00:15 -> 15
        07:34 -> 454
        01:02:03 -> 3723
    """

    if not text:
        return 0

    text = text.strip()

    try:
        parts = [
            int(part)
            for part in text.split(':')
        ]
    except (ValueError, TypeError):
        return 0

    if len(parts) == 2:
        minute, second = parts

        return (
            minute * 60
            + second
        )

    if len(parts) == 3:
        hour, minute, second = parts

        return (
            hour * 3600
            + minute * 60
            + second
        )

    return 0


# ============================================================
# 扫描视频列表
# ============================================================

def scan_video_queue(list_tab):
    """
    获取所有：

        .ant-card-body

    检查其中：

        .ant-progress-text

    如果不是 100%，加入待播放队列。

    队列中不直接保存元素对象，而保存 index。
    """

    print()
    print('========================================')
    print('正在扫描视频列表...')
    print('========================================')

    cards = list_tab.eles(
        CARD_SELECTOR
    )

    print(
        f'共发现 {len(cards)} 个视频卡片。'
    )

    queue = []

    for index, card in enumerate(
        cards,
        start=1
    ):

        try:

            # ----------------------------------------
            # 获取进度
            # ----------------------------------------

            progress_ele = card.ele(
                PROGRESS_SELECTOR,
                timeout=1
            )

            if progress_ele:

                progress = (
                    progress_ele.text
                    .strip()
                    .replace(' ', '')
                )

            else:

                progress = '未知'

            # ----------------------------------------
            # 获取视频名称
            # ----------------------------------------

            card_text = (
                card.text
                .strip()
            )

            if card_text:

                lines = [
                    line.strip()
                    for line in card_text.splitlines()
                    if line.strip()
                ]

                if lines:
                    title = lines[0][:80]
                else:
                    title = f'视频 #{index}'

            else:

                title = f'视频 #{index}'

            # ----------------------------------------
            # 输出
            # ----------------------------------------

            print(
                f'[{index}] '
                f'{title} '
                f'进度：{progress}'
            )

            # ----------------------------------------
            # 已经完成
            # ----------------------------------------

            if progress == '100%':

                print(
                    '    -> 已完成，跳过'
                )

                continue

            # ----------------------------------------
            # 加入队列
            # ----------------------------------------

            queue.append(
                {
                    'index': index,
                    'title': title,
                    'progress': progress,
                }
            )

        except Exception as e:

            print(
                f'[{index}] 读取失败：'
                f'{type(e).__name__}: {e}'
            )

    print()

    print(
        f'扫描完成，需要播放 '
        f'{len(queue)} 个视频。'
    )

    return queue


# ============================================================
# 翻到下一页
# ============================================================

def go_to_next_page(list_tab):
    """在原列表 Tab 中翻页；没有下一页或按钮禁用时结束。"""

    # 使用保存的视频列表 Tab，激活后再检测，避免在后台页面上过早查找。
    list_tab.set.activate()

    next_page = list_tab.ele(
        NEXT_PAGE_SELECTOR,
        timeout=10
    )

    if not next_page:
        print('等待 10 秒后未检测到下一页按钮，停止处理。')
        return False

    button = next_page.ele('css:button', timeout=2)

    if not button:
        raise RuntimeError('找到了下一页元素，但没有找到其中的 button。')

    # disabled 是布尔属性，disabled="" 也表示禁用，不能用真假判断。
    if (
        button.attr('disabled') is not None
        or next_page.attr('aria-disabled') == 'true'
        or 'ant-pagination-disabled' in (
            next_page.attr('class') or ''
        ).split()
    ):
        print('下一页按钮已禁用，已到最后一页。')
        return False

    print('当前页处理完成，正在翻到下一页...')

    if not button.click():
        raise RuntimeError('点击下一页按钮失败。')

    time.sleep(PAGE_LOAD_WAIT)
    list_tab.wait.eles_loaded(
        CARD_SELECTOR,
        timeout=15,
        raise_err=True
    )

    return True


# ============================================================
# 打开视频
# ============================================================

def open_video(list_tab, video_info):
    """
    根据保存的 index，
    重新获取视频卡片并点击。

    假定点击以后会打开一个新 Tab。
    """

    index = video_info['index']

    # 页面可能发生过重新渲染，
    # 所以这里重新获取 card。
    cards = list_tab.eles(
        CARD_SELECTOR
    )

    if index > len(cards):

        print(
            f'视频 #{index} 已经不存在。'
        )

        return None

    card = cards[
        index - 1
    ]

    print()
    print('----------------------------------------')
    print(
        f'准备播放：{video_info["title"]}'
    )

    print(
        f'当前进度：{video_info["progress"]}'
    )

    try:

        print(
            '正在点击视频卡片...'
        )

        video_tab = (
            card.click.for_new_tab()
        )

        if not video_tab:

            print(
                '点击后没有获取到新标签页。'
            )

            return None

        print(
            f'已打开视频页面：'
            f'{video_tab.title}'
        )

        # 等待播放器加载
        time.sleep(
            PLAYER_LOAD_WAIT
        )

        return video_tab

    except Exception as e:

        print(
            '打开视频失败：'
            f'{type(e).__name__}: {e}'
        )

        return None


# ============================================================
# 等待播放器初始化
# ============================================================

def get_player_elements(tab):
    """
    获取：

        #play
        #time-elapsed
        #duration

    并等待 duration 从 00:00
    变成真实视频长度。
    """

    print(
        '正在获取播放器元素...'
    )

    try:

        play = tab.ele(
            PLAY_SELECTOR,
            timeout=10
        )

        current = tab.ele(
            VIDEO_CURRENT_SELECTOR,
            timeout=10
        )

        duration = tab.ele(
            VIDEO_DURATION_SELECTOR,
            timeout=10
        )

    except Exception as e:

        print(
            '获取播放器元素失败：'
            f'{type(e).__name__}: {e}'
        )

        return None

    if not play:
        print(
            '没有找到播放按钮 #play'
        )
        return None

    if not current:
        print(
            '没有找到 #time-elapsed'
        )
        return None

    if not duration:
        print(
            '没有找到 #duration'
        )
        return None

    print(
        '播放器元素获取成功。'
    )

    # ----------------------------------------
    # 等待视频总时长加载
    # ----------------------------------------

    print(
        '等待视频时长加载...'
    )

    for _ in range(30):

        try:

            duration_text = (
                duration.text
                .strip()
            )

            duration_seconds = (
                parse_time(
                    duration_text
                )
            )

            print(
                f'\r总时长：{duration_text}',
                end='',
                flush=True
            )

            if duration_seconds > 0:

                print()

                return {
                    'play': play,
                    'current': current,
                    'duration': duration,
                }

        except Exception:
            pass

        time.sleep(1)

    print()

    print(
        '等待视频时长超时，'
        'duration 一直是 00:00。'
    )

    return None


# ============================================================
# 点击播放
# ============================================================

def click_play(play_button):
    """
    点击实际的播放按钮。
    """

    try:

        print(
            '正在点击播放按钮...'
        )

        play_button.click()

        time.sleep(2)

        print(
            '播放按钮点击完成。'
        )

        return True

    except Exception as e:

        print(
            '点击播放按钮失败：'
            f'{type(e).__name__}: {e}'
        )

        return False


# ============================================================
# 等待视频结束
# ============================================================

def wait_video_finished(tab):
    """
    正常播放视频并监控：

        #time-elapsed
        #duration

    当：

        current >= duration

    且 duration > 0

    时认为视频正常播放结束。

    这样不会出现：

        00:00 == 00:00

    导致误判结束。
    """

    player = get_player_elements(
        tab
    )

    if not player:

        return False

    play_button = player['play']
    current_ele = player['current']
    duration_ele = player['duration']

    # ----------------------------------------
    # 当前状态
    # ----------------------------------------

    try:

        current_text = (
            current_ele.text
            .strip()
        )

        duration_text = (
            duration_ele.text
            .strip()
        )

        print(
            f'开始时间：'
            f'{current_text} / {duration_text}'
        )

    except Exception as e:

        print(
            f'读取播放器状态失败：{e}'
        )

        return False

    # ----------------------------------------
    # 点击播放
    # ----------------------------------------

    if not click_play(
        play_button
    ):

        return False

    print()
    print(
        '开始监控视频进度...'
    )

    last_seconds = -1

    # 连续多少次时间没有变化
    same_count = 0

    while True:

        try:

            current_text = (
                current_ele.text
                .strip()
            )

            duration_text = (
                duration_ele.text
                .strip()
            )

            current_seconds = (
                parse_time(
                    current_text
                )
            )

            duration_seconds = (
                parse_time(
                    duration_text
                )
            )

            # ----------------------------------------
            # 防止 duration 突然暂时变成 00:00
            # ----------------------------------------

            if duration_seconds <= 0:

                print(
                    f'\r[等待播放器] '
                    f'{current_text} / '
                    f'{duration_text}',
                    end='',
                    flush=True
                )

                time.sleep(
                    CHECK_INTERVAL
                )

                continue

            # ----------------------------------------
            # 判断时间是否前进
            # ----------------------------------------

            if current_seconds == last_seconds:

                same_count += 1

            else:

                same_count = 0

            # ----------------------------------------
            # 状态显示
            # ----------------------------------------

            if same_count >= 3:

                status = '暂停/缓冲'

            else:

                status = '播放'

            print(
                f'\r'
                f'[{status}] '
                f'{current_text} / '
                f'{duration_text}',
                end='',
                flush=True
            )

            # ----------------------------------------
            # 正常结束
            # ----------------------------------------

            if (
                duration_seconds > 0
                and
                current_seconds >= duration_seconds
            ):

                print()
                print(
                    '视频播放结束。'
                )

                # 给页面自己的 ended / 进度提交
                # 逻辑一点时间
                time.sleep(
                    AFTER_VIDEO_WAIT
                )

                return True

            last_seconds = (
                current_seconds
            )

        except Exception as e:

            print()

            print(
                '获取视频进度失败：'
                f'{type(e).__name__}: {e}'
            )

            return False

        time.sleep(
            CHECK_INTERVAL
        )
def cleanup_browser(browser):
    """
    尽量清除当前浏览器中的账号数据，
    然后关闭浏览器并删除用户数据目录。
    """

    if browser is None:
        return

    print()
    print('========================================')
    print('正在清理浏览器数据...')
    print('========================================')

    # --------------------------------------------------
    # 1. 清理每一个 Tab 的网站数据
    # --------------------------------------------------

    try:
        tabs = browser.get_tabs()

        print(
            f'当前共有 {len(tabs)} 个标签页。'
        )

        for index, tab in enumerate(
            tabs,
            start=1
        ):
            try:

                print(
                    f'清理 Tab #{index}: '
                    f'{tab.url}'
                )

                tab.clear_cache(
                    session_storage=True,
                    local_storage=True,
                    cache=True,
                    cookies=True
                )

            except Exception as e:

                print(
                    f'Tab #{index} 清理失败：'
                    f'{type(e).__name__}: {e}'
                )

    except Exception as e:

        print(
            '获取 Tab 列表失败：'
            f'{type(e).__name__}: {e}'
        )

    # --------------------------------------------------
    # 2. 再从浏览器级别清 Cookies / Cache
    # --------------------------------------------------

    try:

        browser.clear_cache(
            cache=True,
            cookies=True
        )

        print(
            '浏览器 Cookies / Cache 已清理。'
        )

    except Exception as e:

        print(
            '浏览器级缓存清理失败：'
            f'{type(e).__name__}: {e}'
        )

    # --------------------------------------------------
    # 3. 关闭浏览器，并删除用户数据目录
    # --------------------------------------------------

    try:

        print(
            '正在关闭浏览器并删除用户数据目录...'
        )

        browser.quit(
            timeout=5,
            force=True,
            del_data=True
        )

        print(
            '浏览器已关闭。'
        )

    except Exception as e:

        print(
            '关闭浏览器失败：'
            f'{type(e).__name__}: {e}'
        )


# ============================================================
# 主程序
# ============================================================

def main():

    browser = None

    print(
        '启动 Chromium...'
    )

    try:
        options = ChromiumOptions().auto_port()
        browser = Chromium(options)

        tab = browser.latest_tab

        # ----------------------------------------
        # 打开头歌
        # ----------------------------------------

        print(
            '正在打开头歌实践教学平台...'
        )

        tab.get(
            EDUCODER_URL
        )

        print()
        print('========================================')
        print('请手动完成以下操作：')
        print()
        print('1. 登录头歌实践教学平台')
        print('2. 进入需要学习的课程')
        print('3. 打开视频列表页面')
        print()
        print('保持当前视频列表页面打开。')
        print('========================================')
        print()

        input(
            '准备完成后按回车继续：'
        )

        # ----------------------------------------
        # 用户最后打开的 Tab 就认为是视频列表
        # ----------------------------------------

        list_tab = (
            browser.latest_tab
        )

        print()
        print(
            f'视频列表标题：'
            f'{list_tab.title}'
        )

        print(
            f'视频列表 URL：'
            f'{list_tab.url}'
        )

        # 外层循环翻页，内层循环播放当前页的视频。
        page_number = 1
        stop_processing = False

        while True:

            print()
            print(f'========== 处理第 {page_number} 页 ==========')

            # ----------------------------------------
            # 获取待播放视频
            # ----------------------------------------

            queue = scan_video_queue(
                list_tab
            )

            if not queue:

                print()
                print(
                    '当前页没有需要播放的视频，继续检查下一页。'
                )

            total = len(queue)

            print()
            print('========================================')
            print(
                f'准备依次播放 {total} 个视频。'
            )
            print('========================================')

            # ----------------------------------------
            # 遍历队列
            # ----------------------------------------

            for number, video_info in enumerate(
                queue,
                start=1
            ):

                print()
                print()
                print(
                    f'========== '
                    f'[{number}/{total}] '
                    f'=========='
                )

                video_tab = open_video(
                    list_tab,
                    video_info
                )

                if not video_tab:

                    print(
                        '无法打开该视频，跳过。'
                    )

                    continue

                video_finished = False

                try:

                    video_finished = (
                        wait_video_finished(
                            video_tab
                        )
                    )

                except KeyboardInterrupt:

                    print()
                    print(
                        '检测到 Ctrl+C，准备停止。'
                    )

                    raise

                except Exception as e:

                    print()
                    print(
                        '播放过程中发生错误：'
                        f'{type(e).__name__}: {e}'
                    )

                finally:

                    # ------------------------------------
                    # 只有确定正常结束才自动关闭视频页
                    # ------------------------------------

                    if video_finished:

                        try:

                            print(
                                '关闭当前视频标签页...'
                            )

                            video_tab.close()

                        except Exception as e:

                            print(
                                f'关闭视频标签页失败：{e}'
                            )

                        print(
                            '返回视频列表。'
                        )

                        # 等待平台提交进度
                        time.sleep(
                            AFTER_VIDEO_WAIT
                        )

                    else:

                        print()
                        print(
                            '当前视频没有确认正常结束。'
                        )

                        print(
                            '为避免误操作，程序停止，'
                            '视频页面保持打开。'
                        )

                        stop_processing = True
                        break

            # 播放未正常结束时，停止外层循环，不继续翻页。
            if stop_processing:
                break

            if not go_to_next_page(list_tab):
                break

            page_number += 1

        # ----------------------------------------
        # 最后刷新列表查看进度
        # ----------------------------------------

        print()
        print('========================================')
        print('视频队列处理结束。')
        print('========================================')

        try:

            print(
                '刷新视频列表...'
            )

            list_tab.refresh()

        except Exception as e:

            print(
                f'刷新列表失败：{e}'
            )
            
    except KeyboardInterrupt:
        
        print()
        print(
            '检测到 Ctrl+C，准备退出。'
        )
    except Exception as e:

        print()
        print(
            '程序发生异常：'
        )

        print(
            f'{type(e).__name__}: {e}'
        )

        # 调试阶段建议保留完整堆栈
        traceback.print_exc()

    finally:
        
        cleanup_browser(
            browser
        )
if __name__ == '__main__':
    main()
