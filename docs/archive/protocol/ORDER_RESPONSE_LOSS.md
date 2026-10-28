> 最终唯一审查C0/I3/新M0，三项同轮TDD修正后18socket/207Android GREEN，225server回归GREEN。非目标响应不解读、损坏DEFLATE记错502、所有不支持Expect明确417且不转发；实际游戏样本是修正前63a28c0，不追认已实机运行修正版，未重放。完整裁定见[审查记录](../reviews/2026-10-28-order-response-loss-review.md)。

# 原入场响应丢失与自动重试（2026-10-28）

本轮新增仅本机使用的诊断工具analysis/android/response_loss_proxy.py，没有改服务端业务、APK或Unity。完整六账号idle113源b532原样克隆到order-response-loss-20261028，无队伍/货币/体力夹具。上一轮人工11123、89场62回执活动battle、四旧QA与设备偏好完整备份保留。

## 实际行为

原候选36、PID26758/birth9892217/boot823aea7e-3168-4a17-949f-4967fedea7be，原native11f6与固定系统桥c63信号链双ready，源/包/身份/全六态及backend18767/proxy18766资格通过后，只有一次原MCP驱动flow20261028-012602。

- 原order_quest retry0，请求5558dfee47944ea0acd3d355f7f78f67，服务端成功4096后，代理完整接收413字节GZIP响应，再于UTC17:28:02.436902记录并关闭客户端连接，未向客户端发送响应头或响应体。
- 原客户端自行auth_user retry1，于17:28:03.429125原order_quest retry1返回4096；故障发生后至控制解锁无任何宿主输入，没有重连按钮点击或第二驱动。两次原请求除retry外的脱敏字段相同，实际token SHA相同且匹配持久UUID。
- 两次响应整体SHA不同，因为重认证更换session_id；不能声称完整响应字节相等。只读读取最终完整SQLite中的原session行，以唯一冻结order_result重建GZIP外壳，分别精确匹配实际记录的两个SHA及413字节长度，且对应不同session。由此确认实际相同入场result，而不保存/输出原Cookie或会话标识。
- 只新增run d85d3d9fa1bf4230a5a8f7840ea3b3f6，87→88场，62回执保持；3AP29→26，113单位、五队、其余五账号及配置完整相等。原GameManager控制解锁、restoreEnabled=1，停止输入，未强行胜利或结算。

实际驱动在01:27:48.889与01:27:53.735各点击一次原出发按钮，后者发生在get_level_master/form_units加载期间、首order及故障之前。不能称只有一次出发输入，亦不据此声称原客户端普遍防双击。实际只有一条retry0入场；所有宿主输入都早于故障，所以retry1并非第二次宿主入场点击的结果。原steps与完整请求保留。

## 工具与恢复

代理固定CLI127.0.0.1:18766→127.0.0.1:18767，仅显式--drop-order-quest11000武装一次、十分钟有效、user1/原retry0/HTTP200与4096匹配后才消耗；非目标/失败响应保持，默认无故障。1MiB请求/响应上限、有限超时、唯一日志、并发原子名额、关闭等待在途请求；诊断日志只保存摘要和非敏感元数据。GET health透传，独立/__response_loss_health用于宿主身份检查，不给游戏DTO加字段，不转发后台写。

真实客户端验收结束后，已确认原控制解锁且无输入控制器，固定命令核验后停止唯一拥有的代理/18767后端，再以同库/run-id启动普通18766 API/PID20388。切换后health/数据库路径/experimental=1、完整六态/四旧QA/受保护8文件/已关闭代理日志SHA均通过。运行时使用已知空闲状态下的进程结束，没有声称实际调用了server_close排空；该排空路径由真实本机socket合同测试覆盖。

## 失败与验证边界

初始缺少工具RED，首8合同GREEN；新增HTTP失败响应保持、数值类型拒绝误匹配、关闭在途日志竞争3项RED（1fail2errors）→11GREEN；新增默认未知响应原样转发RED14/1fail→14GREEN。最终14/7.640s、全203 Android/124.422s、72 Node/9140.0339ms均通过。最初测试后端在预期断连时打印ConnectionAbortedError，测试捕获OSError后清净；不是游戏失败。

实际审计先错误要求整个响应摘要相同，在识别外壳会话变化后以原SQLite+实际SHA逐个精确核对；接着发现宿主实际两次出发输入，改为明确记录两次且严格要求故障后零输入。没有重跑游戏、改存档或放宽唯一run/3AP/其他五态约束。关闭上一客户端时宿主读取JSON漏写UTF-8导致GBK错误，改为显式UTF-8后原件1e95/noPID/全六态/四旧库通过，上一包装器正常exit0。

本轮不代表所有操作丢响应、支付/迁移、所有网络错误、无限期无人值守或原生SIG11根因已修复。原生采集窗口与最终审查结论另行记入本页后续检查点；没有实际fatal-hook正例。失败/RED/操作偏差及所有原始索引独立保留。

原生实际窗口UTC17:25:32.283–17:35:32.883严格覆盖17:28:02首响应丢失、17:28:03重试及17:28:14控制完成；双expired/deadline/同身份/卸载close通过，无观测到的fault。本轮唯一整体验证审查待执行。最终完整SQLite备份SHAfeae3a7e67592a098c2009a66af863f19b3edfd15ab9179ebd2111627499d3b8，原生/代理/请求/原UI/完整六态交叉证明；完整证据在analysis/android/flow-runs/order-response-loss-20261028/evidence/execution。
