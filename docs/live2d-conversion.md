# Live2D / BongoCat 转换工具

项目内 Skill 位于 `skills/live2d-to-mc/SKILL.md`，本机安装到 `C:/Users/CJK/.codex/skills/live2d-to-mc`。可通过 `$live2d-to-mc` 调用。项目副本是维护源，修改后需同步本机安装副本。

要求 Python 3.11+、Node.js，Python 包 NumPy、Pillow、soundfile、imageio-ffmpeg（见 requirements-build.txt）。现有 Cubism Core 位于 tools/vendor，仅构建期使用。无需安装 Cubism Editor。先在项目根目录运行：

```powershell
python tools/live2d_pipeline.py inspect assets/source/standard
python tools/live2d_pipeline.py inspect 'C:/Users/CJK/Downloads/Deepseek桌宠.zip'
python tools/live2d_pipeline.py convert --profile default --output build/cat-conversion-01
python tools/live2d_pipeline.py convert --profile deepseek --output build/deepseek-conversion-01
python tools/live2d_pipeline.py validate build/cat-conversion-01
python tools/live2d_pipeline.py export build/cat-conversion-01 --destination build/cat-runtime-01.zip
```

多个模型需 `--model 包内相对路径/model.model3.json`；`inspect --report 新文件.json` 保存检查结果。输出目录须尚不存在。失败保留日志，重新构建换目录，不覆盖现有模组。

**当前可重建默认小猫与现有 DeepSeek。未知/修改过的模型只做检查，需要新增适配器后才能转换。** 原图保持原分辨率，数值纹理存储变形数据，不是图片动画序列帧。

转换结果是当前 BongoCatMC 两模型运行时的隔离副本，其中选定模型重新生成，另一个沿用已有资源；不是独立自定义模型副包。导出的 ZIP 不含 SDK、原始模型、采样缓存或用户 ZIP，不等于网易平台的审核加密包，不应和原 BongoCatMC 重复安装。

音效统一从原音源生成 Ogg Vorbis（96 kbps，最大 128 kbps），validate/export 会检查格式、码率及引用，旧 WAV 包会被拒绝。离线集成测试可通过环境变量 `BONGOCATMC_PIPELINE_TEST_ROOT` 指定含 `pipeline-default`、`pipeline-deepseek` 两个新构建目录的父目录，避免把历史构建当成当前结果。

完整流程、支持范围及扩展方式见 [转换参考](../skills/live2d-to-mc/references/conversion.md)。参数、渲染、物理、动作和触屏经验由 Skill 按任务加载。本工具不启动 MC、不改存档、不连接调试服务，也不自动上传。
