#!/bin/bash
pkill -9 -f commons_node.py 2>/dev/null
sleep 2
cd /root/aafp-commons
.venv/bin/python3 -u commons_node.py --role publication --root /root/commons-data --peers http://localhost:9082,http://localhost:9083 --port 8081 > /root/node.log 2>&1 &
echo $! > /root/daemon.pid
