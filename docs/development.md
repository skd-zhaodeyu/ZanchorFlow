# 开发与验证

源码仓库保留 zanchorflow/tests 及其相对路径；安装 ZIP 采用白名单分发，不包含开发测试。源码和分发包的运行内容逐文件一致。

## 环境与测试
~~~powershell
python -m pip install -r requirements-dev.txt
python -B -m pytest zanchorflow/tests -q -m "not integration" --ignore=zanchorflow/tests/test_native_merge.py --basetemp <project-work/pytest> -o cache_dir=<project-work/cache>
~~~
此命令不调用 Office 或远程服务，与 Windows CI 一致。使用独立 work 目录设置 TEMP/TMP 、PYTHONDONTWRITEBYTECODE=1 和 PYTHONUTF8=1；后者确保 PowerShell 输出解码不随本机 GBK/UTF-8 语言设置变化。

本地安装 Microsoft PowerPoint/Excel 后，运行完整 tests；原生合并模块实际调用 PowerPoint COM，现有 integration 测试实际编辑文字、图形、图表和 OLE，保存并重新打开。离线表示不依赖网络/API，不表示无需 Office。跳过、未验证与通过分开记录，不能用规则检查代替真实模型/浏览器行为。

原保护基准保留。publication scope 仅允许三个运行文件中明确登记的函数和额度文案变化；其余原函数及另外 16 个运行文件仍受基准约束。文档迁移检查只逆转声明的精确修改，再核对原始载荷哈希。

## 构建与验收
~~~powershell
python tools/build.py --work <project-work/package> --output <project-outputs/zanchorflow.zip>
python tools/build.py --check dist/zanchorflow.zip
~~~
先完成测试，再更新受影响规范哈希和 revision_scope，冻结 UTC 更新时间，随后构建。包内发生任何修改后必须重新冻结并构建。源码、ZIP、校验文件、Git 索引和重新检出字节必须一致；不要按操作系统自动改写 skill 换行。

案例属于有日期的真实使用展示；修订后的程序验证、真实模型行为和历史成果分别记录。CI 不提交私人夹具、密钥、原始运行状态或诊断历史。

MIT 适用于本项目拥有权利的代码与文档；不捆绑第三方字体或模型源码，第三方内容遵守原许可。
