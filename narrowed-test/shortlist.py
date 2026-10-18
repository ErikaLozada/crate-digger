import json,glob,os,sys,math,re
sys.path.insert(0,'.'); import vocab
R=json.load(open('../results.json')); LAB=json.load(open('labels.json'))
S=set(vocab.STYLES); T=set(vocab.TAGS)
LIB={str(r[0]):r for r in R['libList']}
def parse(p):
    s=open(p).read(); a=s.find('{'); b=s.rfind('}'); return json.loads(s[a:b+1])
def step1(rid):
    d=parse(f's1/{rid}.json'); d['bad']=[]
    if d.get('s') not in S: d['bad'].append(d.get('s')); d['s']=None
    near=[x for x in d.get('near',[]) if x in S]; d['bad']+=[x for x in d.get('near',[]) if x not in S]; d['near']=near
    d['bad']+=[x for x in d.get('t',[]) if x not in T]; d['t']=[x for x in d.get('t',[]) if x in T]
    return d
def name(cid):
    if cid[0]=='L':
        r=LIB[cid[1:]]; return f"{r[1]} — {r[2]}", r[5], r[6]
    t=R['recs'][cid[1:]]; return f"{t['artist']} — {t['title']}", None, None
def score(q,c):
    st=0
    if c['s']==q['s']: st=6
    elif c['s'] in q['near'] or (c.get('s2') and c['s2']==q['s']): st=3
    elif c.get('s2') and c['s2'] in q['near']: st=1
    if not st: return 0
    tg=min(4,len(set(q['t'])&set(c.get('t',[]))))
    er=0
    if q.get('e') and c.get('e'):
        dd=abs(int(q['e'])-int(c['e'])); er=1 if dd==0 else .5 if dd==10 else 0
    return st+tg+er
def shortlist(rid,q,n=30):
    own=R['lib'].get(str(rid)); skip={'L'+str(own['k'])} if own else set()
    out=[]
    for cid,c in LAB.items():
        if cid in skip: continue
        sc=score(q,c)
        if sc:
            _,plays,_=name(cid); out.append((sc+ (0.2 if (plays or 0)>0 or cid[0]=='S' else 0), cid))
    out.sort(key=lambda x:(-x[0],x[1]))
    return out[:n], len(out)
if __name__=='__main__':
    res={}
    for rid in R['want_order']:
        q=step1(rid); sl,tot=shortlist(rid,q)
        res[str(rid)]={'q':q,'short':[c for _,c in sl],'scores':[s for s,_ in sl],'pool':tot}
        t=R['recs'][str(rid)]
        print(f"{rid} {t['artist']} — {t['title']}: {q['s']} | near {q['near']} | {q['t']} | {q.get('e')} | sure {q.get('sure')} | bad {q['bad']} | pool {tot}")
    json.dump(res,open('short.json','w'),ensure_ascii=False)
