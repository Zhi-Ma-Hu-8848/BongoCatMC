# -*- coding: utf-8 -*-
"""Pure input reduction, shared by PC keys and mobile gameplay events."""


def key_art(code):
    if 65 <= code <= 90:
        return 'Key'+chr(code)
    if 48 <= code <= 57:
        return 'Num'+chr(code)
    return {32:'Space',16:'Shift',17:'Control',18:'Alt',9:'Tab',13:'Return',
            8:'Backspace',20:'CapsLock',46:'Delete',192:'BackQuote',191:'Slash',
            37:'KeyA',38:'KeyW',39:'KeyD',40:'KeyS'}.get(code)


class InputState(object):
    def __init__(self):
        self.keys = {}
        self.mouse = [set(), set()]
        self.mouse_until = [0., 0.]
        self.key_until = 0.
        self.last_art = 'Space'
        self.sequence = 0
        self.events = 0

    def key(self, source, art, down, now):
        if down:
            if source in self.keys and self.keys[source][1] == art:
                return
            self.sequence += 1
            self.keys[source] = (self.sequence, art)
            self.last_art = art
            self.key_until = now+.10
        else:
            self.keys.pop(source, None)
        self.events += 1

    def movement(self, vector, now):
        previous = self.keys.get('move', (0, None))[1]
        left, forward = vector if vector is not None else (0., 0.)
        threshold = .12 if previous else .18
        if left*left+forward*forward < threshold*threshold:
            if previous:
                self.key('move',previous,False,now)
            return
        horizontal, vertical = abs(left), abs(forward)
        art = ('KeyA' if left > 0 else 'KeyD') if horizontal > vertical else ('KeyW' if forward > 0 else 'KeyS')
        # Keep the previous axis near a diagonal boundary. A deliberate turn or
        # sign reversal still takes effect immediately, without a time delay.
        old_horizontal = (previous == 'KeyA' and left > 0) or (previous == 'KeyD' and left < 0)
        old_vertical = (previous == 'KeyW' and forward > 0) or (previous == 'KeyS' and forward < 0)
        if old_horizontal and horizontal+.15 >= vertical:
            art = previous
        elif old_vertical and vertical+.15 >= horizontal:
            art = previous
        self.key('move',art,True,now)

    def click(self, source, button, down, now):
        if down:
            if source not in self.mouse[button]:
                self.mouse_until[button] = now+.10
            self.mouse[button].add(source)
        else:
            self.mouse[button].discard(source)
        self.events += 1

    def snapshot(self, now):
        # Physical keys have precise art; generic movement should not replace W/A/S/D.
        physical = [v for k,v in self.keys.items() if k.startswith('key:')]
        values = physical or list(self.keys.values())
        if values:
            self.last_art = max(values)[1]
        return {'key':bool(self.keys) or now<self.key_until, 'art':self.last_art,
                'left':bool(self.mouse[0]) or now<self.mouse_until[0],
                'right':bool(self.mouse[1]) or now<self.mouse_until[1]}

    def clear(self):
        self.keys.clear()
        for buttons in self.mouse:
            buttons.clear()
        self.key_until = 0.
        self.mouse_until = [0., 0.]
