# 两包发布

普通用户下载发布附件 zanchorflow.zip，开发者下载 github-source.zip。两包都先走 tools/install.py 和 unified-install.md；无需用户选择宿主。

发布精简包顶层 ZanchorFlow/ 只有六个文件：README.md、LICENSE、docs/unified-install.md、tools/install.py、dist/zanchorflow.zip、dist/zanchorflow.zip.sha256。外层精简包的 README 来自 docs/slim-readme.md。

原 dist/zanchorflow.zip 是内嵌的不可变完整版基准，不能用外层同名发布包覆盖。两个安装入口使用相同安装器和统一说明；本仓库不保存按宿主生成的分支或宿主专用发行包。

```text
python -B tools/build.py --slim --work <仓库外work目录> --output <outputs/zanchorflow.zip>
python -B tools/build.py --slim --check <outputs/zanchorflow.zip>
python -B tools/build.py --source --work <仓库外work目录> --output <outputs/github-source.zip>
python -B tools/build.py --source --check <outputs/github-source.zip>
```

--slim 与 --source 互斥。输出和暂存必须在仓库之外。无模式的历史构建与 --check 继续用于原运行基准的开发检查，不是新版外层发行构建。

源码包含开发测试；可通过 ZANCHORFLOW_TEST_INSTALLER_ROOT 指向解压后的精简包根目录，让安装测试加载真实打包安装器。这个变量只由开发测试读取，生产安装器不读取它，也不能用来覆盖宿主。

结果分别记录程序安装、模型入口决策、真实宿主识别、原版离线及 Office 回归。未执行的项目不算通过，WPS 已知失败不改记为通过。

## File-first design_id maintenance candidate

The candidate runtime is built once from the maintained source. Both outer ZIPs embed exactly this candidate runtime and its checksum; install.py BASE_SHA is pinned to those bytes. The user-provided original outer archives remain untouched. tests/download_scope.json records the reversible maintenance delta before inherited frozen-source checks, and the new runtime modules are hash-pinned. Offline download/bind contract tests and a local read-only PowerPoint preview were verified; live Canva title retention and the complete live formal bind remain unverified. Event/History absence never denies the effective recovery link.

## GitHub 更新与展示材料

以远程当前仓库为发布底稿。合入新的技能、安装器、依赖和测试，保留 examples/ 和 docs/assets/；README 将新版安装说明与现有案例展示合并。案例只追加，不用旧源码包中的案例覆盖远程成果。

精简安装包装发布于 downloads/zanchorflow.zip，与内核 dist/zanchorflow.zip 分开。源码网页使用 GitHub 当前分支的 Download ZIP；固定名称 github-source.zip 在仓库之外生成并交付，避免把大源码 ZIP 再提交进 Git 或递归打入自己。

源码构建包含现有案例、案例校验文件及支持作者图片；精简包装仍保留六文件白名单，README 提供在线案例链接。两包内核保持相同，文档更新不改内核来源时间及安装器锚点。每次完成哈希、安装检查及公开内容检查后发布。
