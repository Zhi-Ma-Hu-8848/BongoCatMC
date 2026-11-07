# 源码获取、构建与发布对应关系

项目：灵动桌宠 / BongoCatMC。
仓库：<https://github.com/Zhi-Ma-Hu-8848/BongoCatMC>。
维护者主页：<https://github.com/Zhi-Ma-Hu-8848>。

**2026-11-07，维护者将仓库改为公开，可无需登录浏览和获取源码。**

- 浏览源码：<https://github.com/Zhi-Ma-Hu-8848/BongoCatMC>。
- 下载当前源码：<https://github.com/Zhi-Ma-Hu-8848/BongoCatMC/archive/refs/heads/main.zip>。
- 获取固定版本：使用对应发行记录中的提交 SHA，在 GitHub 选择该提交，或下载 `https://github.com/Zhi-Ma-Hu-8848/BongoCatMC/archive/<提交SHA>.zip`。

`main` 会继续变化，发行模组时仍需登记其实际对应的提交；公开仓库不替代其他许可证条件。

## 对外提供模组前

与每个发行版本对应提供可以获取的相应源码，包含维护者用于修改程序的形式、
构建/安装脚本、接口定义及必要的版本信息。可在同一发布位置提供源码附件，
或提供接收者实际可访问的源码下载地址；单独给出无法访问的私有仓库链接不够。
采用 AGPL 第 6 条的其他方式时，须满足对应条款，不能把一般“接受私信索取”当成通用替代。

本项目的客户端 HUD 不向远程用户提供 Web 服务；以后增加可远程交互的修改版服务时，
还需按第 13 条向相关用户明显提供相应源码。平台审核或加密打包不能替代源码提供。

DeepSeek 美术有独立许可。应在不扩大该授权的前提下，安排代码和必要数据的交付。
缺少必需构建输入的删减包不能直接宣传为“完整可复现源码”。当前仓库含该模型原件
和历史记录；公开可见不代表对第三方授予模型的再分发或商业使用权。
现有作者沟通未明确约定原始模型的公开下载，范围说明仍以 `deepseek-permission.md` 为准。

## 当前开发者构建

在有权取得当前完整仓库的环境使用 Python 3.11+、Node.js，安装：

```powershell
python -m pip install -r requirements-build.txt
npm install
python tools/sync_license_notices.py --check
python tools/live2d_pipeline.py convert --profile default --output build/default-new
python tools/live2d_pipeline.py convert --profile deepseek --output build/deepseek-new
```

选择新目录构建，避免覆盖验收模组。两个 profile 分别重建一个模型，保留另一个现有模型。
要从原始输入重建两个模型，应依次运行 `node tools/sample_cat.cjs`、
`python -c "import sys; sys.path.insert(0,'tools'); from build_cat import build_assets; build_assets()"`、
`node tools/sample_deepseek_parameters.cjs`、`python tools/build_deepseek.py`。
现有 UI 和运行时源码位于 addon，UI 生成器为 `tools/build_menu.py`。
Core/Framework 按各自条款使用，不把它们改名为 AGPL 文件。

游戏脚本兼容 Python 2.7；运行需要网易 Minecraft、ModSDK 和支持当前纸娃娃 GLSL 的后端。
`.mcdev.json` 与启动器路径是本机示例，需按安装目录调整；不附带游戏和平台工具。

## 打包时携带的文件

`python tools/sync_license_notices.py` 将当前法律声明同步到行为包与资源包的 `legal/`。
构建器也会调用它；`--check` 用于检查是否遗漏或陈旧。
该命令不替代源码分发，也不自动确认平台条款、Live2D 出版许可或第三方美术的新授权。
旧 ZIP 不会自动更新，需从当前 addon 重新打包。

## 发行记录

每次发布记录源码提交 SHA、模组版本、实际打包文件哈希和可访问的源码位置。
公开源码入口已登记在本文件开头，并同步至随包副本。尚未登记特定上架包的提交 SHA 和文件哈希；
正式发行时应补充，并在网易作品介绍中加入源码入口与第三方署名。
