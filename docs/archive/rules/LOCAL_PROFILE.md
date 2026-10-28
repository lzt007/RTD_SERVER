# 本地改名及账号扩展边界

原 change_user_name 请求为 ver/retry/user_name，成功 result 为 string[]，本地返回空数组。原 MMEtcChangeName 成功后自行更新缓存名字并回到 ETC_MENU；非法名字使用原 NG_NAME=8448。

本地名称规则：1–32 个字符、非全空白，不含控制字符和代理码点，正常中日文可用。不声称恢复原服禁词规则；只更新当前玩家 user_name，重复同名自然幂等，不改变账号绑定、货币、单位或编队。现有请求事务保证写入失败回滚，好友搜索/列表即时读取当前名字。

make_password、move_save_data、accept_invite_usercode 继续明确返回未实现，不生成假密码、迁移成功或邀请奖励。跨设备本地恢复采用独立备份方案，不冒充官方迁移协议。支付完全排除。

服务端 4 项先 RED 后 GREEN：ASCII/中日文、原空数组、同名重试、重启、好友当前资料、非法输入和注入写后异常回滚。全回归 101 项（48.883 秒）、工具 39 项（0.512 秒）通过。

原 UI 自动化只观察 MMEtcMenu/MMEtcChangeName，选择观测到的 Button_05_change_name，经 Android MCP 原生 EditText 全选替换，再核对 Unity 输入内容与目标名字完全相同才确认。未观察到全选/确认控件或内容不匹配时停止留证，不猜测点击支付或外部链接。

实机 flow 20261026-005515 全自动 CleanSecond→LocalRevived 并返回主界面；与原档比较，只有昵称和自然体力恢复变化，其余完整档一致。客户端/API 重启 flow 20261026-005750 后仍为 LocalRevived，完整玩家状态严格一致 SHA `c66c9df4746348fa2b9d1818f79d8a36fa572392a773039c4f7379a4bbd7cecf`，before-restart.json/after-restart.sqlite3 留在隔离目录 local-profile-20261026。

一次整增量独立审查发现父 MainMenu 覆盖子界面观察，导致首次安全停在其他菜单、未提交改名；补回 profile_observation 及组合观察回归先 RED 后 GREEN，40 项工具测试（0.627 秒）通过，后续实机全自动成功。无其他审查发现。派生包 SHA `0582bf067503175a0c5c8566936c45928a2fbc2fa470ad4573d01c9a61dfc37b`；原件与正式档不改。
