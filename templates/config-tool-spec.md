# {{工具名}} · 配置生成器/工具 Spec 模板

> 适用于「配置生成器」「批量配置工具」类需求(读输入 → 生成 xlsx/json/md)。
> 用法:每次接到此类需求,brainstorming 时按本模板的「澄清链路」依次确认,每节给出选项与默认推荐,跳过不适用项。
> 目的:把这类工具的固定问询链路固化下来,避免每次重新发明问题清单。

---

## 1. 定位

- **工具职责**:{{一句话说清楚 输入 → 输出}}
- **使用者**:{{数值策划 / 关卡策划 / 程序 / AI Agent}}
- **触发方式**:{{命令行 / 双击 / CI / 主生成器内联}}

---

## 2. 输入形态(Input Shape)

固定要追的 5 个维度,选项如下:

### 2.1 输入语义
- [ ] **A. 风格/语义标签**(如 pressure / boss):工具读 tag 推字段
- [ ] **B. 组件式标签**(如 attack-v2 / gk-extreme):tag 直接对应资产实例
- [ ] **C. 参数 patch**(如 +1tier_diff / extra_slice):tag 是 override
- [ ] **D. 阶段/节奏标签**(如 开局-平稳-引爆-终章):tag 描述整段曲线
- [ ] **其他**

### 2.2 与默认体系的关系
- [ ] **A. tag 唯一输入源**:不预设默认,完全由 tag 决定
- [ ] **B. 默认 + tag 调整**(推荐):基线走默认,tag 是 patch
- [ ] **C. tag = 预设包**:每个 tag 是一整套包,关只配 1-2 主 tag

### 2.3 输入文件格式
- [ ] **A. xlsx**(策划体验最好,与项目其它配置一致)
- [ ] **B. yaml/json**(机器友好,但与项目断层)
- [ ] **C. CLI 实参**(适合迭代期快试)
- [ ] **D. GUI**(成本高,通常 NO)

### 2.4 输入路径(项目结构对齐)
按本项目惯例,可选:
- [ ] `input/{{工具名}}/`(策划主输入)
- [ ] `output/test-config/{{工具名}}/`(中间层 / 与生成产物同目录)
- [ ] `scripts/{{工具名}}.config.{ext}`(脚本伴生)

### 2.5 是否必须提供
- [ ] **必须**:无输入则报错退出(保证产物可追踪)
- [ ] **可选**:无输入走默认逻辑(快路径可用)

---

## 3. 词表/枚举(Vocabulary)

### 3.1 词表起点
- [ ] **AI 提初版**:由 AI 据现有默认逻辑提 12-16 个候选,用户迭代
- [ ] **最小集**:6-8 个最常用,起步后扩展
- [ ] **不定词只定机制**:词表后续策划补,工具仅做注册器

### 3.2 词表参数化
- [ ] **A. 纯枚举**(推荐起步):tag 是固定串,工具按表查
- [ ] **B. 枚举 + 参数**:支持 `tagname:value`(如 `difficulty:tier+2`)
- [ ] **C. 宽松查表**:任意串,查不到忽略+警告(隐藏拼写错风险)

### 3.3 词表定义位置
- [ ] **A. yaml 重配置**:词表 + patch 都在 yaml,工具仅读
- [ ] **B. Python 函数**(推荐复杂逻辑):词表是注册器,patch 是函数
- [ ] **C. 同表 TagDef 页**:输入文件内额外页签,人读对照 + 互斥校验

---

## 4. 落点字段(Affected Fields)

### 4.1 工具能改哪几类字段
列出该业务允许 tag 影响的字段集合(避免 tag 越权):
- [ ] {{字段类 1,如 SliceList/SliceCount}}
- [ ] {{字段类 2,如 AiProfile/Difficulty/Modifier}}
- [ ] {{字段类 3,如 OpponentTeam/Threshold/TicketCost}}
- [ ] {{字段类 4,如「生成专属资产」(强表达力但增复杂度,默认 NO)}}

### 4.2 作用粒度
- [ ] **单条**:tag 只对当前行生效
- [ ] **粒度分层**:全局 → tier/group → 单条,从粗到细叠加
- [ ] **粗粒度**:tag 只贴粗层(如 round/group)

### 4.3 叠加顺序(若多源)
{{固定顺序如 默认 → tag → 局部 override,不留歧义}}

---

## 5. 冲突策略(Conflict)

- [ ] **A. 报错退出**(推荐):同行 tag 冲突 → 列出冲突表 → 退出非零
- [ ] **B. 优先级覆盖**:词表序定优先级,后者赢/先者赢
- [ ] **C. 互斥组**:词表预声明 mutual_exclude 组,同组多 tag 报错

---

## 6. 输出形态(Output Shape)

### 6.1 与现有生成器关系
- [ ] **A. 集成进现有生成器**:加一步 patch 后写整 xlsx
- [ ] **B. 独立补丁脚本**:吃现有 xlsx + 输入,输出补丁后 xlsx
- [ ] **C. 另起生成器**:不动旧脚本,独立产物路径
- [ ] **D. 中间 json 路由**:工具吐 json,主生成器读

### 6.2 输出范围
- [ ] **只生成核心子集**(如关卡相关 8 表)
- [ ] **生成完整 xlsx**(复制旧逻辑其余部分)
- [ ] **只生成中间产物**(json/csv,留给下游)

### 6.3 输出路径
- [ ] `output/test-config/{{产物名}}.xlsx`(默认与现有产物同目录)
- [ ] `output/test-config/{{工具名}}/`(子目录)

---

## 7. 校验与产物可追踪

- **必检项清单**:{{ID 唯一 / 引用完整性 / 阈值 lose<draw<win / tag 词表存在等}}
- **报告格式**:{{stdout 摘要 + summary.json + 失败明细}}
- **退出码**:{{0=ok / 1=校验失败 / 2=输入错}}
- **覆盖策略**:{{文件被 Excel 占用时回退到 *.generated.xlsx}}

---

## 8. 实现拆分建议(三层默认)

按职责拆,默认结构:

```
output/test-config/{{工具名}}/
├── {{工具名}}_lib.py            # tag 注册器 + 每个 tag 的 patch 函数(纯逻辑,无 IO)
├── apply_{{工具名}}.py          # 入口:读输入 → 应用 patch → 写产物
└── generate_{{工具名}}_template.py   # 一次性模板生成器(可选)
```

理由:逻辑(lib)/编排(apply)/初始化(template)三类职责彻底分离,各自可独立测试。

---

## 9. 转写 spec 模板

确认完上述节后,把答案折叠成 spec 文档保存到
`docs/superpowers/specs/YYYY-MM-DD-{{kebab-name}}-design.md`,字段对齐
- 1.定位
- 2.输入形态(语义/默认关系/格式/路径/必选)
- 3.词表(起点/参数化/位置)
- 4.落点字段(允许集 / 粒度 / 叠加)
- 5.冲突策略
- 6.输出形态(关系/范围/路径)
- 7.校验
- 8.实现拆分

---

## 10. AI 使用约定

- 此模板适用时,brainstorming 阶段应**一次性把 1-7 节合并到 ≤3 个 AskUserQuestion**(每题 multiSelect,塞同节问题),避免 9 轮单题问询。
- 用户已选过的项就在 spec 里直引,不重复问。
- 词表初版若选 AI 提,先读项目现有默认逻辑(如 generate_*.py 里的 tier 模板),据此提候选,不空想。

---

## 11. 自检自动化(plan 落盘后必跑)

写完 implementation plan 后,plan 通常含几十段 Python 代码片段,函数签名 / 类型 / 全局状态(如 TAG_REGISTRY)不一致是最常见漏检。占位扫和 spec 覆盖度可肉眼过,签名一致只能机器看。

**plan 第一个任务必须是「stub 抽提 + 静态检查」**,通过后再开始按任务实现。具体做法:

1. **抽提**:把 plan 里所有 Python 代码块连缀成 `output/.plan-stub/{{工具名}}_stub.py`(临时文件,不入 git),按出现顺序拼接;import / dataclass / 函数 / 测试 全部入栈。
2. **跑 ruff**:
   ```bash
   ruff check output/.plan-stub/{{工具名}}_stub.py
   ```
   重点看 F821(未定义引用)/ F811(重复定义)/ E999(语法错)。
3. **跑 mypy --strict**(可选,需要项目已配 mypy):
   ```bash
   mypy --strict output/.plan-stub/{{工具名}}_stub.py
   ```
   重点看 `name-defined` / `attr-defined` / 签名不匹配。
4. **修复**:发现的不一致**直接改 plan**(不是改 stub),再次抽提验证。
5. **删除 stub**:静态检查通过后删除 `output/.plan-stub/`,plan 才进入正式实施。

**抽提脚本建议**(`scripts/extract_plan_stub.py`,可选实现):
```python
# 用法: python scripts/extract_plan_stub.py docs/superpowers/plans/<plan>.md > output/.plan-stub/<name>_stub.py
import re, sys
content = open(sys.argv[1], encoding='utf-8').read()
blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
print('\n# --- block ---\n'.join(blocks))
```

**为什么不在执行阶段才发现**:plan 阶段抽提一次拍平所有签名分歧;执行 agent 一边跑测试一边修签名会反复回滚先前任务,代价高 5-10 倍。

**适用条件**:plan 含 ≥10 段 Python 代码块时强制跑;<10 段时人工眼检即可。

