import time
from DrissionPage import Chromium


browser = Chromium()

tab = browser.latest_tab

input(
    '请手动打开视频播放页面，'
    '然后按回车：'
)

tab = browser.latest_tab

print(
    '当前页面：',
    tab.url
)

play = tab.ele(
    'css:#play',
    timeout=5
)

current = tab.ele(
    'css:#time-elapsed',
    timeout=5
)

duration = tab.ele(
    'css:#duration',
    timeout=5
)

print(
    'play =',
    play
)

print(
    'current =',
    current
)

print(
    'duration =',
    duration
)

if play:
    print(
        '播放按钮 HTML：'
    )
    print(
        play.html
    )

if current:
    print(
        '当前时间：',
        current.text
    )

if duration:
    print(
        '总时长：',
        duration.text
    )

if play:

    print(
        '点击播放...'
    )

    play.click()

    for i in range(20):

        print(
            'current =',
            current.text,
            '/',
            duration.text
        )

        time.sleep(1)