# T03 联网面与离线依赖

范围：现有 `analysis/decompiled`、`analysis/decompiled-firstpass` 的C#静态搜索以及现有Java smali和补丁源码。静态位置不证明运行可达；SDK内部与native隐式联网尚不能声明穷尽。完整逐行扫描见 `network-locations.json`（含文件哈希）。不对失效原站发请求。

| 入口 | 用途与离线影响 | 当前替代/边界 |
|---|---|---|
| ComManager SetAddress/SSL | 47个候选PHP操作，核心账号/战斗阻断 | Program.cs仅将两处实际API根改为127.0.0.1:18766；未知操作明确失败 |
| ResidentManager.GetCommonText（675–680） | com_text4.json配置，可能门控启动；配置还含动态URL | 尚未改写此地址；既有运行成功依赖当前缓存/既有资源，不等于可从空设备完全离线重建，需T28验证 |
| AssetBundleDefine.AssetBundleInfo.GetURL | RTD/DLC/<平台>/<版本>/<包>，地图/角色/音效阻断 | 原包载荷由18765提供；仅改根URL；缺包不能返回空成功；provenance见analysis/unity及level-data |
| AssetBundleLoader.m_ServerPath | QRPG/DLC旧路径字段 | 仅静态存在，需调用交叉引用确认，不能当已运行 |
| ComManager.Coroutine_GetTitleBanner | 动态标题广告图片 | 独立WWW路径，不属于47项；动态URL来自公共配置，当前替代未确认 |
| TitleInfo.OpenWebView / MMEtcInfo.ActivateWebView | 标题/菜单公告网页 | 原生公告已能人工/脚本关闭；网页未离线镜像，非核心主界面验收依赖 |
| BannerManager / MMQuest | 动态banner商店/应用链接 | 外部浏览器，非核心，未模拟 |
| MMEtcMenu / MMInformationSite | 支持、结算声明、攻略、Famitsu | 外部网页，未模拟，保留未支持 |
| UIAgreementDialog | neocyon条款及隐私网页 | 仅静态候选，日版当前路径是否可达未确认 |
| MMShop / MMFriendSearch | GooglePlayAppURL与邀请码分享 | 商店/平台依赖，T25边界；不接真实支付 |
| SocialManager、firstpass Facebook/Twitter | 社交分享、graph.facebook.com、远程icon.png | 兼容构建no-social跳过Facebook/Twitter初始化；不等于所有SDK调用已关闭 |
| NoahHandler / firstpass NoahUnity | 身份/统计第三方SDK（认证队列后GuidRequest） | Java/native路径需后续运行取证；不阻断已通过主界面，但不能声称完全离线 |
| DownloadTexture / NGUITools | 通用WWW辅助及样例logo | 不证明场景实例存在；静态候选保留 |
| DebugMenu | 内网/预发布环境切换 | 非正常发布入口；不得误连接内网地址 |

主数据：现实现21表，覆盖启动20类型；来源 `analysis/master-data/index.json` 和 `individual-textasset-provenance.json`。413地图 `analysis/level-data/provenance.json`。type22/LEVELDATA冲突未解决，留T12；不能按同名覆盖。资源层成功范围仅已有真实run用到的资源，不证明全部普通关卡资源可加载。
