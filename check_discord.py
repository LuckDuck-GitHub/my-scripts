#!/usr/bin/env python3
"""
Скрипт для проверки доступности зарубежных сервисов с VDS в России.
Проверяет: YouTube, Discord, Twitch, GitHub, Google и другие сервисы.
"""

import requests
import socket
import subprocess
import json
import time
import dns.resolver
import concurrent.futures
from datetime import datetime
import sys
import ssl
import urllib.parse

def check_dns_resolution(hostname):
    """Проверка разрешения DNS для домена."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '1.1.1.1']  # Используем публичные DNS
        answers = resolver.resolve(hostname, 'A')
        return [str(rdata) for rdata in answers]
    except Exception as e:
        return None

def check_http_access(url, timeout=10):
    """Проверка HTTP/HTTPS доступа к ресурсу."""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            allow_redirects=True
        )
        return {
            'status': response.status_code,
            'time': response.elapsed.total_seconds(),
            'size': len(response.content),
            'headers': dict(response.headers)
        }
    except requests.exceptions.Timeout:
        return {'error': 'timeout'}
    except requests.exceptions.SSLError:
        return {'error': 'ssl_error'}
    except Exception as e:
        return {'error': str(e)}

def check_tcp_connect(host, port, timeout=5):
    """Проверка TCP подключения."""
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        connect_time = time.time() - start
        return {'success': True, 'time': connect_time}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def measure_ping(host, count=3):
    """Измерение ping до хоста."""
    try:
        if sys.platform == 'win32':
            cmd = ['ping', '-n', str(count), host]
        else:
            cmd = ['ping', '-c', str(count), host]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Парсим результат ping
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'min/avg/max' in line or 'Average' in line:
                    return {'success': True, 'output': line.strip()}
        return {'success': False, 'output': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_youtube_access():
    """Специальная проверка доступности YouTube."""
    endpoints = [
        'https://www.youtube.com',
        'https://www.youtube.com/s/desktop/',
        'https://yt3.ggpht.com',  # YouTube CDN
        'https://googlevideo.com'  # Видео хостинг
    ]
    
    results = {}
    for url in endpoints:
        result = check_http_access(url, timeout=15)
        results[url] = result
        time.sleep(1)  # Задержка между запросами
    
    # Дополнительная проверка YouTube API
    try:
        api_check = requests.get(
            'https://www.youtube.com/youtubei/v1/player',
            timeout=10
        )
        results['youtube_api'] = {
            'status': api_check.status_code,
            'time': api_check.elapsed.total_seconds()
        }
    except Exception as e:
        results['youtube_api'] = {'error': str(e)}
    
    return results

def check_discord_access():
    """Проверка доступности Discord."""
    endpoints = [
        'https://discord.com',
        'https://discordapp.com',
        'https://cdn.discordapp.com',
        'wss://gateway.discord.gg'  # WebSocket для проверки
    ]
    
    results = {}
    for url in endpoints:
        if url.startswith('wss://'):
            result = check_tcp_connect(url.replace('wss://', ''), 443)
        else:
            result = check_http_access(url)
        results[url] = result
        time.sleep(0.5)
    
    return results

def check_cloudflare_cdn():
    """Проверка доступности Cloudflare CDN."""
    test_files = [
        'https://cloudflare.com/cdn-cgi/trace',
        'https://1.1.1.1/cdn-cgi/trace',  # Cloudflare DNS
    ]
    
    results = {}
    for url in test_files:
        result = check_http_access(url)
        results[url] = result
    
    return results

def perform_speed_test():
    """Тест скорости загрузки с различных CDN."""
    test_files = {
        'cloudflare': 'https://speed.cloudflare.com/__down?bytes=1000000',
        'google': 'https://dl.google.com/dl/android/studio/install/3.6.3.0/android-studio-ide-201.7042882-linux.tar.gz',  # Большой файл
        'github': 'https://github.com/git/git/archive/refs/tags/v2.35.1.tar.gz',
        'docker': 'https://download.docker.com/linux/static/stable/x86_64/docker-20.10.9.tgz'
    }
    
    speeds = {}
    for name, url in test_files.items():
        try:
            start = time.time()
            response = requests.get(url, stream=True, timeout=30)
            total_size = 0
            chunk_size = 8192
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                total_size += len(chunk)
                if time.time() - start > 5:  # Скачиваем 5 секунд
                    break
            
            duration = time.time() - start
            if duration > 0:
                speed_mbps = (total_size * 8) / (duration * 1000000)
                speeds[name] = {
                    'speed_mbps': round(speed_mbps, 2),
                    'size_mb': round(total_size / 1024 / 1024, 2),
                    'time_sec': round(duration, 2)
                }
        except Exception as e:
            speeds[name] = {'error': str(e)}
    
    return speeds

def check_vpn_detection():
    """Проверка, не определяется ли VDS как VPN/Proxy."""
    services = [
        'https://ipinfo.io/json',
        'https://ipapi.co/json/',
        'https://checkip.amazonaws.com',
        'https://ifconfig.me/all.json'
    ]
    
    results = {}
    for url in services:
        try:
            response = requests.get(url, timeout=10)
            data = response.json() if 'json' in url else response.text
            results[url] = data
        except Exception as e:
            results[url] = {'error': str(e)}
    
    return results

def check_streaming_services():
    """Проверка доступности стриминговых сервисов."""
    services = {
        'twitch': 'https://www.twitch.tv',
        'netflix': 'https://www.netflix.com',
        'spotify': 'https://www.spotify.com',
        'steam': 'https://store.steampowered.com',
        'telegram': 'https://web.telegram.org',
        'whatsapp': 'https://web.whatsapp.com'
    }
    
    results = {}
    for name, url in services.items():
        result = check_http_access(url, timeout=10)
        results[name] = {
            'url': url,
            'accessible': 'error' not in result and result.get('status', 0) < 400,
            'response_time': result.get('time', 0) if 'error' not in result else None
        }
        time.sleep(1)
    
    return results

def check_geo_restrictions():
    """Проверка географических ограничений."""
    geo_checks = [
        ('YouTube Region', 'https://www.youtube.com/red'),
        ('Netflix API', 'https://www.netflix.com/title/80018499'),
        ('BBC iPlayer', 'https://www.bbc.co.uk/iplayer'),
        ('Hulu', 'https://www.hulu.com'),
    ]
    
    results = {}
    for name, url in geo_checks:
        result = check_http_access(url, timeout=15)
        results[name] = {
            'status': result.get('status') if 'error' not in result else 'error',
            'blocked': result.get('status') in [403, 451] or 'error' in result
        }
    
    return results

def main():
    print("=" * 70)
    print("Проверка доступности зарубежных сервисов с российского VDS")
    print("=" * 70)
    
    all_results = {}
    
    # 1. Проверка DNS
    print("\n1. Проверка DNS разрешения...")
    domains = ['youtube.com', 'discord.com', 'twitch.tv', 'github.com', 'google.com']
    dns_results = {}
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_domain = {executor.submit(check_dns_resolution, domain): domain for domain in domains}
        for future in concurrent.futures.as_completed(future_to_domain):
            domain = future_to_domain[future]
            ips = future.result()
            dns_results[domain] = ips
            status = "✅" if ips else "❌"
            print(f"   {status} {domain}: {ips or 'не разрешен'}")
    
    all_results['dns'] = dns_results
    
    # 2. Проверка YouTube
    print("\n2. Проверка доступности YouTube...")
    youtube_results = check_youtube_access()
    
    accessible_count = sum(1 for r in youtube_results.values() if 'error' not in r)
    print(f"   Доступно: {accessible_count}/{len(youtube_results)} endpoints")
    
    for url, result in youtube_results.items():
        if 'error' not in result:
            status = "✅" if result.get('status', 0) < 400 else "⚠️"
            print(f"   {status} {url}: {result.get('status')} ({result.get('time', 0):.2f} сек)")
        else:
            print(f"   ❌ {url}: {result['error']}")
    
    all_results['youtube'] = youtube_results
    
    # 3. Проверка Discord
    print("\n3. Проверка доступности Discord...")
    discord_results = check_discord_access()
    
    for url, result in discord_results.items():
        if 'error' not in result and 'success' in result:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {url}: {result.get('time', 0):.3f} сек")
        elif 'error' in result:
            print(f"   ❌ {url}: {result['error']}")
        else:
            status = "✅" if result.get('status', 0) < 400 else "⚠️"
            print(f"   {status} {url}: {result.get('status')}")
    
    all_results['discord'] = discord_results
    
    # 4. Проверка стриминговых сервисов
    print("\n4. Проверка стриминговых сервисов...")
    streaming_results = check_streaming_services()
    
    for service, data in streaming_results.items():
        status = "✅" if data['accessible'] else "❌"
        time_str = f" ({data['response_time']:.2f} сек)" if data['response_time'] else ""
        print(f"   {status} {service}: {'Доступен' if data['accessible'] else 'Недоступен'}{time_str}")
    
    all_results['streaming'] = streaming_results
    
    # 5. Тест скорости
    print("\n5. Тест скорости загрузки...")
    speed_results = perform_speed_test()
    
    for service, data in speed_results.items():
        if 'error' not in data:
            print(f"   📊 {service}: {data['speed_mbps']} Мбит/с (за {data['time_sec']} сек)")
        else:
            print(f"   ❌ {service}: ошибка скорости")
    
    all_results['speed'] = speed_results
    
    # 6. Проверка геоблокировок
    print("\n6. Проверка географических ограничений...")
    geo_results = check_geo_restrictions()
    
    for service, data in geo_results.items():
        status = "🔒" if data['blocked'] else "✅"
        print(f"   {status} {service}: {'Заблокировано' if data['blocked'] else 'Доступно'}")
    
    all_results['geo'] = geo_results
    
    # 7. Проверка Cloudflare
    print("\n7. Проверка Cloudflare CDN...")
    cloudflare_results = check_cloudflare_cdn()
    
    for url, result in cloudflare_results.items():
        if 'error' not in result:
            status = "✅" if result.get('status', 0) < 400 else "⚠️"
            print(f"   {status} {url}: {result.get('status')} ({result.get('time', 0):.2f} сек)")
        else:
            print(f"   ❌ {url}: {result['error']}")
    
    all_results['cloudflare'] = cloudflare_results
    
    # 8. Итоговая оценка
    print("\n" + "=" * 70)
    print("ИТОГОВАЯ ОЦЕНКА ДОСТУПНОСТИ:")
    print("=" * 70)
    
    # Анализ результатов YouTube
    youtube_accessible = any('error' not in r and r.get('status', 0) < 400 
                           for r in youtube_results.values())
    
    # Анализ результатов Discord
    discord_accessible = any('error' not in r and ('success' in r and r['success'] or 
                           r.get('status', 0) < 400) for r in discord_results.values())
    
    # Анализ скорости
    avg_speed = None
    if speed_results:
        speeds = [v['speed_mbps'] for v in speed_results.values() if 'error' not in v]
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
    
    print(f"\n📊 YouTube: {'✅ Доступен' if youtube_accessible else '❌ Проблемы с доступом'}")
    print(f"📊 Discord: {'✅ Доступен' if discord_accessible else '❌ Проблемы с доступом'}")
    
    if avg_speed:
        print(f"📊 Средняя скорость: {avg_speed:.2f} Мбит/с")
        if avg_speed < 10:
            print("   ⚠️ Низкая скорость, возможны проблемы со стримингом")
        elif avg_speed > 50:
            print("   ✅ Отличная скорость")
    
    # Рекомендации
    print("\n" + "=" * 70)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 70)
    
    recommendations = []
    
    if not youtube_accessible:
        recommendations.append("YouTube недоступен. Рассмотрите использование VPN/Proxy")
    
    if not discord_accessible:
        recommendations.append("Discord недоступен. Проверьте настройки сети")
    
    if avg_speed and avg_speed < 5:
        recommendations.append("Низкая скорость. Выберите другого провайдера или тариф")
    
    # Проверка наличия блокировок
    if any(data['blocked'] for data in geo_results.values()):
        recommendations.append("Обнаружены геоблокировки. Требуется VPN для доступа")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("✅ Все проверенные сервисы доступны с приемлемой скоростью")
    
    # Сохранение результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"vds_access_check_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Полный отчет сохранен в: {filename}")
    
    # Команды для ручной проверки
    print("\n" + "=" * 70)
    print("КОМАНДЫ ДЛЯ РУЧНОЙ ПРОВЕРКИ:")
    print("=" * 70)
    print("""
# Проверка YouTube стрима:
timeout 30 curl -s -o /dev/null -w "%%{http_code} %%{time_total}" https://r2---sn-8xgp1vo-p5qs.googlevideo.com

# Проверка Discord WebSocket:
timeout 10 curl -i -H "Connection: Upgrade" -H "Upgrade: websocket" https://gateway.discord.gg

# Тест скорости через wget:
wget -O /dev/null --report-speed=bits https://dl.google.com/dl/android/studio/install/3.6.3.0/android-studio-ide-201.7042882-linux.tar.gz

# Проверка TCP соединений:
nc -zv youtube.com 443
nc -zv discord.com 443
    """)

if __name__ == "__main__":
    # Установка таймаута для всего скрипта
    import signal
    
    def timeout_handler(signum, frame):
        print("\n⏰ Скрипт остановлен по таймауту")
        sys.exit(1)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(300)  # 5 минут на выполнение
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Проверка прервана пользователем")
    finally:
        signal.alarm(0)  # Отключить таймер