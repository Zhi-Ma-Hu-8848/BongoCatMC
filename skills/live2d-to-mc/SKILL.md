---
name: live2d-to-mc
description: 将 Live2D Cubism 模型及 BongoCat 桌宠适配为网易 Minecraft UI 纸娃娃，整理网格、参数、遮罩、物理、表情动作和输入映射，使用离线转换工具构建与验证。适用于新模型适配、转换管线维护和显示交互修复；不用于普通骨骼动画移植或图片序列帧制作。
---

# Live2D → Minecraft

目标是保留原网格与连续变形，在 MC 中通过自定义纸娃娃和着色器绘制；Cubism Core 只在构建期求值，不把动作烘焙成图片帧。

## 工作入口

先定位 BongoCatMC 工具项目，查找 `tools/live2d_pipeline.py`、`tools/live2d_profiles.json` 和项目 `AGENTS.md`。本机参考位置为 `D:/Users/CJK/ChatGPT/BongoCatMC`；Skill 安装位置与工具项目位置不同，不能按当前工作目录猜路径。工具未找到时先在已有工作区查找，不伪造命令或转换结果。

使用 Python 3.11+、Node.js、NumPy、Pillow、soundfile、imageio-ffmpeg。MC 端行为脚本仍保持该项目要求的 Python 2.7 兼容。CLI 的具体用法及输出边界见 [转换工具](references/conversion.md)。

1. 先 `inspect` 输入模型文件、目录或 ZIP，确认依赖、贴图原尺寸、动作与表情、物理和已支持适配器。
2. 已匹配的模型使用 `convert` 写入新的隔离目录。未知或修改过的模型进入适配研究，不强套现有适配器，不通过改指纹绕过兼容性验证。
3. 根据任务读取 [参数与渲染](references/rendering.md)；BongoCat 的动作语义、按键素材和鼠标响应另见 [BongoCat 适配](references/bongocat.md)。
4. `validate` 检查完整性；需要交付运行包时再 `export`。离线通过、桌面渲染通过和手机实测是不同证据，按实际结果说明。

## 转换中保持的约束

- 保留原图分辨率和全部可见像素；可裁透明空白并保留原画布坐标。不得以预估性能或包体为由缩小图像。
- 颜色图集的预乘 Alpha、混合材质、遮罩计算需要配套；数值纹理不得预乘、滤波或有损编码。
- 当前命令封装两个已验证的专用适配器，不代表任意 `.moc3` 均可转换。输出是现有 BongoCatMC 运行时快照，尚非通用模型副包协议。
- 新模型记录来源和适用许可，不从仓库代码协议推断所有美术或 Cubism SDK 的许可；当前任务只转换时不额外增加发布审批流程。
- 不把修改转换工具等同于授权启动游戏或改用户对局。需要运行时操作时沿用当前会话的授权与限制；新资源热重载的原生崩溃风险见渲染参考。

涉及手机点按、长按拖动、滑条或跟随输入时读取 [输入与验收](references/input.md)。
