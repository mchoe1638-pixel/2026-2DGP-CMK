# sonic_animation_viewer.py 테스트
# LEC09 폴더에서 `python -m unittest -v`로 실행한다.
# pico2d 함수는 가짜(mock)로 바꿔 창을 열지 않고 확인한다.
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import sonic_animation_viewer as viewer


def key_event(key, event_type=None):
    # pico2d의 Event처럼 type과 key를 가진 키 입력 이벤트를 만든다.
    return SimpleNamespace(type=event_type or viewer.SDL_KEYDOWN, key=key)


QUIT_EVENT = SimpleNamespace(type=viewer.SDL_QUIT, key=None)
ESC_EVENT = key_event(viewer.SDLK_ESCAPE)


PICO2D_FUNCTIONS = ('open_canvas', 'close_canvas', 'clear_canvas', 'update_canvas', 'delay',
                    'get_events', 'load_image')


def fake_pico2d():
    # main()이 쓰는 pico2d 함수를 모두 가짜로 바꾸는 mock.patch.multiple 인자
    return {name: mock.DEFAULT for name in PICO2D_FUNCTIONS}


def run_main(events_per_call):
    # pico2d 함수를 가짜로 바꾸고 main()을 실행한 뒤, 가짜 함수들을 돌려준다.
    # events_per_call: get_events()가 호출될 때마다 차례로 돌려줄 이벤트 목록들
    with mock.patch.multiple(viewer, **fake_pico2d()) as fakes:
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

    def test_loads_sprite_sheet_next_to_script(self):
        fakes = run_main([[ESC_EVENT]])
        fakes['load_image'].assert_called_once_with(viewer.resource_path('sonic-sprite.png'))

    def test_draws_first_idle_frame_at_center(self):
        fakes = run_main([[], [ESC_EVENT]])
        sheet = fakes['load_image'].return_value
        sheet.clip_draw.assert_called_once_with(1, 447, 29, 39, 600, 300, 116, 156)

    def test_closes_canvas_when_sheet_cannot_be_loaded(self):
        with mock.patch.multiple(viewer, **fake_pico2d()) as fakes:
            fakes['get_events'].side_effect = [[ESC_EVENT]]
            fakes['load_image'].side_effect = IOError
            with self.assertRaises(IOError):
                viewer.main()
        fakes['close_canvas'].assert_called_once_with()


class SpriteSheetTest(unittest.TestCase):
    def test_sprite_path_is_next_to_script(self):
        path = viewer.resource_path(viewer.SPRITE_FILE)
        script_dir = os.path.dirname(os.path.abspath(viewer.__file__))
        self.assertEqual(path, os.path.join(script_dir, 'sonic-sprite.png'))
        self.assertTrue(os.path.isfile(path))


class DrawFrameTest(unittest.TestCase):
    def test_draws_frame_four_times_larger_centered_at_position(self):
        sheet = mock.Mock()
        viewer.draw_frame(sheet, (1, 447, 29, 39), 600, 300)
        sheet.clip_draw.assert_called_once_with(1, 447, 29, 39, 600, 300, 116, 156)


if __name__ == '__main__':
    unittest.main()
