#!/usr/bin/python
import os
plugins = os.listdir(os.path.dirname(__file__))
plugins = list(filter(lambda x: x not in ['__pycache__','__init__'], map(lambda x: x.split('.')[0], plugins)))
__all__ = plugins
