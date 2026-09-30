# Drill #8: 애니메이션 뷰어
# 캐릭터 스프라이트 시트에서 애니메이션을 읽어와 화면 중앙에서 재생한다.
from pico2d import *

open_canvas(800, 600)

character = load_image('character_sheet.png')

clear_canvas()
# idle 첫 프레임 좌표(left, bottom, width, height)를 우선 하드코딩해서 한 프레임만 잘라 그려본다.
# pico2d는 이미지 좌표 원점이 왼쪽 아래이므로 bottom은 시트 바닥에서 잰 값이다.
character.clip_draw_to_origin(8, 362, 62, 100, 400, 300)
update_canvas()
delay(1)

close_canvas()
