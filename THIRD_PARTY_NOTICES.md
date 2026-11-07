# 灵动桌宠 / BongoCatMC — 第三方署名与许可

维护者：Zhi-Ma-Hu-8848。此项目不是 BongoCat、Live2D、Minecraft 或网易的官方产品。
项目自身代码许可见 `COPYRIGHT.md` 和 `LICENSE`，不能据此重新授权下列第三方内容。

## BongoCat 与默认白猫

- 上游：<https://github.com/vladelaina/BongoCat>
- 程序代码：AGPL-3.0-only。当前模组不附带 BongoCat 桌面程序。
- 默认模型素材：MIT；Copyright (c) 2026 vladelaina。
- 素材来源提交：`29ccda67802e6b6727acae0bdf42f50277f9aade`。
- 上游素材声明：<https://github.com/vladelaina/BongoCat/blob/29ccda67802e6b6727acae0bdf42f50277f9aade/resources/assets/LICENSE-MIT>。
- 本地全文：`licenses/BongoCat-assets-MIT.txt`，游戏资源包亦保留 `BONGOCAT_ASSET_LICENSE.txt`。
- 72 个源文件的 Git blob 校验记录：`assets/source/provenance.json`。
- 行为对照版本：v1.14.0，提交 `666999650f8afb405fa34dbf1ee0b98cd7145117`。

项目修改：将原网格、参数、遮罩、动作曲线和原尺寸按键美术转换为网易纸娃娃资源；
添加游戏内键鼠/触屏响应、菜单、镜像、缩放、位置拖动和移动端材质适配。
原桌面程序的系统级输入监听、桌面窗口及原生运行库没有放入游戏包。
模型图集裁透明边缘但不缩小可见像素，颜色使用预乘 Alpha；音效从原音源编码为网易提审要求的 Ogg Vorbis，原音源保持不变。

## DeepSeek 桌宠

**作者：mefist-兰登版 & 赤风RED**。

作者已同意本项目在网易 Minecraft 模组中使用并免费上架，发布时标注出处。
该授权不等于将模型按 MIT/AGPL 开源，也没有明确授予第三方单独转售、
商业上架或把原始模型在 GitHub 公开下载的权利。详见 `docs/deepseek-permission.md`。

改编：保留原始 4096×4096 美术、17 张按键图、表情、动作、声音及物理参数；
转换为纸娃娃网格、连续数值纹理及客户端参数驱动。
原包说明及 SHA-256 保存在 `assets/source/deepseek/`。转换后资源仍保留作者权利。

## Live2D Cubism

Copyright(c) Live2D Inc. All rights reserved.

- Core：Live2D Proprietary Software License。
  <https://www.live2d.com/eula/live2d-proprietary-software-license-agreement_en.html>
- Framework：Live2D Open Software License。
  <https://www.live2d.com/eula/live2d-open-software-license-agreement_en.html>
- 上游 Framework：<https://github.com/Live2D/CubismWebFramework>。
- 原许可索引全文：`licenses/Live2D-Framework-NOTICE.md`。
- SDK 发行许可说明：<https://www.live2d.com/en/sdk/license/>。

Core 只在离线构建时求值，不进入 addon。Framework 用于参考求值；
`client/cubism_physics.py` 是物理算法的 Python 改编，不能声称运行时完全没有 Framework 衍生内容。
改编保持物理更新顺序，接入 120 Hz 子步、帧间插值与暂停重置，未嵌入 Core 原生库。
保留上游版权与许可，项目 AGPL 不适用于 Live2D 自有代码。

SDK 协议还有出版、可扩展应用及许可兼容等条件；“免费上架”或“Core 只用于构建”
本身不能替代对实际用途的核对。本仓库没有声称已获得 Live2D 的额外出版授权。

## 构建与运行依赖

NumPy（BSD-3-Clause）、Pillow（HPND）、SoundFile（BSD-3-Clause）、imageio-ffmpeg（BSD-2-Clause）和 esbuild（MIT）
由开发者通过各自包管理器安装，不附带在游戏包里。SoundFile 依赖的 libsndfile
按其原条款提供；imageio-ffmpeg 使用的 FFmpeg 二进制遵循其具体构建对应的 LGPL/GPL 条款，不打入游戏包。Node.js、Python、Minecraft、ModSDK、MCDK 的权利由各自权利人保留。
发布自己的依赖二进制副本时，应一并保留对应版本的许可证与声明。
