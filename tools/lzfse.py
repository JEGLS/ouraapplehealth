import struct
L_EB=[0]*16+[2,3,5,8]; L_BV=list(range(16))+[16,20,28,60]
M_EB=[0]*16+[3,5,8,11]; M_BV=list(range(16))+[16,24,56,312]
D_EB=[i//4 if i>=4 else 0 for i in range(64)]
D_EB=[0,0,0,0]+[ (i-4)//4+1 for i in range(4,64)]
D_BV=[0]
for i in range(1,64):
    D_BV.append(D_BV[-1]+(1<<D_EB[i-1]))
NB=[2,3,2,5,2,3,2,8,2,3,2,5,2,3,2,14]*2
VT=[0,2,1,4,0,3,1,-1,0,2,1,5,0,3,1,-1,0,2,1,6,0,3,1,-1,0,2,1,7,0,3,1,-1]
def clz32(x): return 32-x.bit_length()
def fv(bits):
    b=bits&31; n=NB[b]
    if n==8: return 8+((bits>>4)&0xf),n
    if n==14: return 24+((bits>>4)&0x3ff),n
    return VT[b],n
def lit_table(nstates,freq):
    t=[]; nclz=clz32(nstates)
    for i,f in enumerate(freq):
        if not f: continue
        k=clz32(f)-nclz; j0=((2*nstates)>>k)-f
        for j in range(f):
            if j<j0: t.append((k,i,((f+j)<<k)-nstates))
            else: t.append((k-1,i,(j-j0)<<(k-1)))
    assert len(t)==nstates,(len(t),nstates)
    return t
def val_table(nstates,freq,eb,bv):
    t=[]; nclz=clz32(nstates)
    for i,f in enumerate(freq):
        if not f: continue
        k=clz32(f)-nclz; j0=((2*nstates)>>k)-f
        for j in range(f):
            if j<j0: t.append((k+eb[i],eb[i],((f+j)<<k)-nstates,bv[i]))
            else: t.append((k-1+eb[i],eb[i],(j-j0)<<(k-1),bv[i]))
    assert len(t)==nstates
    return t
M64=(1<<64)-1
class In:
    def __init__(s,buf,start,end,n):
        s.b=buf; s.start=start
        if n:
            s.p=end-8; s.acc=int.from_bytes(buf[s.p:s.p+8],'little'); s.nb=n+64
        else:
            s.p=end-7; s.acc=int.from_bytes(buf[s.p:s.p+7],'little'); s.nb=n+56
        assert s.p>=start
    def flush(s):
        nbits=(63-s.nb)&~7
        p=s.p-(nbits>>3)
        if p<s.start:
            nbits=(s.p-s.start)*8; p=s.start
        s.p=p
        inc=int.from_bytes(s.b[p:p+8].ljust(8,b'\0'),'little')
        s.acc=((s.acc<<nbits)|(inc&((1<<nbits)-1)))&M64
        s.nb+=nbits
    def pull(s,n):
        s.nb-=n; r=s.acc>>s.nb; s.acc&=(1<<s.nb)-1; return r
def gf(v,o,n): return (v>>o)&((1<<n)-1)
def decode(buf,pos=0):
    out=bytearray()
    while True:
        magic=buf[pos:pos+4]
        if magic==b'bvx$': return bytes(out),pos+4
        if magic==b'bvx-':
            n=struct.unpack_from('<I',buf,pos+4)[0]; out+=buf[pos+8:pos+8+n]; pos+=8+n; continue
        if magic!=b'bvx2': raise ValueError('unsupported block %r at %d'%(magic,pos))
        nraw,v0,v1,v2=struct.unpack_from('<IQQQ',buf,pos+4)
        n_lit=gf(v0,0,20); n_litb=gf(v0,20,20); n_m=gf(v0,40,20); litbits=gf(v0,60,3)-7
        ls=[gf(v1,i*10,10) for i in range(4)]; n_lmdb=gf(v1,40,20); lmdbits=gf(v1,60,3)-7
        hs=gf(v2,0,32); lst=gf(v2,32,10); mst=gf(v2,42,10); dst=gf(v2,52,10)
        freqs=[]; p=pos+32; end=pos+hs; acc=0; an=0
        for i in range(20+20+64+256):
            while p<end and an+8<=32:
                acc|=buf[p]<<an; an+=8; p+=1
            f,n=fv(acc); assert n<=an; freqs.append(f); acc>>=n; an-=n
        lf,mf,df,litf=freqs[:20],freqs[20:40],freqs[40:104],freqs[104:]
        bs=pos+hs
        lt=lit_table(1024,litf)
        ins=In(buf,bs,bs+n_litb,litbits)
        lits=bytearray()
        st=ls[:]
        for i in range(0,n_lit,4):
            ins.flush()
            for j in range(4):
                k,sym,d=lt[st[j]]; st[j]=d+ins.pull(k); lits.append(sym)
        Lt=val_table(64,lf,L_EB,L_BV); Mt=val_table(64,mf,M_EB,M_BV); Dt=val_table(256,df,D_EB,D_BV)
        ins=In(buf,bs+n_litb,bs+n_litb+n_lmdb,lmdbits)
        li=0; D=-1; start=len(out)
        def vd(tab,s):
            tb,vb,de,base=tab[s]; b=ins.pull(tb); return de+(b>>vb), base+(b&((1<<vb)-1))
        for _ in range(n_m):
            ins.flush()
            lst,L=vd(Lt,lst); mst,M=vd(Mt,mst); dst,nd=vd(Dt,dst)
            if nd: D=nd
            out+=lits[li:li+L]; li+=L
            for _ in range(M): out.append(out[-D])
        assert len(out)-start==nraw,(len(out)-start,nraw)
        pos=bs+n_litb+n_lmdb
