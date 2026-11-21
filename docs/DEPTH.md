# 深度登记 双时态应收快照

- 规模为中型。集团数仓财务工程师需要复盘原结账与后续补报差异。
- 核心规则为独立裁切业务有效日和知悉截止，再用三截面分解迟报、账龄迁移与本期余额差异。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 变更收件 | 导入变更 CSV 并查看隔离原值 | `POST /api/intake` | `app/modules/m1_intake/reader.py` `app/modules/m1_intake/contract.py` | `tests/test_intake.py` |
| M2 有效版本 | 指定切点复核衔接、修订和交叠 | `GET /api/versions` | `app/modules/m2_versions/rules.py` `app/modules/m2_versions/book.py` | `tests/test_versions.py` |
| M3 双时态截面 | 取应收余额并追踪冲减凭证 | `GET /api/snapshot` | `app/modules/m3_snapshot/service.py` `app/modules/m3_snapshot/movements.py` | `tests/test_snapshot.py` |
| M4 过期应收 | 检查分桶、逾期天数及结清 | `GET /api/aging` | `app/modules/m4_aging/buckets.py` `app/modules/m4_aging/service.py` | `tests/test_aging.py` |
| M5 迟报回补 | 固定期初有效日对比两个知悉截面 | `GET /api/backfill` | `app/modules/m5_backfill/service.py` `app/modules/m5_backfill/changes.py` | `tests/test_backfill.py` |
| M6 期间桥接 | 勾稽总金额和每桶迁移 | `GET /api/bridge` | `app/modules/m6_bridge/ledger.py` `app/modules/m6_bridge/bucket_flow.py` | `tests/test_bridge.py` |
| M7 快照归档 | 保存、重算和导出证据 | `POST /api/archive` | `app/modules/m7_archive/service.py` `app/modules/m7_archive/export.py` | `tests/test_archive.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | 分部 GB18030 | 中文备注乱码 | UTF-8 优先，失败回退 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_gb18030_actual_sample` |
| TRAP-02 | 主样例包含 BOM | 首列查找失败 | 解码消除 BOM | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_bom_preserves_first_column` |
| TRAP-03 | A-V1 备注含换行 | 错切记录和行号 | CSV 逻辑记录与物理起点 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_multiline_preserves_source_positions` |
| TRAP-04 | 重复表头 | 假数据送入规则 | 单计重复表头 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_source_counts_conserve` |
| TRAP-05 | BAD-WIDTH 短行 | 字段错配 | 保留列数组并隔离 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_bad_width_isolated_with_source` |
| TRAP-06 | A-V1 全角千分位 | 金额无法解析 | 规范化后转分 | `app/modules/m1_intake/contract.py` | `tests/test_intake.py::test_money_normalization_and_blank_isolation` |
| TRAP-07 | J-BAD 金额为 N/A | 当零入账 | 标为缺失并隔离 | `app/modules/m1_intake/contract.py` | `tests/test_intake.py::test_money_normalization_and_blank_isolation` |
| TRAP-08 | 00017 与 17 | 客户串号 | 原样保留并核验同户 | `app/modules/m1_intake/contract.py` | `tests/test_versions.py::test_customer_identifiers_stay_distinct_and_version_cannot_switch` |
| TRAP-10 | 分位金额汇总 | 二进制小数误差 | Decimal 转整数分 | `app/modules/m1_intake/contract.py` | `tests/test_snapshot.py::test_cent_sums_no_binary_float_error` |
| TRAP-11 | I-V1 同刻不同偏移 | 同一事件重复记账 | UTC 归一再去重 | `app/clock.py` | `tests/test_intake.py::test_duplicate_comparison_uses_utc` |
| TRAP-13 | B-REV 先于原票获知 | 丢弃冲销 | 暂挂，后续切点回补 | `app/modules/m3_snapshot/movements.py` | `tests/test_snapshot.py::test_reversal_arrives_before_invoice` |
| TRAP-14 | Z-CON 同刻冲突 | 最后一行覆盖 | 两条都保留在隔离区 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_conflicting_same_key_isolated_together` |
| TRAP-16 | 测试构造断引号 | 接收半条记录 | 拒绝整份并给起始行 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_truncated_quote_fails_without_storing_source` |
| TRAP-18 | 测试构造三种空文件 | 建立无效来源 | 三种原因独立返回 | `app/modules/m1_intake/reader.py` | `tests/test_intake.py::test_zero_and_blanks_and_header_only_have_distinct_errors` |
| TRAP-19 | I-V2A 与 I-V2B 同知悉时刻 | 随读取顺序覆盖 | 同父冲突一起隔离 | `app/modules/m2_versions/rules.py` | `tests/test_versions.py::test_same_time_fork_is_order_independent` |
| TRAP-23 | D-V1 与 D-V2 相邻 | 终日重复选中 | 有效区间右开 | `app/modules/m2_versions/book.py` | `tests/test_versions.py::test_adjacent_intervals_exclusive_end` |
| TRAP-25 | C-OV 与采信版交叠 | 随排序取错发票金额 | 保留早知悉有效版并披露交叠 | `app/modules/m2_versions/rules.py` | `tests/test_versions.py::test_overlap_reject_keeps_prior_version` |
| TRAP-26 | 测试追加陈旧的 A 修订 | 用旧父版覆盖当前版 | 校验父版可用性 | `app/modules/m2_versions/rules.py` | `tests/test_versions.py::test_stale_parent_cannot_overwrite_new_revision` |

## 对账断言

样例收件 43 条。期初 313180 分，加净入账 145000 分，减净收款 90115 分和净冲销 28000 分，得期末 340065 分。五个账龄桶各自差额和迁移净额均为零。
