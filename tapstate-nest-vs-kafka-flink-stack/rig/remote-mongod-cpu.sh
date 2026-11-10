#!/bin/sh
# remote-mongod-cpu.sh OUTFILE DONEFILE: every 5 s, CPU % of the remote mongod (100 = one vCPU), read from
# /proc over SSH; read-only on the remote host. Stops when DONEFILE appears. Uses EXT_SSH and SSH_KEY.
OUT=$1; DONE=$2
ssh ${SSH_KEY:+-i $SSH_KEY} -o BatchMode=yes "$EXT_SSH" "P=\$(pgrep -x mongod); T=\$(getconf CLK_TCK); prev=\$(awk '{print \$14+\$15}' /proc/\$P/stat); pt=\$(date +%s.%N)
  while :; do sleep 5; cur=\$(awk '{print \$14+\$15}' /proc/\$P/stat); ct=\$(date +%s.%N)
    awk -v a=\$prev -v b=\$cur -v t0=\$pt -v t1=\$ct -v hz=\$T 'BEGIN{printf \"%s %.1f\\n\", t1, 100*(b-a)/hz/(t1-t0)}' || exit 0; prev=\$cur; pt=\$ct; done" > "$OUT" &
SP=$!; while [ ! -f "$DONE" ]; do sleep 5; done; kill $SP 2>/dev/null; true
