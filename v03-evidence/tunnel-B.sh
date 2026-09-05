#!/bin/bash
export AUTOSSH_GATETIME=0
pkill -f "ssh.*-L 908" 2>/dev/null
sleep 1
autossh -M 0 -f -N -L 9081:localhost:8081 \
  -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -p 10245 root@27.64.13.65
autossh -M 0 -f -N -L 9083:localhost:8081 \
  -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -p 58902 root@1.208.108.242
