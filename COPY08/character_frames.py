# character_sheet.png  (482 x 470)
# (x, y, w, h) : 이미지 왼쪽 위 (0,0) 기준
SHEET_W, SHEET_H = 482, 470

FRAMES = {
    'idle': [
        (8, 8, 62, 100),
        (78, 8, 64, 100),
        (150, 10, 66, 98),
        (224, 10, 64, 98),
    ],
    'walk': [
        (8, 118, 70, 98),
        (86, 116, 74, 100),
        (168, 116, 72, 100),
        (248, 118, 72, 98),
        (328, 116, 68, 100),
        (404, 116, 70, 100),
    ],
    'attack': [
        (8, 236, 68, 98),
        (84, 224, 56, 110),
        (148, 230, 96, 104),
        (252, 234, 84, 100),
        (344, 234, 80, 100),
    ],
    'jump': [
        (8, 372, 72, 90),
        (88, 342, 44, 120),
        (140, 368, 94, 94),
    ],
}


def draw_frame(image, anim, index, x, y, scale=3):
    """발 중앙 기준으로 그리기. pico2d는 왼쪽 아래가 원점이라 y를 뒤집는다."""
    fx, fy, fw, fh = FRAMES[anim][index]
    bottom = SHEET_H - fy - fh
    image.clip_draw_to_origin(fx, bottom, fw, fh, x - fw * scale // 2, y, fw * scale, fh * scale)
