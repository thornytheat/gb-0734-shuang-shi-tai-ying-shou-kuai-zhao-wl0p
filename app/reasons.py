REASONS = {
    "ROW_WIDTH": "列数与表头不符",
    "INVALID_ID": "单据、客户或事件编号无效",
    "UNKNOWN_KIND": "未知变更类型",
    "INVALID_DATE": "业务日期无效",
    "INVALID_TIMESTAMP": "知悉时间无效或缺少时区",
    "AMOUNT_MISSING": "金额为空或是空值标记",
    "INVALID_AMOUNT": "金额格式、精度或范围无效",
    "INVALID_INTERVAL": "有效区间结束日须晚于开始日",
    "UNEXPECTED_FIELDS": "变更类型与填写字段不符",
    "DUPLICATE_EVENT": "同一事件的相同副本",
    "EVENT_ID_CONFLICT": "同一事件编号出现不同内容",
    "VERSION_PARENT": "被替换版本在此知悉时点不可用",
    "VERSION_SCOPE": "修订的发票、客户或区间不匹配",
    "VERSION_FORK": "同一时刻有多个版本替换同一父版",
    "INTERVAL_OVERLAP": "有效区间存在交叠",
    "CUSTOMER_CONFLICT": "同一发票编号关联多个客户",
    "TARGET_PENDING": "引用版本尚未可见",
    "TARGET_INVALID": "引用事件无法作为入账版本",
    "TARGET_SCOPE": "引用版本与发票、客户或有效日不匹配",
    "NO_ACTIVE_VERSION": "变更有效日无可用版本",
    "EXCEEDS_BALANCE": "本笔变更超过可冲减余额",
}


def reason(code: str):
    return {"code": code, "message": REASONS[code]}
