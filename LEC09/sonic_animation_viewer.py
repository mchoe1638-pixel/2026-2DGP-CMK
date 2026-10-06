# LEC09: 소닉 애니메이션 뷰어
# sonic-sprite.png에 있는 소닉의 동작을 원본의 4배 크기로 순서대로 재생한다.
# 요구사항과 단계별 개발 계획은 PRD.md를 따른다.
import os
from dataclasses import dataclass

from pico2d import *

# 화면 설정
CANVAS_W, CANVAS_H = 1200, 600
CENTER_X, CENTER_Y = CANVAS_W // 2, CANVAS_H // 2
FRAME_DELAY = 0.01  # 화면을 한 번 갱신한 뒤 쉬는 시간(초)

# 스프라이트 설정
SPRITE_FILE = 'sonic-sprite.png'
SCALE = 4  # 원본 대비 확대 배율

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


def resource_path(file_name: str) -> str:
    # 실행 위치와 상관없이 이 파일과 같은 폴더에 있는 리소스 경로를 돌려준다.
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)


def draw_frame(sheet: Image, frame: Frame, x: float, y: float) -> None:
    # 시트에서 frame 영역을 잘라 가로·세로 4배로 키우고, 그림의 중심이 (x, y)에 오게 그린다.
    left, bottom, width, height = frame
    sheet.clip_draw(left, bottom, width, height, x, y, width * SCALE, height * SCALE)


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
        while handle_events():
            clear_canvas()
            draw_frame(sheet, MOTIONS[0].frames[0], CENTER_X, CENTER_Y)
            update_canvas()
            delay(FRAME_DELAY)
    finally:
        close_canvas()


if __name__ == '__main__':
    main()
