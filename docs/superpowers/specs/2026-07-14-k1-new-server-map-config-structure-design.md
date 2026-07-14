# K1 新服大地图配置表结构调整设计

## 目标

调整 `output/K1新服大地图重构功能策划案-配置表结构.md`，使派生文档以 K1 三端仓库当前正式配置为基础，不再把 `new_server_map.xlsx` 及其逻辑页签描述为既定落地结构。

## 结构原则

- 现有正式表能够承载的内容优先复用或扩展现有表。
- 既有地图对象继续使用原对象配置，避免新增龙巢、圣坛、堡垒、王座对象类型。
- 只有现有表无法清晰表达且具有独立维护价值的关系，才新增正式配置表。
- 运行时归属、占领进度、免战截止时间、服务器共享迷雾状态等数据不进入配置表结构派生文档。
- 文档明确区分新服普通大地图、旧服地图和 KVK 场景，使用地图模板或场景类型隔离，不能直接改写全局旧数据。

## 目标配置分层

### 地图骨架与模板选择

- `MapTypeCfg`：新增或复用新服普通大地图的场景类型记录，关联 `NavMeshId` 与 `NpcRefreshId`。
- `MapSizeCfg`：复用地图尺寸方案及堡垒、旗帜、龙巢、王座等对象范围参数，不承担真实 NavMesh 宽高定义。
- `NavMesh / TileMesh / GlobalObstacles`：由地图工具产出，继续作为地图真实尺寸、通行和阻挡的权威数据；派生文档只写依赖和交付校验，不虚构 Excel 字段。

### 区域、出生与刷新

- `D2NpcZoneCfg`：扩展或复用地图区域、可用空间、玩家出生区域、刷新带及地图模板关联。
- `D2NpcBandCfg / D2NpcTroopClassCfg / D2GatherCfg / D2SearchCfg / D2MonsterCfg`：继续承载区域内怪物、资源点和搜索内容，不重复设计新表。

### 格子与战略建筑

- `UnionWarAreaCfg`：作为新服地图堡垒格子的主配置，承载格子 ID、圈层/等级、中心坐标、建筑坐标和系统堡垒配置引用；补充新服模板、`D2NpcZoneCfg` 区域引用、格子序号、堡垒类别、初始共享标记及是否可占领等必要字段。
- `RandomMapUnitCfg`：继续承载龙巢、圣坛和王座的独立点位，通过 `MapSizeCfg.RandomUnit` 选择新服专用数据集；扩展区域、所在格子和相邻格子引用，不新增平行点位表。
- `UnionTerritoryCfg`：继续承载联盟自建要塞、旗帜和联盟祭坛。新服模板关闭自建入口，不把系统堡垒格子改造成该表的新对象。
- `UnionWarBuildingCfg`：复用系统堡垒、龙巢、小祭坛等固定战略建筑的占领、和平期、守军、产出和属性规则；系统堡垒由 `UnionWarAreaCfg.BuildingID` 引用，龙巢和圣坛由 `RandomMapUnitCfg.BuildingID` 引用。
- `UnionWarBuildingPropertyCfg`：继续承载固定战略建筑属性加成。
- `KingWarBuildingCfg`：继续承载王座与瞭望塔规则、坐标和属性，不新增 `ThronePoint` 逻辑页签。

### 必要新增表

- `FortressAdjacencyCfg`：维护新服地图堡垒格子的四邻攻击拓扑。字段包括 ID、地图模板、当前格子、相邻格子、方向、是否可作为攻击路径。要求互邻、同模板、仅上下左右且无重复边。
- `FogLayerCfg`：维护服务器共享迷雾的层级、适用地图模板、开放时间、`D2NpcZoneCfg` 区域 ID 列表及未开放时的交互限制。格子不重复保存迷雾层级，以 `UnionWarAreaCfg.ZoneID` 关联 `D2NpcZoneCfg`，再由 `FogLayerCfg.ZoneIDs` 确定开放层级。

## 删除的逻辑表口径

派生文档删除下列被误写成正式结构的逻辑页签：

- `new_server_map.xlsx`
- `MapBasic`
- `MapRegion`
- `FortressGrid`
- `InitialSharedFortress`
- `DragonNestPoint`
- `AltarPoint`
- `ThronePoint`
- `SpawnRegion`
- `FortressOccupyRule`
- `AllianceTechBranch`

对应职责分别回归现有正式表；联盟科技仅作为既有科技表扩展依赖说明，不在本文虚构表名和字段。

## 文档呈现方式

正式派生文档按以下顺序重写：

1. 配置改造总览：列出复用、扩展、新增、工具产出四类配置。
2. 依赖链：说明 `MapTypeCfg → NavMesh` 与 `MapTypeCfg → D2NpcZoneCfg → D2NpcBandCfg` 两条主链，以及 `UnionWarAreaCfg → UnionWarBuildingCfg`、`RandomMapUnitCfg → UnionWarBuildingCfg / KingWarBuildingCfg` 的建筑引用。
3. 现有表扩展：逐表给出保留字段、建议新增字段、使用端和填表约束，包含 `RandomMapUnitCfg` 的独立点位关系。
4. 新增表：完整列出 `FortressAdjacencyCfg`、`FogLayerCfg` 的字段结构。
5. 外部依赖：列出联盟科技、任务、成就、排行、多语言和地图工具产物，但不虚构字段。
6. 填表与导表自检：覆盖模板隔离、外键有效性、四邻拓扑、出生区、迷雾时序、建筑类型和三端读取范围。

## 验收标准

- 文档中不再出现 `new_server_map.xlsx` 或已删除逻辑页签作为正式配置。
- 每项新服地图需求都能映射到现有正式表或两张新增表之一。
- 明确 NavMesh 才是地图实际宽高和通行数据来源，`MapSizeCfg` 不越权。
- 明确系统堡垒、龙巢、小祭坛与王座继续复用现有对象配置。
- 明确龙巢、圣坛和王座点位复用 `RandomMapUnitCfg`，并使用新服专用数据集隔离旧服/KVK。
- 新增字段均说明所属正式表、用途、类型、读取端和新旧模板隔离方式。
- 不写入存档字段、协议字段或运行时状态。
