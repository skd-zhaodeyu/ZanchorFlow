# 安装 ZAnchorFlow

用户只需把这个包交给当前 Agent，说：**安装这个 skill**。

## 给安装 Agent 的入口

这是安装包装，不是已安装的技能目录。先读取 [统一安装说明](docs/unified-install.md)，从当前包装目录调用 `tools/install.py`，依次 inspect、prepare，再在确认持久安装位置后 install。

```text
python -B tools/install.py inspect --work <项目中独立work的绝对路径>
```

工作目录必须在包装之外。根据当前宿主真实运行信息确认安装位置；需要时按统一说明登记 runtime-context.json。不要让用户选择宿主，不要直接复制外层 ZanchorFlow，不要绕过安装器直接安装内层 dist/zanchorflow.zip，不临场改写技能。

安装器只在明确千问或 WorkBuddy 时生成 Image Layer 视图。Codex、其他或身份不足的宿主得到原始完整版；身份冲突、位置不明或不安全路径停止。没有 --host 或 --force。全部原有质量要求保留，运行时不重新猜测宿主。

## 包与安装内容

本包装只有安装器、说明、许可和不可变基准包，不含测试或案例。`dist/zanchorflow.zip` 是原始完整版基准，不是需要另行下载的发布包；由安装器读取。安装后的同名 zanchorflow 才是技能目录。

检查本外层包旁的 zanchorflow.zip.sha256。开发者使用配套 github-source.zip。安装不需要网络、远程生图或付费分层；使用阶段的依赖和外部工具按安装后的原技能规则处理。


当前交付为 **V1.0**；包名和调用名不变，同版本更新以内部更新时间区分。Image Layer 按编辑价值选框，差结果如实记录且不自动重新分层。包内版本、安装版本和哈希可用安装器核对；历史 RC 信息只用于来源追溯。

[最新介绍与全部案例](https://github.com/skd-zhaodeyu/ZanchorFlow#看看真实成果)
