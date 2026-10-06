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


def prd_motion_table():
    # PRD.md 5.3절 표에서 {동작 이름: (프레임 수, fps, 1회 재생 시간, 5회 재생 시간)}을 읽는다.
    rows = re.findall(r'^\| \d+ \| ([^|]+?) \| \d+ \| (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \|',
                      read_prd(), re.MULTILINE)
    return {name: (int(count), int(fps), float(loop), float(play))
            for name, count, fps, loop, play in rows}


def simulate(seconds, state=None, dt=0.01):
    # update()를 dt초 간격으로 호출해 seconds초를 흘려보내고, 호출할 때마다 (시각, 새 상태)를 모은다.
    state = state or viewer.ViewerState()
    history = []
    for step in range(1, round(seconds / dt) + 1):
        state = viewer.update(state, dt)
        history.append((step * dt, state))
    return history


def collapse(values):
    # 연달아 같은 값은 하나로 줄인다. (화면에 보인 프레임 번호의 순서를 보려고 쓴다)
    return [value for i, value in enumerate(values) if i == 0 or values[i - 1] != value]


def key_event(key, event_type=None):
    # pico2d의 Event처럼 type과 key를 가진 키 입력 이벤트를 만든다.
    return SimpleNamespace(type=event_type or viewer.SDL_KEYDOWN, key=key)


QUIT_EVENT = SimpleNamespace(type=viewer.SDL_QUIT, key=None)
ESC_EVENT = key_event(viewer.SDLK_ESCAPE)


PICO2D_FUNCTIONS = ('open_canvas', 'close_canvas', 'clear_canvas', 'update_canvas', 'delay',
                    'get_events', 'get_time', 'load_image')


def fake_pico2d():
    # main()이 쓰는 pico2d 함수를 모두 가짜로 바꾸는 mock.patch.multiple 인자
    return {name: mock.DEFAULT for name in PICO2D_FUNCTIONS}


def run_main(events_per_call, times=None):
    # pico2d 함수를 가짜로 바꾸고 main()을 실행한 뒤, 가짜 함수들을 돌려준다.
    # events_per_call: get_events()가 호출될 때마다 차례로 돌려줄 이벤트 목록들
    # times: get_time()이 호출될 때마다 차례로 돌려줄 시각들 (없으면 시간이 흐르지 않는다)
    with mock.patch.multiple(viewer, **fake_pico2d()) as fakes:
        fakes['get_events'].side_effect = events_per_call
        if times is None:
            fakes['get_time'].return_value = 0.0
        else:
            fakes['get_time'].side_effect = times
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

    def test_draws_first_idle_frame_at_center_on_ground(self):
        # 116x156 그림의 아래쪽 끝이 y = 150이 되려면 중심 y는 150 + 156 / 2 = 228이다.
        fakes = run_main([[], [ESC_EVENT]])
        sheet = fakes['load_image'].return_value
        sheet.clip_draw.assert_called_once_with(1, 447, 29, 39, 600, 228, 116, 156)

    def test_holds_last_frame_after_five_loops(self):
        # 대기 5회 재생은 5.5초: 5.35초에는 9번 프레임, 5.6초와 6.3초에는 마지막(10번) 프레임에 머문다.
        fakes = run_main([[], [], [], [ESC_EVENT]], times=[0.0, 5.35, 5.6, 6.3])
        sheet = fakes['load_image'].return_value
        self.assertEqual(sheet.clip_draw.call_args_list, [
            mock.call(270, 448, 24, 32, 600, 214, 96, 128),
            mock.call(302, 448, 29, 26, 600, 202, 116, 104),
            mock.call(302, 448, 29, 26, 600, 202, 116, 104),
        ])

    def test_escape_during_pause_closes_canvas_at_once(self):
        # 대기 정지 중(5.8초)에 ESC를 누르면 정지 1초가 끝나기를 기다리지 않고 바로 끝낸다.
        # 정지 중에 시각을 따로 더 읽으며 기다리면 준비한 시각 목록이 모자라 오류가 난다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 5.8])
        self.assertEqual(fakes['update_canvas'].call_count, 1)
        fakes['close_canvas'].assert_called_once_with()

    def test_draws_frame_for_time_elapsed_since_start(self):
        # 대기(10fps)를 시작 시각 10.0초 기준으로 0.05초, 0.35초, 1.15초 뒤에 그리면 0, 3, 0번 프레임이다.
        fakes = run_main([[], [], [], [ESC_EVENT]], times=[10.0, 10.05, 10.35, 11.15])
        sheet = fakes['load_image'].return_value
        self.assertEqual(sheet.clip_draw.call_args_list, [
            mock.call(1, 447, 29, 39, 600, 228, 116, 156),
            mock.call(86, 447, 30, 38, 600, 226, 120, 152),
            mock.call(1, 447, 29, 39, 600, 228, 116, 156),
        ])

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
    def test_draws_frame_four_times_larger_with_feet_at_given_height(self):
        # 가로 중심은 x, 아래쪽 끝(발)은 foot_y: clip_draw에는 중심 y = foot_y + 그린 높이 / 2를 넘긴다.
        sheet = mock.Mock()
        viewer.draw_frame(sheet, (1, 447, 29, 39), 600, 150)
        sheet.clip_draw.assert_called_once_with(1, 447, 29, 39, 600, 228, 116, 156)

    def test_feet_rest_on_ground_line_for_every_frame(self):
        # 프레임 높이(26~45px)가 달라도 그림의 아래쪽 끝은 항상 발 기준선 y = 150에 놓인다.
        for motion in viewer.MOTIONS:
            for frame in motion.frames:
                sheet = mock.Mock()
                viewer.draw_frame(sheet, frame, 600, viewer.GROUND_Y)
                *_, center_y, _, draw_h = sheet.clip_draw.call_args.args
                self.assertEqual(center_y - draw_h / 2, 150, (motion.name, frame))


class FrameIndexTest(unittest.TestCase):
    def test_starts_at_first_frame(self):
        for motion in viewer.MOTIONS:
            self.assertEqual(viewer.frame_index(motion, 0.0), 0, motion.name)

    def test_advances_one_frame_every_1_over_fps_seconds(self):
        # 각 프레임 구간의 가운데 시각에서 확인한다. (예: 10fps면 0.05초 -> 0번, 0.15초 -> 1번)
        for motion in viewer.MOTIONS:
            for k in range(len(motion.frames)):
                with self.subTest(motion=motion.name, frame=k):
                    self.assertEqual(viewer.frame_index(motion, (k + 0.5) / motion.fps), k)

    def test_returns_to_first_frame_after_last_frame(self):
        for motion in viewer.MOTIONS:
            one_loop = len(motion.frames) / motion.fps
            self.assertEqual(viewer.frame_index(motion, one_loop + 0.5 / motion.fps), 0, motion.name)


class RepeatTest(unittest.TestCase):
    def test_starts_playing_first_motion_from_the_beginning(self):
        state = viewer.ViewerState()
        self.assertEqual((state.motion_index, state.phase, state.elapsed), (0, viewer.PLAY, 0.0))

    def test_loop_and_play_times_match_prd_section_5_3(self):
        table = prd_motion_table()
        self.assertEqual(viewer.REPEAT_COUNT, 5)
        for motion in viewer.MOTIONS:
            _, _, loop, play = table[motion.name]
            self.assertAlmostEqual(viewer.loop_time(motion), loop, delta=1e-9, msg=motion.name)
            self.assertAlmostEqual(viewer.play_time(motion), play, delta=1e-9, msg=motion.name)

    def test_update_returns_new_state_and_keeps_old_one(self):
        state = viewer.ViewerState()
        new_state = viewer.update(state, 0.25)
        self.assertEqual(state.elapsed, 0.0)
        self.assertAlmostEqual(new_state.elapsed, 0.25)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            state.elapsed = 1.0

    def test_plays_every_frame_five_times_then_holds_last_frame(self):
        # 동작마다 0.01초 간격으로 재생 시간 + 0.5초를 흘려보내며 화면에 보이는 프레임을 기록한다.
        for index, motion in enumerate(viewer.MOTIONS):
            with self.subTest(motion=motion.name):
                start = viewer.ViewerState(motion_index=index)
                history = simulate(viewer.play_time(motion) + 0.5, start)
                playing = [viewer.current_frame_index(s) for _, s in history if s.phase == viewer.PLAY]
                holding = [viewer.current_frame_index(s) for _, s in history if s.phase == viewer.PAUSE]
                last = len(motion.frames) - 1
                self.assertEqual(collapse(playing), list(range(last + 1)) * 5)
                self.assertGreater(len(holding), 40)
                self.assertEqual(set(holding), {last})
                self.assertEqual({s.motion_index for _, s in history}, {index})

    def test_stops_exactly_when_fifth_loop_ends(self):
        # 대기 5회 재생은 5.5초: 5.49초에는 재생 중, 5.51초에는 정지 0.01초째
        before = viewer.update(viewer.ViewerState(), 5.49)
        after = viewer.update(before, 0.02)
        self.assertEqual(before.phase, viewer.PLAY)
        self.assertEqual(after.phase, viewer.PAUSE)
        self.assertAlmostEqual(after.elapsed, 0.01)

    def test_long_time_step_carries_over_into_pause(self):
        # 한 번에 5.9초가 지나도 재생 5.5초를 넘은 0.4초는 정지 단계에서 지난 시간으로 센다.
        state = viewer.update(viewer.ViewerState(), 5.9)
        self.assertEqual(state.phase, viewer.PAUSE)
        self.assertAlmostEqual(state.elapsed, 0.4)
        self.assertEqual(viewer.current_frame_index(state), 10)


class PauseTest(unittest.TestCase):
    def test_pause_time_is_one_second(self):
        self.assertEqual(viewer.PAUSE_TIME, 1.0)

    def test_holds_last_frame_for_one_second_then_plays_again(self):
        # 동작마다 0.01초 간격으로 재생 시간 + 1.5초를 흘려보내며 정지 단계를 살펴본다.
        for index, motion in enumerate(viewer.MOTIONS):
            with self.subTest(motion=motion.name):
                history = simulate(viewer.play_time(motion) + 1.5, viewer.ViewerState(motion_index=index))
                paused = [(t, s) for t, s in history if s.phase == viewer.PAUSE]
                self.assertAlmostEqual(paused[0][0], viewer.play_time(motion), delta=0.0101)
                self.assertLessEqual(abs(len(paused) - 100), 1)  # 0.01초 간격으로 1초 = 100번
                self.assertEqual({viewer.current_frame_index(s) for _, s in paused}, {len(motion.frames) - 1})
                _, after = history[-1]
                self.assertEqual(after.phase, viewer.PLAY)
                self.assertAlmostEqual(after.elapsed, 0.5, delta=0.0101)

    def test_long_time_step_can_pass_whole_pause(self):
        # 한 번에 6.8초가 지나면 대기 재생 5.5초와 정지 1초를 모두 마치고 새 재생 단계 0.3초째다.
        state = viewer.update(viewer.ViewerState(), 6.8)
        self.assertEqual(state.phase, viewer.PLAY)
        self.assertAlmostEqual(state.elapsed, 0.3)


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
        table = prd_motion_table()
        for motion in viewer.MOTIONS:
            count, fps, _, _ = table[motion.name]
            self.assertEqual((len(motion.frames), motion.fps), (count, fps), motion.name)

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
