# 大藏經项目 · 结构 / 编译 / 数据来源

> 本文件记录代码与数据的**权威归属**、目录结构、web 三端关系、Android 编译方法、
> 数据来源与管线。改动工作流也在此。

## 0. 权威归属（single source of truth）

| 内容 | 权威位置 |
|---|---|
| **代码 + 数据** | **50.8 `~/code/tripitaka/`**（`guyi@192.168.50.8`） |
| 代码开源镜像 | GitHub `github.com/guyiicn/tripitaka`（本机 push） |
| **生产 web** | **hk2 `/srv/cbeta/`**（`root@hk2.guyii.net` = 阿里云 VPS） |
| 源 CBETA txt | 50.12 `/home/nvidia/cbeta/cbeta-text`（仅上游源料，非成品） |

- **web 改动一律在 50.8 `serve/` 上进行**，再用 `deploy-web.sh` 推到 hk2 生产。
- hk2 只是部署目标；50.12 只是源头。二者都不是「当前版本」的权威。

## 1. 50.8 monorepo 目录结构 `~/code/tripitaka/`

```
~/code/tripitaka/
├── android/          Android Gradle 工程（Kotlin, minSdk26/target34, WebView）
│   ├── app/          主模块; src/main/assets/web/ = 打包用 web 副本(从 serve 同步)
│   │   └── src/{debug,}/... /assets/db/tripitaka.db   派生 DB(360M, gitignore)
│   ├── sutradb/      Play Asset Delivery install-time 资产包(装 DB)
│   ├── keystore.properties   签名(gitignore, 不入库)
│   └── *.gradle.kts gradlew gradle/
├── serve/            ★开发 web(镜像 hk2 结构) = web 权威
│   ├── reader.html index.html about.html privacy.html
│   ├── catalog.json           目录(4869 经)
│   ├── data/                  21956 卷紧凑 JSON(gitignore, 大)
│   ├── font/                  7 款繁体 woff2 子集(gitignore, 49M)
│   ├── plate/                 開經偈/迴向偈 牌记页 PNG
│   └── _num_bak/              数字转换前的原始备份(可回滚, gitignore)
├── pipeline/         数据管线(Python)
│   ├── cbeta_prep.py          CBETA txt→JSON(夹注/缺字/序/句读 + 集成 numconv)
│   ├── numconv.py             阿拉伯数字→中文(索引重映射+句读自检)
│   ├── batch_notes.py         存量 JSON 补夹注/缺字(幂等)
│   └── build_db.py            JSON→SQLite(zstd+训练词典)
├── docs/             README / NOTICE / LICENSE / PROJECT.md(本文件)
└── deploy-web.sh     serve/ → hk2 部署脚本
```

## 2. Web 三端关系与工作流

| 端 | 位置 | 作用 |
|---|---|---|
| **开发 web** | 50.8 `serve/`，预览 `http://192.168.50.8:8899/` | 改这里 |
| **生产 web** | hk2 `/srv/cbeta/`，公网 `https://hk2.guyii.net/cbeta/` | 部署目标 |
| **App 内 web** | `android/app/src/main/assets/web/` | 打包用副本 |

- 预览服务：50.8 systemd user 服务 `tripitaka-web.service`（`python3 -m http.server 8899 --directory serve`，
  linger=yes 开机自启）。控制：`systemctl --user {status,restart} tripitaka-web`。
- **部署到生产**：在 50.8 跑 `~/code/tripitaka/deploy-web.sh`
  - 默认只推 web 文件（html/font/plate/catalog）
  - `deploy-web.sh --data` 连同 data/ 一起推（增量）
  - 走 50.8→hk2 直连 SSH（`ssh hk2` 已配好，rsync 增量）
- **同步到 App**（打包前）：`cp serve/*.html serve/plate/* → android/app/src/main/assets/web/`

## 3. Android 编译方法

前置：JDK 17 + Android SDK 34；`android/keystore.properties`（storeFile/storePassword/keyAlias/keyPassword）。

```bash
cd ~/code/tripitaka/android
# 同步最新 web 到 assets(如 serve 有改动)
cp ../serve/*.html app/src/main/assets/web/ ; cp ../serve/plate/* app/src/main/assets/web/plate/
./gradlew assembleDebug        # → app/build/outputs/apk/debug/  (debug 从 app assets 拷 DB)
./gradlew bundleRelease        # → app/build/outputs/bundle/release/*.aab (上 Google Play)
```

- 正式版经藏库走 **Play Asset Delivery install-time 资产包 `sutradb`**（不塞进 APK）。
- DB 位置：`android/app/src/debug/assets/db/tripitaka.db`（debug）+ `android/sutradb/src/main/assets/db/tripitaka.db`（release 资产包）。
- 本地测 AAB：`bundletool build-apks --local-testing` + `install-apks`。
- 包名 `com.wangsuo.tripitaka`，label「大藏經」。

## 4. 数据来源与管线

```
CBETA txt (50.12:/home/nvidia/cbeta/cbeta-text, 21956 卷/4869 经)
   │  pipeline/cbeta_prep.py  <out> ALL      (需在有源 txt 的机器上跑)
   ▼
serve/data/<id>/<jn>.json (v2: text/ju/dou/fen/br/xr/note/gx) + catalog.json
   │  已含: 夹注(note)/缺字□(gx)/序题(xu/xr)/句读(ju朱圈,dou朱点)
   │  已含: 阿拉伯数字→中文(cbeta_prep 内嵌 numconv.convert_obj)
   ▼
pipeline/build_db.py → tripitaka.db (SQLite + zstd + 训练词典, 376M)
   ▼
android 资产包 sutradb  /  hk2 直接读 JSON
```

- **数字转换**（numconv）：底本阿拉伯数字→中文。年份逐字(1925→一九二五)，其余数值
  (21→二十一, 3360→三千三百六十)；紧邻 ASCII 字母/下划线的数字(J27/p0157/BD2074號/gif 档名)跳过不转；
  ①②等圈号不算阿拉伯数字、不转。转换保持所有索引对齐(实测全库句读违规0/结构错0)。
- **编辑原则**：**忠实底本，不代施句读**。大正藏(T)有标点；龍藏(L)/嘉興藏(J)的禪師語錄多为
  白文(无标点)，如实保留、不机器断句。详见 README「编辑原则」。

## 5. ⚠️ 待办 / 注意

- **APK 的 `tripitaka.db` 是数字转换前的旧数据** → 下次打 AAB 前须用转换后的 `serve/data`
  重建 DB（`pipeline/build_db.py`），再打包。
- 数字转换的原始备份在 `serve/_num_bak/`（可回滚）。
- SSH 拓扑：本机→hk2 ✓ / 本机→50.8 ✓ / **50.8→hk2 ✓**(直连,rsync 部署走这条) / hk2→50.8 ✗(50.8 内网)。
- 字体不入 git（见 NOTICE 来源，`fontTools` 子集化后放 `serve/font/`）。
