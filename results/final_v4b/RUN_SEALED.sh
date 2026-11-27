#!/usr/bin/env bash
# Sealed sample (F2), runs 1 and 2, full independent (own folders and ledgers). Code: commit 4b8fc93 (system 610a97c).
# Starts only after the v4b script logged "v4b done". Same budget guard as RUN_COMMANDS.sh (whole-repo ledger total <= $5).
set -u
cd /c/agentic-wallet-security/cdv-wallet
export PYTHONIOENCODING=utf-8
LOG=results/final_v4b/run_final.log
PY=.venv/Scripts/python.exe
S=results/sealed_eval_610a97c

until grep -q "v4b done\|STOP" "$LOG"; do sleep 30; done
if grep -q "STOP" "$LOG"; then echo "$(date +%H:%M:%S) sealed not started: v4b stopped" >> "$LOG"; exit 3; fi

total() {
  python -c "import json,glob; print(round(sum(json.loads(l).get('cost_usd',0) for f in glob.glob('results/**/ledger*.jsonl',recursive=True) for l in open(f,encoding='utf-8') if l.strip()),6))"
}
room_for() {  # room_for <planned> <expected> -> min(planned, room) or stop
  local t room
  t=$(total)
  room=$(python -c "print(round(5.0-$t-0.01,6))")
  if python -c "import sys; sys.exit(0 if $room >= $2 else 1)"; then
    python -c "print(round(min($1,$room),6))"
  else
    echo "STOP budget: total $t, room $room < expected $2" >> "$LOG"
    return 3
  fi
}
fin() {
  echo "$(date +%H:%M:%S) end $1 rc=$2 (total \$$(total))" >> "$LOG"
  if [ "$2" != 0 ]; then echo "STOP: $1 failed" >> "$LOG"; exit 4; fi
}

for k in 1 2; do
  echo "$(date +%H:%M:%S) start sealed run $k extract (total \$$(total))" >> "$LOG"
  B=$(room_for 0.35 0.26) || exit 3
  $PY eval/seal/run_sealed.py --run $k --step extract --budget $B > results/final_v4b/S${k}-extract.log 2>&1
  fin "sealed run $k extract" $?
  echo "$(date +%H:%M:%S) start sealed run $k eval (total \$$(total))" >> "$LOG"
  B=$(room_for 0.10 0.07) || exit 3
  $PY eval/seal/run_sealed.py --run $k --step eval --m1g-budget $B > results/final_v4b/S${k}-eval.log 2>&1
  fin "sealed run $k eval" $?
  echo "$(date +%H:%M:%S) start sealed run $k precheck (total \$$(total))" >> "$LOG"
  B=$(room_for 0.075 0.04) || exit 3
  $PY eval/seal/run_sealed.py --run $k --step precheck --precheck-budget $B > results/final_v4b/S${k}-precheck.log 2>&1
  fin "sealed run $k precheck" $?
done
$PY eval/seal/run_sealed.py --step agree > results/final_v4b/S-agree.log 2>&1
fin "sealed agree" $?
echo "$(date +%H:%M:%S) sealed done (total \$$(total))" >> "$LOG"
