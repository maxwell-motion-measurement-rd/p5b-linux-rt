"""Functional host simulation; compiler barrier only, no ARM ordering claim."""
import ctypes as C, struct, sys, zlib
BASE=0x60200000
LTX,CTX,PUB,ACK=0x1000,0x2000,0x140,0x180
libc=C.CDLL(None,use_errno=True)
libc.mmap.restype=C.c_void_p
libc.mmap.argtypes=[C.c_void_p,C.c_size_t,C.c_int,C.c_int,C.c_int,C.c_long]
mapped=libc.mmap(BASE,0x4000,3,0x100022,-1,0) # anonymous, private, FIXED_NOREPLACE
assert mapped==BASE, ('simulation mapping failed',mapped,C.get_errno())
lib=C.CDLL(sys.argv[1])
def put32(off,x): C.memmove(BASE+off,struct.pack('<I',x),4)
def get32(off): return struct.unpack('<I',C.string_at(BASE+off,4))[0]
def get64(off): return struct.unpack('<Q',C.string_at(BASE+off,8))[0]
C.memmove(BASE+24,struct.pack('<Q',42),8)
lib.amp_ipc_init()
seq=gen=lastpub=0
session=71
checks=0
def send(kind,p=b'',corr=0,ep=42,corrupt=False,sess=None):
    global seq,gen
    seq=(seq+1)&0xffffffff
    head=struct.pack('<IHHHHIQQII',0x32504d41,1,kind,40,len(p),seq,
                     session if sess is None else sess,ep,corr,0)
    crc=zlib.crc32(head[:36]+p)^(1 if corrupt else 0)
    frame=head[:36]+struct.pack('<I',crc)+p
    assert get32(LTX+ACK)==gen
    C.memmove(BASE+LTX,frame,len(frame))
    gen=(gen+1)&0xffffffff
    put32(LTX+PUB,gen)
    lib.amp_ipc_poll()
    assert get32(LTX+ACK)==gen
    return seq
def receive(ack=True):
    global lastpub,checks
    pub=get32(CTX+PUB)
    assert pub!=lastpub, ('no new reply',pub)
    raw=C.string_at(BASE+CTX,296)
    v=struct.unpack('<IHHHHIQQII',raw[:40])
    payload=raw[40:40+v[4]]
    assert v[:2]==(0x32504d41,1) and v[3]==40 and v[4]<=256
    assert zlib.crc32(raw[:36]+payload)==v[9]
    assert v[6]==session and v[7]==42
    if ack: put32(CTX+ACK,pub)
    lastpub=pub
    checks+=1
    return dict(kind=v[2],seq=v[5],corr=v[8],p=payload,pub=pub)
def hello():
    origin=send(1,ep=0)
    r=receive()
    assert r['kind']==2 and r['corr']==origin and r['p']==b''
hello()
for n in [0,1,4,63,64,65,255,256]:
    for pattern in [bytes(n),b'\xff'*n,b'\x55'*n,b'\xaa'*n,bytes(range(n)),bytes((i*37+13)%256 for i in range(n))]:
        origin=send(3,pattern)
        r=receive()
        assert (r['kind'],r['corr'],r['p'])==(4,origin,pattern)
for kind in [6,7]:
    for n in [0,1,4,63,64,65,255,256]:
        original=bytes((i+19)%256 for i in range(n))
        origin=send(kind,original)
        challenge=receive()
        assert challenge['kind']==3 and challenge['corr']==origin
        assert challenge['p']==bytes((i^challenge['seq']^0xa5)&255 for i in range(n))
        send(4,challenge['p'],challenge['seq'])
        r=receive()
        assert r['corr']==origin and r['kind']==(4 if kind==7 else 2)
        assert r['p']==(original if kind==7 else b'')
# Keep the peer's output slot occupied while submitting one more request.
first=send(3,b'first')
r=receive(ack=False)
assert r['corr']==first
second=send(3,b'second')
assert get32(CTX+PUB)==r['pub'], 'unacknowledged slot overwritten'
put32(CTX+ACK,r['pub'])
lib.amp_ipc_poll()
r=receive()
assert r['corr']==second and r['p']==b'second'
# Rejected frames must be consumed without executing their payload.
assert get64(144)==0
for args in [dict(corrupt=True),dict(ep=43),dict(sess=99)]:
    before=get32(CTX+PUB)
    send(3,b'bad',**args)
    assert get32(CTX+PUB)==before
    hello() # explicit recovery/new handshake, not a timeout retry
assert get64(144)==3
# New session cancels an outstanding reverse transaction.
send(6,b'old')
receive()
session=123
hello()
origin=send(3,b'new session')
r=receive()
assert r['corr']==origin and r['p']==b'new session'
print('HOST_IPC_REPLY_CHECKS_PASSED=%d'%checks)
print('BACKPRESSURE_REJECTIONS_AND_NEW_SESSION=passed')
print('ARM_MEMORY_ORDERING_TESTED=false')
