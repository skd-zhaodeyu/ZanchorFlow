# ZAnchorFlow · by David-Z

从材料、大纲和视觉样页，逐步制作风格统一、文字可修改的 PowerPoint 演示文稿。

ZAnchorFlow 是面向 Codex 的 skill。它把内容规划、Anchor 样页探索、整页视觉生成、文字恢复和可编辑重建接成一个可续作的流程：先确定内容和风格，再逐页生产，最后保留对象与来源完成整套交付。

## 看看真实成果

下面两组均来自实际使用，完成 5 页 9:16 的 ZAnchorFlow 技术介绍。点击查看整套 PPTX、PDF 与编辑方式。

### Magic Layers

[案例与编辑方式](examples/magic-layer/README.md) · [可编辑 PPTX](examples/magic-layer/presentation.pptx) · [PDF 预览](examples/magic-layer/presentation.pdf)

<table>
  <tr>
    <td align="center" width="20%"><a href="examples/magic-layer/page-01.png"><img src="examples/magic-layer/page-01.png" width="150" alt="Magic Layers 第 1 页"></a><br><sub>PAGE 01</sub></td>
    <td align="center" width="20%"><a href="examples/magic-layer/page-02.png"><img src="examples/magic-layer/page-02.png" width="150" alt="Magic Layers 第 2 页"></a><br><sub>PAGE 02</sub></td>
    <td align="center" width="20%"><a href="examples/magic-layer/page-03.png"><img src="examples/magic-layer/page-03.png" width="150" alt="Magic Layers 第 3 页"></a><br><sub>PAGE 03</sub></td>
    <td align="center" width="20%"><a href="examples/magic-layer/page-04.png"><img src="examples/magic-layer/page-04.png" width="150" alt="Magic Layers 第 4 页"></a><br><sub>PAGE 04</sub></td>
    <td align="center" width="20%"><a href="examples/magic-layer/page-05.png"><img src="examples/magic-layer/page-05.png" width="150" alt="Magic Layers 第 5 页"></a><br><sub>PAGE 05</sub></td>
  </tr>
</table>

### Image Layer

[案例与编辑方式](examples/image-layer/README.md) · [可编辑 PPTX](examples/image-layer/presentation.pptx) · [PDF 预览](examples/image-layer/presentation.pdf)

<table>
  <tr>
    <td align="center" width="20%"><a href="examples/image-layer/page-01.png"><img src="examples/image-layer/page-01.png" width="150" alt="Image Layer 第 1 页"></a><br><sub>PAGE 01</sub></td>
    <td align="center" width="20%"><a href="examples/image-layer/page-02.png"><img src="examples/image-layer/page-02.png" width="150" alt="Image Layer 第 2 页"></a><br><sub>PAGE 02</sub></td>
    <td align="center" width="20%"><a href="examples/image-layer/page-03.png"><img src="examples/image-layer/page-03.png" width="150" alt="Image Layer 第 3 页"></a><br><sub>PAGE 03</sub></td>
    <td align="center" width="20%"><a href="examples/image-layer/page-04.png"><img src="examples/image-layer/page-04.png" width="150" alt="Image Layer 第 4 页"></a><br><sub>PAGE 04</sub></td>
    <td align="center" width="20%"><a href="examples/image-layer/page-05.png"><img src="examples/image-layer/page-05.png" width="150" alt="Image Layer 第 5 页"></a><br><sub>PAGE 05</sub></td>
  </tr>
</table>

点击单页图片可查看大图。

两次使用均恢复了 264 个原生文字框。Magic Layers 按返回对象保留图形结构；Image Layer 提供 26 个独立透明前景图片资产和 5 张背景，便于整体移动、替换和删除。具体编辑单位见案例页。

案例日期为 2026-10-01 / 2026-10-02，页面中的竞品星标有对应快照日期。它们是当次真实成果，当前包的程序验证另见开发说明。

## 工作流程

材料 → 内容架构与大纲确认 → 多种 Anchor 样页 → 选定风格与逐页生成 → 文字计划和消字 → 重建路线选择 → 原生文字恢复 → 单页验收、合并和整套交付。

- 内容：明确页面任务、核心表达、关键信息与语义关系。
- 视觉：由选定 Anchor 延续 Style DNA；已验收页面保持锁定。
- 文字：使用内容真值、文字计划和 Native Text Visual Fit 恢复可修改文字。
- 续作：根据当前状态及证据恢复，复用已经完成的设计、下载与模型结果。
- 交付：保留页面顺序、资源、对象和来源绑定，合并后检查整套文件。

## 安装与依赖

**推荐下载精简包：[zanchorflow.zip](dist/zanchorflow.zip) · [SHA-256](dist/zanchorflow.zip.sha256)**

核对校验值后解压，将 zanchorflow 目录放入当前 Codex 的 skill 搜索目录。安装位置取决于你的 Codex 配置。详细步骤见 [安装说明](zanchorflow/docs/installation.md)。

也可从本仓库安装 zanchorflow 文件夹；这种方式包含 tests。精简 ZIP 不含测试，运行材料一致；测试不会作为正常执行指令加载。

Python 基础依赖：
~~~powershell
python -m pip install -r zanchorflow/requirements-base.txt
~~~
Image Layer 另使用 requirements-image.txt。原生整套合并需要 Windows 桌面 PowerPoint 和 requirements-office.txt。已验证的版本组合、预检命令和独立试用方法见安装说明；不安装也可让 Codex 读取解压目录的 SKILL.md 开始测试。

## 第一次使用

在有原始材料的独立项目中，可以这样请求：

> 使用 ZAnchorFlow，将这份材料制作成 5 页中文演示文稿。先规划内容大纲，再提供三种真正不同的样页，选定后延续整套风格。所有状态与成果保存到独立项目目录。

Codex 会按当前步骤读取规范，并在大纲、样页选择、页面正式展示和重建路线等现有确认点与你协作。

## 两条重建路线

**Magic Layer 分支（推荐）**：使用 Canva 实际可用的 Magic Layers，取得并验证 PPTX，再恢复原生文字。支持已批准的受控等比例画布映射与下载恢复。

**Image Layer 分支**：在消字后的页面上形成 Layer Plan，通过图像分层模型返回独立图片资产，再按批准画布重建、恢复原生文字。按实际选框保留编辑分组，940/941 等小幅源尺寸差异通过通用的每轴 5 源像素规则处理。

Image Layer 真实提交前需配置 ZANCHORFLOW_360_API_KEY，核实当前账户权益、余额与价格并确认费用授权。密钥只放执行进程环境，不能进入文件或日志。

## 续作与更新

让 Codex 读取当前 SKILL.md 和独立项目状态，使用 status 定位下一步；保留原身份、锁、预算和文件，复用已完成结果。

包名和调用名始终为 zanchorflow。新旧通过 manifest 的 updated_at_utc 和 ZIP SHA-256 区分。原有协议文件名、格式版本和来源兼容字段保留，不新增发布版本号。

## 开发与测试

源码保留完整测试；精简安装包采用白名单构建。Windows CI 执行无需 Office 的离线回归、包完整性和公开内容检查。本地 Office 测试另验证合并、实际编辑、保存及重新打开。

查看 [开发与验证](docs/development.md)。测试结果按程序测试、Office 集成和远程实际行为分别记录，不用测试数量替代功能覆盖。

## English

ZAnchorFlow is a Codex skill for turning source material into a coherent, editable PowerPoint deck. It connects content planning, approved visual anchors, page generation, text restoration and two reconstruction routes: Canva Magic Layers and Image Layer assets.

Download the fixed-name installation ZIP, check its SHA-256, and follow the installation guide. The source repository includes development tests; the slim ZIP retains the complete runtime. Updates are identified by an internal UTC timestamp and archive hash.

## License

[MIT](LICENSE) · David-Z. Third-party services and materials retain their own terms. No third-party fonts or model source code are bundled.

<details>
<summary>支持作者</summary>

如果 ZAnchorFlow 对你有帮助，欢迎自愿打赏。感谢支持。

<a href="docs/assets/support-wechat.png"><img src="docs/assets/support-wechat.png" width="240" alt="David-Z 微信收款二维码"></a>

</details>
