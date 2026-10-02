# 安装与首次使用

ZAnchorFlow · by David-Z

下载仓库提供的 dist/zanchorflow.zip，核对旁边的 SHA-256 文件，解压为 zanchorflow/。这是面向普通用户的精简包，包含完整运行材料，不含开发测试。安装时把整个 zanchorflow 目录放入当前 Codex 的 skill 搜索目录；安装位置由你的 Codex 配置决定。安装与升级都应由用户明确要求。

也可从 GitHub 安装仓库内 zanchorflow 文件夹。这种方式会复制该文件夹中的 tests 和 pytest.ini；测试不会作为正常运行指令加载。ZIP 和源码文件夹的运行文件一致。

不安装也可以测试：解压后让 Codex 读取该目录的 SKILL.md，在独立项目 work/outputs 保存状态与成果。已有任务不自动切换路线，不伪造来源。

## 依赖

本地验证环境：Windows、Python 3.14.5；具体已验证依赖版本见分组 requirements 文件。
~~~powershell
python -m pip install -r requirements-base.txt
python scripts/preflight.py --skill-dir . --output-dir <project-work/preflight> --scope package
~~~
Image Layer 另安装 requirements-image.txt。完整原生合并需要 Windows、桌面 Microsoft PowerPoint，以及 requirements-office.txt；Office 不是 pip 包。测试与 Excel/OLE 编辑夹具另见仓库开发说明。

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
既有 skill_version、protocol_baseline、协议文件名与格式版本是来源/兼容标识，不代表本次新增版本。来源字段保留 0.9.0-rc19-candidate 与 Protocol Baseline RC17，仅用于兼容识别。

升级时先准备第二份副本、核对哈希和预检；用户决定替换后再操作。旧项目继续绑定其原来源，已封页成果不强制迁移。项目工作文件不放入 skill 目录。
