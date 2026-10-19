from pico2d import *
import random

class ball:
    def __init__(self):
        self.image = load_image("ball21x21.png")
    def update(self):
        pass
    def draw(self):
        self.image.draw(100, 100)

class Boy:
    def __init__(self):
        self.image = load_image("run_animation.png")
        self.frame = random.randint(0, 9)
        self.image = load_image("zombie_run_animation.png")
        self.frame_w = self.image.w // 10
        self.frame_h = self.image.h
    def update(self):
        self.frame = (self.frame + 1) % 10
        self.x += 5
    def draw(self):
        self.image.clip_draw(self.frame*)