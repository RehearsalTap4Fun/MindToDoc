# 可验证样例

`small-requirement.md` 是小型单文档的格式与分支覆盖基线：确认成功、校验失败、取消、关闭均有落点，正文没有重复完整规则。它不绑定游戏项目，不作为待实现需求。

运行 `python scripts/check_doc_quality.py tests/fixtures/small-requirement.md` 检查静态格式。转换与失效输入由 `tests/test_document_sync.py`、`tests/test_table_plan.py`、`tests/test_doc_quality.py`、`tests/test_delivery.py` 验证，运行 `python -m pytest`。

历史案例保留在 `examples/`，不要把历史审核“通过”当成当前版本重新验证的结果。
