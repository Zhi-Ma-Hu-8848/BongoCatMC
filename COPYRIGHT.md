# 许可范围 / License scope

Copyright (C) 2026 Zhi-Ma-Hu-8848 and BongoCatMC contributors.

Unless a file or the exceptions below state otherwise, the original program
code, shaders, UI definitions, build scripts, tests and documentation authored
for BongoCatMC / 灵动桌宠 are licensed under the GNU Affero General Public
License, version 3 only (AGPL-3.0-only). See LICENSE for the complete terms and
licenses/BongoCatMC-additional-permission.txt for a limited additional permission
concerning the host game and separately licensed Live2D components.

This program is distributed WITHOUT ANY WARRANTY, including without the implied
warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

## 不由项目 AGPL 重新授权的内容

| 内容 | 适用条款 |
| --- | --- |
| `assets/source/standard/` 及由其生成的白猫贴图、网格、动作、声音、`client/data.py`、`client/motion_data.py` | 上游素材 MIT，见 `licenses/BongoCat-assets-MIT.txt` |
| `assets/source/deepseek/`、DeepSeek 图集/网格/数值纹理/音效、`client/deepseek_parameters.py` 及模型派生数据、展示其形象的宣传图 | 作者单独授权，见 `docs/deepseek-permission.md`；不因文件扩展名是 `.py`、`.json` 或图片由转换器生成而成为 AGPL 素材 |
| `tools/vendor/framework/` | Live2D Open Software License；保留原文件版权与 `LICENSE.md` |
| `addon/behavior_pack/bongocat_mod/client/cubism_physics.py` 中来自 Framework 的改编部分 | Live2D Open Software License，原权利归 Live2D；本项目不将该部分重新授权为 AGPL |
| `tools/vendor/live2dcubismcore*.min.js` | Live2D Proprietary Software License；仅构建期使用，不随游戏模组打包 |
| Minecraft、网易 ModSDK、MCDK 等外部工具/运行环境 | 各自原许可证；不由本仓库授权 |

上述第三方内容保留自身条款；本项目不能替第三方授予没有取得的权利。
DeepSeek 素材使用范围不限制独立项目代码在 AGPL 下的使用权；也不能据此宣称整个模组素材都允许商业复用。

本次为项目自身代码明确许可，不把“参考 BongoCat 的功能”自动认定为复制其代码。
若引入 BongoCat 的 AGPL 程序代码，必须保留上游版权及 AGPL 条款，
不能将仅由本项目维护者授予的额外许可用于他人代码。

源码和发布对应关系见 `docs/source-distribution.md`。仅在私有仓库放置 LICENSE，
并不自动完成面向模组接收者的相应源码提供义务。
