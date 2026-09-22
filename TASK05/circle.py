from pico2d import *

open_canvas(800, 600)
grass = load_image('grass.png')
character = load_image('character.png')

def draw_frame(x,y):
    get_events()    # 창이 멈춘 것처럼 보이지 않도록 매 프레임 이벤트 처리
    clear_canvas()
    grass.draw(400, 30)
    character.draw(x,y)
    update_canvas()

CX = 400
CY = 300
R = 200
A = 0
while True:
    while A < 360:
        x = CX + R * math.cos(math.radians(A))
        y = CY + R * math.sin(math.radians(A))

        draw_frame(x,y)

        A+=2
        delay(0.01)

    A -= 360    # 다음 바퀴를 위해 각도를 시작점으로 되돌림