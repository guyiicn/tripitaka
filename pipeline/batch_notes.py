#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全 corpus 夹注/缺字批处理 (hk2 本地跑, 脱离 ssh).
   - () 夹注 -> note[] 锚点; [组字式]缺字 -> □ (公式存 gx); 重映射 ju/dou/fen/br/xr
   - 幂等: 处理过的打 v=2, 重跑自动跳过 (断线直接再发起即可续)
   - 原子写: .tmp + os.replace, 半路被杀不留坏文件
   - 未闭合括号防护: 落单 ( 或 [ 退化为普通字符, 不吞后文
   用法: batch_notes.py            (处理全部, 跳过已完成)
         batch_notes.py --force    (强制重处理, 需先确保数据是原始态)
"""
import os, glob, json, sys, time

DATA = "/srv/cbeta/data"
LOG  = "/tmp/fontwork/batch.log"
XU_END = ("序", "敘")
FORCE = "--force" in sys.argv

def log(msg):
    line = "[%s] %s" % (time.strftime("%m-%d %H:%M:%S"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)

def find_close(s, i, op, cl):
    """s[i]==op; 返回匹配 cl 的下标, 未闭合返回 -1"""
    depth = 0; j = i
    while j < len(s):
        if s[j] == op: depth += 1
        elif s[j] == cl:
            depth -= 1
            if depth == 0: return j
        j += 1
    return -1

def strip_gaiji_in_note(inner):
    out = []; i = 0
    while i < len(inner):
        if inner[i] == '[':
            j = find_close(inner, i, '[', ']')
            if j < 0:                      # 未闭合 -> 当普通字符
                out.append(inner[i]); i += 1
            else:
                out.append('□'); i = j + 1
        else:
            out.append(inner[i]); i += 1
    return ''.join(out)

def transform_text(s):
    new = []; notes = []; gx = []
    nof = [-1] * len(s)
    i = 0
    while i < len(s):
        c = s[i]
        if c == '[':
            j = find_close(s, i, '[', ']')
            if j < 0:                       # 未闭合 [ -> 普通字符
                ni = len(new); new.append(c); nof[i] = ni; i += 1; continue
            formula = s[i+1:j]
            ni = len(new); new.append('□'); gx.append([ni, formula])
            for k in range(i, j+1): nof[k] = ni
            i = j + 1
        elif c == '(':
            j = find_close(s, i, '(', ')')
            if j < 0:                       # 未闭合 ( -> 普通字符
                ni = len(new); new.append(c); nof[i] = ni; i += 1; continue
            inner = s[i+1:j]
            notes.append([len(new) - 1, strip_gaiji_in_note(inner)])
            for k in range(i, j+1): nof[k] = len(new) - 1
            i = j + 1
        else:
            ni = len(new); new.append(c); nof[i] = ni; i += 1
    return ''.join(new), notes, gx, nof

def remap_marks(idxs, nof, s):
    out = []
    for x in idxs:
        if 0 <= x < len(s) and nof[x] >= 0 and s[x] not in '()[]':
            out.append(nof[x])
    return sorted(set(out))

def remap_start(x, nof, n_old, n_new):
    if x >= n_old: return n_new
    k = x
    while k < n_old and nof[k] < 0: k += 1
    return nof[k] if k < n_old else n_new

def atomic_dump(d, jf):
    tmp = jf + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, jf)

def process(jf):
    d = json.load(open(jf, encoding="utf-8"))
    if not FORCE and d.get("v") == 2:
        return -1                          # 已处理, 跳过
    s = d.get("text", "")
    if '(' not in s and '[' not in s:      # 无夹注/缺字: 只打标记
        d.setdefault("note", []); d.setdefault("gx", []); d["v"] = 2
        atomic_dump(d, jf); return 0
    new, notes, gx, nof = transform_text(s)
    n_old, n_new = len(s), len(new)
    d["ju"]  = remap_marks(d.get("ju", []),  nof, s)
    d["dou"] = remap_marks(d.get("dou", []), nof, s)
    d["fen"] = [[remap_start(f[0], nof, n_old, n_new), f[1], (f[2] if len(f) > 2 else "fen")] for f in d.get("fen", [])]
    d["br"]  = sorted(set(remap_start(b, nof, n_old, n_new) for b in d.get("br", [])))
    d["xr"]  = [[remap_start(a, nof, n_old, n_new), remap_start(b, nof, n_old, n_new)] for a, b in d.get("xr", [])]
    d["text"] = new; d["n"] = n_new; d["note"] = notes; d["gx"] = gx; d["v"] = 2
    atomic_dump(d, jf); return len(notes)

def main():
    files = sorted(f for f in glob.glob(os.path.join(DATA, "*", "*.json")) if not f.endswith("_meta.json"))
    log("START total_files=%d force=%s" % (len(files), FORCE))
    done = skipped = tot_notes = errs = 0
    for k, jf in enumerate(files):
        try:
            r = process(jf)
            if r == -1: skipped += 1
            else: done += 1; tot_notes += r
        except Exception as e:
            errs += 1; log("ERR %s : %s" % (jf, e))
        if k % 500 == 0:
            log("...%d/%d done=%d skip=%d notes=%d err=%d" % (k, len(files), done, skipped, tot_notes, errs))
    log("BATCH DONE files=%d done=%d skipped=%d notes=%d errors=%d" % (len(files), done, skipped, tot_notes, errs))

if __name__ == "__main__":
    main()
