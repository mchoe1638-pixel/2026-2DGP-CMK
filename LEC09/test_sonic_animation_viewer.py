# sonic_animation_viewer.py 테스트
# LEC09 폴더에서 `python -m unittest -v`로 실행한다.
# pico2d 함수는 가짜(mock)로 바꿔 창을 열지 않고 확인한다.
import dataclasses
import itertools
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


def prd_movement_table():
    # PRD.md 6.1절 표에서 {동작 이름: (분류, 속도, 5회 재생 중 이동 거리, 점프 높이)}를 읽는다.
    rows = re.findall(r'^\| \d+ \| ([^|]+?) \| (중앙|이동) \| (\d+) \| (\d+) \| (\d+) \|$',
                      read_prd(), re.MULTILINE)
    return {name: (kind, int(speed), int(distance), int(jump))
            for name, kind, speed, distance, jump in rows}


def prd_expected_moves():
    # PRD.md 6.6절 표에서 {동작 이름: (이동 범위 왼쪽 끝, 오른쪽 끝, 반전 시각 또는 None, 끝 위치, 끝 방향)}을 읽는다.
    rows = re.findall(r'^\| ([^|]+?) \| (\d+) ~ (\d+) \| (?:([\d.]+)초 \([^)]*\)|없음) \| (\d+) \| (왼쪽|오른쪽) \|$',
                      read_prd(), re.MULTILINE)
    return {name: (int(low), int(high), float(turn) if turn else None, int(end),
                   viewer.LEFT if facing == '왼쪽' else viewer.RIGHT)
            for name, low, high, turn, end, facing in rows}


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


def motion_runs():
    # 처음부터 0.01초 간격으로 1회 순환(44.75초)을 흘려보내며 동작마다 [(그 동작이 시작된 뒤 지난 시각, 상태), ...]를 모은다.
    # 동작이 시작되는 시각은 앞선 동작들의 (5회 재생 시간 + 정지 1초)의 합이다.
    by_motion = itertools.groupby(simulate(44.75), key=lambda sample: sample[1].motion_index)
    runs, start = [], 0.0
    for motion, (_, run) in zip(viewer.MOTIONS, by_motion):
        runs.append([(t - start, state) for t, state in run])
        start += viewer.play_time(motion) + viewer.PAUSE_TIME
    return runs


def key_event(key, event_type=None):
    # pico2d의 Event처럼 type과 key를 가진 키 입력 이벤트를 만든다.
    return SimpleNamespace(type=event_type or viewer.SDL_KEYDOWN, key=key)


QUIT_EVENT = SimpleNamespace(type=viewer.SDL_QUIT, key=None)
ESC_EVENT = key_event(viewer.SDLK_ESCAPE)


PICO2D_FUNCTIONS = ('open_canvas', 'close_canvas', 'clear_canvas', 'update_canvas', 'delay',
                    'get_events', 'get_time', 'load_image', 'load_font')


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
        sheet.clip_composite_draw.assert_called_once_with(1, 447, 29, 39, 0, '', 600, 228, 116, 156)

    def test_holds_last_frame_after_five_loops(self):
        # 대기 5회 재생은 5.5초: 5.35초에는 9번 프레임, 5.6초와 6.3초에는 마지막(10번) 프레임에 머문다.
        fakes = run_main([[], [], [], [ESC_EVENT]], times=[0.0, 5.35, 5.6, 6.3])
        sheet = fakes['load_image'].return_value
        self.assertEqual(sheet.clip_composite_draw.call_args_list, [
            mock.call(270, 448, 24, 32, 0, '', 600, 214, 96, 128),
            mock.call(302, 448, 29, 26, 0, '', 600, 202, 116, 104),
            mock.call(302, 448, 29, 26, 0, '', 600, 202, 116, 104),
        ])

    def test_escape_during_pause_closes_canvas_at_once(self):
        # 대기 정지 중(5.8초)에 ESC를 누르면 정지 1초가 끝나기를 기다리지 않고 바로 끝낸다.
        # 정지 중에 시각을 따로 더 읽으며 기다리면 준비한 시각 목록이 모자라 오류가 난다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 5.8])
        self.assertEqual(fakes['update_canvas'].call_count, 1)
        fakes['close_canvas'].assert_called_once_with()

    def test_draws_first_walk_frame_after_idle_pause(self):
        # 대기는 5.5초 재생 + 1초 정지: 6.45초에는 대기 마지막 프레임, 6.55초에는 걷기 첫 프레임을 그린다.
        # 걷기는 6.5초에 x = 600에서 출발해 0.05초 동안 150px/초로 움직였으므로 x = 607.5에 그린다.
        fakes = run_main([[], [], [ESC_EVENT]], times=[0.0, 6.45, 6.55])
        idle_call, walk_call = fakes['load_image'].return_value.clip_composite_draw.call_args_list
        self.assertEqual(idle_call, mock.call(302, 448, 29, 26, 0, '', 600, 202, 116, 104))
        *frame_and_flip, x, y, draw_w, draw_h = walk_call.args
        self.assertEqual((*frame_and_flip, y, draw_w, draw_h), (8, 408, 26, 37, 0, '', 224, 104, 148))
        self.assertAlmostEqual(x, 607.5)

    def test_draws_frame_for_time_elapsed_since_start(self):
        # 대기(10fps)를 시작 시각 10.0초 기준으로 0.05초, 0.35초, 1.15초 뒤에 그리면 0, 3, 0번 프레임이다.
        fakes = run_main([[], [], [], [ESC_EVENT]], times=[10.0, 10.05, 10.35, 11.15])
        sheet = fakes['load_image'].return_value
        self.assertEqual(sheet.clip_composite_draw.call_args_list, [
            mock.call(1, 447, 29, 39, 0, '', 600, 228, 116, 156),
            mock.call(86, 447, 30, 38, 0, '', 600, 226, 120, 152),
            mock.call(1, 447, 29, 39, 0, '', 600, 228, 116, 156),
        ])

    def test_draws_walking_sonic_at_moved_x(self):
        # 걷기는 6.5초에 x = 600에서 시작해 150px/초로 움직인다: 7.5초에는 x = 750에 첫 프레임을 그린다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 7.5])
        sheet = fakes['load_image'].return_value
        sheet.clip_composite_draw.assert_called_once_with(8, 408, 26, 37, 0, '', 750, 224, 104, 148)

    def test_draws_walking_sonic_flipped_after_turning_back(self):
        # 걷기는 4초 동안 600px을 가려다 오른쪽 끝(1126)에서 74px 되돌아온다: 10.5초에는 x = 1052에서 왼쪽을 본다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 10.5])
        sheet = fakes['load_image'].return_value
        sheet.clip_composite_draw.assert_called_once_with(8, 408, 26, 37, 0, 'h', 1052, 224, 104, 148)

    def test_draws_spin_jump_in_the_air(self):
        # 스핀 점프는 21.25초에 시작한다: 0.3초 뒤(1회째 재생의 60% 지점)에는 x = 690에서
        # 160 × 4 × 0.6 × 0.4 = 153.6px 떠 있으므로 3번 프레임(116x108)의 중심 y는 150 + 153.6 + 54 = 357.6이다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 21.55])
        *frame_and_flip, x, y, draw_w, draw_h = fakes['load_image'].return_value.clip_composite_draw.call_args.args
        self.assertEqual((*frame_and_flip, draw_w, draw_h), (105, 292, 29, 27, 0, '', 116, 108))
        self.assertAlmostEqual(x, 690)
        self.assertAlmostEqual(y, 357.6)

    def test_loads_hangul_font_bundled_with_pico2d(self):
        fakes = run_main([[ESC_EVENT]])
        fakes['load_font'].assert_called_once_with(viewer.font_path(), 20)

    def test_draws_status_text_at_top_left_every_frame(self):
        # 2.6초: 대기 3회째 재생 중 5번째 프레임, 5.96초: 5회 재생(5.5초)을 마치고 0.46초째 정지 중
        fakes = run_main([[], [], [ESC_EVENT]], times=[0.0, 2.6, 5.96])
        font = fakes['load_font'].return_value
        self.assertEqual(font.draw.call_args_list, [
            mock.call(10, 580, '[1/10] 대기 | 반복 3/5 | 프레임 5/11 | 재생 중', (0, 0, 0)),
            mock.call(10, 580, '[1/10] 대기 | 반복 5/5 | 프레임 11/11 | 정지 0.4/1.0초', (0, 0, 0)),
        ])

    def test_closes_canvas_when_font_cannot_be_loaded(self):
        with mock.patch.multiple(viewer, **fake_pico2d()) as fakes:
            fakes['get_events'].side_effect = [[ESC_EVENT]]
            fakes['load_font'].side_effect = IOError
            with self.assertRaises(IOError):
                viewer.main()
        fakes['close_canvas'].assert_called_once_with()

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


class FontTest(unittest.TestCase):
    def test_font_is_hangul_font_in_pico2d_data_folder(self):
        path = viewer.font_path()
        self.assertEqual(path, os.path.join(os.environ['PICO2D_DATA_PATH'], 'ConsolaMalgun.ttf'))
        self.assertTrue(os.path.isfile(path))


class DrawFrameTest(unittest.TestCase):
    def test_draws_frame_four_times_larger_with_feet_at_given_height(self):
        # 가로 중심은 x, 아래쪽 끝(발)은 foot_y: 그리기 함수에는 중심 y = foot_y + 그린 높이 / 2를 넘긴다.
        sheet = mock.Mock()
        viewer.draw_frame(sheet, (1, 447, 29, 39), 600, 150, viewer.RIGHT)
        sheet.clip_composite_draw.assert_called_once_with(1, 447, 29, 39, 0, '', 600, 228, 116, 156)

    def test_flips_frame_horizontally_when_facing_left(self):
        # 시트의 소닉은 오른쪽을 보므로 왼쪽을 볼 때는 좌우를 뒤집어('h') 그린다.
        sheet = mock.Mock()
        viewer.draw_frame(sheet, (8, 408, 26, 37), 1052, 150, viewer.LEFT)
        sheet.clip_composite_draw.assert_called_once_with(8, 408, 26, 37, 0, 'h', 1052, 224, 104, 148)

    def test_feet_rest_on_ground_line_for_every_frame(self):
        # 프레임 높이(26~45px)가 달라도 그림의 아래쪽 끝은 항상 발 기준선 y = 150에 놓인다.
        for motion in viewer.MOTIONS:
            for frame in motion.frames:
                sheet = mock.Mock()
                viewer.draw_frame(sheet, frame, 600, viewer.GROUND_Y, viewer.RIGHT)
                *_, center_y, _, draw_h = sheet.clip_composite_draw.call_args.args
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


class CycleTest(unittest.TestCase):
    def test_switches_to_next_motion_after_pause(self):
        # 정지 0.99초째에서 0.02초가 지나면 다음 동작을 처음부터 0.01초째 재생한다. (10번 뒤에는 1번)
        for index in range(len(viewer.MOTIONS)):
            with self.subTest(motion=viewer.MOTIONS[index].name):
                pausing = viewer.ViewerState(motion_index=index, phase=viewer.PAUSE, elapsed=0.99)
                state = viewer.update(pausing, 0.02)
                self.assertEqual((state.motion_index, state.phase), ((index + 1) % 10, viewer.PLAY))
                self.assertAlmostEqual(state.elapsed, 0.01)
                self.assertEqual(viewer.current_frame_index(state), 0)

    def test_one_cycle_takes_44_75_seconds(self):
        # PRD.md 5.3절: 재생 34.75초 + 정지 1초 x 10 = 44.75초
        total = sum(viewer.play_time(motion) + viewer.PAUSE_TIME for motion in viewer.MOTIONS)
        self.assertAlmostEqual(total, 44.75)
        self.assertIn('**44.75초**', read_prd())

    def test_plays_all_motions_in_order_and_returns_to_first(self):
        # 0.01초 간격으로 44.75초 + 0.5초를 흘려보내면 1번 -> 10번 동작을 차례로 재생한 뒤 1번으로 돌아온다.
        history = simulate(44.75 + 0.5)
        self.assertEqual(collapse([s.motion_index for _, s in history]), list(range(10)) + [0])
        switches = [t for (t, s), (_, before) in zip(history[1:], history) if s.motion_index != before.motion_index]
        self.assertAlmostEqual(switches[-1], 44.75, delta=0.0101)  # 10번 -> 1번으로 돌아오는 시각

    def test_each_motion_starts_when_previous_pause_ends(self):
        # 동작 k의 시작 시각 = 앞선 동작들의 (5회 재생 시간 + 정지 1초)의 합
        history = simulate(44.75)
        expected_start = 0.0
        for index, motion in enumerate(viewer.MOTIONS):
            with self.subTest(motion=motion.name):
                start = next(t for t, s in history if s.motion_index == index) - 0.01
                self.assertAlmostEqual(start, expected_start, delta=0.0101)
            expected_start += viewer.play_time(motion) + viewer.PAUSE_TIME


class HudTest(unittest.TestCase):
    def check(self, cases):
        for state, expected in cases:
            with self.subTest(state=state):
                self.assertEqual(viewer.hud_text(state), expected)

    def test_shows_motion_repeat_and_frame_while_playing(self):
        # 걷기 2.6초째: 1회 1초라 3회째, 12fps라 31번째 프레임 = 3회째의 8번째 프레임
        self.check([
            (viewer.ViewerState(), '[1/10] 대기 | 반복 1/5 | 프레임 1/11 | 재생 중'),
            (viewer.ViewerState(motion_index=1, elapsed=2.6), '[2/10] 걷기 | 반복 3/5 | 프레임 8/12 | 재생 중'),
            (viewer.ViewerState(motion_index=9, elapsed=4.99), '[10/10] 포즈 | 반복 5/5 | 프레임 4/4 | 재생 중'),
        ])

    def test_shows_pause_elapsed_time_while_paused(self):
        # 정지 시간은 0.1초 단위로 버림해 정지가 끝나기 전에 1.0초로 보이지 않게 한다.
        paused = viewer.ViewerState(motion_index=1, phase=viewer.PAUSE)
        self.check([
            (paused, '[2/10] 걷기 | 반복 5/5 | 프레임 12/12 | 정지 0.0/1.0초'),
            (dataclasses.replace(paused, elapsed=0.46), '[2/10] 걷기 | 반복 5/5 | 프레임 12/12 | 정지 0.4/1.0초'),
            (dataclasses.replace(paused, elapsed=0.96), '[2/10] 걷기 | 반복 5/5 | 프레임 12/12 | 정지 0.9/1.0초'),
        ])

    def test_repeat_number_counts_one_to_five_once_per_loop(self):
        # k번째 반복은 (k - 1) x 1회 재생 시간에 시작하고, 정지 중에는 5/5로 남는다.
        for index, motion in enumerate(viewer.MOTIONS):
            with self.subTest(motion=motion.name):
                history = simulate(viewer.play_time(motion) + 0.5, viewer.ViewerState(motion_index=index))
                repeats = [viewer.repeat_number(s) for _, s in history]
                self.assertEqual(collapse(repeats), [1, 2, 3, 4, 5])
                for k in range(2, 6):
                    start = next(t for t, s in history if viewer.repeat_number(s) == k)
                    self.assertAlmostEqual(start, (k - 1) * viewer.loop_time(motion), delta=0.0101)


class MovementTest(unittest.TestCase):
    def test_speeds_match_prd_section_6_1(self):
        # 이동 거리 = 속도 x 5회 재생 시간
        table = prd_movement_table()
        self.assertEqual(len(table), 10)
        for motion in viewer.MOTIONS:
            with self.subTest(motion=motion.name):
                kind, speed, distance, _ = table[motion.name]
                self.assertEqual(motion.speed, speed)
                self.assertEqual(kind == '이동', speed > 0)
                self.assertAlmostEqual(motion.speed * viewer.play_time(motion), distance)

    def test_seven_motions_move_and_three_stay_at_center(self):
        moving = [motion.name for motion in viewer.MOTIONS if motion.speed > 0]
        self.assertEqual(moving, ['걷기', '발차기', '스핀 점프', '질주', '최고속 질주', '공중 회전', '정면 달리기'])

    def test_every_motion_starts_at_center_facing_right(self):
        # 앞 동작이 왼쪽을 보며 x = 900에서 멈췄어도 다음 동작은 x = 600에서 오른쪽을 보고 시작한다.
        self.assertEqual((viewer.ViewerState().x, viewer.ViewerState().direction), (600, 1))
        for index in range(len(viewer.MOTIONS)):
            next_motion = viewer.MOTIONS[(index + 1) % 10]
            with self.subTest(motion=next_motion.name):
                pausing = viewer.ViewerState(motion_index=index, phase=viewer.PAUSE, elapsed=0.99,
                                             x=900.0, direction=-1)
                state = viewer.update(pausing, 0.02)  # 다음 동작을 0.01초 재생한 상태
                self.assertEqual(state.direction, 1)
                self.assertAlmostEqual(state.x, 600 + next_motion.speed * 0.01)

    def test_moves_at_motion_speed_while_playing(self):
        # 걷기(150px/초)를 0.01초 간격으로 2초 재생하면 x = 600 -> 900
        history = simulate(2.0, viewer.ViewerState(motion_index=1))
        self.assertAlmostEqual(history[-1][1].x, 900.0)

    def test_keeps_moving_while_one_frame_is_shown(self):
        # 걷기(12fps)의 첫 프레임이 보이는 0.08초 동안에도 x는 0.01초마다 1.5px씩 늘어난다.
        history = simulate(0.08, viewer.ViewerState(motion_index=1))
        xs = [s.x for _, s in history]
        self.assertEqual({viewer.current_frame_index(s) for _, s in history}, {0})
        self.assertTrue(all(after > before for before, after in zip(xs, xs[1:])))
        self.assertAlmostEqual(xs[-1], 600 + 150 * 0.08)

    def test_center_motions_stay_at_center(self):
        for index, motion in enumerate(viewer.MOTIONS):
            if motion.speed == 0:
                with self.subTest(motion=motion.name):
                    history = simulate(viewer.play_time(motion) + 0.5, viewer.ViewerState(motion_index=index))
                    self.assertEqual({(s.x, s.direction) for _, s in history}, {(600, 1)})

    def test_stays_still_during_pause(self):
        # 발차기(100px/초)는 3초 재생하는 동안 300px 움직여 x = 900에서 멈추고, 정지 중에는 그 자리에 있다.
        history = simulate(3.0 + 0.95, viewer.ViewerState(motion_index=2))
        paused = {(s.x, s.direction) for _, s in history if s.phase == viewer.PAUSE}
        self.assertEqual(len(paused), 1)
        x, direction = paused.pop()
        self.assertAlmostEqual(x, 900.0)
        self.assertEqual(direction, 1)

    def test_long_time_step_moves_only_until_play_ends(self):
        # 발차기 2.9초째(x = 890)에서 0.5초가 지나면 재생이 끝나는 0.1초 동안만 움직이고 정지한다.
        state = viewer.update(viewer.ViewerState(motion_index=2, elapsed=2.9, x=890.0), 0.5)
        self.assertEqual(state.phase, viewer.PAUSE)
        self.assertAlmostEqual(state.x, 900.0)
        self.assertAlmostEqual(state.elapsed, 0.4)


class BoundaryTest(unittest.TestCase):
    def test_x_limits_match_prd_section_6_6(self):
        # 이동 범위 = 가장 넓은 프레임을 그린 폭의 절반 ~ 1200 - 그 절반
        table = prd_expected_moves()
        moving = [motion for motion in viewer.MOTIONS if motion.speed > 0]
        self.assertEqual(sorted(table), sorted(motion.name for motion in moving))
        for motion in moving:
            with self.subTest(motion=motion.name):
                low, high, *_ = table[motion.name]
                self.assertEqual(viewer.x_limits(motion), (low, high))

    def test_every_frame_stays_on_screen_inside_limits(self):
        # 범위 양 끝에 어떤 프레임을 그려도 그림이 화면(0 ~ 1200) 밖으로 나가지 않는다.
        for motion in viewer.MOTIONS:
            low, high = viewer.x_limits(motion)
            for _, _, width, _ in motion.frames:
                half = width * 4 / 2
                self.assertGreaterEqual(low - half, 0, motion.name)
                self.assertLessEqual(high + half, 1200, motion.name)

    def test_reflect_returns_overshoot_and_turns_around(self):
        right, left = viewer.RIGHT, viewer.LEFT
        cases = {
            (600, right): (600, right),  # 범위 안: 그대로
            (1126, right): (1126, right),  # 경계에 딱 닿은 것은 넘은 것이 아니다.
            (1130, right): (1122, left),  # 오른쪽 끝을 4px 넘음: 4px 되돌아오고 왼쪽을 본다.
            (70, left): (78, right),  # 왼쪽 끝을 4px 넘음: 4px 되돌아오고 오른쪽을 본다.
            (2200, right): (96, right),  # 오른쪽 끝에서 52까지 되돌아오다 왼쪽 끝을 22px 넘음: 두 번 반사
        }
        for (x, direction), expected in cases.items():
            with self.subTest(x=x, direction=direction):
                self.assertEqual(viewer.reflect(x, direction, 74, 1126), expected)

    def test_turns_back_at_right_edge(self):
        # 걷기 x = 1050에서 1초 동안 150px 가면 1200: 오른쪽 끝 1126을 74px 넘어 1052로 돌아오고 왼쪽을 본다.
        state = viewer.update(viewer.ViewerState(motion_index=1, elapsed=3.0, x=1050.0), 1.0)
        self.assertEqual((state.x, state.direction), (1052, viewer.LEFT))

    def test_turns_back_at_left_edge(self):
        # 왼쪽을 보는 걷기 x = 100에서 0.5초 동안 75px 가면 25: 왼쪽 끝 74를 49px 넘어 123으로 돌아온다.
        start = viewer.ViewerState(motion_index=1, elapsed=1.0, x=100.0, direction=viewer.LEFT)
        state = viewer.update(start, 0.5)
        self.assertEqual((state.x, state.direction), (123, viewer.RIGHT))

    def test_walk_turns_once_and_stays_inside_limits(self):
        # 걷기 5회 재생(5초): x는 74 ~ 1126 안에 있고, 3.51초쯤 오른쪽 끝에서 한 번만 돌아선다.
        history = simulate(5.0, viewer.ViewerState(motion_index=1))
        self.assertTrue(all(74 <= s.x <= 1126 for _, s in history))
        self.assertEqual(collapse([s.direction for _, s in history]), [viewer.RIGHT, viewer.LEFT])
        turned_at = next(t for t, s in history if s.direction == viewer.LEFT)
        self.assertAlmostEqual(turned_at, 3.51, delta=0.0101)


class JumpTest(unittest.TestCase):
    def test_jump_heights_match_prd_section_6_1(self):
        table = prd_movement_table()
        for motion in viewer.MOTIONS:
            with self.subTest(motion=motion.name):
                self.assertEqual(motion.jump_height, table[motion.name][3])

    def test_only_spin_jump_and_air_spin_jump(self):
        jumping = [(motion.name, motion.jump_height) for motion in viewer.MOTIONS if motion.jump_height > 0]
        self.assertEqual(jumping, [('스핀 점프', 160), ('공중 회전', 200)])

    def test_jump_draws_parabola_in_every_loop(self):
        # 스핀 점프(1회 0.5초, 높이 160): 회차마다 시작할 때 0, 1/4 지점에서 120, 가운데에서 160, 3/4 지점에서 120
        for loop in range(5):
            with self.subTest(loop=loop + 1):
                for fraction, height in ((0.0, 0), (0.25, 120), (0.5, 160), (0.75, 120)):
                    state = viewer.ViewerState(motion_index=4, elapsed=(loop + fraction) * 0.5)
                    self.assertAlmostEqual(viewer.jump_offset(state), height, places=6)

    def test_jumps_five_times_while_playing(self):
        # 0.01초 간격으로 2.5초 재생하면 꼭대기(160)에 다섯 번 오른다.
        history = simulate(2.5, viewer.ViewerState(motion_index=4))
        heights = [viewer.jump_offset(s) for _, s in history]
        peaks = [h for before, h, after in zip(heights, heights[1:], heights[2:]) if before < h >= after]
        self.assertEqual(len(peaks), 5)
        for peak in peaks:
            self.assertAlmostEqual(peak, 160, delta=0.01)

    def test_lands_when_play_ends_and_stays_on_ground_while_paused(self):
        # 5회째가 끝나는 순간 높이가 0이 되고, 1초 정지 동안 발은 기준선에 있다.
        self.assertAlmostEqual(viewer.jump_offset(viewer.ViewerState(motion_index=4, elapsed=2.5 - 1e-9)), 0,
                               places=5)
        history = simulate(2.5 + 0.95, viewer.ViewerState(motion_index=4))
        paused = [s for _, s in history if s.phase == viewer.PAUSE]
        self.assertGreater(len(paused), 90)
        self.assertEqual({viewer.jump_offset(s) for s in paused}, {0})

    def test_motions_without_jump_height_stay_on_ground(self):
        for index, motion in enumerate(viewer.MOTIONS):
            if motion.jump_height == 0:
                with self.subTest(motion=motion.name):
                    history = simulate(viewer.play_time(motion), viewer.ViewerState(motion_index=index))
                    self.assertEqual({viewer.jump_offset(s) for _, s in history}, {0})

    def test_top_of_highest_jump_stays_below_status_text(self):
        # 가장 높이 뛰었을 때 그림 위쪽 끝: 스핀 점프 150 + 160 + 27×4 = 418, 공중 회전 150 + 200 + 45×4 = 530
        # 상태 표시가 있는 화면 위쪽 40px(y 560 이상)과 겹치지 않는다. (PRD 6.4절)
        tops = {motion.name: viewer.GROUND_Y + motion.jump_height + max(h for *_, h in motion.frames) * 4
                for motion in viewer.MOTIONS if motion.jump_height > 0}
        self.assertEqual(tops, {'스핀 점프': 418, '공중 회전': 530})
        self.assertTrue(all(top <= 600 - 40 for top in tops.values()))


class TimeSimulationTest(unittest.TestCase):
    # PRD.md 9절 시간 모의 실행: update()를 0.01초 간격으로 호출해 1회 순환(44.75초)을 흘려보내고 동작마다 결과를 확인한다.
    def test_plays_each_motion_five_times_then_pauses_one_second(self):
        # 1번 -> 10번 동작을 차례로 5회씩 재생하고, 재생이 끝나면 1초 동안 정지한 뒤 다음 동작으로 넘어간다.
        runs = motion_runs()
        self.assertEqual([run[0][1].motion_index for run in runs], list(range(10)))
        for motion, run in zip(viewer.MOTIONS, runs):
            with self.subTest(motion=motion.name):
                playing = [s for _, s in run if s.phase == viewer.PLAY]
                paused = [(t, s) for t, s in run if s.phase == viewer.PAUSE]
                self.assertEqual(collapse([viewer.repeat_number(s) for s in playing]), [1, 2, 3, 4, 5])
                self.assertAlmostEqual(paused[0][0], viewer.play_time(motion), delta=0.0101)
                self.assertLessEqual(abs(len(paused) - 100), 1)  # 0.01초 간격으로 1초 = 100번

    def test_moving_motions_match_prd_section_6_6(self):
        # 이동 동작 7종: x는 이동 범위 안에 있고, 반전 시각(±0.01초)·끝 위치(±1px)·끝 방향이 표와 같다.
        table = prd_expected_moves()
        for motion, run in zip(viewer.MOTIONS, motion_runs()):
            if motion.speed == 0:
                continue
            with self.subTest(motion=motion.name):
                low, high, turn, end_x, end_direction = table[motion.name]
                self.assertTrue(all(low <= s.x <= high for _, s in run))
                turns = [t for (t, s), (_, before) in zip(run[1:], run) if s.direction != before.direction]
                if turn is None:
                    self.assertEqual(turns, [])
                else:
                    self.assertEqual(len(turns), 1)
                    self.assertAlmostEqual(turns[0], turn, delta=0.0101)
                _, last = run[-1]  # 정지 단계의 마지막 상태
                self.assertAlmostEqual(last.x, end_x, delta=1)
                self.assertEqual(last.direction, end_direction)

    def test_moves_while_each_frame_is_shown(self):
        # 이동 동작은 프레임 하나가 보이는 동안에도 갱신할 때마다 x가 바뀌고, 중앙 동작은 처음부터 끝까지 x = 600이다.
        for motion, run in zip(viewer.MOTIONS, motion_runs()):
            with self.subTest(motion=motion.name):
                if motion.speed == 0:
                    self.assertEqual({(s.x, s.direction) for _, s in run}, {(600, viewer.RIGHT)})
                    continue
                playing = [s for _, s in run if s.phase == viewer.PLAY]
                for _, shown in itertools.groupby(playing, key=viewer.current_frame_index):
                    xs = [s.x for s in shown]
                    self.assertGreater(len(xs), 1)
                    self.assertTrue(all(before != after for before, after in zip(xs, xs[1:])))

    def test_pause_holds_last_frame_and_position_on_ground(self):
        # 1초 정지 동안 마지막 프레임을 같은 위치·방향으로 보여 주고, 발은 기준선에 있다(점프 높이 0).
        for motion, run in zip(viewer.MOTIONS, motion_runs()):
            with self.subTest(motion=motion.name):
                paused = [s for _, s in run if s.phase == viewer.PAUSE]
                shown = {(viewer.current_frame_index(s), s.x, s.direction, viewer.jump_offset(s)) for s in paused}
                self.assertEqual(len(shown), 1)
                frame, _, _, jump = shown.pop()
                self.assertEqual((frame, jump), (len(motion.frames) - 1, 0))

    def test_jumping_motions_rise_and_land_in_every_loop(self):
        # 스핀 점프와 공중 회전은 회차마다 가운데에서 꼭대기(H)에 오르고, 회차가 바뀌는 순간 기준선(0)에 내려온다.
        for motion, run in zip(viewer.MOTIONS, motion_runs()):
            if motion.jump_height == 0:
                continue
            with self.subTest(motion=motion.name):
                heights = [viewer.jump_offset(s) for _, s in run if s.phase == viewer.PLAY]
                neighbours = list(zip(heights, heights[1:], heights[2:]))
                tops = [h for before, h, after in neighbours if before < h >= after]
                landings = [h for before, h, after in neighbours if before > h <= after]
                self.assertEqual(len(tops), 5)
                self.assertEqual(len(landings), 4)  # 1 ~ 4회째가 끝나는 순간 (5회째가 끝나면 정지 단계로 넘어간다)
                for top in tops:
                    self.assertAlmostEqual(top, motion.jump_height, delta=0.01)
                for landing in landings:
                    self.assertAlmostEqual(landing, 0, delta=0.01)


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
