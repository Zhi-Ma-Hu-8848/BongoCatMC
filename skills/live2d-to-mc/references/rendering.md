# 连续变形与渲染经验

## 通用模型检查

`.model3.json` 连接 moc、贴图、physics3、pose3、动作 motion3、表情 exp3 和声音。MOC 是运行模型，不是可编辑工程；不要假定能恢复原 Cubism 编辑器工程。构建期 Core 用来获取网格、参数求值和参考结果，游戏运行时不加载 Core。

参数采样图存储顶点数值，区别于画面序列帧。只对每个参数采几个点再把全局位移相加，无法准确表示父子旋转和参数耦合。先分解局部形变与父仿射，再对无法分解的部件直接建联合张量。误差应换算源画布像素，而非只报归一化小数。

## 两个已完成的实例

默认猫：224 个原顶点、21 个 drawable，输入姿态库与效果参数库分离，GPU 插值；55 张键盘爪保留 612×354 原画布。关闭的眼镜在 Core 中仍可能不透明，只是放在画布外，需针对关闭状态裁切；不要裁掉正在显示的光环或其他配饰。

DeepSeek：53 个 drawable、5867 个原顶点、33 个有效参数。原模型的六个无效参数为 ParamBrowLY/RY、ParamMouthForm、ParamMouthOpenY、ParamBodyAngleY/Z。

- 父变换：ParamAngleZ、ParamBodyAngleX、ParamBreath；大部分网格用局部形变张量配精确父变换。
- ArtMeshNeckwear、ArtMeshTopwear、ArtMeshLegwearL/R 使用直接张量。
- 当前局部张量最多三轴，遮罩 UV 张量最多四轴；并非所有模型均满足此限制。
- 已有 100 组独立全参数组合与 Core 对照，历史最大误差约为 1024 源画布的 1.082 像素、透明度 0.000368；每次适配按新日志报告。
- 原图集 4096×4096，姿态图 4096×2048；按键图仅可放入所有原始 UV 边界之外的空区，不能凭肉眼判断透明处就覆盖。
- 参数以三字节数值编码，四组 uniform 向量预算；更复杂模型需要另行评估参数容量与顶点纹理开销。

## Alpha、纹理与手机后端

美术 RGBA 图集预乘 Alpha，混合 `One / OneMinusSrcAlpha`。遮罩和部件透明度同时作用于 RGB 和 Alpha。否则白色爪子接缝会出现灰线。姿态与元数据纹理保持原始数值、Point 采样、显式 level 0，不能预乘。

GLSL 保留 `// __multiversion__` 与引擎头，显式 highp 浮点及采样器。现代版本用 `texelFetch`，旧桌面 1.20 使用 `texture2DLod`；不能把旧 vertex `texture2D` 假设成 GLES 3.1 可用。

`verify_mobile_shaders.py` 和 `verify_render_portability.py` 分别验证编译组合与真实网格画面。其本地引擎头路径依赖本机 MC 安装，换机器先检查路径。历史通过 32 组编译与 72 次真实网格比较，仅证明电脑驱动下这些版本的表现，不代表 Android/iOS 性能和画面已通过。当前面向网易纸娃娃 GLES 3.x，不承诺 GLES 2、Metal、Vulkan、DirectX。

曾在新加 shader include 后直接 ReloadAllShaders 导致原生断言 `Unable to find shader #include file`：运行资源索引尚未发现新文件。新增文件应等资源重扫描/重启，不能循环热重载碰运气。当前采样 helper 在两份 vertex 内联；仅退出世界不一定清除 GPU shader 缓存。不要将 API 返回成功等同于真实画面更新。
