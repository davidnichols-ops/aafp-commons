#!/bin/bash
export AUTOSSH_GATETIME=0
pkill -f "ssh.*-L 908" 2>/dev/null
sleep 1
autossh -M 0 -f -N -L 9082:localhost:8081 \
  -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -p 19626 root@84.18.245.171
autossh -M 0 -f -N -L 9083:localhost:8081 \
  -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -p 58902 root@1.208.108.242
