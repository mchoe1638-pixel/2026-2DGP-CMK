from pico2d import *

w = 800
h = 600
open_canvas(w, h)
grass = load_image('grass.png')
character = load_image('character.png')

def move_circle():
    print('circle')
    grass.draw(w//2, h//8)
    character.draw(w//2, h//5)
    update_canvas()
def move_rectangle():
    print('rectangle')
    grass.draw(w//2, h//8)
    character.draw(w//2, h//5)
    update_canvas()
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
