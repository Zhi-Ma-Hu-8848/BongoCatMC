# 工具流程与交付范围

在 BongoCatMC 项目根目录运行（其他目录使用绝对脚本路径）：

```powershell
python tools/live2d_pipeline.py inspect assets/source/standard
python tools/live2d_pipeline.py inspect 'C:/path/model.zip' --model 'folder/cat.model3.json'
python tools/live2d_pipeline.py convert --profile default --output build/cat-conversion-01
python tools/live2d_pipeline.py convert --profile deepseek --output build/deepseek-conversion-01
python tools/live2d_pipeline.py validate build/cat-conversion-01
python tools/live2d_pipeline.py export build/cat-conversion-01 --destination build/cat-runtime-01.zip
```

`inspect --report NEW_FILE.json` 保存报告；缺失引用返回非零状态。模型目录有多个 model3 文件时必须选择一个。ZIP 解包在临时目录，拒绝目录穿越、重复文件、符号链接及超过 2 GiB 的展开总大小。检查读取模型数据，不执行模型包内程序。

适配器使用整个模型目录 SHA-256 指纹，包含动作、物理、声音及额外按键图。`--source` 可指定外部相同版本的包，但内容须与已验证指纹一致。新增说明文件也会导致不匹配：先检查差异，按实际影响验证后更新适配器；不能仅因模型名字相同就放行。

## 两条当前流水线

| profile | 数值采样 | 构建 | 回归 |
|---|---|---|---|
| default | sample_cat.cjs，旧版 Core | build_cat.build_assets() | test_texture_alpha.py、test_effect_assets.py |
| deepseek | sample_deepseek_parameters.cjs，Core 6 | build_deepseek.py → build_deepseek_parameters.py | test_deepseek.py |

默认猫只调用 `build_assets()`，避免 `build_cat.py` 的历史主入口重写 UI 和 manifest。`sample_deepseek.ts` 是旧研究路线，不是当前 DeepSeek 转换入口。

隔离目录包含 tools/vendor、源模型、现有运行时的副本。选中的模型重新生成，另一个模型及 HUD 保留。原构建脚本依赖固定相对路径，所以当前通过复制工作区隔离，而非修改全局路径。保留失败目录和日志便于定位，重试用新目录。

输出文件：

- `source-inspection.json`：依赖、原图尺寸、源目录指纹、适配器匹配。
- `conversion.json`：构建状态、阶段命令、工具和运行资源指纹。
- `pipeline-logs/`：采样、构建、测试日志。
- `validation.json`：离线验证摘要。
- `addon/`：两个模型和当前 HUD 的运行时快照。

导出只包含行为包、资源包及简短构建报告，不包含 SDK、原始模型、临时采样文件、诊断记录和用户已有 ZIP。这是开发用运行时快照，UUID 与原模组一致，不作为可并装的独立新模组，也不是网易审核加密包。不得把它描述成“任意模型自动生成副包”。

## 扩展新适配器

1. 检查 Core 版本、参数范围、部件顶点、UV、裁切遮罩、混合模式、动态绘制顺序、物理和动作。
2. 单参数与组合参数对照 Core，识别局部形变及父变换；判断当前 shader 是否支持多重遮罩、混合模式和顺序变化。缺项要报告或实现，不能静默丢弃。
3. 建立独立采样/编译器及运行时参数映射，用原模型随机组合和边界值校验几何、透明度、遮罩，再录入 profile。
4. 为新模型接入注册表、UI 选项和行为驱动。当前模型 ID 与运行时仍有固定接线，profile 本身不会自动增加可选模型。
5. 使用新的隔离目录重建；验证原像素、参数误差及依赖，按任务授权再进行 MC/真机验收。

未来若多个客户端需要远程调用，再将这些 CLI 封装为 MCP；核心算法不应依赖 MCP 会话。
