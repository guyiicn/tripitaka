#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阿拉伯数字 -> 中文数字, 并重映射 v2 JSON 的所有位置索引(ju/dou/br/fen/xr/note/gx).
规则: 4位且1000-2999按年份逐字读(1925->一九二五); 其余按数值(21->二十一,3360->三千三百六十);
紧邻ASCII字母/下划线的数字(标识符/图档名 如 J27/p0157/01.gif)跳过不转.
用法: numconv.py test <json>  |  numconv.py batch <dataroot> <catalog.json>"""
import json, os, sys, glob, re, shutil

_D = '〇一二三四五六七八九'
def _digits(s): return ''.join(_D[int(c)] for c in s)
def _chunk(n):                       # 0..9999 完整式(10->一十,110->一百一十)
    if n == 0: return ''
    r = ''; zero = False
    for val, u in ((1000,'千'),(100,'百'),(10,'十'),(1,'')):
        d = (n // val) % 10
        if d == 0:
            if r: zero = True
        else:
            if zero: r += '〇'; zero = False
            r += _D[d] + u
    return r
def int_to_cn(n):
    if n == 0: return '〇'
    if n < 10000:
        r = _chunk(n)
    elif n < 100000000:
        hi, lo = n // 10000, n % 10000
        r = _chunk(hi) + '萬'
        if lo:
            if lo < 1000: r += '〇'
            r += _chunk(lo)
    else:
        return _digits(str(n))
    if r.startswith('一十'): r = '十' + r[2:]     # 十一..十九 去首一
    return r
def _conv_run(run, nxt):
    n = int(run)
    if len(run) == 4 and 1000 <= n <= 2999: return _digits(run)   # 年份
    return int_to_cn(n)

def _is_ident(ch): return ch.isascii() and (ch.isalpha() or ch == '_')

def convert_map(text):
    """返回 (新文本, newpos[]) —— newpos[i]=旧第i字在新文本的起始下标; newpos[len]=新长度."""
    L = len(text); out = []; newpos = [0]*(L+1); newlen = 0; i = 0
    while i < L:
        c = text[i]
        if c.isdigit():
            j = i
            while j < L and text[j].isdigit(): j += 1
            skip = (i > 0 and _is_ident(text[i-1])) or (j < L and _is_ident(text[j]))
            if skip:
                for k in range(i, j): newpos[k] = newlen; out.append(text[k]); newlen += 1
            else:
                cn = _conv_run(text[i:j], text[j] if j < L else '')
                for k in range(i, j): newpos[k] = newlen
                out.append(cn); newlen += len(cn)
            i = j
        else:
            newpos[i] = newlen; out.append(c); newlen += 1
    newpos[L] = newlen
    return ''.join(out), newpos

def convert_plain(s):                # 无索引的纯文本(标题/夹注/序题/by)
    return convert_map(s)[0] if s else s

def convert_obj(obj, stats):
    text = obj.get('text', '')
    if not text:
        for k in ('title','by'):
            if obj.get(k): obj[k] = convert_plain(obj[k])
        return obj, False
    if not re.search(r'[0-9]', text) and not re.search(r'[0-9]', obj.get('title','')+obj.get('by','')+''.join(f[1] for f in obj.get('fen',[]))+''.join(n[1] for n in obj.get('note',[]))):
        return obj, False            # 无数字, 不动
    nt, np = convert_map(text); L = len(text)
    def rm(x):
        if x <= 0: return 0
        if x >= L: return len(nt)
        return np[x]
    # 句读对齐自检: 标记落在非数字字上时, 字符必须保持不变
    for arr in (obj.get('ju',[]), obj.get('dou',[])):
        for p in arr:
            if 0 <= p < L and not text[p].isdigit() and nt[rm(p)] != text[p]:
                stats['viol'] += 1
    for g in obj.get('gx',[]):
        p = g[0]
        if 0 <= p < L and text[p] != '□' and nt[rm(p)] != text[p]:
            stats['viol'] += 1
    obj['text'] = nt
    obj['ju']  = sorted(set(rm(x) for x in obj.get('ju',[])))
    obj['dou'] = sorted(set(rm(x) for x in obj.get('dou',[])))
    obj['br']  = sorted(set(rm(x) for x in obj.get('br',[])))
    obj['fen'] = [[rm(f[0]), convert_plain(f[1]), (f[2] if len(f)>2 else 'fen')] for f in obj.get('fen',[])]
    obj['xr']  = [[rm(a), rm(b)] for a,b in obj.get('xr',[])]
    obj['note']= [[rm(nt2[0]), convert_plain(nt2[1])] for nt2 in obj.get('note',[])]
    obj['gx']  = [[rm(g[0]), g[1]] for g in obj.get('gx',[])]
    obj['n']   = len(nt)
    if obj.get('title'): obj['title'] = convert_plain(obj['title'])
    if obj.get('by'):    obj['by']    = convert_plain(obj['by'])
    return obj, True

# ---------------- CLI ----------------
def cmd_test(path):
    d = json.load(open(path, encoding='utf-8'))
    print('--- title:', repr(d.get('title')), '->', repr(convert_plain(d.get('title',''))))
    t = d.get('text','')
    for m in re.finditer(r'.{0,4}[0-9]+.{0,4}', t):
        a = m.group(); b = convert_map(a)[0]
        if a != b: print('  ', repr(a), '->', repr(b))
    obj2, ch = convert_obj(json.loads(json.dumps(d)), {'viol':0})
    print('changed:', ch, ' n:', d.get('n'), '->', obj2.get('n'), ' ju/dou keep:', len(d.get('ju',[])),'/',len(d.get('dou',[])),'->',len(obj2['ju']),'/',len(obj2['dou']))

def cmd_batch(dataroot, catalog):
    bak = os.path.join(os.path.dirname(dataroot.rstrip('/')), '_num_bak')
    os.makedirs(bak, exist_ok=True)
    stats = {'viol':0}; changed=0; scanned=0
    files = glob.glob(os.path.join(dataroot, '*', '*.json'))
    for f in files:
        scanned += 1
        try: d = json.load(open(f, encoding='utf-8'))
        except: continue
        obj, ch = convert_obj(d, stats)
        if ch:
            rel = os.path.relpath(f, dataroot); bf = os.path.join(bak, rel)
            os.makedirs(os.path.dirname(bf), exist_ok=True)
            if not os.path.exists(bf): shutil.copy2(f, bf)
            json.dump(obj, open(f,'w',encoding='utf-8'), ensure_ascii=False, separators=(',',':'))
            changed += 1
        if scanned % 4000 == 0: print('...', scanned, 'changed', changed, 'viol', stats['viol'])
    # catalog.json
    if catalog and os.path.exists(catalog):
        shutil.copy2(catalog, os.path.join(bak, 'catalog.json'))
        cat = json.load(open(catalog, encoding='utf-8'))
        for e in cat:
            for k in ('title','s','by'):
                if e.get(k): e[k] = convert_plain(e[k])
        json.dump(cat, open(catalog,'w',encoding='utf-8'), ensure_ascii=False, separators=(',',':'))
        print('catalog converted:', len(cat))
    print('DONE scanned', scanned, 'changed', changed, '句读对齐违规', stats['viol'], 'backup->', bak)

if __name__ == '__main__':
    if sys.argv[1] == 'test': cmd_test(sys.argv[2])
    elif sys.argv[1] == 'batch': cmd_batch(sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None)
