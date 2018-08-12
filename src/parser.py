from . import *

def count_seq(seq, match=''):
    if not seq:
        return 0
    r = 0
    if match == '':
        try:
            match = seq[0]
        except IndexError:
            return 0
    for c in seq:
        if c != match:
            break
        r+=1
    return r

def peel_uint(s, d=None):
    a,b = peel_uint_s(s,str(d) if d!=None else None)
    return (int(a) if a!=None and a!='' else None,b)

def peel_int(s, d=None):
    a,b = peel_uint_s(s,str(d) if d!=None else None)
    return (int(a) if a!=None and a!='' else None,b)

# don't cast
def peel_uint_s(s, d=None):
    r = ''
    for ch in s:
        if ch.isdigit():
            r += ch
        else:
            break
    if not r: return (d,0) if d!=None else ('',0)
    return (r,len(r))

def peel_roman_s(s, d=None):
    nums = 'ivx'
    r = ''
    case = -1 # -1 unknown, 0 low, 1 uppper
    for ch in s:
        chl = ch.lower()
        chcase = (chl==ch)
        if chl in nums:
            if case > 0 and case != chcase:
                break # changing case ends peel
            r += ch
            chcase = 0 if (chl==ch) else 1
        else:
            break
    if not r: return (d,0) if d!=None else ('',0)
    return (r,len(r))

def peel_int_s(s, d=None):
    r = ''
    for ch in s:
        if ch.isdigit():
            r += ch
        elif ch=='-' and not r:
            r += ch
        else:
            break
    if r == '-': return (0,0)
    if not r: return (d,'') if d!=None else (0,'')
    return (int(r),len(r))

def peel_float(s, d=None):
    r = ''
    decimals = 0
    for ch in s:
        if ch.isdigit():
            r += ch
        elif ch=='-' and not r:
            r += ch
        elif ch=='.':
            if decimals >= 1:
                break
            r += ch
            decimals += 1
        else:
            break
    # don't parse trailing decimals
    if r and r[-1]=='.': r = r[:-1]
    if not r: return (d,0) if d!=None else (0,0)
    return (float(r),len(r))

def peel_any(s, match, d=''):
    r = ''
    ct = 0
    for ch in s:
        if ch in match:
            r += ch
            ct += 1
        else:
            break
    return (ct,orr(r,d))

def note_value(s): # turns dot note values (. and *) into frac
    if not s:
        return (0.0, 0)
    r = 1.0
    dots = count_seq(s)
    s = s[dots:]
    num,ct = peel_float(s, 1.0)
    s = s[ct:]
    if s[0]=='*':
        if dots==1:
            r = num
        else:
            r = num*pow(2.0,float(dots-1))
    elif s[0]=='.':
        num,ct = peel_int_s(s)
        if ct:
            num = int('0.' + num)
        else:
            num = 1.0
        s = s[ct:]
        r = num*pow(0.5,float(dots))
    return (r, dots)

