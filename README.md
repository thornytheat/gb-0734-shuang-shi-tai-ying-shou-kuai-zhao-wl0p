# 双时态应收快照

集团数仓财务工程师可在同一份应收变更文件上回看结账时的账面，再用后续已知材料复核当时的业务日期。来源、有效版本、账龄、迟报凭证、期间桥接和归档都可独立查看。

## 启动与试跑

```bash
docker compose up --build
docker compose exec -T app pytest -q
```

打开 [工作台](http://localhost:18423/) 或 [接口文档](http://localhost:18423/docs)。服务启动时幂等载入 `sample_data/receivable.csv`。首页默认显示样例的 2025 年末至 2026 年 1 月末。业务有效轴和知悉轴都可选刻度，也可在工具条编辑切点。返回「载入样例」可恢复预设。

- 「变更收件」可上传分部的 `sample_data/branch-gb18030.csv` 或查看隔离原值。
- 「期间桥接」可查看总账、五个账龄桶与逐发票变动。
- 「归档快照」保存当前期间，在「快照归档」可选历史记录、重跑和导出一份 JSON 证据。
- 容器的 SQLite 位于命名卷 `workbench`。如需重建并确认可丢弃所有本地归档与导入文件，执行 `docker compose down -v` 后重新启动。

### 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --port 18423
```

## 七个业务入口

| 模块 | API | 主要结论 |
|---|---|---|
| 变更收件 | `GET /api/intake/sample`、`POST /api/intake` | 原值、行号、重复与隔离原因 |
| 有效版本 | `GET /api/versions` | 双轴边界、冲突和替换关系 |
| 双时态截面 | `GET /api/snapshot` | 面额、收款、冲销和余额 |
| 过期应收 | `GET /api/aging` | 五个账龄桶与发票证据 |
| 迟报回补 | `GET /api/backfill` | 固定期初有效日后的事件及余额变化 |
| 期间桥接 | `GET /api/bridge` | 期初、迟报、迁移、本期与期末 |
| 快照归档 | `GET/POST /api/archive` | 批次与摘要、幂等重跑与证据 |

[数据定义](docs/DATA-DICTIONARY.md)说明日期边界、冲突取舍和对账公式。[深度登记](docs/DEPTH.md)列出可重复验证的情形。
