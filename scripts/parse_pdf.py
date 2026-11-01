import pdfplumber,sys,re,json,collections
GRP=re.compile(r'^\d{3}\s?[А-ЯA-Zа-я]?$')
def cluster(vals,tol):
    out=[]
    for v in sorted(vals):
        if out and v-out[-1][-1]<=tol: out[-1].append(v)
        else: out.append([v])
    return [sum(c)/len(c) for c in out]

def load(path):
    pdf=pdfplumber.open(path)
    words=[];dates=[];edges=[];headers=[]
    off=0;prev_last=None
    for pi,p in enumerate(pdf.pages):
        if not p.rects and not p.chars: continue
        bounds=sorted([r['top'] for r in p.rects]+[r['bottom'] for r in p.rects])
        if prev_last is not None: off=prev_last-bounds[0]
        prev_last=bounds[-1]+off
        edges+= [r['x0'] for r in p.rects if r['height']<2.6]
        rc=sorted([c for c in p.chars if not c['upright']],key=lambda c:c['top'])
        blk=[]
        for c in rc+[None]:
            if c is None or (blk and c['top']-blk[-1]['top']>3):
                if blk:
                    t=''.join(x['text'] for x in blk)
                    if not re.match(r'\d{2}\.\d{2}\.\d{4}',t): t=t[::-1]
                    m=re.search(r'(\d{2})\.(\d{2})\.(\d{4})',t)
                    if m: dates.append((m.group(3)+'-'+m.group(2)+'-'+m.group(1),(blk[0]['top']+blk[-1]['bottom'])/2+off))
                blk=[]
            if c is not None: blk.append(c)
        for w in p.extract_words(x_tolerance=0.25,y_tolerance=0.3):
            words.append(dict(text=w['text'],x0=w['x0'],x1=w['x1'],top=w['top']+off))
    return words,dates,cluster(edges,0.15)

def parse(path):
    words,dates,edges=load(path)
    # rows of words
    lines={}
    cur=None
    for w in sorted(words,key=lambda w:w['top']):
        if cur is None or w['top']-cur>0.2:
            cur=w['top']; lines[cur]=[]
        lines[cur].append(w)
    # header rows: many group labels
    hdr=[]
    for t,ws in lines.items():
        ws=sorted(ws,key=lambda w:w['x0'])
        labels=[];i=0
        while i<len(ws):
            tx=ws[i]['text'];x0=ws[i]['x0']
            if re.match(r'^\d{3}[А-Яа-я]?$',tx):
                if i+1<len(ws) and re.match(r'^[А-Яа-я]$',ws[i+1]['text']) and ws[i+1]['x0']-ws[i]['x1']<0.6:
                    tx+=ws[i+1]['text'];i+=1
                labels.append((tx.upper().replace(' ',''),x0))
            i+=1
        if len(labels)>=8: hdr.append((t,labels))
    hdr.sort()
    # merge header lines that are within 0.3
    H=[]
    for t,l in hdr:
        if H and t-H[-1][0]<0.5: continue
        H.append((t,l))
    days={}
    for hi,(ht,labels) in enumerate(H):
        nt=H[hi+1][0] if hi+1<len(H) else ht+16
        # date
        cand=[d for d in dates if ht-1<d[1]<nt]
        if not cand: continue
        date=cand[0][0]
        bw=[w for w in words if ht+0.5<w['top']<nt-0.4]
        rowof=lambda w:int(w['top']-ht+0.5)
        has_rv=any('Разговор' in w['text'] for w in bw)
        start=3 if has_rv else 1
        gs=sorted(labels,key=lambda x:x[1])
        G={}
        for name,lx in gs:
            gstart=max([e for e in edges if e<=lx-0.05],default=lx)
            nxt=[e for e in edges if e>gstart+0.3]
            G[name]=(gstart,nxt[:3])
        names=[g[0] for g in gs]
        starts=[G[n][0] for n in names]
        cells=collections.defaultdict(lambda:collections.defaultdict(list))
        for w in bw:
            idx=max([i for i,s in enumerate(starts) if s<=w['x0']+0.05],default=None)
            if idx is None: continue
            n=names[idx];gst,(e1,e2,e3)=G[n]
            if w['x0']>=e3-0.05: continue
            col=0 if w['x0']<e1-0.05 else (1 if w['x0']<e2-0.05 else 2)
            cells[n][(rowof(w),col)].append(w)
        for n in names:
            rows={}
            for (r,c),ws in cells[n].items():
                rows.setdefault(r,['','',''])[c]=' '.join(x['text'] for x in sorted(ws,key=lambda x:x['x0']))
            days.setdefault(n,{})[date]={'rv':has_rv and any('Разговор' in ' '.join(v) for r,v in rows.items() if r<start),
                                         'start':start,'rows':rows}
    return days

if __name__=='__main__':
    d=parse(sys.argv[1])
    json.dump(d,open(sys.argv[2],'w'),ensure_ascii=False,indent=0)
    print(len(d),sorted(d.keys()))
    for g in sorted(d): print(g,len(d[g]),min(d[g]),max(d[g]))
