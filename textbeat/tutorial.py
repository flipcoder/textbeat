from .defs import *

class Tutorial(object):
    def __init__(self, player):
        self.player = player
        player.shell = True
        self.idx = 0
    def next(self):
        pass
        # print(MSG[self.idx])
        # self.idx += 1

