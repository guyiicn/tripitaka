#!/usr/bin/env python3
# 透明背景牌记页(只留京華老宋墨字), 落在 reader 纸底上零色差
import subprocess, os, base64
D='/tmp/fix/plate'
JH=base64.b64encode(open(f'{D}/jhsong.woff2','rb').read()).decode()
INK='#241a10'

def plate(title, verse_cols, out, vfs, tfs, pad):
    cols = f'<div class="tcol" style="font-size:{tfs}px">{title}</div>'
    cols += ''.join(f'<div class="vcol" style="font-size:{vfs}px;padding:6px {pad}px">{c}</div>' for c in verse_cols)
    html=f'''<!DOCTYPE html><html><head><meta charset=UTF-8><style>
@font-face{{font-family:JH;src:url(data:font/woff2;base64,{JH}) format('woff2');}}
*{{margin:0;box-sizing:border-box}} html,body{{width:1080px;height:1440px;overflow:hidden;background:transparent}}
body{{padding:60px; font-family:JH,serif;}}
.inner{{width:100%;height:100%;padding:70px 40px;
  display:flex;flex-direction:row-reverse;justify-content:center;align-items:center;}}
.tcol,.vcol{{writing-mode:vertical-rl;text-orientation:upright;color:{INK};
  display:flex;flex-direction:column;align-items:center;}}
.tcol{{letter-spacing:.05em;font-weight:600;padding:6px 26px;margin-left:24px;}}
.vcol{{line-height:1.14;letter-spacing:.02em;}}
</style></head><body><div class="inner">{cols}</div></body></html>'''
    open(f'{D}/{out}.html','w').write(html)
    subprocess.run(['google-chrome','--headless=new','--no-sandbox','--force-device-scale-factor=1',
        '--window-size=1080,1440','--hide-scrollbars','--default-background-color=00000000',
        '--disable-gpu','--disable-dev-shm-usage','--user-data-dir=/tmp/cc_prof2',
        f'--screenshot={D}/{out}.png',f'{D}/{out}.html'],capture_output=True,timeout=60)
    print(out, os.path.getsize(f'{D}/{out}.png') if os.path.exists(f'{D}/{out}.png') else 'FAIL')

plate('開經偈', ['無上甚深微妙法','百千萬劫難遭遇','我今見聞得受持','願解如來真實義'],
      'kaijing', vfs=80, tfs=90, pad=26)
plate('迴向偈', ['願以此功德　莊嚴佛淨土','上報四重恩　下濟三途苦','若有見聞者　悉發菩提心','盡此一報身　同生極樂國'],
      'huixiang', vfs=76, tfs=90, pad=26)
