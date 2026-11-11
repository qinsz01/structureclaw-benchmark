"""Experimental 2027-only ABI probe; not a production qualification or 2025 guard edit."""
import ctypes as c
import hashlib
from pathlib import Path

DLL=Path(r'C:\PKPM2027R1.0.1\Ribbon\PM\PmsrwData_x64.dll')
SHA='0045850ca7dfa7f2f3a71fd6b6f807d1be432974f30e388a520185dbf60a00f9'
class Material(c.Structure):
    _fields_=[('vtable',c.c_void_p),('id',c.c_int),('kind',c.c_int),('name',c.c_char*32),('data',c.c_double*20)]
class Guarded(c.Structure):
    _fields_=[('before',c.c_ubyte*64),('record',Material),('after',c.c_ubyte*64)]
assert c.sizeof(Material)==208 and Material.data.offset==48
assert hashlib.sha256(DLL.read_bytes()).hexdigest()==SHA
lib=c.CDLL(str(DLL))
lib.AddOneUserMaterial.argtypes=[c.POINTER(Material)]; lib.AddOneUserMaterial.restype=None
lib.GetUserMaterialByID.argtypes=[c.c_int,c.POINTER(Material),c.POINTER(c.c_int)];lib.GetUserMaterialByID.restype=None
@c.WINFUNCTYPE(c.c_void_p,c.c_void_p,c.c_void_p)
def copy_record(target,source):
    c.memmove(target+8,source+8,200)
    return target
vtable=(c.c_void_p*1)(c.cast(copy_record,c.c_void_p).value)
def new():
    g=Guarded();g.before[:]=[0xa5]*64;g.after[:]=[0x5a]*64;g.record.vtable=c.addressof(vtable)
    return g
def valid(g):
    assert list(g.before)==[0xa5]*64 and list(g.after)==[0x5a]*64
    assert g.record.vtable==c.addressof(vtable)
def read(identity):
    g=new();status=c.c_int(-8)
    lib.GetUserMaterialByID(identity,c.byref(g.record),c.byref(status));valid(g)
    assert status.value==0 and g.record.id==identity
    return {'nativeMaterialId':g.record.id,'kind':g.record.kind,'name':g.record.name.decode('ascii'),
            'nativeValues':list(g.record.data),'guardBytesIntact':True,'dllSha256':SHA,'recordBytes':208}
def add(name,E,nu):
    g=new();g.record.kind=15;g.record.name=name.encode('ascii');g.record.data[:3]=[0.,E,nu]
    lib.AddOneUserMaterial(c.byref(g.record));valid(g)
    out=read(g.record.id)
    assert out['nativeValues']==list(g.record.data) and out['name']==name and out['kind']==15
    out['requested']={'E_MPa':E,'nu':nu,'unitWeight':0.}
    out['status']='ABI microprobe; native solve verification separate'
    return out
