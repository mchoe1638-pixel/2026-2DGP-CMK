# sonic_animation_viewer.py 테스트
# LEC09 폴더에서 `python -m unittest -v`로 실행한다.
# pico2d 함수는 가짜(mock)로 바꿔 창을 열지 않고 확인한다. (RealWindowTest만 실제 창을 잠깐 열어 확인한다)
import ctypes
import dataclasses
import itertools
import os
import re
import unittest
from types import SimpleNamespace
from unittest import mock

import pico2d.pico2d as pico2d_core  # 실제 창 테스트: open_canvas()가 만든 창(window)과 렌더러(renderer)를 쓴다.
import sdl2

import sonic_animation_viewer as viewer

try:
    from PIL import Image as PILImage, ImageChops
except ImportError:  # Pillow가 없으면 픽셀 검사 테스트만 건너뛴다.
    PILImage = ImageChops = None

PRD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'PRD.md')
SHEET_SIZE = (399, 525)  # sonic-sprite.png 크기 (PRD.md 2절)
STATUS_AREA_HEIGHT = 40  # 상태 표시가 있는 화면 위쪽 띠의 높이(px) (PRD.md 6.4절)
CYCLE_TIME = 44.75  # 동작 10종을 한 바퀴 도는 시간(초): 재생 34.75초 + 정지 1초 x 10 (PRD.md 5.3절)

# 재생 순서대로 등록할 동작과 프레임 수 (PRD.md 5.3절: 10종 76프레임)
EXPECTED_FRAME_COUNTS = {'대기': 11, '걷기': 12, '발차기': 6, '회전 진입': 9, '스핀 점프': 6,
                         '질주': 6, '최고속 질주': 6, '공중 회전': 8, '정면 달리기': 8, '포즈': 4}

# 시간 모의 실행: update()를 SIM_DT초 간격으로 호출하므로, 무슨 일이 일어난 시각은 한 간격만큼 어긋나 보일 수 있다.
SIM_DT = 0.01
TIME_TOLERANCE = SIM_DT + 0.0001  # 한 간격 + 부동소수점 오차
Sample = tuple[float, viewer.ViewerState]  # 모의 실행에서 모은 (시각, 그 시각의 상태)

# 실제 창 테스트
FRAMES_BEFORE_ESCAPE = 3  # 화면을 이만큼 내보낸 뒤 ESC 키를 누른다.
FRAME_LIMIT = 300  # ESC 키로 끝나지 않아도 테스트가 멈추지 않게, 이만큼 내보내면 오류를 내 루프를 끊는다.


def read_prd() -> str:
    with open(PRD_PATH, encoding='utf-8') as prd:
        return prd.read()


def prd_frames() -> list[tuple[str, list[viewer.Frame]]]:
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


def prd_motion_table() -> dict[str, tuple[int, int, float, float]]:
    # PRD.md 5.3절 표에서 {동작 이름: (프레임 수, fps, 1회 재생 시간, 5회 재생 시간)}을 읽는다.
    rows = re.findall(r'^\| \d+ \| ([^|]+?) \| \d+ \| (\d+) \| (\d+) \| ([\d.]+) \| ([\d.]+) \|',
                      read_prd(), re.MULTILINE)
    return {name: (int(count), int(fps), float(loop), float(play))
            for name, count, fps, loop, play in rows}


def prd_movement_table() -> dict[str, tuple[str, int, int, int]]:
    # PRD.md 6.1절 표에서 {동작 이름: (분류, 속도, 5회 재생 중 이동 거리, 점프 높이)}를 읽는다.
    rows = re.findall(r'^\| \d+ \| ([^|]+?) \| (중앙|이동) \| (\d+) \| (\d+) \| (\d+) \|$',
                      read_prd(), re.MULTILINE)
    return {name: (kind, int(speed), int(distance), int(jump))
            for name, kind, speed, distance, jump in rows}


def prd_expected_moves() -> dict[str, tuple[int, int, float | None, int, int]]:
    # PRD.md 6.6절 표에서 {동작 이름: (이동 범위 왼쪽 끝, 오른쪽 끝, 반전 시각 또는 None, 끝 위치, 끝 방향)}을 읽는다.
    rows = re.findall(r'^\| ([^|]+?) \| (\d+) ~ (\d+) \| (?:([\d.]+)초 \([^)]*\)|없음) \| (\d+) \| (왼쪽|오른쪽) \|$',
                      read_prd(), re.MULTILINE)
    return {name: (int(low), int(high), float(turn) if turn else None, int(end),
                   viewer.LEFT if facing == '왼쪽' else viewer.RIGHT)
            for name, low, high, turn, end, facing in rows}


def simulate(seconds: float, state: viewer.ViewerState | None = None) -> list[Sample]:
    # update()를 SIM_DT초 간격으로 호출해 seconds초를 흘려보내고, 호출할 때마다 (시각, 새 상태)를 모은다.
    state = state or viewer.ViewerState()
    history = []
    for step in range(1, round(seconds / SIM_DT) + 1):
        state = viewer.update(state, SIM_DT)
        history.append((step * SIM_DT, state))
    return history


def collapse(values: list) -> list:
    # 연달아 같은 값은 하나로 줄인다. (화면에 보인 프레임 번호의 순서를 보려고 쓴다)
    return [value for i, value in enumerate(values) if i == 0 or values[i - 1] != value]


def motion_runs() -> list[list[Sample]]:
    # 처음부터 0.01초 간격으로 1회 순환(44.75초)을 흘려보내며 동작마다 [(그 동작이 시작된 뒤 지난 시각, 상태), ...]를 모은다.
    # 동작이 시작되는 시각은 앞선 동작들의 (5회 재생 시간 + 정지 1초)의 합이다.
    by_motion = itertools.groupby(simulate(CYCLE_TIME), key=lambda sample: sample[1].motion_index)
    runs, start = [], 0.0
    for motion, (_, run) in zip(viewer.MOTIONS, by_motion):
        runs.append([(t - start, state) for t, state in run])
        start += viewer.play_time(motion) + viewer.PAUSE_TIME
    return runs


def key_event(key: int, event_type: int | None = None) -> SimpleNamespace:
    # pico2d의 Event처럼 type과 key를 가진 키 입력 이벤트를 만든다.
    return SimpleNamespace(type=event_type or viewer.SDL_KEYDOWN, key=key)


QUIT_EVENT = SimpleNamespace(type=viewer.SDL_QUIT, key=None)
ESC_EVENT = key_event(viewer.SDLK_ESCAPE)


PICO2D_FUNCTIONS = ('open_canvas', 'close_canvas', 'clear_canvas', 'update_canvas', 'delay',
                    'get_events', 'get_time', 'load_image', 'load_font')


def fake_pico2d() -> dict[str, object]:
    # main()이 쓰는 pico2d 함수를 모두 가짜로 바꾸는 mock.patch.multiple 인자
    return {name: mock.DEFAULT for name in PICO2D_FUNCTIONS}


def run_main(events_per_call: list[list[SimpleNamespace]],
             times: list[float] | None = None) -> dict[str, mock.MagicMock]:
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


def draw_calls(fakes: dict[str, mock.MagicMock]) -> list:
    # run_main()이 돌려준 가짜 함수들에서, 불러온 시트로 프레임을 그린 호출을 차례로 꺼낸다.
    return fakes['load_image'].return_value.clip_composite_draw.call_args_list


def real_window_size() -> tuple[int, int]:
    # open_canvas()가 실제로 연 창의 크기를 SDL에 직접 묻는다.
    width, height = ctypes.c_int(), ctypes.c_int()
    sdl2.SDL_GetWindowSize(pico2d_core.window, ctypes.byref(width), ctypes.byref(height))
    return width.value, height.value


def read_screen() -> bytes:
    # 지금까지 그린 화면(아직 내보내기 전)을 맨 위 줄부터 픽셀마다 RGBA 4바이트로 읽는다.
    width, height = viewer.CANVAS_W, viewer.CANVAS_H
    pixels = (ctypes.c_ubyte * (width * height * 4))()
    if sdl2.SDL_RenderReadPixels(pico2d_core.renderer, None, sdl2.SDL_PIXELFORMAT_ABGR8888, pixels, width * 4):
        raise RuntimeError(sdl2.SDL_GetError())
    return bytes(pixels)


def push_escape_key() -> None:
    # 사용자가 ESC 키를 누른 것과 같은 키 입력 이벤트를 SDL 이벤트 큐에 넣는다. pico2d의 get_events()가 이 큐에서 읽는다.
    event = sdl2.SDL_Event()
    event.type = sdl2.SDL_KEYDOWN
    event.key.keysym.sym = sdl2.SDLK_ESCAPE
    if sdl2.SDL_PushEvent(ctypes.byref(event)) != 1:
        raise RuntimeError(sdl2.SDL_GetError())


def run_real_main() -> SimpleNamespace:
    # 가짜 함수 없이 실제 pico2d 창을 열어 main()을 실행하고, 그동안 본 것을 모아 돌려준다.
    # 화면을 FRAMES_BEFORE_ESCAPE번 내보낸 뒤 ESC 키를 누른다.
    # 첫 화면은 지운 직후(배경)와 내보내기 직전(그린 뒤)에 읽어 두어, 둘을 비교해 그린 위치를 찾을 수 있게 한다.
    seen = SimpleNamespace(presented=0, window_size=None, background=None, first_screen=None)
    real_clear_canvas, real_update_canvas = viewer.clear_canvas, viewer.update_canvas

    def clear_canvas() -> None:
        real_clear_canvas()
        if seen.presented == 0:
            seen.background = read_screen()

    def update_canvas() -> None:
        if seen.presented == 0:
            seen.window_size, seen.first_screen = real_window_size(), read_screen()
        real_update_canvas()
        seen.presented += 1
        if seen.presented == FRAMES_BEFORE_ESCAPE:
            push_escape_key()
        if seen.presented >= FRAME_LIMIT:
            raise RuntimeError('ESC 키를 눌렀는데도 메인 루프가 끝나지 않았다.')

    with mock.patch.multiple(viewer, clear_canvas=clear_canvas, update_canvas=update_canvas), \
            mock.patch.object(viewer, 'close_canvas', wraps=viewer.close_canvas) as close_canvas:
        viewer.main()
    seen.close_calls = close_canvas.call_count
    seen.video_still_on = bool(sdl2.SDL_WasInit(sdl2.SDL_INIT_VIDEO))  # 창을 닫고 SDL을 끝냈으면 False
    return seen


def drawn_box(seen: SimpleNamespace, top: int, bottom: int) -> tuple[int, int, int, int] | None:
    # 첫 화면의 top ~ bottom 행에 그려진 것을 모두 감싸는 상자 (왼쪽, 위, 오른쪽, 아래)를 화면 좌표(맨 위 줄이 0행)로 돌려준다.
    # 지운 직후의 화면(배경)과 색이 다른 픽셀을 그려진 것으로 본다. 그려진 것이 없으면 None이다.
    size = (viewer.CANVAS_W, viewer.CANVAS_H)
    background, screen = (PILImage.frombuffer('RGBA', size, pixels, 'raw', 'RGBA', 0, 1).convert('RGB')
                          for pixels in (seen.background, seen.first_screen))
    box = ImageChops.difference(background, screen).crop((0, top, size[0], bottom)).getbbox()
    if box is None:
        return None
    left, upper, right, lower = box
    return left, upper + top, right, lower + top


class HandleEventsTest(unittest.TestCase):
    def check(self, events: list[SimpleNamespace], expected: bool) -> None:
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

    def test_holds_last_frame_after_five_loops(self):
        # 대기 5회 재생은 5.5초: 5.35초에는 9번 프레임, 5.6초와 6.3초에는 마지막(10번) 프레임에 머문다.
        fakes = run_main([[], [], [], [ESC_EVENT]], times=[0.0, 5.35, 5.6, 6.3])
        self.assertEqual(draw_calls(fakes), [
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
        idle_call, walk_call = draw_calls(fakes)
        self.assertEqual(idle_call, mock.call(302, 448, 29, 26, 0, '', 600, 202, 116, 104))
        *frame_and_flip, x, y, draw_w, draw_h = walk_call.args
        self.assertEqual((*frame_and_flip, y, draw_w, draw_h), (8, 408, 26, 37, 0, '', 224, 104, 148))
        self.assertAlmostEqual(x, 607.5)

    def test_draws_frame_for_time_elapsed_since_start(self):
        # 대기(10fps)를 시작 시각 10.0초 기준으로 0.05초, 0.35초, 1.15초 뒤에 그리면 0, 3, 0번 프레임이다.
        # 가로 중심은 x = 600이고, 발이 y = 150에 오도록 0번 프레임(116x156)의 중심 y는 150 + 156 / 2 = 228이다.
        fakes = run_main([[], [], [], [ESC_EVENT]], times=[10.0, 10.05, 10.35, 11.15])
        self.assertEqual(draw_calls(fakes), [
            mock.call(1, 447, 29, 39, 0, '', 600, 228, 116, 156),
            mock.call(86, 447, 30, 38, 0, '', 600, 226, 120, 152),
            mock.call(1, 447, 29, 39, 0, '', 600, 228, 116, 156),
        ])

    def test_draws_walking_sonic_flipped_after_turning_back(self):
        # 걷기는 4초 동안 600px을 가려다 오른쪽 끝(1126)에서 74px 되돌아온다: 10.5초에는 x = 1052에서 왼쪽을 본다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 10.5])
        self.assertEqual(draw_calls(fakes), [mock.call(8, 408, 26, 37, 0, 'h', 1052, 224, 104, 148)])

    def test_draws_spin_jump_in_the_air(self):
        # 스핀 점프는 21.25초에 시작한다: 0.3초 뒤(1회째 재생의 60% 지점)에는 x = 690에서
        # 160 × 4 × 0.6 × 0.4 = 153.6px 떠 있으므로 3번 프레임(116x108)의 중심 y는 150 + 153.6 + 54 = 357.6이다.
        fakes = run_main([[], [ESC_EVENT]], times=[0.0, 21.55])
        *frame_and_flip, x, y, draw_w, draw_h = draw_calls(fakes)[-1].args
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

    def test_closes_canvas_when_sheet_or_font_cannot_be_loaded(self):
        # 시트나 글꼴을 읽다가 오류가 나도 창을 닫고, 오류는 그대로 알린다.
        for loader in ('load_image', 'load_font'):
            with self.subTest(loader=loader), mock.patch.multiple(viewer, **fake_pico2d()) as fakes:
                fakes['get_events'].side_effect = [[ESC_EVENT]]
                fakes[loader].side_effect = IOError
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
        # 첫 동작을 처음부터 재생하고, 소닉은 화면 가운데(x = 600)에서 오른쪽을 보고 시작한다.
        state = viewer.ViewerState()
        self.assertEqual((state.motion_index, state.phase, state.elapsed, state.x, state.direction),
                         (0, viewer.PLAY, 0.0, 600, viewer.RIGHT))

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

    def test_long_time_step_can_pass_whole_pause(self):
        # 한 번에 6.8초가 지나면 대기 재생 5.5초와 정지 1초를 모두 마치고 새 재생 단계 0.3초째다.
        state = viewer.update(viewer.ViewerState(), 6.8)
        self.assertEqual(state.phase, viewer.PLAY)
        self.assertAlmostEqual(state.elapsed, 0.3)


class CycleTest(unittest.TestCase):
    def test_switches_to_next_motion_after_pause(self):
        # 정지 0.99초째에서 0.02초가 지나면 다음 동작을 처음부터 0.01초째 재생한다. (10번 뒤에는 1번)
        # 앞 동작이 왼쪽을 보며 x = 900에서 멈췄어도 다음 동작은 x = 600에서 오른쪽을 보고 출발한다.
        for index in range(len(viewer.MOTIONS)):
            next_motion = viewer.MOTIONS[(index + 1) % 10]
            with self.subTest(motion=next_motion.name):
                pausing = viewer.ViewerState(motion_index=index, phase=viewer.PAUSE, elapsed=0.99,
                                             x=900.0, direction=viewer.LEFT)
                state = viewer.update(pausing, 0.02)
                self.assertEqual((state.motion_index, state.phase), ((index + 1) % 10, viewer.PLAY))
                self.assertAlmostEqual(state.elapsed, 0.01)
                self.assertEqual((viewer.current_frame_index(state), state.direction), (0, viewer.RIGHT))
                self.assertAlmostEqual(state.x, 600 + next_motion.speed * 0.01)

    def test_one_cycle_takes_44_75_seconds(self):
        # PRD.md 5.3절: 재생 34.75초 + 정지 1초 x 10 = 44.75초
        total = sum(viewer.play_time(motion) + viewer.PAUSE_TIME for motion in viewer.MOTIONS)
        self.assertAlmostEqual(total, CYCLE_TIME)
        self.assertIn(f'**{CYCLE_TIME}초**', read_prd())

    def test_plays_all_motions_in_order_and_returns_to_first(self):
        # 0.01초 간격으로 44.75초 + 0.5초를 흘려보내면 1번 -> 10번 동작을 차례로 재생한 뒤 1번으로 돌아온다.
        history = simulate(CYCLE_TIME + 0.5)
        self.assertEqual(collapse([s.motion_index for _, s in history]), list(range(10)) + [0])
        switches = [t for (t, s), (_, before) in zip(history[1:], history) if s.motion_index != before.motion_index]
        self.assertAlmostEqual(switches[-1], CYCLE_TIME, delta=TIME_TOLERANCE)  # 10번 -> 1번으로 돌아오는 시각

    def test_each_motion_starts_when_previous_pause_ends(self):
        # 동작 k의 시작 시각 = 앞선 동작들의 (5회 재생 시간 + 정지 1초)의 합
        history = simulate(CYCLE_TIME)
        expected_start = 0.0
        for index, motion in enumerate(viewer.MOTIONS):
            with self.subTest(motion=motion.name):
                start = next(t for t, s in history if s.motion_index == index) - SIM_DT
                self.assertAlmostEqual(start, expected_start, delta=TIME_TOLERANCE)
            expected_start += viewer.play_time(motion) + viewer.PAUSE_TIME


class HudTest(unittest.TestCase):
    def check(self, cases: list[tuple[viewer.ViewerState, str]]) -> None:
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
        # 1회 순환 모의 실행에서 k번째 반복은 그 동작이 시작되고 (k - 1) x 1회 재생 시간 뒤에 시작하고, 정지 중에는 5/5로 남는다.
        for motion, run in zip(viewer.MOTIONS, motion_runs()):
            with self.subTest(motion=motion.name):
                self.assertEqual(collapse([viewer.repeat_number(s) for _, s in run]), [1, 2, 3, 4, 5])
                for k in range(2, 6):
                    start = next(t for t, s in run if viewer.repeat_number(s) == k)
                    self.assertAlmostEqual(start, (k - 1) * viewer.loop_time(motion), delta=TIME_TOLERANCE)


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

    def test_moves_at_motion_speed_while_playing(self):
        # 걷기(150px/초)를 0.01초 간격으로 2초 재생하면 x = 600 -> 900
        history = simulate(2.0, viewer.ViewerState(motion_index=1))
        self.assertAlmostEqual(history[-1][1].x, 900.0)

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

    def test_lands_when_fifth_loop_ends(self):
        # 스핀 점프 5회 재생(2.5초)이 끝나기 직전에는 기준선까지 내려와 있어, 정지 단계(높이 0)로 넘어갈 때 튀지 않는다.
        about_to_stop = viewer.ViewerState(motion_index=4, elapsed=2.5 - 1e-9)
        self.assertAlmostEqual(viewer.jump_offset(about_to_stop), 0, places=5)

    def test_top_of_highest_jump_stays_below_status_text(self):
        # 가장 높이 뛰었을 때 그림 위쪽 끝: 스핀 점프 150 + 160 + 27×4 = 418, 공중 회전 150 + 200 + 45×4 = 530
        # 상태 표시가 있는 화면 위쪽 40px(y 560 이상)과 겹치지 않는다. (PRD 6.4절)
        tops = {motion.name: viewer.GROUND_Y + motion.jump_height + max(h for *_, h in motion.frames) * 4
                for motion in viewer.MOTIONS if motion.jump_height > 0}
        self.assertEqual(tops, {'스핀 점프': 418, '공중 회전': 530})
        self.assertTrue(all(top <= 600 - STATUS_AREA_HEIGHT for top in tops.values()))


class TimeSimulationTest(unittest.TestCase):
    # PRD.md 9절 시간 모의 실행: update()를 0.01초 간격으로 호출해 1회 순환(44.75초)을 흘려보내고 동작마다 결과를 확인한다.
    def test_plays_each_motion_five_times_then_pauses_one_second(self):
        # 1번 -> 10번 동작을 차례로 재생한다. 동작마다 모든 프레임을 차례로 5번 보여 준 뒤,
        # 5회 재생이 끝나는 시각부터 1초 동안 정지하고 다음 동작으로 넘어간다.
        runs = motion_runs()
        self.assertEqual([run[0][1].motion_index for run in runs], list(range(10)))
        for motion, run in zip(viewer.MOTIONS, runs):
            with self.subTest(motion=motion.name):
                shown = [viewer.current_frame_index(s) for _, s in run if s.phase == viewer.PLAY]
                paused_at = [t for t, s in run if s.phase == viewer.PAUSE]
                self.assertEqual(collapse(shown), list(range(len(motion.frames))) * 5)
                self.assertAlmostEqual(paused_at[0], viewer.play_time(motion), delta=TIME_TOLERANCE)
                self.assertLessEqual(abs(len(paused_at) - 100), 1)  # 0.01초 간격으로 1초 = 100번

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
                    self.assertAlmostEqual(turns[0], turn, delta=TIME_TOLERANCE)
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
        # 점프 높이가 0인 동작은 재생하는 내내 기준선에 있다.
        for motion, run in zip(viewer.MOTIONS, motion_runs()):
            with self.subTest(motion=motion.name):
                heights = [viewer.jump_offset(s) for _, s in run if s.phase == viewer.PLAY]
                if motion.jump_height == 0:
                    self.assertEqual(set(heights), {0})
                    continue
                neighbours = list(zip(heights, heights[1:], heights[2:]))
                tops = [h for before, h, after in neighbours if before < h >= after]
                landings = [h for before, h, after in neighbours if before > h <= after]
                self.assertEqual(len(tops), 5)
                self.assertEqual(len(landings), 4)  # 1 ~ 4회째가 끝나는 순간 (5회째가 끝나면 정지 단계로 넘어간다)
                for top in tops:
                    self.assertAlmostEqual(top, motion.jump_height, delta=0.01)
                for landing in landings:
                    self.assertAlmostEqual(landing, 0, delta=0.01)


class RealWindowTest(unittest.TestCase):
    # PRD.md 8.2절 구현 단계 17: 가짜 함수 없이 실제 pico2d 창을 열어 main()을 한 번 실행하고 확인한다.
    # 화면을 3번 내보낸 뒤 실제 ESC 키 입력 이벤트를 넣으므로 창은 1초도 안 되어 닫힌다.
    @classmethod
    def setUpClass(cls) -> None:
        cls.seen = run_real_main()

    def test_opens_1200x600_window(self):
        self.assertEqual(self.seen.window_size, (1200, 600))

    def test_escape_key_ends_loop_and_closes_window(self):
        # ESC 키를 누른 뒤에는 화면을 더 그리지 않고 루프를 끝내며, 창을 닫아 SDL 화면 기능도 꺼진다.
        self.assertEqual(self.seen.presented, FRAMES_BEFORE_ESCAPE)
        self.assertEqual(self.seen.close_calls, 1)
        self.assertFalse(self.seen.video_still_on)

    @unittest.skipIf(PILImage is None, 'Pillow가 없어 픽셀 검사를 건너뜀')
    def test_first_screen_draws_idle_frame_4x_at_center_on_ground(self):
        # 첫 화면에는 대기 1번 프레임(29x39)이 4배 크기(116x156)로 가로 중심 x = 600, 발 y = 150에 그려진다.
        box = drawn_box(self.seen, STATUS_AREA_HEIGHT, viewer.CANVAS_H)
        self.assertIsNotNone(box)
        left, top, right, bottom = box
        self.assertEqual((right - left, bottom - top), (116, 156))
        self.assertEqual((left + right) / 2, 600)
        self.assertEqual(viewer.CANVAS_H - bottom, 150)  # 화면 좌표(맨 위 줄이 0행) -> pico2d 좌표(맨 아래가 0)

    @unittest.skipIf(PILImage is None, 'Pillow가 없어 픽셀 검사를 건너뜀')
    def test_first_screen_draws_status_text_at_top_left(self):
        # 상태 글자는 x = 10 바로 오른쪽(첫 글자의 왼쪽 여백만큼)부터 시작하고, 세로 중심은 y = 580 근처다.
        # 글자가 위쪽 띠의 위아래 경계나 화면 오른쪽 끝에 닿지 않아야 잘리지 않고 다 보인다.
        box = drawn_box(self.seen, 0, STATUS_AREA_HEIGHT)
        self.assertIsNotNone(box)
        left, top, right, bottom = box
        self.assertTrue(viewer.HUD_X <= left <= viewer.HUD_X + 10, left)
        self.assertAlmostEqual(viewer.CANVAS_H - (top + bottom) / 2, viewer.HUD_Y, delta=4)
        self.assertTrue(0 < top and bottom < STATUS_AREA_HEIGHT, (top, bottom))
        self.assertLess(right, viewer.CANVAS_W)


class MotionDataTest(unittest.TestCase):
    def all_frames(self) -> list[tuple[str, viewer.Frame]]:
        return [(motion.name, frame) for motion in viewer.MOTIONS for frame in motion.frames]

    def test_all_10_motions_and_76_frames_are_registered(self):
        # 재생 순서대로 동작마다 이름과 프레임 수를 세어 보고, 모두 합하면 10종 76프레임이다.
        counts = [(motion.name, len(motion.frames)) for motion in viewer.MOTIONS]
        self.assertEqual(counts, list(EXPECTED_FRAME_COUNTS.items()))
        self.assertEqual((len(counts), len(self.all_frames())), (10, 76))

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
