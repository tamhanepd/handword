#handword.py
#Tries to make approximate handwritten letters.

#    Copyright (C) 2013  K Hariram (hariran@gmail.com)
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from PIL import Image, ImageDraw
import random, math

def randbox(mean, halfwidth):
    """ This method will be called whenever some randomness is required"""
    return mean + halfwidth * random.uniform(-1, 1)

# constants
VERT_BORDER = 200 # borders for savefile
HORZ_BORDER = 200
VARM = 1.0 # multiply variances with this. Increase this to make the handwriting bad
XSCALE = 1.0
YSCALE = 1.0
THICKNESS = 4

### File writing part
def makeim(lines, filename = "text.bmp", bgcolor = (256, 256, 256), linecolor = (0, 0, 0)):
    """ Makes an image file.
    [0]lines, must be a list of lists. each smaller list must be [x1, y1, x2, y2, ...]
    [1]filename = "text.bmp", name of output file
    [2]bgcolor = (256, 256, 256)
    [3]linecolor = (0, 0, 0)
    """
    minx = min([min(i[0::2]) for i in lines])
    miny = min([min(i[1::2]) for i in lines])
    # Repositioning to adjust min
    for line in lines:
        for i in range(0, len(line), 2):
            line[i] = int(line[i] + HORZ_BORDER - minx)
            line[i+1] = int(line[i+1] + VERT_BORDER - miny)
    maxx = max([max(i[0::2]) for i in lines]) + HORZ_BORDER
    maxy = max([max(i[1::2]) for i in lines]) + VERT_BORDER
    # Drawing the image
    im = Image.new("RGB", (maxx, maxy), bgcolor)
    liner = ImageDraw.Draw(im)
    for line in lines:
        liner.line(line, fill = linecolor, width = THICKNESS)
    filename = check_extension(filename, ["bmp", "gif", "jpg", "jpeg"])
    im.save(filename)

def check_extension(filename, types, default = None, case_sense = False):
    """ Checks whether the extension of the given filename is in types or not.
    Otherwise adds the default or types[0] extension."""
    ext = filename.split(".")[-1]
    if not case_sense: ext = ext.lower()
    if ext in types:
        return filename
    else:
        if default == None: default = types[0]
        return "{0}.{1}".format(filename, default)

### the stroke et al classes. They create lines with some randomness.

class stroke(object):
    def __init__(self, steps = 10, llen = 1.0, turni = 0.0, turnf = None, stepsvar = 0, llenvar = 0.0, turnvar = 0.0):
        self.steps = steps
        self.llen = llen
        self.turni = turni
        if turnf == None: self.turnf == turni
        else: self.turnf = turnf
        self.stepsvar = stepsvar
        self.llenvar = llenvar
        self.turnvar = turnvar
    def __call__(self, x, y, angle, xframe, yframe, varm=VARM, xscale=XSCALE, yscale=YSCALE, **kwargs):
        line = [x, y]
        s = int(randbox(self.steps, self.stepsvar * varm) + 0.5)
        for t in range(s):
            stride = randbox(self.llen, self.llenvar * varm)
            x += stride * math.cos(angle) * xscale
            y += stride * math.sin(angle) * yscale
            line.extend([x, y])
            if s != 1: turn = self.turni + t*(self.turnf-self.turni)/(s-1)
            else: turn = (self.turnf+self.turni)/2.0
            angle += randbox(turn, self.turnvar * varm)
            angle %= 2*math.pi
        return line, x, y, angle
            
class reposition(object):
    """ Repositions and reorients the current pen position.
    type can be 'a'bsolute, 'f'rame or 'r'elative."""
    def __init__(self, xtype = 'r', x = 0.0, xvar = 0.0, ytype = 'r', y = 0.0, yvar = 0.0, angletype = 'a', angle = 0.0, anglevar = 0.0):
        self.xtype = xtype
        self.x = x
        self.xvar = xvar
        self.ytype = ytype
        self.y = y
        self.yvar = yvar
        self.angletype = angletype
        self.angle = angle
        self.anglevar = anglevar
    def __call__(self, x, y, angle, xframe, yframe,  varm=VARM, xscale=XSCALE, yscale=YSCALE, **kwargs):
        if   self.xtype == "f": x = xframe
        elif self.xtype == "a": x = 0
        if   self.ytype == "f": y = yframe
        elif self.ytype == "a": y = 0
        if self.angletype in "af": angle = 0
        x += randbox(self.x, self.xvar * varm) * xscale
        y += randbox(self.y, self.yvar * varm) * yscale
        angle += randbox(self.angle, self.anglevar * varm)
        angle %= 2*math.pi
        return [], x, y, angle

class letter(object):
    def __init__(self, strokes, char, varm=VARM, xscale=XSCALE, yscale=YSCALE):
        self.strokes = strokes
        self.char = char
        self.varm = varm
        self.xscale = xscale
        self.yscale = yscale
    def __call__(self, x, y, angle, xframe, yframe, varm = None, xscale = 1.0, yscale = 1.0):
        xscale *= self.xscale
        yscale *= self.yscale
        if varm == None :varm = self.varm
        xframe = x
        yframe = y
        lines = []
        for st in self.strokes:
            line, x, y, angle = st(x, y, angle, xframe, yframe, varm=varm, xscale=xscale, yscale=yscale)
            if len(line) > 0 and type(line[0]) == list: lines.extend(line)
            elif len(line)>=4: lines.append(line)
        return lines, x, y, angle

### Functions to read the .hw files

class HWfileError(Exception):
    pass

def hwfile(f, chars):
    mode = "main"
    oocerror = "{0} {1}: Encountered {2} command out of context"
    uperror = "{0} {1}: Unidentified parameter or insufficient arguments {2} for {3} command"
    iperror = "{0} {1}: All parameters for {2} not supplied"
    slerror = "{0} {1}: Subletter {2} not defined yet"
    ucerror = "{0} {1}: Unkown command {2}"
    verror = "{0} {1}: Value error: {2}"
    for lno, com in enumerate(f.readlines()):
        com = com.split()
        try:
            if not com or com[0].startswith("#"):
                pass
            elif com[0] == "load":
                nf = open(com[1], 'r')
                hwfile(nf, chars)
            elif com[0] == "letter":
                if mode == "main":
                    mode = "letter"
                    char = com[1]
                    strokes = []
                else:
                    raise HWfileError(oocerror.format(f.name, lno+1, com[0]))
            elif com[0] in ["stroke", "reposition", "arc", "subletter"]:
                if mode == "letter":
                    done = [1]*3 # Keeps track of whether all parameters are given
                    i = 1
                    if com[0] == "subletter":
                        done = [0]
                        if com[1] not in chars:
                            raise HWfileError(slerror.format(f.name, lno+1, com[1]))
                        xscale = yscale = 1.0
                        varm = VARM
                        i = 2
                    while i < len(com):
                        elser = False
                        if com[0] == "stroke":
                            if com[i] == "steps" and i+2 < len(com):
                                steps = float(com[i+1])
                                stepsvar = float(com[i+2])
                                done[0] = 0
                                i += 3
                            elif com[i] == "len" and i+2 < len(com):
                                llen = float(com[i+1])
                                llenvar = float(com[i+2])
                                done[1] = 0
                                i += 3
                            elif com[i] == "turn" and i+3 < len(com):
                                turni = float(com[i+1])
                                turnf = float(com[i+2])
                                turnvar = float(com[i+3])
                                done[2] = 0
                                i += 4
                            else: elser = True
                        elif com[0] == "reposition":
                            if com[i] == "x" and i+3 < len(com):
                                xtype = str(com[i+1])
                                x = float(com[i+2])
                                xvar = float(com[i+3])
                                done[0] = 0
                                i += 4
                            elif com[i] == "y" and i+3 < len(com):
                                ytype = str(com[i+1])
                                y = float(com[i+2])
                                yvar = float(com[i+3])
                                done[1] = 0
                                i += 4
                            elif com[i] == "angle" and i+3 < len(com):
                                angletype = str(com[i+1])
                                angle = float(com[i+2])
                                anglevar = float(com[i+3])
                                done[2] = 0
                                i += 4
                            else: elser = True
                        elif com[0] == "arc":
                            if com[i] == "radius" and i+1 < len(com):
                                radius = float(com[i+1])
                                done[0] = 0
                                i += 2
                            elif com[i] == "turn" and i+3 < len(com):
                                turn = float(com[i+1])
                                stepsvar = float(com[i+2])
                                turnvar = float(com[i+3])
                                done[1] = 0
                                i += 4
                            elif com[i] == "len" and i+2 < len(com):
                                llen = float(com[i+1])
                                llenvar = float(com[i+2])
                                done[2] = 0
                                i += 3
                            else: elser = True
                        elif com[0] == "subletter":
                            if com[i] == "xscale" and i+1 < len(com):
                                xscale = float(com[i+1])
                                i += 2
                            elif com[i] == "yscale" and i+1 < len(com):
                                yscale = float(com[i+1])
                                i += 2
                            elif com[i] == "scale" and i+1 < len(com):
                                xscale = yscale = float(com[i+1])
                                i += 2
                            elif com[i] == "varm" and i+1 < len(com):
                                varm = float(com[i+1])
                                i += 2
                            else: elser = True
                        else: elser = True # We should never reach this else
                        if not elser:
                            pass
                        elif com[i].startswith("#"):
                            i = len(com)
                        else:
                            raise HWfileError(uperror.format(f.name, lno+1, com[i], com[0]))
                    if sum(done) == 0:
                        if com[0] == "stroke": strokes.append(stroke(steps = steps, llen = llen, turni = turni, turnf = turnf, stepsvar = stepsvar, llenvar = llenvar, turnvar = turnvar))
                        elif com[0] == "reposition": strokes.append(reposition(xtype = xtype, x = x, xvar = xvar, ytype = ytype, y = y, yvar = yvar, angletype = angletype, angle = angle, anglevar = anglevar))
                        elif com[0] == "arc":
                            steps = radius*turn
                            turni = turnf = turn/steps
                            steps = abs(steps)
                            strokes.append(stroke(steps = steps, llen = llen, turni = turni, turnf = turnf, stepsvar = stepsvar, llenvar = llenvar, turnvar = turnvar))
                        elif com[0] == "subletter":
                            strokes.append(letter(strokes = chars[com[1]].strokes, char = chars[com[1]].char, varm = varm, xscale = xscale, yscale = yscale))
                    else:
                        raise HWfileError(iperror.format(f.name, lno+1, com[0]))
                else:
                    raise HWfileError(oocerror.format(f.name, lno+1, com[0]))
            elif com[0] == "end":
                if mode == "letter":
                    mode = "main"
                    chars[char] = letter(strokes, char)
                else: raise HWfileError(oocerror.format(f.name, lno+1, com[0]))
            else: raise HWfileError(ucerror.format(f.name, lno+1, com[0]))
        except ValueError as ve:
            raise HWfileError(verror.format(f.name, lno+1, ve))
        
def hwencode(s):
    maps = {' ':'\\s', '\t':'\\t', '\n':'\\n'}
    ret = []
    for l in s:
        if l in maps: ret.append(maps[l])
        else: ret.append(l)
    return ret

if __name__ == "__main__":
    with open("default.hw") as f:
        chars = {}
        hwfile(f, chars)
    x, y, a = 0, 0, 0
    k = []
    with open("text.txt") as txtf:
        mes = hwencode(txtf.read())
    for let in mes:#list('AaBbCcDd')+['\\n']+ list('EeFfGgHh')+['\\n'] + list('IiJjKkLl') + ['\\n'] + list('MmNnOoPp') + ['\\n']+ list('QqRrSsTt') + ['\\n']+ list('UuVvWw') + ['\\n']+ list('XxYyZz.,;'):
        l, x, y, a = chars[let](x, y, a, x, y, varm = VARM)
        k.extend(l)
    makeim(k)
