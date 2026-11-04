# 新备份资源修复与报告

本目录记录本次基于解包资源的缺口审计、兼容构建和本地安装结果。

- [资源修补前后对照报告（Markdown 图文版）](资源修补前后对照报告.md)
- [交互式 HTML 报告](资源修补前后对照报告.html)（下载后在浏览器打开，可搜索与筛选）
- [CSV 完整清单](资源修补前后对照.csv)
- [逐项修复结果与原因](本次逐项修复结果.json)
- [模型与贴图素材候选审计](本次修复审计说明.md)
- [唯一骨架兼容障碍的证据](mind-skeleton-compatibility.json)

原218项：194项已在本地修补（126模型、68贴图）；22项无同族来源；1项已有原优先资源保留；1项同族源缺必要骨链，保留原方案。已安装不代表远端部署或实机验收，既有通关闪退仍未解决。

图片为实际资源解码的UV贴图，不是3D渲染。报告引用的缩略图随文档保存。原始资源包、APK、完整本地生成包仍遵守仓库忽略规则，不进入Git。

## 复现顺序

先按 ../monster-recovery/模型替换流程.md 准备离线依赖、原件及加载目录索引，再执行：

```sh
python scripts/prepare_backup_recovery.py
python scripts/finalize_backup_metadata.py
python scripts/validate_backup_recovery.py resources/reconstructed/backup-recovery/bundles
python scripts/install_backup_recovery.py
python scripts/install_backup_recovery.py --apply
python scripts/report_backup_recovery.py
python scripts/report_repaired_resource_gaps.py
```

命令从仓库根执行，使用安装了 requirements-model-recovery.txt 的离线解释器。安装命令默认dry-run；--apply仅写本地最终分发目录和清单，不部署运行服务。

## GitHub 整理验证

本次暂存版本在隔离目录运行32项资源转换、动作、骨架、Shader、分发及安装回归，全部通过。全量探测发现既有管理页面测试未提供Basic鉴权却预期200；单独复现该用例同样失败，本次不修改该无关功能。因此不宣称全量测试通过。

原始包及完整兼容包留在本地；GitHub保存构建工具、来源和哈希清单、报告及其引用图片。
