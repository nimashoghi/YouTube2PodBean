#!/bin/bash

mkdir -p /var/vm
fallocate -l 2048m /var/vm/swapfile1
chmod 600 /var/vm/swapfile1
mkswap /var/vm/swapfile1

cat > FILE.txt <<EOF
[Unit]
Description=Turn on swap

[Swap]
What=/var/vm/swapfile1

[Install]
WantedBy=multi-user.target
EOF

systemctl enable --now var-vm-swapfile1.swap
systemctl restart systemd-sysctl
