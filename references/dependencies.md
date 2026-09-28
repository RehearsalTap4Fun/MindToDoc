# 能力依赖与 vendor 维护

Python 最低版本为 3.10。本轮测试环境为 Python 3.10.6、pytest 9.0.3。
`requirements*.txt` 声明兼容范围，不是精确环境锁定；升级后须重跑测试。

默认写作与转换只安装 `requirements.txt`。图像标注另装 `requirements-image.txt`，开发另装 `requirements-dev.txt`。

```powershell
python scripts/doctor.py
python scripts/doctor.py --capability image --capability test
python scripts/doctor.py --capability bi-code --skill-root "$env:USERPROFILE/.skills"
python scripts/doctor.py --capability dingtalk-cli --skill-root "$env:USERPROFILE/.skills"
```

可检查能力以根目录 `dependencies.json` 为准。Doctor 只检查指定能力，不以缺少可选能力阻断纯文档任务。
通过检查只说明文件、模块或命令可发现，不代表远端服务和鉴权可用。

## 外部 Skill 与服务

- BI 查已有埋点依赖 `k1-bi-tracking`，钉钉 CLI 回退依赖 `dws`；两者未 vendor。
- 从当前会话 Skill 清单读取它们的真实路径，或通过 `--skill-root` 检查本机安装目录。不得假定 vendor 相邻目录存在。
- 缺少对应 Skill 或权限时，记录未核验的数据，先完成本地可验证部分；不能把猜测的埋点或在线表结构视为查证结果。
- 在线同步需要会话提供的钉钉 MCP 或按专用 Skill 配置的 dws。Doctor 不列举远端权限。
- 音效需求表无需生产 API。试听、生成与转码另外依赖本地 ffmpeg 和公司服务凭据。
- 可选服务的凭据按各 Skill 的 example 配置，禁止写入交付登记或版本库。

## Vendor 更新

已收录 audio-production-pipeline、bi-log-requirements、dev-checklist-generator、slg-testcase-generator、guizang-ppt-skill、diagram-design。
来源信息见 `vendor/provenance.json`。导入时未记录的上游提交保留 unknown，不能用本仓库提交冒充上游版本。

升级步骤：保留现有副本，记录来源及真实上游版本，比较本地补丁，合并后运行根目录回归与受影响 vendor 测试。
不得直接覆盖本地安全补丁。现有 examples 是历史资料，不会因更新 Skill 自动成为新规范的合格样例。
