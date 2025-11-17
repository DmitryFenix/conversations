#!/bin/bash
set -e

echo "Исправляем Docker на Kali..."

# 1. iptables legacy
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy 2>/dev/null || true
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy 2>/dev/null || true

# 2. Отключаем nftables
sudo systemctl stop nftables 2>/dev/null || true
sudo systemctl disable nftables 2>/dev/null || true

# 3. Запускаем containerd
sudo systemctl start containerd 2>/dev/null || true
sudo systemctl enable containerd 2>/dev/null || true

# 4. Очистка (опционально)
# sudo rm -rf /var/lib/docker /var/lib/containerd

# 5. Перезапуск
sudo systemctl restart docker

echo "Готово! Проверяем:"
docker run --rm hello-world
