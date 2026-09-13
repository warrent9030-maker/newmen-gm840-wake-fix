"""Authored LED overlay assembler; no firmware input or hardware access."""
BASE=0x9100
class Asm:
    def __init__(self):self.b=bytearray();self.labels={};self.fix=[]
    def e(self,*b):self.b.extend(b)
    def label(self,n):self.labels[n]=BASE+len(self.b)
    def jump(self,target):
        self.e(0x02)
        if isinstance(target,int):self.e(target>>8,target&255)
        else:self.fix.append((len(self.b),target));self.e(0,0)
    def bitbranch(self,bit,target,on=False):
        # Opposite short branch skips the long target jump.
        self.e(0x30 if on else 0x20,bit,3);self.jump(target)
    def cond(self,op,target):
        self.e({0x40:0x50,0x50:0x40,0x60:0x70,0x70:0x60}[op],3);self.jump(target)
    def finish(self):
        for off,n in self.fix:self.b[off:off+2]=self.labels[n].to_bytes(2,'big')
        return self.b


def assemble():
    a=Asm()
    a.label('colour')
    a.e(0xe5,0x5e);a.bitbranch(0xe5,'stock_colour') # Fn matrix index 65
    a.e(0xe5,0x59);a.bitbranch(0xe4,'stock_colour') # B matrix index 34
    # All non-number lights stay off during the overlay.
    a.e(0xe5,0x18,0xc3,0x94,22);a.cond(0x40,'emit')
    a.e(0xe5,0x18,0xc3,0x94,32);a.cond(0x50,'emit')
    # Only use battery data after a valid vendor status; wired mode may lack it.
    a.e(0x90,0x0f,0x10,0xe0,0x64,0xbb);a.cond(0x70,'unknown')
    a.e(0x90,0x0f,0x3a,0xe0);a.bitbranch(0xe7,'unknown')
    a.e(0x90,0x0f,0x80,0xe0,0xc3,0x13,0x54,7,0xf9)
    # Rounded relative gauge. Lowest raw level retains a red warning light.
    a.e(0x90);a.fix.append((len(a.b),'counts'));a.e(0,0,0xe9,0x93,0xf8)
    a.e(0xe5,0x18,0xc3,0x94,22,0xc3,0x98);a.cond(0x50,'emit')
    # Raw 0..1 red, 2..3 amber, 4..7 green; colours are channel 0/1/2.
    a.e(0xe9,0xc3,0x94,2);a.cond(0x40,'red')
    a.e(0xe9,0xc3,0x94,4);a.cond(0x40,'amber')
    a.e(0xe5,0x19,0x64,1);a.cond(0x70,'emit');a.jump('on')
    a.label('red');a.e(0xe5,0x19);a.cond(0x70,'emit');a.jump('on')
    a.label('amber');a.e(0xe5,0x19,0xc3,0x94,2);a.cond(0x50,'emit');a.jump('on')
    # Unknown reading: blue endpoint lights (1 and 0), never a fake full bar.
    a.label('unknown');a.e(0xe5,0x19,0x64,2);a.cond(0x70,'emit')
    a.e(0xe5,0x18,0x64,22);a.cond(0x60,'on')
    a.e(0xe5,0x18,0x64,31);a.cond(0x70,'emit')
    a.label('on');a.e(0x75,0x15,2,0x75,0x16,0x80)
    a.label('emit');a.jump(0x1e58)
    a.label('stock_colour');a.bitbranch(0x29,0x1c50);a.jump(0x1c44)
    a.label('enable')
    a.e(0xe5,0x5e);a.bitbranch(0xe5,'stock_enable')
    a.e(0xe5,0x59);a.bitbranch(0xe4,'stock_enable');a.jump(0x1e66)
    a.label('stock_enable');a.bitbranch(0x1a,0x1e6f,on=True);a.jump(0x1e66)
    a.label('counts');a.e(1,1,3,4,6,7,9,10)
    code=a.finish()
    return bytes(code)

if __name__ == "__main__":
    print(assemble().hex())
