# LEC09: 소닉 애니메이션 뷰어
# sonic-sprite.png에 있는 소닉의 동작을 원본의 4배 크기로 순서대로 재생한다.
# 요구사항과 단계별 개발 계획은 PRD.md를 따른다.
import os
from dataclasses import dataclass, replace

from pico2d import *

# 화면 설정
CANVAS_W, CANVAS_H = 1200, 600
CENTER_X = CANVAS_W // 2  # 화면 가로 중앙
GROUND_Y = 150  # 발 기준선: 프레임 높이가 달라도 그림의 아래쪽 끝(발)을 이 높이에 맞춘다.
FRAME_DELAY = 0.01  # 화면을 한 번 갱신한 뒤 쉬는 시간(초)

# 스프라이트 설정
SPRITE_FILE = 'sonic-sprite.png'
SCALE = 4  # 원본 대비 확대 배율

# 재생 설정
REPEAT_COUNT = 5  # 동작 하나를 처음부터 끝까지 되풀이해 재생하는 횟수
PAUSE_TIME = 1.0  # 5회 재생을 마친 뒤 마지막 프레임에 멈춰 있는 시간(초)

# 재생 단계: 프레임을 넘기며 재생하는 중(PLAY)이거나, 마지막 프레임에서 멈춰 있는 중(PAUSE)이다.
PLAY, PAUSE = 'PLAY', 'PAUSE'

# 프레임 영역: pico2d 이미지 좌표계(원점이 왼쪽 아래)의 (left, bottom, width, height)
Frame = tuple[int, int, int, int]


@dataclass(frozen=True)
class Motion:
    # 동작 하나: 이름, 재생 속도(초당 프레임 수), 재생 순서대로 늘어선 프레임 영역
    name: str
    fps: float
    frames: tuple[Frame, ...]


# 재생 순서대로 늘어선 동작 목록
# 시트를 분석해 얻은 프레임 좌표(PRD.md 5.4절)와 동작별 fps(5.3절)를 그대로 옮겼다.
MOTIONS: tuple[Motion, ...] = (
    Motion('대기', 10, (
        (1, 447, 29, 39), (31, 447, 26, 38), (58, 447, 28, 39), (86, 447, 30, 38),
        (118, 447, 30, 38), (150, 447, 30, 38), (182, 447, 29, 38), (211, 448, 29, 38),
        (240, 448, 29, 38), (270, 448, 24, 32), (302, 448, 29, 26),
    )),
    Motion('걷기', 12, (
        (8, 408, 26, 37), (37, 408, 27, 37), (65, 407, 31, 38), (97, 408, 37, 37),
        (135, 410, 32, 35), (170, 408, 32, 38), (206, 408, 26, 38), (238, 408, 24, 37),
        (263, 408, 30, 37), (295, 408, 36, 37), (334, 409, 32, 36), (370, 408, 29, 38),
    )),
    Motion('발차기', 10, (
        (1, 361, 33, 40), (39, 362, 35, 39), (89, 362, 35, 38), (130, 362, 34, 42),
        (181, 362, 34, 41), (228, 363, 33, 40),
    )),
    Motion('회전 진입', 12, (
        (1, 326, 29, 30), (35, 327, 29, 31), (67, 327, 30, 29), (98, 327, 31, 29),
        (131, 327, 29, 30), (162, 326, 29, 31), (193, 326, 30, 29), (230, 326, 31, 29),
        (268, 325, 30, 30),
    )),
    Motion('스핀 점프', 12, (
        (1, 292, 30, 27), (36, 292, 29, 27), (70, 292, 29, 27), (105, 292, 29, 27),
        (139, 292, 29, 27), (174, 292, 29, 27),
    )),
    Motion('질주', 15, (
        (1, 251, 29, 35), (36, 251, 30, 35), (74, 251, 31, 35), (111, 251, 31, 36),
        (149, 251, 30, 35), (186, 251, 31, 36),
    )),
    Motion('최고속 질주', 20, (
        (1, 207, 29, 35), (36, 207, 30, 35), (72, 208, 39, 31), (123, 208, 39, 32),
        (172, 208, 39, 31), (218, 208, 38, 32),
    )),
    Motion('공중 회전', 10, (
        (1, 154, 24, 45), (31, 154, 29, 44), (65, 154, 20, 44), (90, 155, 25, 43),
        (119, 155, 25, 43), (149, 154, 20, 44), (184, 156, 40, 28), (232, 157, 39, 27),
    )),
    Motion('정면 달리기', 16, (
        (1, 108, 27, 38), (31, 110, 31, 36), (64, 110, 31, 36), (99, 110, 33, 38),
        (136, 110, 32, 36), (176, 110, 33, 36), (217, 110, 33, 36), (254, 111, 33, 36),
    )),
    Motion('포즈', 4, (
        (6, 56, 34, 40), (49, 56, 34, 43), (96, 59, 23, 39), (125, 59, 23, 39),
    )),
)


@dataclass(frozen=True)
class ViewerState:
    # 뷰어의 현재 상태: 몇 번째 동작을, 어느 단계에서, 그 단계가 시작되고 몇 초째 보여 주는지
    # 바꿀 수 없는 값이라 시간이 흐르면 update()가 새 상태를 만들어 돌려준다.
    motion_index: int = 0
    phase: str = PLAY
    elapsed: float = 0.0


def resource_path(file_name: str) -> str:
    # 실행 위치와 상관없이 이 파일과 같은 폴더에 있는 리소스 경로를 돌려준다.
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)


def frame_index(motion: Motion, elapsed: float) -> int:
    # 재생을 시작하고 elapsed초가 지났을 때 보여 줄 프레임 번호
    # 1/fps초마다 다음 프레임으로 넘어가고, 마지막 프레임 다음에는 첫 프레임으로 돌아간다.
    return int(elapsed * motion.fps) % len(motion.frames)


def loop_time(motion: Motion) -> float:
    # 동작을 처음부터 끝까지 한 번 재생하는 데 걸리는 시간(초)
    return len(motion.frames) / motion.fps


def play_time(motion: Motion) -> float:
    # 동작을 REPEAT_COUNT번 되풀이해 재생하는 데 걸리는 시간(초)
    return loop_time(motion) * REPEAT_COUNT


def current_frame_index(state: ViewerState) -> int:
    # 지금 보여 줄 프레임 번호: 재생 중에는 지난 시간으로 정하고, 멈춘 뒤에는 마지막 프레임에 머문다.
    motion = MOTIONS[state.motion_index]
    if state.phase == PAUSE:
        return len(motion.frames) - 1
    return frame_index(motion, state.elapsed)


def phase_time(state: ViewerState) -> float:
    # 지금 단계가 이어지는 시간(초): 재생 단계는 5회 재생 시간, 정지 단계는 PAUSE_TIME
    if state.phase == PAUSE:
        return PAUSE_TIME
    return play_time(MOTIONS[state.motion_index])


def next_phase(state: ViewerState) -> ViewerState:
    # 지금 단계가 끝났을 때 이어지는 단계의 시작 상태
    # 5회 재생이 끝나면 정지하고, 정지가 끝나면 다음 동작을 처음부터 재생한다. (마지막 동작 다음은 첫 동작)
    if state.phase == PLAY:
        return replace(state, phase=PAUSE, elapsed=0.0)
    return ViewerState(motion_index=(state.motion_index + 1) % len(MOTIONS))


def update(state: ViewerState, dt: float) -> ViewerState:
    # dt초가 지난 뒤의 상태를 새로 만들어 돌려준다.
    # 그사이 지금 단계가 끝나면 다음 단계로 넘기고, 남은 시간은 다음 단계에서 이어서 센다.
    while state.elapsed + dt >= phase_time(state):
        dt -= phase_time(state) - state.elapsed
        state = next_phase(state)
    return replace(state, elapsed=state.elapsed + dt)


def draw_frame(sheet: Image, frame: Frame, x: float, foot_y: float) -> None:
    # 시트에서 frame 영역을 잘라 가로·세로 4배로 키워 그린다.
    # 그림의 가로 중심은 x에, 아래쪽 끝(발)은 foot_y에 맞춘다.
    # clip_draw는 그림의 중심 좌표를 받으므로 y에는 그린 높이의 절반을 더해 넘긴다.
    left, bottom, width, height = frame
    draw_w, draw_h = width * SCALE, height * SCALE
    sheet.clip_draw(left, bottom, width, height, x, foot_y + draw_h / 2, draw_w, draw_h)


def handle_events() -> bool:
    # 창 닫기나 ESC 키 입력이 있으면 False를 돌려줘 메인 루프를 끝낸다.
    for event in get_events():
        if event.type == SDL_QUIT:
            return False
        if event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            return False
    return True


def main() -> None:
    open_canvas(CANVAS_W, CANVAS_H)
    try:  # 시트를 읽지 못하는 등 오류가 나도 창은 닫는다.
        sheet = load_image(resource_path(SPRITE_FILE))
        state = ViewerState()
        last_time = get_time()
        while handle_events():
            now = get_time()  # 상태는 실제로 지난 시간만큼 진행한다.
            state, last_time = update(state, now - last_time), now
            motion = MOTIONS[state.motion_index]
            clear_canvas()
            draw_frame(sheet, motion.frames[current_frame_index(state)], CENTER_X, GROUND_Y)
            update_canvas()
            delay(FRAME_DELAY)
    finally:
        close_canvas()


if __name__ == '__main__':
    main()
