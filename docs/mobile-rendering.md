# 移动端渲染适配

2026-11-05。本轮只修改渲染，不改变菜单、触控操作或美术分辨率。

## 发现与修正

参考本机 Balatro 的 `docs/screen-shaders.md`、`tools/verify_mobile_shaders.py`，保留网易多版本加载协议及引擎骨骼头文件。验证包含实际 `USE_SKINNING` / `NETEASE_SKINNING` 分支、MSAA 开关和大小骨骼 uniform 分支。

- 修复前 32 组编译中有 8 组失败：两个模型的 GLES 3.1 顶点着色器使用了该版本已经移除的 `texture2D`。
- 两个现有顶点着色器中的 `bongoData` 函数统一使用同一采样规则：现代 GLSL 使用 `texelFetch(..., 0)` 按整数像素读取数值；桌面 1.20 使用像素中心的 `texture2DLod(..., 0.0)`。数据读取不依赖隐式 LOD 或纹理插值。
- 三个纹理采样器均显式使用 `highp`。默认 float 的 highp 并不能替代 sampler 自身的精度声明；数值纹理中的字节不能作为普通低精度颜色读取。
- 不修改 atlas、poses、meta 的像素或尺寸，不使用有损压缩，不改变原来的预乘 Alpha 混合。

## 可复现验证

构建机安装 `moderngl`、NumPy、Pillow 后执行。引擎头文件需使用目标版本对应的文件；不把本机引擎头文件复制进模组。

```powershell
python tools/verify_mobile_shaders.py `
  --headers 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.436581/data/resource_packs/vanilla_netease/shaders/glsl' `
  --headers 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.436581/data/shaders/glsl'

python tools/verify_render_portability.py `
  --headers 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.436581/data/resource_packs/vanilla_netease/shaders/glsl' `
  --headers 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.436581/data/shaders/glsl'
```

编译矩阵：GLSL 1.20、3.30 Core、ESSL 3.00、3.10，共 32/32 通过。真实网格渲染涵盖默认猫与 DeepSeek 共 18 个姿态，包括按键、鼠标、遮罩、表情、动作及组合参数。四版本共 72 次比较通过。

本次额外用 `--baseline-shaders diagnostics/mobile-shaders/before` 指向修改前的着色器快照，确认全部 72 次输出与修改前桌面输出完全一致。该临时快照不入库；默认命令比较当前桌面与 ES 输出。结果和预览在 `diagnostics/mobile-shaders/`。

## 验证边界

上述检查运行于电脑 GPU 驱动，不能代替移动设备驱动、温控、内存或帧率测试。真实网格图像检查不启用骨骼宏，骨骼通路另由编译矩阵覆盖。当前 MC 仅使用单个根骨骼定位，仍需真机核对纸娃娃实际显示。

运行要求：网易支持此自定义材质的 GLES 3.x 通路、顶点纹理读取、高精度运算；默认猫最大纹理边长 2048，DeepSeek 最大 4096。GLES 2 的引擎骨骼头兼容性不在本轮支持范围；也没有实现 Metal、Vulkan 或 DirectX 专用着色器。不存在根据 `GetPlatform()` 猜测 GPU 能力的自动启用/关闭开关。

真机验收需分别检查两种模型初次显示、菜单鼠标/触摸与游戏输入、眨眼和各表情的遮罩、同时动作、镜像与大小，以及切后台恢复。若手机出现空白、花屏或断层，应记录设备、系统、MC 版本、所选模型及截图，继续定位对应后端。不能仅凭接口返回成功判断画面正常。

## 热更新断言修复

首次实现把采样函数放在新增头文件中，直接调用 `ReloadAllShaders()` 后，运行中的资源索引未识别新增 include，触发原生断言 `Unable to find shader #include file`。已移除新文件依赖，把小函数内联到两份已有顶点着色器。关闭断言进程后重新加载验证；不通过反复忽略断言继续使用失效渲染状态。桌面离线编译并不能发现游戏资源索引的热更新问题。

修复后已通过独立启动器只启动一个新 MC 进程，读取到 DeepSeek 纸娃娃正常更新，错误日志为空，并通过实际游戏截图确认角色、键盘和鼠标显示。未修改用户的模型选择、位置、大小或存档；不再执行新增 include 的直接热刷新。
