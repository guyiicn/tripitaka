import glob,os,random,sqlite3,time,sys,zstandard as zstd
# 用法: build_db.py [data_root] [catalog.json] [out.db]  (默认 /srv/cbeta)
DATA=sys.argv[1] if len(sys.argv)>1 else "/srv/cbeta/data"
CAT =sys.argv[2] if len(sys.argv)>2 else "/srv/cbeta/catalog.json"
DB  =sys.argv[3] if len(sys.argv)>3 else "/tmp/tripitaka.db"
t0=time.time(); LOG="/tmp/db_build.log"
def log(m):
    open(LOG,"a").write("[%s] %s\n"%(time.strftime("%H:%M:%S"),m))
files=[f for f in glob.glob(DATA+"/*/*.json") if not f.endswith("_meta.json")]
metas=glob.glob(DATA+"/*/_meta.json")
log("START files=%d metas=%d"%(len(files),len(metas)))
random.seed(1)
train=[open(f,"rb").read() for f in random.sample(files,min(12000,len(files)))]
dic=zstd.train_dictionary(128*1024, train)
log("dict trained %d bytes"%len(dic.as_bytes()))
c=zstd.ZstdCompressor(level=19, dict_data=dic)
d=zstd.ZstdDecompressor(dict_data=dic)
if os.path.exists(DB): os.remove(DB)
db=sqlite3.connect(DB)
db.execute("PRAGMA page_size=4096"); db.execute("PRAGMA journal_mode=OFF")
db.execute("CREATE TABLE juan(id TEXT,jn TEXT,zb BLOB,PRIMARY KEY(id,jn)) WITHOUT ROWID")
db.execute("CREATE TABLE meta(id TEXT PRIMARY KEY,zb BLOB)")
db.execute("CREATE TABLE kv(k TEXT PRIMARY KEY,v BLOB)")
db.execute("INSERT INTO kv VALUES('dict',?)",(dic.as_bytes(),))
db.execute("INSERT INTO kv VALUES('schema','2')")
db.execute("INSERT INTO kv VALUES('catalog',?)",(c.compress(open(CAT,"rb").read()),))
for i,mf in enumerate(metas):
    jid=os.path.basename(os.path.dirname(mf))
    db.execute("INSERT INTO meta VALUES(?,?)",(jid,c.compress(open(mf,"rb").read())))
log("meta done")
n=0
for jf in files:
    jid=os.path.basename(os.path.dirname(jf)); jn=os.path.basename(jf)[:-5]
    db.execute("INSERT INTO juan VALUES(?,?,?)",(jid,jn,c.compress(open(jf,"rb").read()))); n+=1
    if n%3000==0: log("...%d/%d"%(n,len(files)))
db.commit(); log("all inserted, vacuum...")
db.execute("VACUUM"); db.commit()
# 抽样往返校验
row=db.execute("SELECT zb FROM juan WHERE id='T0235' AND jn='001'").fetchone()
ok=d.decompress(row[0])[:20]
db.close()
sz=os.path.getsize(DB)
log("DONE DB=%.1f MB  sample=%s  %.0fs"%(sz/1e6, ok.decode('utf-8','replace'), time.time()-t0))
