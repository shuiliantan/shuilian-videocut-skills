# 水莲剪辑 Skills

把口播剪辑中的风格、字幕、声音、返修和交付要求，整理成 Agent 可读取的流程。默认采用明亮沉稳的画面、真实素材、前三秒空间动画、关键词字幕和自然半身口播。

这个仓库包含编辑规范、字幕检查脚本和可离线打开的分镜核对页生成器。粗剪、素材搜索、动画制作、实际试听和 MP4 合成仍由具备相应工具的 Agent 执行；它不是独立视频编辑软件，也没有一条命令自动完成整片的渲染引擎。

## 先试分镜核对页

Python 3.10 或以上，无第三方 Python 依赖。在仓库根目录运行：

```bash
python3 skills/shuilian-video-editor/scripts/review_storyboard.py examples/demo.srt --shots examples/shots.json --out output/storyboard.html
```

浏览器打开生成的 HTML。左侧查看代表帧或画面说明，右侧核对字幕、时间、素材来源、镜头动作和阅读停留。可逐段选择状态、写修改意见、导出反馈 JSON。输入内容只在本地页面使用，不联网。

示例只有文字和分镜设计，不含真人素材或已渲染动画；核对页不是可播放的成片预览。

有自己的 SRT 时，先生成待填写的分镜：

```bash
python3 skills/shuilian-video-editor/scripts/review_storyboard.py my-video.srt --write-shots my-shots.json --out output/first-review.html
```

让 Agent 读取 `my-shots.json`，按语义合并连续字幕并补齐画面说明，再用 `--shots my-shots.json` 重新生成。时间来自 SRT；合并镜头不能改变字幕时间，也不能漏掉或重复使用字幕。

## 从 GitHub 安装

以本地 Codex（CLI 或 IDE 扩展）为例，复制本仓库的 GitHub 地址，连同下面的提示词发给 Codex：

> 请使用 $skill-installer，从 https://github.com/shuiliantan/shuilian-videocut-skills 安装水莲剪辑 Skill。Skill 目录为 skills/shuilian-video-editor。请安装完整目录，检查 SKILL.md、references 和 scripts 是否齐全，并确认能调用 shuilian-video-editor。

安装后，在新对话中让 Codex 读取“水莲剪辑 Skill”，确认名称与流程。完整文件夹应包含 `SKILL.md`、`agents/`、`references/` 和 `scripts/`。

本地安装方式参考 [OpenAI 官方说明](https://learn.chatgpt.com/docs/build-skills)。其他 Agent 按其宿主支持的方式安装同一文件夹；本仓库没有发布 npm 安装包。

## 交给 Agent 使用

下载本仓库后，向支持读取本地文件的 Agent 发送：

> 读取 skills/shuilian-video-editor/SKILL.md，按水莲的默认风格处理我提供的口播视频和文字稿。先列素材与环境缺口、整理粗剪删除清单；重校剪后字幕，再生成分镜核对页。只做到我这次要求的范围，实际检查后再报告完成。

已安装时，也可以直接说：“按水莲剪辑 Skill 处理我提供的视频和文字稿。”

## 默认制作顺序

1. 整理原视频、文字稿、真实截图、人物素材和配乐；核实可用工具。
2. 根据原声列出停顿、口误、重说等删除项，保留自然表达；粗剪后重新对齐字幕。
3. 先按完整词检查字幕，再设置关键词样式；保留原稿及修改对照。
4. 根据字幕选择本人动态口播、实图、实录或关系图解，生成分镜核对页。
5. 按段号修改；使用实际剪辑工具输出可播放预览，检查时间线和声音。
6. 通过检查后导出成片；先审主画幅封面，再适配另两种比例，配一条发布简介。

用户已经授权完整制作时，不为每一步机械增加确认。明确要求先审分镜或预览时，按该节点停下；封面沿用先审主画幅的默认规则。

## 自定义与素材

- 默认竖屏 9:16；三张封面为 4:3、16:9、9:16，各自重排。
- 默认用户自行提供 `intro.m4a`，音乐轨增益 −22 dB。仓库不分发音乐、肖像、原视频或第三方截图。
- 水莲算力系列封面署名“硅姬算力”；其他使用者在本次任务中指定自己的署名。
- `references/wording-list.txt` 是个人表达偏好，不是平台官方禁词表。换成自己的规则后使用；技术术语与事实优先，不能盲目拆字替换。
- 下载真实图片时记录页面来源、日期及使用条件；不将生成图冒充新闻或操作实录。

## 检查脚本

```bash
python3 skills/shuilian-video-editor/scripts/validate_srt.py examples/demo.srt --duration 12
python3 skills/shuilian-video-editor/scripts/scan_terms.py examples/demo.srt
python3 -m unittest discover -s tests -v
```

字幕结构检查不能证明音画同步；候选词扫描不能替代语境改写；静态核对页不能证明动画和混音合格。最终验收必须针对实际导出文件。

## 费用与开放范围

本仓库代码和自写流程按 MIT 许可提供。Agent、模型、素材服务或渲染服务可能产生费用，具体取决于使用环境。不要将代码许可理解为第三方图片、音乐或商标的授权。
