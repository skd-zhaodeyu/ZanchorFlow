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

## Editable Path

Full Codex 新任务还可在完整页面视觉批准与 Truth 对账后、第一次消字前选择 Editable Path：本地重建原生文字、表格和结构路径，复杂视觉元素保留独立图片资产。无需强制 OCR 上传平台，不要求全元素矢量化；公式保留来源，素材修正额度与四项 Hard Gates 仍须满足。旧任务保持原路由；Qwen/WorkBuddy 的安装视图仍仅支持 Image Layer。重建质量是否优于其他路径需实际同输入比较，不能从对象数量或契约测试推断。

## 重建方式与费用

**Magic Layer**：通过 Canva Magic Layers 拆解消字后的页面，取得并验证 PPTX，再恢复原生文字；图形编辑单位以实际返回并验收的对象为准。Canva 免费用户额度有限，每月一般不超过 20 页，具体以账户实际额度为准。

**Image Layer**：通过图像分层服务将消字后的页面拆为背景和独立前景图片，再恢复原生文字；图形可独立移动、缩放和替换，内部仍是图片。需要配置分层服务，提交前核实权益、余额与价格并确认费用授权。

**Editable Path**：直接依据批准的完整页面和 Truth 重建原生文字、表格及可表达的结构；复杂图形优先复用素材，必要时用图像编辑分离为独立图片。跳过消字，不要求全元素矢量化。无需额外购买分层服务；必要的图像编辑使用当前宿主的生图能力，受现有套餐额度及计费规则约束。

Full Codex 由用户自行选择路线，不预设推荐；Image-only 安装视图只提供 Image Layer。完整案例见 [GitHub README](https://github.com/skd-zhaodeyu/ZanchorFlow#readme)。
