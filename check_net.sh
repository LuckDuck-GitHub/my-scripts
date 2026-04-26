#!/bin/bash

LOG_FILE="network_check_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== СБОР ДАННЫХ О СЕТИ ==="
echo "Время проверки: $(date)"
echo "Хост: $(hostname)"
echo "Ядро: $(uname -a)"
echo "Аптайм: $(uptime)"
echo

echo "=== СЕТЕВЫЕ ИНТЕРФЕЙСЫ ==="
ip addr show || ifconfig -a
echo

echo "=== ТАБЛИЦА МАРШРУТИЗАЦИИ ==="
ip route show || route -n
echo

# Шлюз по умолчанию
GW=$(ip route | grep default | awk '{print $3}')
echo "=== ШЛЮЗ ПО УМОЛЧАНИЮ: $GW ==="
ping -c 4 -W 2 "$GW" && echo "Шлюз отвечает" || echo "Шлюз НЕ отвечает"
echo

echo "=== ПРОВЕРКА ДОСТУПНОСТИ ВНЕШНЕГО IP (8.8.8.8) ==="
ping -c 4 -W 2 8.8.8.8
echo

echo "=== ПРОВЕРКА ДОСТУПНОСТИ ХОСТА ПО ИМЕНИ (google.com) ==="
ping -c 4 -W 2 google.com
echo

echo "=== ПРОВЕРКА DNS (системный резолвер) ==="
nslookup google.com || dig google.com || host google.com
echo

echo "=== ПРОВЕРКА DNS через внешний сервер 8.8.8.8 ==="
nslookup google.com 8.8.8.8 || dig @8.8.8.8 google.com
echo

echo "=== ПРОВЕРКА ПОРТОВ (curl) ==="
curl -s --connect-timeout 5 -I http://1.1.1.1:80 && echo "Порт 80 (HTTP) на 1.1.1.1 открыт" || echo "Порт 80 НЕ ДОСТУПЕН"
curl -s --connect-timeout 5 -I https://8.8.8.8:443 && echo "Порт 443 (HTTPS) на 8.8.8.8 открыт" || echo "Порт 443 НЕ ДОСТУПЕН"
echo

echo "=== ТРАССИРОВКА ДО 8.8.8.8 ==="
if command -v traceroute &> /dev/null; then
    traceroute -n 8.8.8.8
elif command -v tracepath &> /dev/null; then
    tracepath 8.8.8.8
else
    echo "traceroute/tracepath не установлены, пропускаем"
fi
echo

echo "=== ПРОВЕРКА ПОТЕРЬ ПАКЕТОВ (20 пингов до 8.8.8.8) ==="
ping -c 20 8.8.8.8 | tail -5
echo

echo "=== АКТИВНЫЕ СЕТЕВЫЕ СОЕДИНЕНИЯ ==="
ss -tunap || netstat -tunap
echo

echo "=== ARP-ТАБЛИЦА ==="
ip neigh show || arp -n
echo

echo "=== ЛОГИ ЯДРА (ошибки сети) ==="
dmesg | grep -i -E "eth|net|error|fail" | tail -20
echo

echo "=== MTU ПРОВЕРКА ==="
ping -M do -s 1472 -c 1 8.8.8.8 && echo "MTU >= 1500 (норма)" || echo "Возможны проблемы с MTU (фрагментация заблокирована)"
echo

echo "=== СБОР ЗАВЕРШЁН ==="
echo "Лог сохранён в: $LOG_FILE"