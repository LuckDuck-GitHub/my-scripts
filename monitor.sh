#!/bin/bash

# Скрипт мониторинга доступности сервисов
LOG_FILE="service_monitor_$(date +%Y%m%d).log"

# Список сервисов для мониторинга
SERVICES=(
    "youtube.com"
    "discord.com"
    "twitch.tv"
    "github.com"
    "google.com"
    "api.telegram.org"
)

echo "=== Мониторинг доступности сервисов ===" | tee -a $LOG_FILE
echo "Запущено: $(date)" | tee -a $LOG_FILE
echo "=======================================" | tee -a $LOG_FILE

while true; do
    echo "" | tee -a $LOG_FILE
    echo "[$(date +%H:%M:%S)] Проверка..." | tee -a $LOG_FILE
    
    for service in "${SERVICES[@]}"; do
        # Проверка через ping
        if ping -c 2 -W 1 "$service" > /dev/null 2>&1; then
            ping_status="✅"
        else
            ping_status="❌"
        fi
        
        # Проверка HTTP
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$service")
        if [[ $http_code -eq 200 ]] || [[ $http_code -eq 301 ]] || [[ $http_code -eq 302 ]]; then
            http_status="✅"
        else
            http_status="❌"
        fi
        
        # Измерение времени ответа
        response_time=$(curl -s -o /dev/null -w "%{time_total}" --max-time 5 "https://$service")
        
        echo "  $ping_status$http_status $service: HTTP $http_code, время: ${response_time}s" | tee -a $LOG_FILE
    done
    
    # Проверка скорости каждые 10 минут
    if [[ $(( $(date +%M) % 10 )) -eq 0 ]]; then
        echo "  📊 Тест скорости..." | tee -a $LOG_FILE
        speedtest-cli --simple | tee -a $LOG_FILE 2>/dev/null || \
        echo "    speedtest-cli не установлен" | tee -a $LOG_FILE
    fi
    
    sleep 300  # Проверка каждые 5 минут
done