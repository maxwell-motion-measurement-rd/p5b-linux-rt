"""r004 host model: negative paths and fake counter time; no ARM ordering claim."""
import pathlib,sys
auto_heartbeat=True
python_heartbeat=0
def beat():
    global python_heartbeat
    if auto_heartbeat:
        python_heartbeat+=1
        C.memmove(BASE+216,struct.pack('<Q',python_heartbeat),8)
legacy=pathlib.Path(sys.argv[2]).read_text()
legacy=legacy.replace("C.memmove(BASE+24,struct.pack('<Q',42),8)","C.memmove(BASE+16,struct.pack('<Q',100000000),8)\nC.memmove(BASE+24,struct.pack('<Q',42),8)")
legacy=legacy.replace('session=71','session=71\nepoch=42').replace('v[7]==42','v[7]==epoch')
legacy=legacy.replace('def hello():\n    origin=', 'def hello():\n    global session\n    session+=1\n    origin=')
legacy=legacy.replace('lib.amp_ipc_poll()','beat();lib.amp_ipc_poll()')
exec(compile(legacy,sys.argv[2],'exec'))
fault_checks=0
clock=C.c_uint64.in_dll(lib,'amp_test_ticks')
def raw_send(kind):
    global seq,gen
    seq=(seq+1)&0xffffffff
    frame=bytearray(struct.pack('<IHHHHIQQII',0x32504d41,1,3,40,1,seq,session,epoch,0,0)+b'X')
    if kind==1:frame[0]^=1
    elif kind==2:frame[4]=2
    elif kind==3:frame[8]=39
    elif kind==4:struct.pack_into('<H',frame,10,257)
    elif kind==6:struct.pack_into('<I',frame,12,(seq-1)&0xffffffff)
    elif kind==7:frame[16]^=1
    elif kind==8:frame[24]^=1
    struct.pack_into('<I',frame,36,zlib.crc32(frame[:36]+frame[40:]))
    if kind==5:frame[36]^=1
    assert get32(LTX+ACK)==gen
    C.memmove(BASE+LTX,bytes(frame),len(frame));gen=(gen+1)&0xffffffff;put32(LTX+PUB,gen)
    before=get32(CTX+PUB);lib.amp_ipc_poll()
    assert get32(LTX+ACK)==gen and get32(CTX+PUB)==before
    assert get32(152)=={1:2,2:3,3:4,4:1,5:5,6:8,7:6,8:7}[kind]
def raw_receive():
    global lastpub
    pub=get32(CTX+PUB);assert pub!=lastpub
    raw=C.string_at(BASE+CTX,296)
    put32(CTX+ACK,pub);lastpub=pub
    return raw
for kind in range(1,9):
    for repeat in range(10):
        raw_send(kind);hello();fault_checks+=1
        before_wire=struct.unpack_from('<I',C.string_at(BASE+CTX,40),12)[0]
        send(0x70,struct.pack('<I',kind))
        raw=raw_receive();h=struct.unpack('<IHHHHIQQII',raw[:40])
        if kind==1:assert h[0]!=0x32504d41
        elif kind==2:assert h[1]!=1
        elif kind==3:assert h[3]!=40
        elif kind==4:assert h[4]==257
        elif kind==5:assert zlib.crc32(raw[:36]+raw[40:40+h[4]])!=h[9]
        else:
            assert zlib.crc32(raw[:36]+raw[40:40+h[4]])==h[9]
            if kind==6:assert h[5]==before_wire
            if kind==7:assert h[6]!=session
            if kind==8:assert h[7]!=epoch
        hello();fault_checks+=1
for repeat in range(10):
    before=get64(168)
    origin=send(6,b'reverse timeout')
    receive()
    clock.value+=10000001;lib.amp_ipc_poll()
    r=receive();assert r['kind']==5 and r['corr']==origin
    assert get64(168)==before+1 and get64(192)-get64(184)>=10000000
    hello();fault_checks+=1
for repeat in range(10):
    send(0x71,struct.pack('<I',1000));receive()
    seq=(seq+1)&0xffffffff
    p=b'paused';head=struct.pack('<IHHHHIQQII',0x32504d41,1,3,40,len(p),seq,session,epoch,0,0)
    frame=head[:36]+struct.pack('<I',zlib.crc32(head[:36]+p))+p
    C.memmove(BASE+LTX,frame,len(frame));gen=(gen+1)&0xffffffff;put32(LTX+PUB,gen)
    lib.amp_ipc_poll();assert get32(LTX+ACK)!=gen
    clock.value+=99999999;beat();lib.amp_ipc_poll();assert get32(LTX+ACK)!=gen
    clock.value+=1;lib.amp_ipc_poll();assert get32(LTX+ACK)==gen
    r=receive();assert r['p']==p and r['corr']==seq
    fault_checks+=1
for repeat in range(10):
    seq=0xfffffffd;hello()
    for expected in [0xffffffff,0,1]:
        sent_seq=send(3,b'wrap',ep=epoch);assert sent_seq==expected
        assert receive()['p']==b'wrap'
    fault_checks+=1
    send(0x73,struct.pack('<I',0xfffffffd),ep=epoch)
    assert receive()['seq']==0xfffffffe
    for expected in [0xffffffff,0,1]:
        send(3,b'wrap back',ep=epoch);assert receive()['seq']==expected
    fault_checks+=1
for repeat in range(10):
    before=get64(200);old_epoch=epoch;old_pub=get32(CTX+PUB)
    send(0x72,ep=epoch)
    epoch=get64(160)
    assert epoch==old_epoch+1 and get64(200)==before+1 and get32(CTX+PUB)==old_pub
    assert get64(24)==42, 'communication reset changed boot token'
    send(1,ep=0)
    assert get32(CTX+PUB)==old_pub and get32(152)==6, 'old HELLO reinstalled retired session'
    session+=1;hello()
    for i in range(100):
        send(3,b'after service reset',ep=epoch)
        assert receive()['p']==b'after service reset'
    fault_checks+=1
auto_heartbeat=False
put32(216,1);lib.amp_ipc_poll();before=get64(232)
clock.value+=100000000;lib.amp_ipc_poll()
assert get64(232)==before+1 and get64(248)>=100000000
old_pub=get32(CTX+PUB);send(3,b'heartbeat lost',ep=epoch)
assert get32(CTX+PUB)==old_pub and get32(152)==11
put32(216,2);lib.amp_ipc_poll();assert get64(240)==1
auto_heartbeat=True
hello();send(3,b'heartbeat restored',ep=epoch);assert receive()['p']==b'heartbeat restored'
fault_checks+=1
send(0x74,struct.pack('<I',1200),ep=epoch);receive()
assert lib.amp_heartbeat_allowed()==0
clock.value+=119999999;assert lib.amp_heartbeat_allowed()==0
clock.value+=1;assert lib.amp_heartbeat_allowed()==1
beat();lib.amp_ipc_poll()
fault_checks+=1
print('G4_HOST_FAULT_SCENARIOS_PASSED=%d'%fault_checks)
print('HARDWARE_FAULT_INJECTION_TESTED=false')
