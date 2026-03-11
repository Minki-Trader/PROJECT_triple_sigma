# STEP21 Control Trade Artifact

Included files:
- `README.md`
- `manifest.json`
- `trade_log.csv`
- `exec_state.ini`
- `broker_audit.csv` when enabled
- `tester_log_tail.txt`
- `bar_log_YYYYMMDD.csv` files emitted by the run

Source run:
- preset: `C:\Users\awdse\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\PROJECT_triple_sigma\_coord\tester\step21\step21_tester_control_trade.ini`
- summary: `_coord/logs/smoke/step21_control_trade_summary.md`
- validation class: `control-regression`
- trigger source: `feature-off regression gate`
- synthetic: `false`
- baseline compare: `_coord/artifacts/step20_control_trade`
