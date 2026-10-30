"""Cross-check C codec against Python struct/zlib (run on Ubuntu)."""
import ctypes as C, pathlib, struct, sys, zlib
class View(C.Structure):
    _fields_=[('type',C.c_uint16),('payload_len',C.c_uint16),('seq',C.c_uint32),
              ('correlation',C.c_uint32),('session',C.c_uint64),('epoch',C.c_uint64),
              ('payload',C.POINTER(C.c_uint8))]
U8=C.c_uint8
lib=C.CDLL(sys.argv[1])
lib.amp_encode.argtypes=[C.POINTER(U8),C.c_size_t,C.POINTER(View)]
lib.amp_decode.argtypes=[C.POINTER(U8),C.c_size_t,C.POINTER(View)]
lib.amp_crc32.argtypes=[C.POINTER(U8),C.c_size_t]
lib.amp_crc32.restype=C.c_uint32
def arr(b): return (U8*max(1,len(b)))(*b)
assert lib.amp_crc32(arr(b'123456789'),9)==zlib.crc32(b'123456789')==0xcbf43926
passed=1
for n in [0,1,4,63,64,65,255,256]:
    for pattern in [bytes(n),b'\xff'*n,b'\x55'*n,b'\xaa'*n,bytes(i%256 for i in range(n))]:
        head=struct.pack('<IHHHHIQQII',0x32504d41,1,3,40,n,0xffffffff,
                         0x0123456789abcdef,0xfedcba9876543210,19,0)
        crc=zlib.crc32(head[:36]+pattern)
        expected=head[:36]+struct.pack('<I',crc)+pattern
        payload=arr(pattern)
        v=View(3,n,0xffffffff,19,0x0123456789abcdef,0xfedcba9876543210,payload)
        out=(U8*320)(*([0xa5]*320))
        assert lib.amp_encode(out,296,C.byref(v))==len(expected)
        assert bytes(out)[:len(expected)]==expected
        assert bytes(out)[len(expected):]==b'\xa5'*(320-len(expected))
        got=View()
        encoded=arr(expected)
        assert lib.amp_decode(encoded,len(expected),C.byref(got))==0
        assert (got.type,got.payload_len,got.seq,got.correlation,got.session,got.epoch)==(v.type,n,v.seq,v.correlation,v.session,v.epoch)
        assert C.string_at(got.payload,n)==pattern
        tiny=(U8*320)(*([0xa5]*320))
        assert lib.amp_encode(tiny,len(expected)-1,C.byref(v))==-1
        assert bytes(tiny)==b'\xa5'*320
        passed+=1
        for index in [16,24,32,36]+([40,len(expected)-1] if n else []):
            bad=bytearray(expected); bad[index]^=1
            assert lib.amp_decode(arr(bad),len(bad),C.byref(got))==-5
            passed+=1
for n in range(40):
    assert lib.amp_decode(arr(bytes(n)),n,C.byref(View()))==-1
    passed+=1
for index,val,code in [(0,0,-2),(4,2,-3),(8,39,-4)]:
    bad=bytearray(expected); bad[index]=val
    assert lib.amp_decode(arr(bad),len(bad),C.byref(View()))==code
    passed+=1
bad=bytearray(expected); struct.pack_into('<H',bad,10,257)
assert lib.amp_decode(arr(bad),len(bad),C.byref(View()))==-1
passed+=1
print('INDEPENDENT_CODEC_CHECKS_PASSED=%d'%passed)
print('BOARD_MESSAGE_PATH_TESTED=false')
