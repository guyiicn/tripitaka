# NOTICE — 第三方内容与许可 / Third-party content & licenses

本项目的**源代码**以 MIT 协议开源（见 `LICENSE`）。
但**佛经文本**与**字体**属于第三方作品，各自遵循其自身许可，**不**受 MIT 覆盖。
使用、再分发本项目时请一并遵守下列条款。

The **source code** of this project is licensed under MIT (see `LICENSE`).
However, the **scripture text** and **fonts** are third-party works under their
own licenses and are **not** covered by MIT. Please comply with the terms below.

---

## 一、经文数据 / Scripture text

- **来源**：CBETA 中華電子佛典協會（Chinese Buddhist Electronic Text Association）
  电子佛典集成 — <https://www.cbeta.org>
- 本项目对 CBETA 电子佛典的纯文本做了排版处理（竖排、句读圈点、夹注抽取、
  缺字标注等），未改动经文内容本身。
- CBETA 授权：可自由流通，非营利使用，需保留出处声明。请见
  <https://www.cbeta.org/copyright.php>。
- 数据文件（SQLite 库）**不包含在本仓库中**；请依 `pipeline/` 下脚本，从 CBETA
  官方文本自行生成。

## 二、字体 / Fonts

字体文件**不包含在本仓库中**（体积大 + 各自许可）。请自行从下列来源获取，
并遵守各自协议：

| 字体 | 用途 | 许可 | 来源 |
|---|---|---|---|
| 京華老宋体 KingHwa_OldSong | 正文·标题（默认） | 免费商用 | TerryWang |
| 汇文明朝体 Huiwen-Mincho | 可选正文 | 免费 | github.com/bosswnx/huiwenmincho-improved |
| 令东齐伋体 QIJI | 可选正文 | SIL OFL 1.1 | github.com/LingDong-/qiji-font |
| 霞鹜文楷 LXGW WenKai | 序文·可选正文 | SIL OFL 1.1 | github.com/lxgw/LxgwWenkai |
| 思源宋体 / Noto Serif CJK | 兜底 | SIL OFL 1.1 | github.com/notofonts |
| Plangothic | 生僻字（Ext-B+）兜底 | SIL OFL 1.1 | github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project |

字体在本项目中经 `fontTools` 子集化后使用（见 `pipeline/` 文档）。
OFL 字体的再分发须随附其 OFL 许可文件。

## 三、代码依赖 / Code dependencies

- **zstd-jni**（Luben Tuikov）— BSD 2-Clause。用于设备端解压经藏库。
- AndroidX / Kotlin — Apache 2.0。

---

联系 / Contact: guyiicn@gmail.com
