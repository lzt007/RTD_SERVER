# GitHub 上传范围

仓库保存源码、配置、翻译文本及项目文档。大型资源和生成包保留在本地，不上传 GitHub。

排除内容包括 ZIP/7z/RAR 压缩包、APK/AAB/OBB 安装包、Unity assets/unity3d 资源，以及原有 .gitignore 中的资源、构建产物和缓存。翻译项目另排除 analysis/ 解包分析目录和 sources/fonts/ 字体资源目录。服务端 RTD_SERVER.zip 也不上传。

运行和打包需要的原始资源、安装包及字体须另行在本地准备，路径参见项目 README 和配置文件。
