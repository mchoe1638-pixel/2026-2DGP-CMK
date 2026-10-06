# sonic_animation_viewer.py 테스트
# LEC09 폴더에서 `python -m unittest -v`로 실행한다.
# pico2d 함수는 가짜(mock)로 바꿔 창을 열지 않고 확인한다.
import unittest
from types import SimpleNamespace
from unittest import mock

import sonic_animation_viewer as viewer


def key_event(key, event_type=None):
    # pico2d의 Event처럼 type과 key를 가진 키 입력 이벤트를 만든다.
    return SimpleNamespace(type=event_type or viewer.SDL_KEYDOWN, key=key)


QUIT_EVENT = SimpleNamespace(type=viewer.SDL_QUIT, key=None)
ESC_EVENT = key_event(viewer.SDLK_ESCAPE)


def run_main(events_per_call):
    # pico2d 함수를 가짜로 바꾸고 main()을 실행한 뒤, 가짜 함수들을 돌려준다.
    # events_per_call: get_events()가 호출될 때마다 차례로 돌려줄 이벤트 목록들
    with mock.patch.multiple(viewer, open_canvas=mock.DEFAULT, close_canvas=mock.DEFAULT,
                             clear_canvas=mock.DEFAULT, update_canvas=mock.DEFAULT,
                             delay=mock.DEFAULT, get_events=mock.DEFAULT) as fakes:
        fakes['get_events'].side_effect = events_per_call
        viewer.main()
    return fakes


class HandleEventsTest(unittest.TestCase):
    def check(self, events, expected):
        with mock.patch.object(viewer, 'get_events', return_value=events):
            self.assertIs(viewer.handle_events(), expected)

    def test_keeps_running_without_events(self):
        self.check([], True)

    def test_stops_on_window_close(self):
        self.check([QUIT_EVENT], False)

    def test_stops_on_escape_key(self):
        self.check([ESC_EVENT], False)

    def test_ignores_other_keys(self):
        self.check([key_event(viewer.SDLK_SPACE)], True)

    def test_ignores_escape_key_release(self):
        self.check([key_event(viewer.SDLK_ESCAPE, viewer.SDL_KEYUP)], True)


class MainLoopTest(unittest.TestCase):
    def test_opens_1200x600_canvas(self):
        fakes = run_main([[ESC_EVENT]])
        fakes['open_canvas'].assert_called_once_with(1200, 600)

    def test_redraws_until_escape_then_closes_canvas(self):
        fakes = run_main([[], [], [ESC_EVENT]])
        self.assertEqual(fakes['clear_canvas'].call_count, 2)
        self.assertEqual(fakes['update_canvas'].call_count, 2)
        fakes['close_canvas'].assert_called_once_with()

    def test_closes_canvas_on_window_close(self):
        fakes = run_main([[], [QUIT_EVENT]])
        fakes['close_canvas'].assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
