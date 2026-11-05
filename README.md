# BongoCatMC

独立的网易 Minecraft ModSDK 项目。第一阶段：默认小猫 HUD 响应游戏输入。

## 当前功能

- 进入世界后自动显示右下角小猫，HUD 不吸收游戏操作。
- 字母、数字、空格、Shift、Ctrl 等按键使用原模型配套的键盘爪贴图；箭头键映射为 WASD。
- 多键同时按下，显示最近按下且仍按住的键；松开一个键不会清除其他按键。
- 鼠标左键/右键分别显示原模型的鼠标按键效果，可与键盘同时响应。
- 转动游戏视角带动小猫和鼠标爪，停止后平滑回中；自动眨眼。
- 触屏下蹲跟随玩家的实际下蹲状态，显示 Shift；点击切换模式下松开手指仍保持，取消下蹲后松爪。不会因移动、跳跃或右键松手而清掉下蹲状态。
- F8 显示/隐藏 HUD；菜单内隐藏并清理输入。游戏暂停超过 0.75 秒后清理遗留按键。
- 接入移动端的移动、跳跃、短按、长按和松手事件。通过 `GetInputVector()` 连续读取摇杆，前后左右对应 W/S/A/D；斜向选主方向并加方向边界防抖，回中松爪。短按使用右键效果，长按使用左键效果；原生使用按钮的触屏释放也会正确清除右键状态。

## 启动

双击根目录 `启动BongoCatMC.cmd`。

启动器使用本机 `D:\MCDevTool\v1.6.1\mcdk.exe`，配置在 `.mcdev.json`。使用独立世界 `BONGOCATMC_HUD_001`、本地调试端口 `18905`，不会重置旧世界。如果已有 MC 或 MCDK 进程，会提示使用已有窗口，避免重复启动。

当前版本使用 **OpenGL GLSL**。启动器会选择 OpenGL，并将之前的渲染设置记录到 `diagnostics/launcher/`。本轮没有实现 DirectX 着色器分支。

## 实现

默认小猫来自 BongoCat 的 `standard` 模型。构建时通过 Cubism Core 采样数值顶点位置、透明度和遮罩坐标，游戏内使用网易纸娃娃自定义网格与着色器插值。保留原始网格、材质裁切和键盘爪的静态贴图，不生成动作图片序列帧，不在游戏内运行 Cubism Core。

原始模型 224 顶点，运行网格 264 个三角形（含背景及按键爪）。400 组数值姿态；3 张运行纹理合计约 633 KB。每帧只更新改变的着色器参数，输入完全在客户端处理，无持续网络同步。

`tools/build_cat.py` 目前专用于默认小猫；这还不是通用的自定义模型转换器。自定义模型副包、模型注册协议、设置界面和商店发布不属于本轮范围。

## 构建与检查

依赖 Node.js、Python 3、NumPy、Pillow。游戏脚本兼容 Python 2.7。

```powershell
node tools/sample_cat.cjs
& 'C:\Users\CJK\AppData\Local\Programs\Python\Python313\python.exe' tools/build_cat.py
& 'C:\Users\CJK\AppData\Local\Programs\Python\Python313\python.exe' tools/test_input.py
```

MCDK 正在运行时，`tools/check_runtime.py` 只读取运行状态及截图；`tools/verify_runtime.py` 在后台注入模组回调验证 HUD，不发送操作系统键鼠输入，不改变世界。后者只应在没有同时游玩时运行，结束后恢复原输入对象。

本轮已验证：7 项纯输入逻辑测试、10 项后台回调到渲染的测试、原模型的静止/键盘爪/鼠标爪截图，以及 ModSDK 代码检查。按用户要求，后半程不使用前台输入。**真实键鼠的完整操作验收和手机实机测试尚未完成。** 当前只监听游戏内输入，不监听 Windows 桌面其他应用。

## 资源记录

来源和 Git 对象校验记录：`assets/source/provenance.json`。随下载保留原资产 `LICENSE-MIT`。构建用 Cubism Core 保存在 `tools/vendor/`，没有放入游戏 addon；原仓库的桌面程序也没有打进 addon。

旧 `live2D` 实验项目未修改。只需要发布模组时，运行资源在 `addon/`，不应把 `assets/`、`build/`、`tools/vendor/` 或 `diagnostics/` 当成运行模组一起打包。
