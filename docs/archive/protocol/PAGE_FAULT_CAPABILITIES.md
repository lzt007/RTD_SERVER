# User page-fault evidence capability inventory

2026-10-28，回退后的boot4c6e3e3a-40c2-49af-a36d-33f509b82bc1，Android9/i686/4.4.124+。只读查询，没有新游戏/夹具/追踪实例/事件启用/security设置修改。

已有exceptions:page_fault_user与page_fault_kernel。用户事件ID44，address/ip/error_code均unsigned long、size8，原始格式打印address=%pf ip=%pf error_code=0x%lx。该接口有机会补齐现有signal事件没有的故障地址和指令指针；仅接口存在还不是有效捕获证明。

kprobe_events与kprobes/blacklist不存在，明确exit1/No such file；不能声称kprobe可用。kallsyms列do_page_fault/__do_page_fault/force_sig_info等名字，但地址全0，不修改kptr_restrict来解锁。全局tracing0，仅既有wifi实例。

下一方案应优先使用已有user page-fault事件，在自己的有限实例内选择保护类fault，避免所有正常缺页淹没缓冲。需要先以自有、可识别、私有命令触发的保护错误夹具验证真实fault PC/地址/位宽、计数完整和清理，再允许一次默认游戏捕获；不把接口存在、解析单测或旧SI_USER正例冒充该新事件的正例。筛选保护错误不能承诺捕获所有MAPERR，有限样本仍不能自动修复SIG11。

只读脚本analysis/android/page_fault_capabilities.py；原始25文件及查询退出状态/哈希在analysis/android/flow-runs/page-fault-capabilities-20261028。该清单与前一GLES2实测分开保存。
