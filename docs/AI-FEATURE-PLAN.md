# AI 翻译 / 解释 · 设计文档

选一段经文 → 一键调 LLM →「白话翻译」或「经文解释」，结果以**浮层**呈现。
辅助理解，**不修改经文数据、不改忠实白文原则**。

## 决策汇总（已定）

| 项 | 决定 |
|---|---|
| 范围 | **仅 app + 内网 web（50.8:8899）**；**hk2 公网不出现** |
| app 联网 | **原生 HTTP 桥**（Kotlin OkHttp），绕 CORS、密钥留本地 |
| 受众 | 纯内部自用，密钥存本地（localStorage / SharedPrefs） |
| 协议 | **同时支持 OpenAI 与 Anthropic(Claude) 两种调用模式** |
| 预设 provider | OpenAI / Claude / DeepSeek / Qwen / Kimi / GLM + 自定义 |
| 选段 | **点选按句**（用现成 ju/dou 句读边界），可扩展区间 |
| 结果显示 | **阅读区浮层**（position:fixed，高 z-index，不破坏竖排结构） |

## 1. 一份 reader.html 通吃 + hk2 屏蔽

AI 代码写在 reader.html（web/app 共用），用运行时开关屏蔽 hk2：
```js
var AI_ON = (typeof NativeLLM!=='undefined')      // app：有原生桥
         || /^192\.168\./.test(location.hostname) // 内网 web(50.8)
         || localStorage.getItem('cbeta_ai')==='1'; // 手动开(调试)
```
hk2（`hk2.guyii.net`，无桥、非内网、无 flag）→ `false` → AI UI 不渲染、不绑定、不请求。deploy-web.sh 照常推 hk2，代码 inert、无害（开源也不敏感）。

## 2. LLM 适配层（双协议）

`callLLM(cfg, system, user, onDelta, onDone, onErr)`，按 `cfg.protocol` 分派：

| protocol | 端点 | 认证头 | 请求体 | 流式解析 |
|---|---|---|---|---|
| `openai` | `{base}/chat/completions` | `Authorization: Bearer {key}` | `{model, messages:[{role,content}], stream:true, temperature, max_tokens}` | SSE `data: {choices[0].delta.content}`，`[DONE]` 结束 |
| `anthropic` | `{base}/v1/messages` | `x-api-key: {key}` + `anthropic-version: 2023-06-01` | `{model, system, messages:[{role:'user',content}], stream:true, max_tokens}` | SSE `event: content_block_delta` → `delta.text` |

**app**：两种协议都由原生 OkHttp 发（无 CORS）。
**内网 web**：`fetch` + `ReadableStream` 解析 SSE；端点需允许 CORS（自建 llama.cpp/Ollama 开 CORS 头即可；Anthropic 直连浏览器需 `anthropic-dangerous-direct-browser-access: true`，app 走原生则无需）。

### 预设 provider（用户只填 key + 选 model）

| 名称 | protocol | base_url | 示例 model |
|---|---|---|---|
| OpenAI | openai | `https://api.openai.com/v1` | gpt-4o / gpt-4o-mini |
| Claude | anthropic | `https://api.anthropic.com` | claude-3-5-sonnet-latest |
| DeepSeek | openai | `https://api.deepseek.com/v1` | deepseek-chat |
| Qwen(百炼) | openai | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-plus |
| Kimi(Moonshot) | openai | `https://api.moonshot.cn/v1` | moonshot-v1-8k |
| GLM(智谱) | openai | `https://open.bigmodel.cn/api/paas/v4` | glm-4-plus |
| 自定义 | openai/anthropic | 用户填 | 用户填 |
| （内网自建） | openai | 如 `http://192.168.34.101:8080/v1` | 已加载模型 |

## 3. 配置（存本地）

`localStorage.cbeta_llm = { active, providers:[{id,name,protocol,base,key,model,temp,maxTokens}] }`
多套可切换。app 端 key 也可选存 SharedPrefs（更安全），MVP 先统一 localStorage。
设置入口：工具栏「⚙️」或结果浮层里的齿轮。

## 4. 选段（点选按句）

- **给每字标索引**：`addC` 里给 `.c` span 加 `data-i={charIndex}`（现在只有列有 data-ci）。
- **点一字**：由该字 index，用 `ju`/`dou` 找到所在句边界（上一个句末+1 ~ 下一个句末），选中整句。
- **再点另一句**：扩展为 [起句首, 终句末] 区间；朱色/淡黄高亮选区的 `.c`。
- **取文**：`DATA.text.slice(start, end+1)`（剔除 BRK 括号后的纯正文，与显示一致）。
- 取消：点空白/关闭浮层。
- 备选手势（后续）：长按微调端点。

## 5. 结果浮层（不破坏竖排结构）

- `position:fixed` 卡片（底部上滑 sheet 或右侧浮窗），高 z-index，**竖排阅读区在其下原样不动**。
- 内容：①原文选段（可折叠，横排小字）②译文/解释（**流式逐字**，横排易读）③工具条：`白话翻译 | 经文解释 | 复制 | 重新生成 | ⚙️ | ✕`。
- 上下文随选段一起发：`经名 + 卷/品题 + 选段（+可选前后各一句）`。
- 面板可拖动高度/关闭；关闭后选区高亮清除。
- 纸色主题延续（与 reader 一致），横排结果用无衬线便于阅读。

## 6. 预设提示词（可编辑）

- **白话翻译**（system）：「你是佛典白话译者。将用户给出的佛经原文译为准确、通顺的现代白话文；忠实原意，不增删教义；专有名词保留并首次出现括注。只输出译文。」
  user：`【{经名}·{卷/品}】\n{选段}`
- **经文解释**（system）：「你是佛学讲解者。解释用户给出的佛经段落：先一句总说大意，再逐句讲解，标注关键术语（如有梵/巴对照），点明在该经中的脉络。条理清晰、避免臆断。」
- 用户可改模板、增删自定义条目（存 localStorage）。

## 7. Android 改动

- `AndroidManifest.xml` 加 `<uses-permission android:name="android.permission.INTERNET"/>`。
- `MainActivity`：`webView.addJavascriptInterface(NativeLLM(), "NativeLLM")`。
- `NativeLLM.chat(cfgJson, msgsJson, cbId)`：OkHttp（SSE）流式；每 chunk `runOnUiThread { webView.evaluateJavascript("__llmChunk('$cbId', ${JSONObject.quote(text)})", null) }`；结束/错误回 `__llmDone/__llmErr`。
- 隐私政策补注：AI 为**可选、需自配端点、仅开启时联网**的功能；核心阅读仍完全离线。

## 8. 分期实现

1. **选段 + 高亮 + 浮层骨架**（纯前端，不接 LLM）：data-i、按句选、朱色高亮、浮层开合。
2. **LLM 适配层 + 配置面板 + 流式**（先用一个内网端点跑通 openai 协议，再补 anthropic）。
3. **预设 provider + 提示词管理**。
4. **Android INTERNET + NativeLLM 桥**（app 端流式），更新隐私政策；重打 APK。
5. 打磨：错误处理、超时、重试、长文分段、复制/分享。

## 9. 开放项（实现时再定）
- 首个联网调试端点（Claude / OpenAI / 内网自建，任一即可）。
- 浮层形态：底部 sheet vs 右侧浮窗（可先做 sheet）。
- 选段上下文是否默认带前后句。
- key 是否迁到原生 SharedPrefs（app）。
