# LEC09: 소닉 애니메이션 뷰어
# sonic-sprite.png에 있는 소닉의 동작을 원본의 4배 크기로 순서대로 재생한다.
# 요구사항과 단계별 개발 계획은 PRD.md를 따른다.
from pico2d import *

# 화면 설정
CANVAS_W, CANVAS_H = 1200, 600
FRAME_DELAY = 0.01  # 화면을 한 번 갱신한 뒤 쉬는 시간(초)


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
    while handle_events():
        clear_canvas()
        update_canvas()
        delay(FRAME_DELAY)
    close_canvas()


if __name__ == '__main__':
    main()
