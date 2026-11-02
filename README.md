# 视频知识 → HTML 手册流水线 · Douyin / Video to HTML Playbook

> 抖音/短视频作品 → 单文件 HTML 实操手册：解析链接取原图、逐帧取证、覆盖度契约、五段式提示词、四道自检

![License](https://img.shields.io/badge/license-MIT-5a6b4f)
![Type](https://img.shields.io/badge/type-Agent%20Skill-4a6b7c)
![Platform](https://img.shields.io/badge/platform-WorkBuddy%20%7C%20Claude%20Code-b8935a)

## 它解决什么问题

刷到一条讲得很好的视频，收藏了，然后再也没打开过——因为视频是线性的，你要的那一步在第 47 秒，而你记不住第 47 秒在哪。

这个 skill 把一次性的视频消费，变成一份**可以照着做、可以打印、可以检索**的文档：把作品的每一帧都读成证据，反推它背后完整的技能链条，再补齐画面里看不见的那 90%。

## 流水线（S0–S6）

| 阶段 | 动作 | 关键约束 |
|---|---|---|
| S0 | 收料与确认 | 明确作品形态（图文 / 视频 / slides 混合），确认产物主题与落点 |
| S1 | 解析链接 | 短链 → 真实落地页 → 原始素材，**原图不压缩** |
| S1.5 | 三种形态三种取法 | 见下表 |
| S1.6 | 拿不到画面时 | 用公开报道补证据链，每条标来源等级 |
| S2 | 逐图读证据 | 一张一张读，不跳；抄原文丝印、界面文字、读数 |
| S3 | 建覆盖度契约 | **先写契约再写正文**：N 个画面 × 每画面 ≥ 8 个可执行要点 |
| S3.5 | 情感型 / 事件型素材 | 落点从「复述感动」改为「拆解机制」 |
| S4 | 产出元提示词 | 五段式：身份 / 需求 / 约束 / 输出格式 / 迭代 |
| S5 | 按提示词生成 HTML | 单文件、零依赖、离线可开 |
| S6 | 四道自检 | 结构闭合 / 脚本语法 / 锚点对应 / 敏感信息 |

## 三种素材形态，三种取法

| 形态 | 特征 | 取法 |
|---|---|---|
| 图文作品 | `share/note/<id>` 有 SSR 数据 | 搜索引擎 UA 直接 curl，正则取原图 |
| 纯视频 | `share/video/<id>` 无 `play_addr` | 只能取封面 + 文案，用公开报道补证据 |
| slides 混合 | React 单页，curl 拿到空壳 | 无头浏览器 `--dump-dom --virtual-time-budget` 渲染后取 `365yg.com` mp4 直链 |

> 实测要点：`slides` 形态的 mp4 直链**无需签名**，直接 GET 即可下载；视频主机在 `v5-default` / `v11-default` 之间会变，正则不要写死。

## 产出物长什么样

一次完整跑通通常会得到两份文件：

```
<主题>_HTML指导文件生成提示词.md     # 可复用的元提示词
<主题>_实操指导手册.html            # 100KB+ 单文件，含目录 scrollspy、canvas 示意图、
                                    # 勾选式预算器、90 天清单（localStorage 持久化）
```

手册的固定骨架：覆盖度契约表 → 证据分级 → 技能链拆解 → 可执行步骤 → 坑表 → 延伸思考 → 一页速查。

## 触发方式

```
你：9.25 复制打开抖音，看看【某某的作品】…… https://v.douyin.com/xxxx/
   用 douyin-to-html-guide 给我生成一份 HTML 实操手册
```

## 目录结构

```
douyin-to-html-guide/
├─ SKILL.md                     流水线 S0–S6 + 反模式清单
├─ scripts/
│  ├─ fetch_douyin.py           短链解析 + 原图批量下载 + meta 抽取
│  ├─ extract_slides.py         slides 形态：按序抽图 + 视频直链
│  └─ check_html.py             四道自检：结构 / 语法 / 锚点 / 敏感词
└─ references/
   ├─ prompt-template.md        五段式元提示词模板（含占位符与易漏点表）
   └─ html-spec.md              HTML 手册的视觉与交互规范
```

## 设计取舍

- **先提示词，后文件**。跳过提示词直接写 HTML，会写成一篇读后感；先定契约，才能保证每个画面都被交代。
- **不追画面数量，追覆盖密度**。20 个画面只写 20 句话，等于没做；契约要求每个画面展开 ≥ 8 个要点。
- **宁可标注存疑，也不要抹平矛盾**。素材与公开报道口径不一致时，单开一节写清矛盾，标「存疑」而不是「事实」。

## 已知边界

- 拿不到评论区、作者主页作品列表、私密/粉丝可见内容。
- 纯视频形态拿不到视频流（需客户端签名），只能封面 + 文案 + 公开报道。
- 生成的 HTML 里不会写入他人真实姓名、学校、报名号等隐私信息。

## 许可

MIT © 2026 px-pangu


## 安装

把本仓库整个目录放进 Agent 的 skills 目录即可，目录名保持仓库名：

```bash
# WorkBuddy
git clone https://github.com/px-pangu/douyin-to-html-guide.git ~/.workbuddy/skills/douyin-to-html-guide

# Claude Code
git clone https://github.com/px-pangu/douyin-to-html-guide.git ~/.claude/skills/douyin-to-html-guide
```

装好后在对话里说一句相关的话就会自动触发，也可以用 `@douyin-to-html-guide` 显式点名。

