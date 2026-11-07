# BongoCat 行为适配

Live2D 负责变形，BongoCat 应用决定输入、动作是否持续、切换逻辑、声音与表情混合。模型内 `Loop` 字段并不完整描述应用行为；对比具体桌面版本，本项目依据 BongoCat v1.14.0，不能拿主分支的新行为直接替换。

## 输入与模型资源

默认猫有 55 张按键爪，DeepSeek 有 17 张。图片是独立按键状态素材，不是低清动画帧。保留原分辨率，只裁全透明边缘，记录原画布位置。按键缺图时不假装成 W；多键显示最近按下且仍保持的有效键。松开其中一个键不能清空其他保持键。

模型注册涉及 `client/menu_catalog.py`、preferences、HUD 驱动、参数模块与 `models/netease_models.json`；不是添加一张图或 profile 就完成接入。原版 config、README、来源与许可独立保留。默认猫代码/资源来源信息不能自动覆盖到 DeepSeek 或 Core/Framework。

## 表情、动作及时间曲线

表情带旧状态淡出与新状态淡入。正确处理 Add/Multiply/Overwrite 等参数模式，不能仅改一个布尔值。动作保留原 Cubism 曲线；非受限 Bezier 需要根据时间求逆，不能按均匀时间样条解释。

DeepSeek 当前语义：

- Surprised 一次性播放。
- Hello、Sweat、Heart 到末尾保持，再次点击可取消。
- 控制不同参数的动作可以共存。
- 动作中仍保留游戏输入；Hello 挥手时暂时拥有该手的控制权。
- 声音与动作启停配套；原声音转 PCM WAV，避免重复/遗留播放。

默认猫两个重复动作分组只展示一份；闪电、挥手沿原曲线播放，结束恢复当前输入。切换模型停止旧动作与声音，切换页面不应让 HUD 状态意外失效。

## 自动呼吸与物理

DeepSeek 六组物理、15 个粒子覆盖前后发、眼、耳、呆毛、三节尾。使用 120 Hz 子步并插值，长暂停后重置，避免不规则帧率把形变越推越大。`tools/reference_deepseek_physics.ts` 生成 Framework 参考，`tools/fixtures/deepseek_physics_reference.json` 是现有可复用基准。

呼吸 offset/peak/period/weight：AngleX 0/15/6.5345/.5；AngleY 0/8/3.5345/.5；AngleZ 0/10/5.5345/.5；BodyX 0/4/15.5345/.5；Breath .5/.5/3.2345/.5。眨眼间隔 random×7 秒，闭眼过程 .1 秒、保持 .05 秒、睁眼 .15 秒，活动动作期间暂停。新模型按其数据和应用逻辑判断，勿将这些数值设为全模型标准。
