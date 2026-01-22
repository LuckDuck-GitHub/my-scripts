#!/bin/bash

# Проверка сетевых настроек для российских VDS

echo "=== Проверка сетевых настроек VDS ==="

# 1. Проверка DNS
echo -e "\n1. DNS серверы:"
cat /etc/resolv.conf | grep nameserver

# 2. Проверка маршрутизации до российских ресурсов
echo -e "\n2. Маршрутизация до российских серверов:"
echo "Яндекс:"
traceroute -m 5 yandex.ru 2>/dev/null || echo "traceroute не установлен"

echo -e "\nСбербанк:"
ping -c 2 sberbank.ru 2>/dev/null && echo "Доступен" || echo "Не доступен"

# 3. Проверка времени
echo -e "\n3. Время на сервере:"
date
echo "Временная зона:"
timedatectl | grep "Time zone" 2>/dev/null || echo "Проверьте настройки времени"

# 4. Проверка портов
echo -e "\n4. Проверка необходимых портов:"
ports=(443 80 22)
for port in "${ports[@]}"; do
    timeout 1 bash -c "echo >/dev/tcp/$(hostname -i)/$port" 2>/dev/null && 
    echo "Порт $port: открыт" || echo "Порт $port: закрыт"
done