# LEC09: 소닉 애니메이션 뷰어
# sonic-sprite.png에 있는 소닉의 동작을 원본의 4배 크기로 순서대로 재생한다.
# 요구사항과 단계별 개발 계획은 PRD.md를 따른다.
import os

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
FIRST_FRAME: Frame = (1, 447, 29, 39)  # 대기 1번 프레임


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
            draw_frame(sheet, FIRST_FRAME, CENTER_X, CENTER_Y)
            update_canvas()
            delay(FRAME_DELAY)
    finally:
        close_canvas()


if __name__ == '__main__':
    main()
