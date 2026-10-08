# 开发与验证

源码仓库保留 zanchorflow/tests 及其相对路径；安装 ZIP 采用白名单分发，不包含开发测试。源码和分发包的运行内容逐文件一致。

## 环境与测试
~~~powershell
python -m pip install -r requirements-dev.txt
python -B -m pytest zanchorflow/tests -q -m "not integration" --ignore=zanchorflow/tests/test_native_merge.py --basetemp <project-work/pytest> -o cache_dir=<project-work/cache>
~~~
此命令不调用 Office 或远程服务，与 Windows CI 一致。使用独立 work 目录设置 TEMP/TMP 、PYTHONDONTWRITEBYTECODE=1 和 PYTHONUTF8=1；后者确保 PowerShell 输出解码不随本机 GBK/UTF-8 语言设置变化。

本地安装 Microsoft PowerPoint/Excel 后，运行原有完整 tests；新增 WPS integration 测试另需本机 WPS 演示与 KWPP.Application，CI 不安装 WPS。原生合并模块实际调用 PowerPoint COM，现有 integration 测试实际编辑文字、图形、图表和 OLE，保存并重新打开。离线表示不依赖网络/API，不表示无需 Office。跳过、未验证与通过分开记录，不能用规则检查代替真实模型/浏览器行为。

原保护基准保留。publication scope 仅允许三个运行文件中明确登记的函数和额度文案变化；其余原函数及另外 16 个运行文件仍受基准约束。文档迁移检查只逆转声明的精确修改，再核对原始载荷哈希。

## 构建与验收
~~~powershell
python tools/build.py --work <project-work/package> --output <project-outputs/zanchorflow.zip>
python tools/build.py --check dist/zanchorflow.zip
~~~
先完成测试，再更新受影响规范哈希和 revision_scope，冻结 UTC 更新时间，随后构建。包内发生任何修改后必须重新冻结并构建。源码、ZIP、校验文件、Git 索引和重新检出字节必须一致；不要按操作系统自动改写 skill 换行。

案例属于有日期的真实使用展示；修订后的程序验证、真实模型行为和历史成果分别记录。CI 不提交私人夹具、密钥、原始运行状态或诊断历史。

MIT 适用于本项目拥有权利的代码与文档；不捆绑第三方字体或模型源码，第三方内容遵守原许可。

## 正文标题一致性修订

新任务在现有启动命令加 `--title-choice-required`，保存待选择状态；先依据当前大纲分类，再选择统一／自由。全为封面、目录、过渡或纯致谢等不适用页时，用 `stage2-title-policy --mode pending --page-roles-json <roles.json>` 自动跳过提问，不伪造作者决定。旧调用与旧状态保持自由标题。

正常执行只通过三个短入口：`stage2-title-policy`、`stage2-title-context`、`stage2-title-bind`。生成前读取当前页上下文并携带 `--title-contract-ref` 登记候选；初次基准由系统在既有检查 PASS 后登记。具体规则在协议 03/04/07，不能只读取命令而漏掉前置审批、身份、内容真值和锁约束。

新增测试保留以前的运行基准，先精确逆转登记的标题修改，再运行原函数和文档断言；独立新增模块另有固定校验。未声明修改不能借新功能改变已有 Gate、下载、画布或合并逻辑。两条路线的三页回放使用合成外部结果和合成页面评估；另有 `integration` 测试使用真实 PowerPoint 原生合并，不将前者称为在线生成验证。

精简包验收后，将同一 ZIP 和 SHA-256 放入 `dist`，再构建完整源码包：
~~~powershell
python tools/build.py --source --work <project-work/source> --output <project-outputs/github-source.zip>
python tools/build.py --source --check <project-outputs/github-source.zip>
~~~
完整包顶层为 `ZanchorFlow/`，包含全部测试、CI、公开案例及 `dist`；输出和临时打包目录必须位于仓库之外。构建使用白名单，不收集 `.git`、运行状态、缓存、凭据或本次报告。

## 标题后处理、阴影与接口修订验证

本轮按协议 07 中可执行示例验证真实 PPTX 属性、保留对象、输入输出哈希和复用；示例的 adjusted 仅代表参数已应用，视觉结果另行观察。新增错误样本包括映射/内容不一致、受保护对象、分组不明、来源或参数变化、非标题变化和旧验收证据。模型阴影判断与自然换行不能用填写 PASS 的 JSON 代替。

本轮修改通过 heading_refine_scope 的精确差异还原先回到 2026-10-02T17:27:14Z 源码，再进入原 title_scope 保护链；不替换历史基准哈希。旧自由模式、审批、下载、画布、付费和合并行为保持原断言。报告首表反映当前结果，事件历史独立保留。

## WPS 备用与 Python 条件提醒验证
新增 office_scope 精确差异还原先回到本轮来源基线，再进入 heading_refine_scope/title_scope；旧基线及行为断言保留。普通测试模拟两种应用，不启动真实 Office。WPS integration 使用合成输入进行原生合并、重开、编辑保存、错误页序与图片负例；仅操作本次文档。跨应用字体差异另记，其他 WPS 版本和复杂对象不据此声明兼容。Python 指引的静态检查、程序依赖诊断和实际 agent 行为分开记录。

## 二维与图形身份修订验证
visual_text_scope 精确还原本次差异后进入原 office_scope / heading_refine_scope / title_scope / publication 保护链；旧哈希与行为断言保留。仅共享文字计划验证器增加可选 graphic_identity 分支，准确内容角色继续走原校验。独立识别与最多两张图的实际消字是此次开发验收，原始图片、提示词、模型输出和失败日志保存在项目 work，不进入运行包；不增加 skill 的运行阶段、审批或常规材料。


当前交付为 **V1.0**；包名和调用名不变，同版本更新以内部更新时间区分。Image Layer 按编辑价值选框，差结果如实记录且不自动重新分层。包内版本、安装版本和哈希可用安装器核对；历史 RC 信息只用于来源追溯。
