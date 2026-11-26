#!/usr/bin/env bash
# v4b final evaluation, run 1 then run 2 (M1-G only). Code = commit b08d33c (system 610a97c). Approved 2026-11-27.
# Budget guard: before every step the whole-repo ledger total is recomputed; the step's cap for its ledger is
# (what that ledger already holds) + min(planned new spend, 5.00 - total - 0.01). If the room is below the step's
# expected spend the script stops (exit 3) and nothing else runs.
set -u
cd /c/agentic-wallet-security/cdv-wallet
export PYTHONIOENCODING=utf-8
X=results/extdata_20261126
D=C:/ct/external/carttrace_cdv_evaluation_v4b
LOG=results/final_v4b/run_final.log
PY=.venv/Scripts/python.exe

total() {
  python -c "import json,glob; print(round(sum(json.loads(l).get('cost_usd',0) for f in glob.glob('results/**/ledger*.jsonl',recursive=True) for l in open(f,encoding='utf-8') if l.strip()),6))"
}
held() {
  python -c "import json,os,sys; f=sys.argv[1]; print(round(sum(json.loads(l).get('cost_usd',0) for l in open(f,encoding='utf-8') if l.strip()),6) if os.path.exists(f) else 0.0)" "$1"
}
cap() {  # cap <ledger> <planned new spend> <expected new spend>  -> cumulative cap for that ledger, or stop
  local t room h
  t=$(total)
  room=$(python -c "print(round(5.0-$t-0.01,6))")
  h=$(held "$1")
  if python -c "import sys; sys.exit(0 if $room >= $3 else 1)"; then
    python -c "print(round($h+min($2,$room),6))"
  else
    echo "STOP budget: total $t, room $room < expected $3 for $1" >> "$LOG"
    return 3
  fi
}
step() { echo "$(date +%H:%M:%S) start $1 (total \$$(total))" >> "$LOG"; }
fin() {
  echo "$(date +%H:%M:%S) end $1 rc=$2 (total \$$(total))" >> "$LOG"
  if [ "$2" != 0 ]; then echo "STOP: $1 failed" >> "$LOG"; exit 4; fi
}

step "E-A run1 condition A"
EB=$(cap $X/ledger_v4b.jsonl 0.75 0.61) || exit 3
MB=$(cap $X/ledger_m1g_v4b.jsonl 0.35 0.26) || exit 3
$PY eval/extdata/run_ext.py --data $D --name v4b --split eval --with-matched --m1g --m1g-memo --tag m1g --budget $EB --m1g-budget $MB > results/final_v4b/E-A.log 2>&1
fin E-A $?

step "E-B run1 condition B"
EB=$(cap $X/ledger_v4b.jsonl 0.15 0.10) || exit 3
MB=$(cap $X/ledger_m1g_v4b.jsonl 0.08 0.03) || exit 3
$PY eval/extdata/run_ext.py --data $D --name v4b --split eval --with-matched --m1g --m1g-memo --tag m1g --seller-to-extractor --budget $EB --m1g-budget $MB > results/final_v4b/E-B.log 2>&1
fin E-B $?

step "E-P PRECHECK A"
PB=$(cap $X/ledger_baselines_v4b.jsonl 0.35 0.27) || exit 3
$PY eval/extdata/run_baselines.py --data $D --name v4b --split eval --precheck-only --budget $PB > results/final_v4b/E-P.log 2>&1
fin E-P $?

step "E-PB PRECHECK B"
T=$(total)
NEW=$(python -c "print(round(min(0.15, 5.0-$T-0.01),6))")
if ! python -c "import sys; sys.exit(0 if $NEW >= 0.12 else 1)"; then echo "STOP budget before E-PB" >> "$LOG"; exit 3; fi
$PY eval/extdata/run_baselines.py --data $D --name v4b --split eval --precheck-only --seller-in-input --cap-new-spend $NEW > results/final_v4b/E-PB.log 2>&1
fin E-PB $?

step "E-I M1-G basis judgement (gold candidates) x2"
T=$(total)
R=$(python -c "print(round(min(0.06, (5.0-$T-0.01)/2),6))")
if ! python -c "import sys; sys.exit(0 if $R >= 0.045 else 1)"; then echo "STOP budget before E-I" >> "$LOG"; exit 3; fi
$PY eval/v4check/inject_m1g.py --data $D --name v4b --split eval --prompt-version v2 --budget $R > results/final_v4b/E-I.log 2>&1
fin E-I $?

step "R2 run2 M1-G only (condition A, run-1 extraction, empty M1-G ledger)"
EB=$(cap $X/ledger_v4b.jsonl 0.01 0.0) || exit 3
MB=$(cap $X/ledger_m1g_v4b_run2.jsonl 0.32 0.26) || exit 3
$PY eval/extdata/run_ext.py --data $D --name v4b --split eval --with-matched --m1g --m1g-memo --m1g-ledger-tag run2 --tag m1g_run2 --budget $EB --m1g-budget $MB > results/final_v4b/R2.log 2>&1
fin R2 $?

echo "$(date +%H:%M:%S) v4b done (total \$$(total))" >> "$LOG"
