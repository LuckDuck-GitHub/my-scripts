#!/usr/bin/env python3
"""
Скрипт для проверки VDS на соответствие требованиям для работы с российскими ресурсами.
Проверяет: IP-адрес, ASN, геолокацию, наличие в реестре запрещенных IP.
"""

import requests
import socket
import json
import urllib.request
import ipaddress
import sys

def get_public_ip():
    """Получение публичного IP-адреса VDS."""
    try:
        return requests.get('https://api.ipify.org').text
    except:
        try:
            return requests.get('https://ident.me').text
        except:
            return None

def check_ip_geolocation(ip):
    """Проверка геолокации IP-адреса."""
    try:
        response = requests.get(f'https://ipapi.co/{ip}/json/').json()
        country = response.get('country')
        country_name = response.get('country_name')
        asn = response.get('asn')
        org = response.get('org')
        
        return {
            'country': country,
            'country_name': country_name,
            'asn': asn,
            'org': org,
            'city': response.get('city'),
            'region': response.get('region')
        }
    except:
        return None

def check_russian_asn(asn):
    """Проверка, принадлежит ли ASN российским провайдерам."""
    # Список основных российских ASN (можно дополнить)
    russian_asns = [
        'AS12389', 'AS25532', 'AS200350',  # Ростелеком
        'AS8402',  # Билайн
        'AS31224',  # МГТС
        'AS42610',  # МегаФон
        'AS28917',  # МТС
        'AS41733',  # Тинькофф
        'AS50817',  # VK
        'AS47764',  # Яндекс
        'AS210042',  # Альфа-Банк
    ]
    
    if asn:
        for ru_asn in russian_asns:
            if ru_asn in asn:
                return True
    return False

def check_rdap_info(ip):
    """Получение информации о IP через RDAP."""
    try:
        if ipaddress.ip_address(ip).version == 4:
            url = f'https://rdap.db.ripe.net/ip/{ip}'
        else:
            url = f'https://rdap.db.ripe.net/ip/{ip}'
        
        response = requests.get(url, headers={'Accept': 'application/json'})
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def check_roskomnadzor_blocks(ip):
    """Проверка наличия IP в реестре запрещенных сайтов Роскомнадзора."""
    # Внимание: Это упрощенная проверка. Полный список не публикуется открыто.
    try:
        # Пример проверки через открытые API
        response = requests.get(
            f'https://api.anti-block.org/check/{ip}',
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('blocked', False)
    except:
        pass
    return False

def check_dns_resolution():
    """Проверка разрешения DNS для российских доменов."""
    domains = [
        'alfa-bank.ru',
        'sberbank.ru',
        'yandex.ru',
        'vk.com',
        'gosuslugi.ru',
        'rkn.gov.ru'
    ]
    
    results = {}
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            results[domain] = {'ip': ip, 'resolved': True}
        except:
            results[domain] = {'ip': None, 'resolved': False}
    
    return results

def main():
    print("=" * 60)
    print("Проверка VDS для работы с российскими ресурсами")
    print("=" * 60)
    
    # 1. Получаем публичный IP
    print("\n1. Определение публичного IP-адреса...")
    ip = get_public_ip()
    
    if not ip:
        print("❌ Не удалось определить публичный IP-адрес")
        sys.exit(1)
    
    print(f"   IP-адрес VDS: {ip}")
    
    # 2. Проверяем геолокацию
    print("\n2. Проверка геолокации IP...")
    geo_info = check_ip_geolocation(ip)
    
    if geo_info:
        print(f"   Страна: {geo_info['country_name']} ({geo_info['country']})")
        print(f"   Регион: {geo_info['region']}")
        print(f"   Город: {geo_info['city']}")
        print(f"   Провайдер: {geo_info['org']}")
        print(f"   ASN: {geo_info['asn']}")
        
        # Проверяем, российский ли IP
        is_russian_ip = geo_info['country'] == 'RU'
        if is_russian_ip:
            print("   ✅ IP-адрес российский")
        else:
            print("   ⚠️ IP-адрес не российский. Возможны проблемы с доступом.")
    else:
        print("   ❌ Не удалось получить информацию о геолокации")
        is_russian_ip = False
    
    # 3. Проверяем ASN
    print("\n3. Проверка интернет-провайдера (ASN)...")
    if geo_info and geo_info.get('asn'):
        is_russian_asn = check_russian_asn(geo_info['asn'])
        if is_russian_asn:
            print("   ✅ ASN принадлежит российскому провайдеру")
        else:
            print("   ⚠️ ASN не принадлежит известным российским провайдерам")
    else:
        print("   ❌ Не удалось определить ASN")
    
    # 4. Проверка DNS
    print("\n4. Проверка разрешения российских доменов...")
    dns_results = check_dns_resolution()
    
    resolved_count = sum(1 for domain in dns_results.values() if domain['resolved'])
    print(f"   Успешно разрешено: {resolved_count}/{len(dns_results)} доменов")
    
    for domain, result in dns_results.items():
        status = "✅" if result['resolved'] else "❌"
        print(f"   {status} {domain}: {result['ip'] or 'не разрешен'}")
    
    # 5. Проверка блокировок
    print("\n5. Проверка возможных блокировок...")
    is_blocked = check_roskomnadzor_blocks(ip)
    
    if is_blocked:
        print("   ❌ IP-адрес может быть в реестре блокировок")
    else:
        print("   ✅ IP-адрес не обнаружен в открытых реестрах блокировок")
    
    # 6. Итоговая рекомендация
    print("\n" + "=" * 60)
    print("ИТОГОВАЯ ОЦЕНКА:")
    print("=" * 60)
    
    recommendations = []
    
    if is_russian_ip:
        print("✅ IP-адрес находится в России")
    else:
        print("❌ IP-адрес НЕ в России")
        recommendations.append("Рассмотрите аренду VDS у российского хостинг-провайдера")
    
    if resolved_count >= len(dns_results) * 0.8:
        print("✅ DNS разрешение работает корректно")
    else:
        print("❌ Проблемы с DNS разрешением")
        recommendations.append("Проверьте настройки DNS resolver (используйте 8.8.8.8 или российские DNS)")
    
    if not is_blocked:
        print("✅ IP не заблокирован в открытых реестрах")
    else:
        print("❌ ВНИМАНИЕ: IP может быть заблокирован")
        recommendations.append("Смените IP-адрес или обратитесь к провайдеру")
    
    print(f"\nСтатус для установки образов alfa.rf: {'ПОДХОДИТ' if is_russian_ip and not is_blocked else 'МОГУТ БЫТЬ ПРОБЛЕМЫ'}")
    
    if recommendations:
        print("\nРекомендации:")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    # Дополнительная информация
    print("\n" + "=" * 60)
    print("ДОПОЛНИТЕЛЬНО:")
    print("=" * 60)
    print("1. Для работы с alfa.rf также убедитесь, что:")
    print("   - На VDS установлен российский SSL-сертификат")
    print("   - Используются российские DNS-серверы")
    print("   - Настроено корректное время (MSK)")
    print("\n2. Проверьте доступность напрямую:")
    print(f"   curl -I https://alfa-bank.ru")
    print(f"   ping -c 3 api.alfa-bank.ru")

if __name__ == "__main__":
    main()