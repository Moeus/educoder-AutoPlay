import unittest
from unittest.mock import Mock, call, patch

import main


class PaginationTests(unittest.TestCase):
    def make_list_tab(self, button_attrs=None, page_attrs=None):
        list_tab = Mock()
        next_page = Mock()
        button = Mock()
        button.attr.side_effect = (button_attrs or {}).get
        next_page.attr.side_effect = (page_attrs or {}).get
        next_page.ele.return_value = button
        list_tab.ele.return_value = next_page
        return list_tab, button

    @patch('main.time.sleep')
    def test_enabled_button_clicks_in_same_tab(self, sleep):
        list_tab, button = self.make_list_tab(
            page_attrs={'aria-disabled': 'false'}
        )

        self.assertTrue(main.go_to_next_page(list_tab))

        list_tab.set.activate.assert_called_once_with()
        list_tab.ele.assert_called_once_with(main.NEXT_PAGE_SELECTOR, timeout=10)
        activate_index = list_tab.mock_calls.index(call.set.activate())
        detect_index = list_tab.mock_calls.index(
            call.ele(main.NEXT_PAGE_SELECTOR, timeout=10)
        )
        self.assertLess(activate_index, detect_index)
        button.click.assert_called_once_with()
        button.click.for_new_tab.assert_not_called()
        sleep.assert_called_once_with(main.PAGE_LOAD_WAIT)
        list_tab.wait.eles_loaded.assert_called_once_with(
            main.CARD_SELECTOR, timeout=15, raise_err=True
        )

    def test_disabled_boolean_attribute_prevents_click(self):
        for value in ('', 'true', 'disabled'):
            with self.subTest(disabled=value):
                list_tab, button = self.make_list_tab(
                    button_attrs={'disabled': value}
                )

                self.assertFalse(main.go_to_next_page(list_tab))
                button.click.assert_not_called()
                list_tab.wait.eles_loaded.assert_not_called()

    def test_disabled_pagination_prevents_click(self):
        for attrs in (
            {'aria-disabled': 'true'},
            {'class': 'ant-pagination-next ant-pagination-disabled'},
        ):
            with self.subTest(attrs=attrs):
                list_tab, button = self.make_list_tab(page_attrs=attrs)

                self.assertFalse(main.go_to_next_page(list_tab))
                button.click.assert_not_called()

    def test_missing_next_page_finishes(self):
        list_tab, button = self.make_list_tab()
        list_tab.ele.return_value = None

        with patch('builtins.print') as output:
            self.assertFalse(main.go_to_next_page(list_tab))

        button.click.assert_not_called()
        list_tab.eles.assert_not_called()
        list_tab.run_js.assert_not_called()
        output.assert_called_once_with(
            '等待 10 秒后未检测到下一页按钮，停止处理。'
        )

    def test_failed_click_stops_without_scanning_old_page(self):
        list_tab, button = self.make_list_tab()
        button.click.return_value = False

        with self.assertRaisesRegex(RuntimeError, '点击下一页按钮失败'):
            main.go_to_next_page(list_tab)

        list_tab.wait.eles_loaded.assert_not_called()

    def run_pages(self, pages, finished=True):
        list_tab, button = self.make_list_tab()
        page_index = 0

        def button_attr(name):
            if name == 'disabled' and page_index == len(pages) - 1:
                return ''
            return None

        def click_next():
            nonlocal page_index
            page_index += 1
            return button

        button.attr.side_effect = button_attr
        button.click.side_effect = click_next
        browser = Mock(latest_tab=list_tab)
        video_tab = Mock()

        with (
            patch('main.Chromium', return_value=browser),
            patch('main.ChromiumOptions'),
            patch('builtins.input', return_value=''),
            patch('builtins.print'),
            patch('main.time.sleep'),
            patch('main.scan_video_queue', side_effect=lambda tab: pages[page_index]) as scan,
            patch('main.open_video', return_value=video_tab) as open_video,
            patch('main.wait_video_finished', return_value=finished),
            patch('main.cleanup_browser') as cleanup,
        ):
            main.main()

        cleanup.assert_called_once_with(browser)
        return list_tab, button, scan, open_video, video_tab

    def test_processes_each_page_and_skips_completed_page(self):
        first = {'index': 1, 'title': '第一页视频', 'progress': '0%'}
        second = {'index': 2, 'title': '第一页另一个视频', 'progress': '50%'}
        third = {'index': 1, 'title': '第三页视频', 'progress': '0%'}

        list_tab, button, scan, open_video, video_tab = self.run_pages(
            [[first, second], [], [third]]
        )

        self.assertEqual(scan.call_args_list, [call(list_tab)] * 3)
        self.assertEqual(open_video.call_args_list, [
            call(list_tab, first), call(list_tab, second), call(list_tab, third)
        ])
        self.assertEqual(button.click.call_count, 2)
        self.assertEqual(video_tab.close.call_count, 3)

    def test_unfinished_video_stops_outer_loop(self):
        video = {'index': 1, 'title': '未播放完的视频', 'progress': '0%'}
        _, button, scan, open_video, video_tab = self.run_pages(
            [[video, video], [video]], finished=False
        )

        self.assertEqual(scan.call_count, 1)
        self.assertEqual(open_video.call_count, 1)
        button.click.assert_not_called()
        video_tab.close.assert_not_called()


if __name__ == '__main__':
    unittest.main()
