# 新项目接入指南

本文档说明如何将 SLG 测试用例生成 Skill 接入到新项目中。

**仓库地址**：https://github.com/HardcoreLi/slg-testcase-generator

---

## 架构说明

```
通用基础层（所有项目共享）          项目配置层（每个项目独立）
~/.cursor/skills/                  [项目工作区]/
└── slg-testcase-generator/        └── testcase-config/
    ├── SKILL.md                       ├── project_config.md    ← 核心配置
    ├── references/                    ├── config.json          ← 脚本用配置
    │   ├── core_writing_rules.md      ├── game_knowledge/      ← 项目特色玩法
    │   ├── common_scenarios.md        │   └── ...
    │   ├── type_a/b/c/d.md           ├── doc/                 ← 人工用例样本
    │   ├── file-operations-compact.md └── output/              ← 历史输出
    │   ├── 2_config.md
    │   └── game_knowledge/        
    │       ├── battle_system.md   
    │       ├── hero_system.md     
    │       ├── redpoint_system.md 
    │       └── cross_server_system.md
    └── scripts/                   
```

- **通用基础层**：包含7步流程、9条核心规则、59个场景模板、通用 SLG 知识框架等，所有项目共享
- **项目配置层**：包含项目特有的路径/ID、特色玩法知识、人工样本等，每个项目独立维护

---

## 接入步骤

### 第一步：克隆共享仓库

```bash
git clone https://github.com/HardcoreLi/slg-testcase-generator.git ~/Desktop/slg-testcase-generator_ForAll
```

### 第二步：安装通用 Skill 到 Cursor

```bash
# 如果已存在旧版，先删除
rm -rf ~/.cursor/skills/slg-testcase-generator

# 方式1：软链接（推荐，git pull 更新后自动生效）
ln -s ~/Desktop/slg-testcase-generator_ForAll/slg-testcase-generator ~/.cursor/skills/slg-testcase-generator

# 方式2：复制（需手动更新）
cp -r ~/Desktop/slg-testcase-generator_ForAll/slg-testcase-generator ~/.cursor/skills/slg-testcase-generator
```

> 安装后重启 Cursor，在对话中提到"生成用例"/"测试用例"时 AI 会自动激活此 Skill。

### 第三步：创建项目配置目录

在你的项目工作区根目录下创建 `testcase-config/` 目录：

```bash
cd /path/to/your-project-workspace
mkdir -p testcase-config/game_knowledge testcase-config/doc testcase-config/output
```

### 第四步：创建项目配置文件

复制模板并填写：

```bash
cp ~/.cursor/skills/slg-testcase-generator/project_config.template.md testcase-config/project_config.md
```

打开 `testcase-config/project_config.md`，填写以下必填项：

| 配置项 | 说明 | 如何获取 |
|--------|------|----------|
| 用例根目录 ID | Google Drive 文件夹 ID | 从 Drive 链接中提取 |
| 用例模板 Sheet ID | 用例模板文件 ID | 从模板文件链接中提取 |
| 凭证文件名 | OAuth 凭证文件 | 从 GCP 控制台下载 |
| 配置表总文件夹链接 | 配置表根目录 | 向策划获取 |
| 配置表释义 Sheet ID | 配置表释义文档 | 向策划获取 |

### 第五步：创建脚本配置文件

```bash
cp ~/.cursor/skills/slg-testcase-generator/scripts/config.template.json testcase-config/config.json
```

编辑 `testcase-config/config.json`，填入实际值。

### 第六步：添加项目特色玩法知识（可选）

如果项目有通用框架未覆盖的特色玩法，在 `testcase-config/game_knowledge/` 下创建知识文件：

```bash
# 示例：创建项目特色玩法知识
touch testcase-config/game_knowledge/my_special_system.md
```

然后在 `testcase-config/project_config.md` 的「关键词触发规则」中添加触发规则。

### 第七步：添加人工用例样本（可选）

将项目的人工用例样本放入 `testcase-config/doc/` 目录，供 AI 参考写法风格。

---

## 验证

配置完成后，在 Cursor 中打开项目工作区，对 AI 说：

```
帮我生成 [功能名称] 的测试用例，PRD 链接：[链接]
```

AI 应该会：
1. 先读取 `testcase-config/project_config.md` 获取项目配置
2. 按照7步流程执行
3. 使用项目配置中的路径/ID 进行文件操作

如果 AI 提示「当前项目未配置 testcase-config/」，说明配置文件路径不正确，请检查目录结构。

---

## P2 项目配置参考

可以参考 `K1-testcase-config/` 目录作为完整的项目配置示例。

---

## 更新通用 Skill

```bash
cd ~/Desktop/slg-testcase-generator_ForAll
git pull origin main
```

如果是软链接方式安装的，更新后自动生效。如果是复制的，需要重新复制到 `~/.cursor/skills/`。

---

## 常见问题

**Q: 通用 Skill 更新后，项目配置需要改吗？**
A: 通常不需要。通用 Skill 的更新主要是规则和模板的优化，不影响项目配置。

**Q: 多个项目可以共用同一个凭证文件吗？**
A: 取决于 GCP 项目配置。如果多个项目的 Google Drive 在同一个组织下，可以共用。

**Q: 项目特色玩法知识怎么写？**
A: 参考 `references/game_knowledge/README.md` 中的知识提取模板。

**Q: config.json 里的 API Key 会被上传到 Git 吗？**
A: 不会。仓库的 `.gitignore` 已配置排除所有 `config.json`（含敏感信息），只保留 `config.template.json` 模板。
