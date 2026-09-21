"""Independent streaming check of exported 8K PNG values, no Qt/GPU involved."""
import array
import json
import os
import struct
import zlib
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK=os.path.join(ROOT,"work")


def png_rows(filename,row_size):
    pending=bytearray()
    decoder=zlib.decompressobj()
    with open(filename,"rb") as stream:
        assert stream.read(8)==b"\x89PNG\r\n\x1a\n"
        while True:
            length,kind=struct.unpack(">I4s",stream.read(8))
            payload=stream.read(length)
            crc=struct.unpack(">I",stream.read(4))[0]
            assert crc==(zlib.crc32(kind+payload)&0xffffffff)
            if kind==b"IDAT":
                remaining=payload
                while remaining:
                    block=decoder.decompress(remaining,1024*1024)
                    remaining=decoder.unconsumed_tail
                    pending.extend(block)
                    position=0
                    while len(pending)-position>=row_size+1:
                        assert pending[position]==0
                        yield bytes(pending[position+1:position+row_size+1])
                        position+=row_size+1
                    if position:
                        del pending[:position]
            if kind==b"IEND":
                assert decoder.eof
                assert not pending
                break


row=array.array("H",(round(x*65535/8191) for x in range(8192)))
row.byteswap()
expected=row.tobytes()
count=0
for actual in png_rows(os.path.join(WORK,"8k_displacement.png"),16384):
    assert actual==expected,"Displacement mismatch at row %d"%count
    count+=1
assert count==8192
report={"8k_displacement_all_pixels_exact":True,"rows":count,"samples":8192*count}
with open(os.path.join(WORK,"large_file_verification.json"),"w") as stream:
    json.dump(report,stream,indent=2)
print(report)
