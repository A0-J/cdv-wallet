#!/usr/bin/env bash
# v4b analyses with the scripts fixed in b08d33c / 4b8fc93 (no model calls). Outputs go to new files only.
set -u
cd /c/agentic-wallet-security/cdv-wallet
export PYTHONIOENCODING=utf-8
PY=.venv/Scripts/python.exe
D=C:/ct/external/carttrace_cdv_evaluation_v4b
O=results/final_v4b
A=$O/analysis.log
run() { echo "$(date +%H:%M:%S) $1" >> $A; shift; "$@" >> $A 2>&1; echo "  rc=$?" >> $A; }
run "fault injection (E-I run 1 decisions)" $PY eval/v4check/contamination.py v4b --data $D --name v4b --split eval --m1g-rows results/m1g_20261126/prompt_v2/v4b_eval/rows_dev.jsonl --out $O/contamination
run "primary F1" $PY eval/prereg/run_primary.py F1 --data $D --name v4b --split eval --tag m1g --ctag v4b --cdir $O/contamination --label "최종 평가(독립), v4b eval 1회차" --out $O/primary
run "analyze_v4" $PY eval/extdata/analyze_v4.py m1g --name v4b --split eval --data $D
run "av2plus" $PY eval/review/av2plus.py m1g --data $D --name v4b --split eval
run "tradeoff" $PY eval/review/tradeoff.py m1g --data $D --name v4b --split eval
run "report_by_type" $PY eval/final/report_by_type.py --data $D --name v4b --split eval --tag m1g
run "m1_metrics eval" $PY eval/final/m1_metrics.py --data $D --split eval --train-data C:/ct/external/carttrace_cdv_evaluation_v4 --rows results/m1g_20261126/prompt_v2/v4b_eval/rows_dev.jsonl --out $O/m1_metrics
run "selective_clauses" $PY eval/review/selective_clauses.py m1g --data $D --name v4b --split eval --m1g-ledger v4b
run "B3-A A" $PY eval/aux_arms/run_b3a.py --data $D --name v4b --split eval --tag m1g --m1g-ledger v4b --cond A
run "B3-A B" $PY eval/aux_arms/run_b3a.py --data $D --name v4b --split eval --tag m1g --m1g-ledger v4b --cond B
echo "$(date +%H:%M:%S) analysis done" >> $A
