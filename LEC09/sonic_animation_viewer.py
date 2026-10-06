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

# 상태 표시 설정
FONT_FILE = 'ConsolaMalgun.ttf'  # pico2d에 함께 들어 있는 한글 글꼴
FONT_SIZE = 20
HUD_X, HUD_Y = 10, 580  # 상태 글자의 왼쪽 끝과 세로 중심: 화면 왼쪽 위
HUD_COLOR = (0, 0, 0)

# 재생 설정
REPEAT_COUNT = 5  # 동작 하나를 처음부터 끝까지 되풀이해 재생하는 횟수
PAUSE_TIME = 1.0  # 5회 재생을 마친 뒤 마지막 프레임에 멈춰 있는 시간(초)

# 재생 단계: 프레임을 넘기며 재생하는 중(PLAY)이거나, 마지막 프레임에서 멈춰 있는 중(PAUSE)이다.
PLAY, PAUSE = 'PLAY', 'PAUSE'

# 소닉이 보는 방향: 오른쪽(x가 커지는 쪽)은 1, 왼쪽은 -1이라 이동 속도에 그대로 곱한다.
RIGHT, LEFT = 1, -1

# 프레임 영역: pico2d 이미지 좌표계(원점이 왼쪽 아래)의 (left, bottom, width, height)
Frame = tuple[int, int, int, int]


@dataclass(frozen=True)
class Motion:
    # 동작 하나: 이름, 재생 속도(초당 프레임 수), 재생 순서대로 늘어선 프레임 영역, 가로 이동 속도(px/초)
    # 이동 속도가 0인 동작은 화면 가운데에 서서 재생한다.
    name: str
    fps: float
    frames: tuple[Frame, ...]
    speed: float = 0


# 재생 순서대로 늘어선 동작 목록
# 시트를 분석해 얻은 프레임 좌표(PRD.md 5.4절)와 동작별 fps(5.3절), 이동 속도(6.1절)를 그대로 옮겼다.
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
    ), speed=150),
    Motion('발차기', 10, (
        (1, 361, 33, 40), (39, 362, 35, 39), (89, 362, 35, 38), (130, 362, 34, 42),
        (181, 362, 34, 41), (228, 363, 33, 40),
    ), speed=100),
    Motion('회전 진입', 12, (
        (1, 326, 29, 30), (35, 327, 29, 31), (67, 327, 30, 29), (98, 327, 31, 29),
        (131, 327, 29, 30), (162, 326, 29, 31), (193, 326, 30, 29), (230, 326, 31, 29),
        (268, 325, 30, 30),
    )),
    Motion('스핀 점프', 12, (
        (1, 292, 30, 27), (36, 292, 29, 27), (70, 292, 29, 27), (105, 292, 29, 27),
        (139, 292, 29, 27), (174, 292, 29, 27),
    ), speed=300),
    Motion('질주', 15, (
        (1, 251, 29, 35), (36, 251, 30, 35), (74, 251, 31, 35), (111, 251, 31, 36),
        (149, 251, 30, 35), (186, 251, 31, 36),
    ), speed=450),
    Motion('최고속 질주', 20, (
        (1, 207, 29, 35), (36, 207, 30, 35), (72, 208, 39, 31), (123, 208, 39, 32),
        (172, 208, 39, 31), (218, 208, 38, 32),
    ), speed=700),
    Motion('공중 회전', 10, (
        (1, 154, 24, 45), (31, 154, 29, 44), (65, 154, 20, 44), (90, 155, 25, 43),
        (119, 155, 25, 43), (149, 154, 20, 44), (184, 156, 40, 28), (232, 157, 39, 27),
    ), speed=200),
    Motion('정면 달리기', 16, (
        (1, 108, 27, 38), (31, 110, 31, 36), (64, 110, 31, 36), (99, 110, 33, 38),
        (136, 110, 32, 36), (176, 110, 33, 36), (217, 110, 33, 36), (254, 111, 33, 36),
    ), speed=250),
    Motion('포즈', 4, (
        (6, 56, 34, 40), (49, 56, 34, 43), (96, 59, 23, 39), (125, 59, 23, 39),
    )),
)


@dataclass(frozen=True)
class ViewerState:
    # 뷰어의 현재 상태: 몇 번째 동작을, 어느 단계에서, 그 단계가 시작되고 몇 초째 보여 주는지와
    # 소닉이 서 있는 가로 위치(x), 보는 방향(direction)
    # 바꿀 수 없는 값이라 시간이 흐르면 update()가 새 상태를 만들어 돌려준다.
    motion_index: int = 0
    phase: str = PLAY
    elapsed: float = 0.0
    x: float = CENTER_X  # 모든 동작은 화면 가운데에서
    direction: int = RIGHT  # 오른쪽을 보고 시작한다.


def resource_path(file_name: str) -> str:
    # 실행 위치와 상관없이 이 파일과 같은 폴더에 있는 리소스 경로를 돌려준다.
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)


def font_path() -> str:
    # pico2d 패키지의 data 폴더에 있는 글꼴 경로 (PICO2D_DATA_PATH는 pico2d를 불러올 때 정해진다)
    return os.path.join(os.environ['PICO2D_DATA_PATH'], FONT_FILE)


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


def repeat_number(state: ViewerState) -> int:
    # 지금 몇 번째 반복을 재생하는지(1 ~ REPEAT_COUNT). 정지 중에는 마지막 반복을 마친 상태다.
    if state.phase == PAUSE:
        return REPEAT_COUNT
    return min(int(state.elapsed / loop_time(MOTIONS[state.motion_index])) + 1, REPEAT_COUNT)


def hud_text(state: ViewerState) -> str:
    # 화면 왼쪽 위에 띄울 상태 글자: 동작 순번·이름, 반복 횟수, 프레임 번호, 재생 중 또는 정지 경과 시간
    # 정지 시간은 0.1초 단위로 버려서 정지가 끝나기 전에 1.0초로 보이지 않게 한다.
    motion = MOTIONS[state.motion_index]
    if state.phase == PAUSE:
        status = f'정지 {int(state.elapsed * 10) / 10:.1f}/{PAUSE_TIME:.1f}초'
    else:
        status = '재생 중'
    return (f'[{state.motion_index + 1}/{len(MOTIONS)}] {motion.name} | '
            f'반복 {repeat_number(state)}/{REPEAT_COUNT} | '
            f'프레임 {current_frame_index(state) + 1}/{len(motion.frames)} | {status}')


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


def x_limits(motion: Motion) -> tuple[float, float]:
    # 그 동작의 어떤 프레임을 그려도 화면 밖으로 나가지 않는 x의 범위(왼쪽 끝, 오른쪽 끝)
    # 가장 넓은 프레임을 그린 폭의 절반만큼 화면 양쪽 끝에서 안쪽으로 들어온다.
    half = max(width for _, _, width, _ in motion.frames) * SCALE / 2
    return half, CANVAS_W - half


def reflect(x: float, direction: int, low: float, high: float) -> tuple[float, int]:
    # x가 범위(low ~ high)를 넘었으면 넘은 거리만큼 반대쪽으로 되돌리고 방향을 바꾼다(반사).
    # 한 번에 많이 움직여 반대쪽 끝까지 넘어가면 범위 안에 들어올 때까지 되풀이한다.
    while not low <= x <= high:
        if x > high:
            x, direction = 2 * high - x, LEFT
        else:
            x, direction = 2 * low - x, RIGHT
    return x, direction


def advance(state: ViewerState, dt: float) -> ViewerState:
    # 지금 단계 안에서 dt초가 지난 상태
    # 재생 중에는 보는 방향으로 동작의 이동 속도만큼 움직이고(화면 끝에서는 돌아선다), 정지 중에는 그 자리에 머문다.
    if state.phase == PAUSE:
        return replace(state, elapsed=state.elapsed + dt)
    motion = MOTIONS[state.motion_index]
    moved_x = state.x + state.direction * motion.speed * dt
    x, direction = reflect(moved_x, state.direction, *x_limits(motion))
    return replace(state, elapsed=state.elapsed + dt, x=x, direction=direction)


def update(state: ViewerState, dt: float) -> ViewerState:
    # dt초가 지난 뒤의 상태를 새로 만들어 돌려준다.
    # 그사이 지금 단계가 끝나면 끝나는 순간까지만 진행해 다음 단계로 넘기고, 남은 시간은 다음 단계에서 이어서 센다.
    while state.elapsed + dt >= phase_time(state):
        remaining = phase_time(state) - state.elapsed
        state = next_phase(advance(state, remaining))
        dt -= remaining
    return advance(state, dt)


def draw_frame(sheet: Image, frame: Frame, x: float, foot_y: float, direction: int) -> None:
    # 시트에서 frame 영역을 잘라 가로·세로 4배로 키워 그린다.
    # 그림의 가로 중심은 x에, 아래쪽 끝(발)은 foot_y에 맞춘다.
    # 시트의 소닉은 오른쪽을 보므로 왼쪽을 볼 때는 좌우를 뒤집어('h') 그린다. (회전 각도는 0)
    # clip_composite_draw는 그림의 중심 좌표를 받으므로 y에는 그린 높이의 절반을 더해 넘긴다.
    left, bottom, width, height = frame
    draw_w, draw_h = width * SCALE, height * SCALE
    flip = 'h' if direction == LEFT else ''
    sheet.clip_composite_draw(left, bottom, width, height, 0, flip, x, foot_y + draw_h / 2, draw_w, draw_h)


def draw_viewer(sheet: Image, font: Font, state: ViewerState) -> None:
    # 화면을 지우고 지금 상태의 프레임과 상태 글자를 그린 뒤 화면에 내보낸다.
    motion = MOTIONS[state.motion_index]
    clear_canvas()
    draw_frame(sheet, motion.frames[current_frame_index(state)], state.x, GROUND_Y, state.direction)
    font.draw(HUD_X, HUD_Y, hud_text(state), HUD_COLOR)
    update_canvas()


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
    try:  # 시트나 글꼴을 읽지 못하는 등 오류가 나도 창은 닫는다.
        sheet = load_image(resource_path(SPRITE_FILE))
        font = load_font(font_path(), FONT_SIZE)
        state = ViewerState()
        last_time = get_time()
        while handle_events():
            now = get_time()  # 상태는 실제로 지난 시간만큼 진행한다.
            state, last_time = update(state, now - last_time), now
            draw_viewer(sheet, font, state)
            delay(FRAME_DELAY)
    finally:
        close_canvas()


if __name__ == '__main__':
    main()
