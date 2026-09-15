from pico2d import *

open_canvas(800, 600)
update_canvas()
delay(10)
close_canvas()

character = load_image('character.png')

character.draw(400, 300)
character.draw(300, 200)
character.draw(500, 400)
update_canvas()