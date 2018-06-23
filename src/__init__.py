EPSILON = 0.0001

def cmp(a,b):
    return bool(a>b) - bool(a<b)
def sgn(a):
    return bool(a>0) - bool(a<0)
def orr(a,b,bad=False):
    return a if (bool(a)!=bad if bad==False else a) else b
def indexor(a,i,d=None):
    try:
        return a[i]
    except:
        return d
class Wrapper:
    def __init__(self, value=None):
        self.value = value
    def __len__(self):
        return len(self.value)

def fcmp(a, b=0.0, ep=EPSILON):
    v = a - b
    av = abs(v)
    if av > EPSILON:
        return sgn(v)
    return 0
def feq(a, b=0.0, ep=EPSILON):
    return not fcmp(a,b,ep)
def fzero(a,ep=EPSILON):
    return 0==fcmp(a,0.0,ep)
def fsnap(a,b,ep=EPSILON):
    return a if fcmp(a,b) else b
def forr(a,b,bad=False):
    return a if (fcmp(a) if bad==False else a) else b
