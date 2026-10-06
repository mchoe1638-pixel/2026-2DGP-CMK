# sonic_animation_viewer.py 테스트
# LEC09 폴더에서 `python -m unittest -v`로 실행한다.
# pico2d 함수는 가짜(mock)로 바꿔 창을 열지 않고 확인한다.
import dataclasses
import os
import re
import unittest
from types import SimpleNamespace
from unittest import mock

import sonic_animation_viewer as viewer

try:
    from PIL import Image as PILImage
except ImportError:  # Pillow가 없으면 픽셀 검사 테스트만 건너뛴다.
    PILImage = None

PRD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PRD.md')
SHEET_SIZE = (399, 525)  # sonic-sprite.png 크기 (PRD.md 2절)

# 재생 순서대로 등록할 동작과 프레임 수 (PRD.md 5.3절: 10종 76프레임)
EXPECTED_FRAME_COUNTS = {'대기': 11, '걷기': 12, '발차기': 6, '회전 진입': 9, '스핀 점프': 6,
                         '질주': 6, '최고속 질주': 6, '공중 회전': 8, '정면 달리기': 8, '포즈': 4}


def read_prd() -> str:
    with open(PRD_PATH, encoding='utf-8') as prd:
        return prd.read()


def prd_frames():
    # PRD.md 5.4절 코드 블록에서 [(동작 이름, [프레임 좌표, ...]), ...]를 순서대로 읽는다.
    block = read_prd().split('### 5.4 프레임 좌표', 1)[1].split('```')[1]
    motions = []
    for line in block.splitlines():
        header = re.fullmatch(r'\d+ (.+) \((\d+)\)', line.strip())
        if header:
            motions.append((header.group(1), [], int(header.group(2))))
        elif line.strip():
            boxes = re.findall(r'\((\d+), (\d+), (\d+), (\d+)\)', line)
            motions[-1][1].extend(tuple(map(int, box)) for box in boxes)
    for name, frames, count in motions:  # 머리말의 프레임 수와 읽은 좌표 수가 같아야 한다.
        assert len(frames) == count, (name, len(frames), count)
    return [(name, frames) for name, frames, _ in motions]


def prd_fps():
    # PRD.md 5.3절 표에서 {동작 이름: (프레임 수, fps)}를 읽는다.
    rows = re.findall(r'^\| \d+ \| ([^|]+?) \| \d+ \| (\d+) \| (\d+) \|', read_prd(), re.MULTILINE)
    return {name: (int(count), int(fps)) for name, count, fps in rows}


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


class MotionDataTest(unittest.TestCase):
    def all_frames(self):
        return [(motion.name, frame) for motion in viewer.MOTIONS for frame in motion.frames]

    def test_registered_motions_and_frame_counts(self):
        counts = [(motion.name, len(motion.frames)) for motion in viewer.MOTIONS]
        self.assertEqual(counts, list(EXPECTED_FRAME_COUNTS.items()))

    def test_all_10_motions_and_76_frames_are_registered(self):
        self.assertEqual(len(viewer.MOTIONS), 10)
        self.assertEqual(len(self.all_frames()), 76)

    def test_frames_match_prd_section_5_4_in_order(self):
        registered = [(motion.name, list(motion.frames)) for motion in viewer.MOTIONS]
        self.assertEqual(registered, prd_frames())

    def test_fps_match_prd_section_5_3(self):
        table = prd_fps()
        for motion in viewer.MOTIONS:
            self.assertEqual((len(motion.frames), motion.fps), table[motion.name], motion.name)

    def test_frames_stay_inside_sheet(self):
        sheet_w, sheet_h = SHEET_SIZE
        for name, (left, bottom, width, height) in self.all_frames():
            with self.subTest(motion=name, frame=(left, bottom, width, height)):
                self.assertTrue(width > 0 and height > 0)
                self.assertTrue(0 <= left and left + width <= sheet_w)
                self.assertTrue(0 <= bottom and bottom + height <= sheet_h)

    def test_frames_do_not_overlap(self):
        frames = self.all_frames()
        for i, (name1, (l1, b1, w1, h1)) in enumerate(frames):
            for name2, (l2, b2, w2, h2) in frames[i + 1:]:
                overlap = l1 < l2 + w2 and l2 < l1 + w1 and b1 < b2 + h2 and b2 < b1 + h1
                self.assertFalse(overlap, (name1, (l1, b1, w1, h1), name2, (l2, b2, w2, h2)))

    @unittest.skipIf(PILImage is None, 'Pillow가 없어 픽셀 검사를 건너뜀')
    def test_frame_edges_touch_opaque_pixels(self):
        # 상자의 네 변 모두에 불투명 픽셀이 닿아야 프레임을 꼭 맞게 자른 것이다.
        with PILImage.open(viewer.resource_path(viewer.SPRITE_FILE)) as image:
            sheet = image.convert('RGBA')
        self.assertEqual(sheet.size, SHEET_SIZE)
        for name, (left, bottom, width, height) in self.all_frames():
            top = SHEET_SIZE[1] - bottom - height  # pico2d 좌표(아래 원점) -> 이미지 좌표(위 원점)
            alpha = sheet.crop((left, top, left + width, top + height)).getchannel('A')
            with self.subTest(motion=name, frame=(left, bottom, width, height)):
                self.assertEqual(alpha.getbbox(), (0, 0, width, height))

    def test_motion_data_is_immutable(self):
        self.assertIsInstance(viewer.MOTIONS, tuple)
        self.assertIsInstance(viewer.MOTIONS[0].frames, tuple)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            viewer.MOTIONS[0].fps = 30


if __name__ == '__main__':
    unittest.main()
