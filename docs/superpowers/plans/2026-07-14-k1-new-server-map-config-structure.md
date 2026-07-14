# K1 New Server Map Config Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the K1 new-server world-map configuration derivative document so it is grounded in current formal K1 configuration tables and introduces only `FortressAdjacencyCfg` and `FogLayerCfg`.

**Architecture:** The document is organized by the existing configuration dependency chain: scene and navigation, region and refresh, strategic grid and buildings, then the two necessary new relation tables. Logical placeholder workbooks and sheets are removed, while runtime state and protocol details remain outside the derivative document.

**Tech Stack:** Markdown, K1 XCfg/Excel configuration conventions, Git text validation.

## Global Constraints

- Existing formal K1 tables are reused or extended before any new table is proposed.
- New tables are limited to `FortressAdjacencyCfg` and `FogLayerCfg`.
- `NavMesh / TileMesh / GlobalObstacles` remain the authority for physical map dimensions, navigation and blocking.
- Runtime ownership, occupation progress, ceasefire timestamps, persistence and protocol fields are excluded.
- New-server, old-server and KVK data must be isolated by scene type or map template.
- Do not modify the main feature specification in this task.

---

### Task 1: Rewrite the configuration derivative document

**Files:**
- Modify: `output/K1新服大地图重构功能策划案-配置表结构.md`
- Reference: `docs/superpowers/specs/2026-07-14-k1-new-server-map-config-structure-design.md`

**Interfaces:**
- Consumes: the approved design and the existing K1 configuration names confirmed in client, server and dataconfig repositories.
- Produces: one reviewable Markdown derivative document whose table names map to formal K1 configuration assets.

- [ ] **Step 1: Replace the configuration overview**

  Replace `new_server_map.xlsx` and its logical sheet inventory with four categories: reused formal tables, extended formal tables, new formal tables, and map-tool outputs. State the owning workbook, exported bean, purpose and reading side for each entry.

- [ ] **Step 2: Document the dependency chains**

  Add the exact relationships:

  ```text
  SceneType -> MapTypeCfg -> NavMeshId -> NavMesh / TileMesh / GlobalObstacles
  SceneType -> MapTypeCfg -> NpcRefreshId -> D2NpcZoneCfg -> D2NpcBandCfg
  UnionWarAreaCfg -> UnionWarBuildingCfg / KingWarBuildingCfg
  UnionWarAreaCfg.ZoneID -> D2NpcZoneCfg.ID -> FogLayerCfg.ZoneIDs
  ```

- [ ] **Step 3: Define extensions to existing formal tables**

  For `MapTypeCfg`, `MapSizeCfg`, `RandomMapUnitCfg`, `D2NpcZoneCfg`, `UnionWarAreaCfg`, `UnionWarBuildingCfg`, `KingWarBuildingCfg` and their property tables, list retained responsibilities, proposed new fields, field types, reading side and template-isolation constraints. Keep `UnionTerritoryCfg` as a reused dependency whose construction entry is disabled for the new-server template.

- [ ] **Step 4: Define the two new tables**

  Add complete field tables for:

  ```text
  FortressAdjacencyCfg:
    ID, MapType, AreaID, AdjacentAreaID, Direction, IsAttackPath

  FogLayerCfg:
    ID, MapType, Layer, ZoneIDs, UnlockOpenDay, UnlockTime,
    ShowObjectModel, HideObjectData, BlockObjectClick, BlockMarch
  ```

  Specify four-neighbor symmetry, same-template validation, unique edges, zone ownership and unlock-order checks.

- [ ] **Step 5: Restore external dependencies to their actual scope**

  Describe alliance technology, task/achievement/ranking configuration, localization and map-tool outputs as external dependencies. Do not invent formal workbook or bean names when they were not confirmed from the repositories.

- [ ] **Step 6: Replace the fill-in checklist**

  Add checks for scene isolation, foreign-key validity, four-neighbor topology, birth-zone coverage, fog chronology, object type reuse, client/server export sides and the absence of legacy obelisk targets in new-server deliveries.

### Task 2: Verify document consistency

**Files:**
- Verify: `output/K1新服大地图重构功能策划案-配置表结构.md`

**Interfaces:**
- Consumes: the rewritten derivative document from Task 1.
- Produces: evidence that removed logical tables are not presented as formal tables and all approved design requirements are represented.

- [ ] **Step 1: Scan for forbidden formal-table claims and placeholders**

  Run:

  ```powershell
  rg -n 'new_server_map\.xlsx|^## `?(MapBasic|MapRegion|FortressGrid|InitialSharedFortress|DragonNestPoint|AltarPoint|ThronePoint|SpawnRegion|FortressOccupyRule|AllianceTechBranch)`?|TB[D]|TO[D]O|待确[认]' 'output/K1新服大地图重构功能策划案-配置表结构.md'
  ```

  Expected: no matches.

- [ ] **Step 2: Confirm required formal tables and dependency terms**

  Run:

  ```powershell
  rg -n 'MapTypeCfg|MapSizeCfg|RandomMapUnitCfg|D2NpcZoneCfg|D2NpcBandCfg|UnionWarAreaCfg|UnionTerritoryCfg|UnionWarBuildingCfg|KingWarBuildingCfg|FortressAdjacencyCfg|FogLayerCfg|NavMesh|TileMesh|GlobalObstacles' 'output/K1新服大地图重构功能策划案-配置表结构.md'
  ```

  Expected: every required term appears in the intended overview or field section.

- [ ] **Step 3: Run Markdown and Git whitespace validation**

  Run:

  ```powershell
  git diff --check
  git diff -- 'output/K1新服大地图重构功能策划案-配置表结构.md'
  ```

  Expected: `git diff --check` exits 0 and the diff is limited to the derivative document.

- [ ] **Step 4: Commit the completed document update**

  Run:

  ```powershell
  git add -- 'output/K1新服大地图重构功能策划案-配置表结构.md' 'docs/superpowers/plans/2026-07-14-k1-new-server-map-config-structure.md'
  git commit -m '更新新服大地图配置表结构'
  ```

  Expected: one commit containing the implementation plan and revised derivative document.
