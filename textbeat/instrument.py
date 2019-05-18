#!/usr/bin/env python

class Instrument(object):
    def __init__(self,name):
        self.name = name
    def inited(self):
        return False
    def supported(self):
        return False
    def support(self):
        return []
    def stop(self):
        pass

PLUGINS = []
# plugins call this method
def export(s):
    global PLUGINS
    if s not in PLUGINS:
        PLUGINS.append(s())
def plugins():
    return PLUGINS

