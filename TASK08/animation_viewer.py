# Drill #8: 애니메이션 뷰어
# 캐릭터 스프라이트 시트에서 애니메이션을 읽어와 화면 중앙에서 재생한다.
from pico2d import *

open_canvas(800, 600)

character = load_image('character_sheet.png')

clear_canvas()
character.draw(400, 300)
update_canvas()
delay(1)

close_canvas()
