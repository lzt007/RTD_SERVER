# 90 份原缓存的名称、版本和下载发布核查

## 结果

90 个原缓存目录已全部唯一识别，0 个未匹配：

| 类别 | 包数 | 说明 |
| --- | ---: | --- |
| 当前 APK 基础包 | 76 | 音频 1 包、角色 1–750 共 75 包 |
| 原敌人包 | 7 | death、bear、dra、两种 gold slime、four_zako、four_02 |
| 超出当前 APK 基础表的角色包 | 7 | 751–760、761–770、771–780、781–790、791–800、801–810、811–820 |

此前 14 个未命名包是上述 7 个敌人包与 7 个较新角色包，不是打不开的未知压缩包。完整目录身份见 `original-cache-identities-20261028.csv`。

## 原生缓存键规则

实际引擎为 APK 的 `assets/libs/armeabi-v7a/libunity.so`，SHA256 `eb8ab8714c7eda4dbf49c5f032557caba08c4eadfe02742b8337c7f184cf4724`。`lib/armeabi-v7a/libunity.so` 是另一层代理，不能混为同一文件。

本引擎 Shared 缓存的已确认路径，对本次使用的 ASCII URL/名称：

```text
name = URL 最后一个斜杠之后的部分
name = name 中问号之前的部分
version 非 0 时：name += "@" + version 的十进制表示
目录名 = SHA1(name 的 UTF-8 字节) 的小写十六进制
```

CDN 域名、平台及版本目录不参与此键。这纠正了此前“换 CDN 根地址可能导致这批 Shared 缓存不命中”的猜想。不能把此规则推广到其他 Unity 版本或带项目隔离前缀的缓存。

绑定和调用证据由 `analysis/android/native_cache_keys.py` 从原文件读取：

- 原生注册函数 VA `0x2e6fa8` 将名称表 VA `0x66eff4` 与函数表 VA `0x677b84` 逐项传给 `mono_add_internal_call`。
- 表索引 25：`UnityEngine.Caching::IsVersionCached` → VA `0x311414` → 缓存查询 `0x1df540` → 键生成 `0x1db094`。
- 文件名提取 `0x2625fc` → `0x261440`；键生成常量 `?`、`@%d`；摘要 `0x2cc8a8` 实际经 PLT 调用 `SHA1Init`、`SHA1Update`、`SHA1Final` 并编码 40 个十六进制字符。
- 原备份 90 个目录全部精确命中；模拟器测试前 82 个真实资源缓存目录也全部吻合当前 APK 请求版本。Shared 根的 `__info` 不是第 83 个资源目录。

本机 REA 原生分析提供者受平台限制，本轮使用原文件 ELF 重定位/注册表与 Capstone 指令读取，未执行原生目标代码。托管 URL 表此前已结合 REA 检查；原生审计导出保留文件身份、VA、绑定、PLT 名称和指令片段。

## 为什么原样复制不一定全部命中

| 包 | 当前 APK 请求的缓存版本 | 原备份缓存版本 |
| --- | ---: | ---: |
| AudioClipManager | 6 | 12 |
| 741–750 | 10 | 11 |

其余当前 APK 表中的 81 个原包版本匹配。另 7 个角色包尚未进入当前 APK 基础清单，其版本为 11（751–790）或 12（791–820）。缓存版本号不是从 `__info` 第三行猜出来的，而由原生键规则与目录哈希精确匹配。

这直接支持“备份含有比当前 APK 资源表更新的内容”，不能据此断言旧手机具体 APK 版本或当年 URL 的 V1021/V1022 目录拼法。当前 APK 的最大版本枚举为 10；没有原常量时不伪造新目录地址。

完整更新后的缓存仍可包含按需敌人包子集：原客户端 GameManager 按当前关卡敌人列表加载，基础更新与所有关卡敌人预下载不是同一流程。对 `ms01_sla_lv3.unity3d@1`，备份没有对应的独立缓存目录；这不是对所有 APK 对象和跨包依赖做完排查后的“贴图物理不存在”结论。

## 本轮实际修复

仅新增 8 个原资源到现有下载服务：`ms01_dra_lv4` 与上述 7 个角色包。其他资源文件未覆盖。此前服务是 82 个可对应原包加 1 个已授权视觉替代包；现在为 90 个原包加该替代包，共 91 个文件。

全部 90 个原包解压载荷与各自备份 SHA256 一致；新增 8 个包的 HTTP 响应 Content-Length、实际长度与传输 SHA256 一致。沿用现有已验证 UnityWeb/LZMA 传输封装，未修改原 SerializedFile 字节，也不声称重建压缩包等于当年 CDN 原始响应。

新增较新角色包不代表角色 751–820 的主表、抽取和战斗功能已经恢复；旧 APK 清单不会自动请求它们。

## 运行时实验与边界

三次探针都没有完整结果，不能算缓存 API 命中或原包游戏内加载验收通过。第一轮发现私有目录副本丢失 SELinux 标签；修正并加断言后的两轮仍未产生完整探针输出。本轮停止继续研究启动问题，不据无输出推断缓存未命中。

每轮均在原数据目录保留、使用副本的情况下运行，结束后原 APK SHA、私有数据/外部文件逐文件内容及后台 SQLite 逻辑内容一致，无游戏进程。未执行 90 份原目录恢复阶段，因为对照未过，不能说“原缓存恢复已经实际成功”。

运行时路径保留为诊断工具，不替换日常客户端；后续在客户端能稳定执行探针时仍需分别验证原缓存命中、实际 AssetBundle 加载及对象依赖。

## 证据与复现

- 测试：`python -m unittest discover -s analysis/android -p test_cache_probe.py`。
- 静态审计：`python analysis/android/native_cache_keys.py <新的输出 JSON 路径>`。
- 新增包校验/发布：`python analysis/android/publish_original_cache.py <新的清单路径>`；已有文件内容不符时拒绝覆盖。
- 本轮完整证据：`analysis/android/flow-runs/original-cache-probe-20261028-v3/` 中 native-cache-audit.json、original-cache-identities.csv、publish-manifest.json、http-verification.json、current-key-validation.json 和 summary.json。前两轮分别在无后缀与 v2 目录。

唯一最终审查确认静态结论，发现一处回滚移动依赖 Important，已单轮离线故障测试修复；最终 10 项测试通过，新 Minor 为 0。细节见 `docs/reviews/2026-10-28-original-cache-review.md`，未为修复重跑设备实验。
