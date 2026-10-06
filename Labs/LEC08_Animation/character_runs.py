from pico2d import *

open_canvas()

grass = load_image('grass.png')
character = load_image('animation_sheet.png')
while True:
    frame = 0
    for x in range(0, 800, 5):
        clear_canvas()
        grass.draw(400, 30)
        character.clip_draw(
            frame * 100, 300, 100, 100,
            x, 90, 
            100, 100
        )
        update_canvas()
        get_events()

        frame = (frame+1)%8
        delay(0.05)

    for x in range(800, 0, -5):
        clear_canvas()
        grass.draw(400, 30)
        character.clip_composite_draw(
            frame * 100, 300, 100, 100,
            0, 'h',
            x, 90, 
            100, 100
        )
        update_canvas()
        get_events()

        frame = (frame+1)%8
        delay(0.05)

    frame = 0
    for x in range(0, 800, 5):
        clear_canvas()
        grass.draw(400, 30)
        character.clip_draw(
            frame * 100, 100, 100, 100, 
            x, 90,
            100, 100
        )
        # image.clip_draw(left, bottom, width, hieght, x, y, 배울크기, 배율 크기)
        #잘라낼 사각형 왼쪽 x좌표, 잘라낼 사각형의 아래쪽 y좌표, 잘라낼 가로크기, 잘라낼 세로크기
        #화면에 그릴 중심점 x좌표, 화면에 그릴 중심점 y좌표
        #배율 x크기, 배율 y크기

        update_canvas()
        get_events()

        frame = (frame+1)%8
        delay(0.05)

    frame = 0
    for x in range(800, 0, -5):
        clear_canvas()
        grass.draw(400, 30)
        character.clip_composite_draw(
            frame * 100, 100, 100, 100, 
            0,'h',
            x, 90,
            100, 100
        )
        # image.clip_draw(left, bottom, width, hieght, x, y)
        #잘라낼 사각형 왼쪽 x좌표, 잘라낼 사각형의 아래쪽 y좌표, 잘라낼 가로크기, 잘라낼 세로크기
        #0, h(좌우반전), v(상하반전)
        #화면에 그릴 중심점 x좌표, 화면에 그릴 중심점 y좌표
        #배율 x크기, 배율 y크기

        update_canvas()
        get_events()

        frame = (frame+1)%8
        delay(0.05)




