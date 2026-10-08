# 安装与首次使用

ZAnchorFlow · by David-Z

下载仓库提供的 dist/zanchorflow.zip，核对旁边的 SHA-256 文件，解压为 zanchorflow/。这是面向普通用户的精简包，包含完整运行材料，不含开发测试。安装时把整个 zanchorflow 目录放入当前 Codex 的 skill 搜索目录；安装位置由你的 Codex 配置决定。安装与升级都应由用户明确要求。

也可从 GitHub 安装仓库内 zanchorflow 文件夹。这种方式会复制该文件夹中的 tests 和 pytest.ini；测试不会作为正常运行指令加载。ZIP 和源码文件夹的运行文件一致。

不安装也可以测试：解压后让 Codex 读取该目录的 SKILL.md，在独立项目 work/outputs 保存状态与成果。已有任务不自动切换路线，不伪造来源。

## 依赖

本地验证环境：Windows、Python 3.14.5；具体已验证依赖版本见分组 requirements 文件。
优先复用当前 Host 的可用 Python。执行 agent 仅在发现当前步骤缺少解释器或必要依赖时提醒，并按实际缺项说明需要做的准备；不固定开场提醒。单个 python 命令不可用不代表未安装，先结合 Host 运行环境、可用启动器及实际路径判断。没有可用解释器时说明受影响步骤和建立环境的方法；缺库时仅安装当前步骤对应的分组依赖。路径、权限、COM 和网络错误分别诊断。以下命令供实际缺项时使用，不要求重复安装；不自动安装、改全局 PATH 或捆绑环境管理器。
~~~powershell
python -m pip install -r requirements-base.txt
python scripts/preflight.py --skill-dir . --output-dir <project-work/preflight> --scope package
~~~
Image Layer 另安装 requirements-image.txt。完整原生合并需要 Windows、桌面 Microsoft PowerPoint 或通过本机能力预检的 WPS 演示，以及 requirements-office.txt；Office/WPS 不是 pip 包。默认优先 PowerPoint，不可用时检测 WPS 的 KWPP.Application；也可使用 --office-host powerpoint 或 --office-host wps 显式选择。测试与 Excel/OLE 编辑夹具另见仓库开发说明。已实测 WPS Office 12.1.0.28505 的小型 PPTX 合并和编辑；其他版本、复杂对象及跨应用字体呈现另行验证，不承诺跨应用像素一致。

Magic Layer 使用 Canva 中实际可用的 Magic Layers 功能与受支持的 Host 下载能力，按账号实际权限操作。Image Layer 的 Layer Plan 可以先准备；真实提交前使用 https://research.360.cn/workspace/apikeys 配置 ZANCHORFLOW_360_API_KEY，核实当前权益、余额与价格并确认费用授权。密钥只放执行进程环境，不写入状态、日志或包。

## 首次使用与续作

让 Codex 使用本目录 SKILL.md，例如：“使用 ZAnchorFlow，把这份材料制作成 5 页中文演示文稿，先规划大纲，再提供有明显差异的样页。”
现有大纲、Anchor 选择、页面正式展示和重建路线选择的确认点均保留。

从解压目录运行命令；所有项目状态、临时文件和输出放在独立项目目录。
~~~powershell
python scripts/canva_bridge.py init --state <project-work/state.json>
python scripts/canva_bridge.py status --state <project-work/state.json>
~~~
按当前步骤读取八份规范及必要前置规则。完整的 Codex 接线和合并命令见 [Host bridge](codex-canva-bridge.md)；Image Layer 的正式打包命令见协议 08。先跑预检，再按真实状态续作；已经完成的远程任务沿原身份恢复。

下载后验证使用相同 Python 环境；若 PATH python 与验证环境不同，通过 finalizer 的 -PythonExecutable 指定绝对路径。预检只检查，不安装依赖。

## 更新时间与升级

归档、目录和调用名始终为 zanchorflow，不增加发布版本号。用 manifest.yaml 的 updated_at_utc 和 ZIP SHA-256 区分新旧。
当前正式标识为 V1.0，skill_version 为字符串 1.0；同版本维护以 updated_at_utc 区分。Protocol Baseline RC17、历史 RC 记录、子协议和内部格式编号仍是兼容/来源信息，不代表当前发布版本。

升级时先准备第二份副本、核对哈希和预检；用户决定替换后再操作。旧项目继续绑定其原来源，已封页成果不强制迁移。项目工作文件不放入 skill 目录。

## 核对正在使用的版本

两个同名包包含同一运行内核。安装器 inspect/prepare/install 结果展示 package_identity（skill_version、updated_at_utc）、package_runtime_sha256、installed_identity 及 installed_runtime_matches。同为 V1.0 也要核对更新时间和字节匹配，不能仅看名称。

交付包更新不会自动覆盖已安装的 skill。若仍使用之前安装的候选版，其界面可能继续显示旧标识；先 inspect，确认使用的目录及包来源。读取解压目录的 SKILL.md 可以独立试用，实际安装/发布由使用者明确指示。本轮不自动操作 GitHub Release、分支或标签。完整旧 release/… 标签若来源未定位，不宣称已修改该外部标签。
