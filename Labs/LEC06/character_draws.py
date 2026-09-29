from pico2d import *

w = 800
h = 600
open_canvas(w, h)
grass = load_image('grass.png')
character = load_image('character.png')



def draw_frame(x,y):
    get_events()
    clear_canvas()
    grass.draw(w//2, h//8)
    character.draw(x,y)
    update_canvas()

def move_circle():
    CENTER_X = 400
    CENTER_Y = 300
    RADIAN = 200
    ANGLE = 0
    
    character.draw(w//2, h//5)
    update_canvas()
    while ANGLE < 360:
        x = CENTER_X+RADIAN*math.cos(math.radians(ANGLE))
        y = CENTER_Y+RADIAN*math.sin(math.radians(ANGLE))        
        draw_frame(x,y)
        ANGLE+=2
        delay(0.01)
    ANGLE = 0

def move_rectangle():
    print('rectangle')
    grass.draw(w//2, h//8)
    character.draw(w//2, h//5)
    update_canvas()
    for x in range(400, 750, 5):
        draw_frame(x, 100)
    for y in range(100, 550, 5):
        draw_frame(750, y)
    for x in range(750, 50, 5):
        draw_frame(x, 550)
    for y in range(550, 100, -5):
        draw_frame(50, y)
    for x in range(50, 400, 5):
        draw_frame(x,100)
        
def move_triangle():
    print('triangle')
    grass.draw(w//2, h//8)
    character.draw(w//2, h//5)
    update_canvas()

while True:
    move_circle()
    move_rectangle()
    move_triangle()
    pass
