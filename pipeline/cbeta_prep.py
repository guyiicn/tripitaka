#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CBETA txt -> 紧凑JSON. 含: 段落提行(br) + 序题(xu) + 序正文区间(xr) + 简体经名(catalog s)
   + 导出全用字/序用字集用于字体子集化. 用法: cbeta_prep.py <out_dir> ALL|<ids...>"""
import os, re, json, sys, glob
try:
    import zhconv
    def to_s(t): return zhconv.convert(t, "zh-cn")
except Exception:
    def to_s(t): return t
try:                                    # 阿拉伯数字->中文(同目录 numconv.py)
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from numconv import convert_obj as _num_obj, convert_plain as _num_plain
except Exception:
    _num_obj = None
    def _num_plain(s): return s

SRC = "/home/nvidia/cbeta/cbeta-text"
JU = set("。！？"); DOU = set("，、；：·")
DROP = set("「」『』（）〔〕《》〈〉—…　 ")
JUAN_RE = re.compile(r'卷第[一二三四五六七八九十〇零百千]+')
XU_END = ("序", "敘")          # 只有真序/敘 才作序正文锚点(讚/銘 只做题样式不整块换体)
ALLCH = set(); XUCH = set()    # 全用字(京華宋) / 序用字(文楷)

def read_yaml_title(jing_dir, jid):
    y = os.path.join(jing_dir, jid + ".yaml"); title = jid
    if os.path.exists(y):
        for l in open(y, encoding="utf-8"):
            if l.startswith("title:"):
                title = l.split(":", 1)[1].strip(); break
    return title

def clean_lines(txt):
    out = []
    for l in txt.splitlines():
        if l.startswith("#"): continue
        s = l.strip()
        if not s or s.startswith("No."): continue
        out.append(s)
    return out

def line_kind(line, title):
    """返回 (type,label): fen=卷/品题(朱), xu=序题(灰), None=正文段落"""
    if len(line) <= 24 and ("卷第" in line or "品第" in line):
        return "fen", line
    if len(line) <= 26 and (line.endswith("序") or line.endswith("敘") or line.endswith("讚") or line.endswith("銘")):
        return "xu", line
    return None, None

def find_translator(lines, title):
    byline = re.compile(r'(譯|奉[ 　]?詔譯|撰|述|造|集|說)$')
    for i, l in enumerate(lines):
        if l == title or (title in l and len(l) <= len(title) + 2):
            for j in range(i + 1, min(i + 4, len(lines))):
                cand = lines[j]
                if len(cand) <= 24 and byline.search(cand) and any(k in cand for k in ("三藏","沙門","法師","尊者","菩薩","居士","國","譯","奘","什")):
                    return cand
    return ""

def build_juan(lines, title):
    chars, marks, fen, br = [], [], [], []
    seen = set()
    for line in lines:
        typ, label = line_kind(line, title)
        if typ:
            if typ == "fen" and label in seen and JUAN_RE.search(label):
                continue
            seen.add(label)
            fen.append([len(chars), label, typ]); continue
        # 正文/序文 段落 -> 提行
        if chars:
            br.append(len(chars))
        for ch in line:
            if ch in JU:
                if marks: marks[-1] = 1
            elif ch in DOU:
                if marks: marks[-1] = 2
            elif ch in DROP:
                continue
            else:
                chars.append(ch); marks.append(0)
    text = "".join(chars)
    ju = [i for i, m in enumerate(marks) if m == 1]
    dou = [i for i, m in enumerate(marks) if m == 2]
    # 序正文区间 xr: 序/敘 题 -> 紧随其后的 卷/品 题 之间(gap<1200) 判为序正文
    xr = []; last_xu = None
    for pos, label, typ in fen:
        if typ == "xu":
            last_xu = pos if label.endswith(XU_END) else None
        elif typ == "fen":
            if last_xu is not None and 0 < pos - last_xu < 1200:
                xr.append([last_xu, pos])
            last_xu = None
    # 收集用字
    ALLCH.update(text)
    for _, label, _t in fen: ALLCH.update(label)
    for _, label, t in fen:
        if t == "xu": XUCH.update(label)
    for s, e in xr: XUCH.update(text[s:e])
    return text, ju, dou, fen, br, xr

def _find_close(s, i, op, cl):
    depth = 0; j = i
    while j < len(s):
        if s[j] == op: depth += 1
        elif s[j] == cl:
            depth -= 1
            if depth == 0: return j
        j += 1
    return -1

def _strip_gaiji(inner):
    out = []; i = 0
    while i < len(inner):
        if inner[i] == '[':
            j = _find_close(inner, i, '[', ']')
            if j < 0: out.append(inner[i]); i += 1
            else: out.append('□'); i = j + 1
        else: out.append(inner[i]); i += 1
    return ''.join(out)

def apply_notes(text, ju, dou, fen, br, xr):
    """() 夹注 -> note[]; [组字式] -> □(gx 存公式); 重映射所有索引. 未闭合括号退化为普通字符."""
    s = text; new = []; notes = []; gx = []; nof = [-1] * len(s); i = 0
    while i < len(s):
        c = s[i]
        if c == '[':
            j = _find_close(s, i, '[', ']')
            if j < 0:
                ni = len(new); new.append(c); nof[i] = ni; i += 1; continue
            ni = len(new); new.append('□'); gx.append([ni, s[i+1:j]])
            for k in range(i, j+1): nof[k] = ni
            i = j + 1
        elif c == '(':
            j = _find_close(s, i, '(', ')')
            if j < 0:
                ni = len(new); new.append(c); nof[i] = ni; i += 1; continue
            notes.append([len(new) - 1, _strip_gaiji(s[i+1:j])])
            for k in range(i, j+1): nof[k] = len(new) - 1
            i = j + 1
        else:
            ni = len(new); new.append(c); nof[i] = ni; i += 1
    nt = ''.join(new); no = len(s); nn = len(nt)
    def rmark(idxs):
        out = []
        for x in idxs:
            if 0 <= x < no and nof[x] >= 0 and s[x] not in '()[]': out.append(nof[x])
        return sorted(set(out))
    def rstart(x):
        if x >= no: return nn
        k = x
        while k < no and nof[k] < 0: k += 1
        return nof[k] if k < no else nn
    fen2 = [[rstart(f[0]), f[1], (f[2] if len(f) > 2 else 'fen')] for f in fen]
    xr2 = [[rstart(a), rstart(b)] for a, b in xr]
    return nt, rmark(ju), rmark(dou), fen2, sorted(set(rstart(b) for b in br)), xr2, notes, gx

def process_jing(jid, out_dir):
    jing_dir = canon = None
    for a in os.listdir(SRC):
        d = os.path.join(SRC, a, jid)
        if os.path.isdir(d): jing_dir, canon = d, a; break
    if not jing_dir: return None
    title = read_yaml_title(jing_dir, jid)
    ALLCH.update(title)
    txts = sorted(glob.glob(os.path.join(jing_dir, jid + "_*.txt")))
    if not txts: return None
    od = os.path.join(out_dir, "data", jid); os.makedirs(od, exist_ok=True)
    juans, translator = [], ""
    for t in txts:
        jn = re.search(r'_(\d+)\.txt$', t).group(1)
        lines = clean_lines(open(t, encoding="utf-8").read())
        if not translator: translator = find_translator(lines, title)
        text, ju, dou, fen, br, xr = build_juan(lines, title)
        if not text: continue
        text, ju, dou, fen, br, xr, note, gx = apply_notes(text, ju, dou, fen, br, xr)
        obj = {"id": jid, "title": title, "by": translator, "juan": jn, "n": len(text),
               "text": text, "ju": ju, "dou": dou, "fen": fen, "br": br, "xr": xr, "note": note, "gx": gx, "v": 2}
        if _num_obj: obj, _ = _num_obj(obj, {"viol": 0})   # 阿拉伯数字->中文(含索引重映射)
        json.dump(obj, open(os.path.join(od, jn + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        juans.append(jn)
    ALLCH.update(translator)
    meta = {"id": jid, "canon": canon, "title": _num_plain(title), "by": _num_plain(translator), "juans": juans}
    json.dump(meta, open(os.path.join(od, "_meta.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return meta

def main():
    out_dir = sys.argv[1]; ids = sys.argv[2:]
    if ids == ["ALL"]:
        ids = []
        for a in sorted(os.listdir(SRC)):
            ad = os.path.join(SRC, a)
            if os.path.isdir(ad):
                for j in sorted(os.listdir(ad)):
                    if os.path.isdir(os.path.join(ad, j)): ids.append(j)
    catalog = []
    for k, jid in enumerate(ids):
        m = process_jing(jid, out_dir)
        if m:
            catalog.append({"id": m["id"], "canon": m["canon"], "title": m["title"],
                            "s": to_s(m["title"]), "by": m["by"], "juans": len(m["juans"])})
        if k % 500 == 0: print("  ...%d/%d" % (k, len(ids)), flush=True)
    json.dump(catalog, open(os.path.join(out_dir, "catalog.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(out_dir, "all_chars.txt"), "w", encoding="utf-8").write("".join(sorted(ALLCH)))
    open(os.path.join(out_dir, "xu_chars.txt"), "w", encoding="utf-8").write("".join(sorted(XUCH)))
    print("DONE jing=%d allch=%d xuch=%d -> %s" % (len(catalog), len(ALLCH), len(XUCH), out_dir))

if __name__ == "__main__":
    main()
