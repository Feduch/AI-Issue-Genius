#!/bin/bash

while read MESSAGE; do
    # Пропускаем MARK сообщения
    if echo "$MESSAGE" | grep -q "-- MARK --"; then
        continue
    fi

    # Извлекаем данные из сообщения nginx error log
    TIMESTAMP=$(echo "$MESSAGE" | grep -oE '[A-Z][a-z]{2} [0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' | head -1)
    PID=$(echo "$MESSAGE" | grep -oE '\[[0-9]+\]#[0-9]+:' | grep -oE '[0-9]+' | head -1)
    CLIENT=$(echo "$MESSAGE" | grep -o 'client: [^,]*' | cut -d' ' -f2)
    SERVER=$(echo "$MESSAGE" | grep -o 'server: [^,]*' | cut -d' ' -f2)
    REQUEST=$(echo "$MESSAGE" | grep -o 'request: "[^"]*"' | cut -d'"' -f2)
    UPSTREAM=$(echo "$MESSAGE" | grep -o 'upstream: "[^"]*"' | cut -d'"' -f2)
    HOST=$(echo "$MESSAGE" | grep -o 'host: "[^"]*"' | cut -d'"' -f2)

    # Основное сообщение об ошибке
    MESSAGE_TEXT=$(echo "$MESSAGE" | sed 's/.*\*[0-9]* //' | sed 's/, client:.*//')

    # Определяем уровень ошибки
    if echo "$MESSAGE" | grep -q "\[error\]"; then
        LEVEL="error"
    elif echo "$MESSAGE" | grep -q "\[crit\]"; then
        LEVEL="critical"
    else
        LEVEL="unknown"
    fi

    # Формируем JSON
    JSON_DATA=$(jq -n \
      --arg service "nginx" \
      --arg timestamp "$(date -d "$TIMESTAMP" +%s 2>/dev/null || date +%s)" \
      --arg level "$LEVEL" \
      --arg pid "$PID" \
      --arg client "$CLIENT" \
      --arg server "$SERVER" \
      --arg request "$REQUEST" \
      --arg upstream "$UPSTREAM" \
      --arg host "$HOST" \
      --arg message "$MESSAGE_TEXT" \
      '{
        service: $service,
        timestamp: $timestamp,
        level: $level,
        pid: $pid,
        client: $client,
        server: $server,
        request: $request,
        upstream: $upstream,
        host: $host,
        message: $message
      }')

    # Отправляем на сервер
    curl --insecure -s -H 'Content-Type: application/json' -X POST -d "$JSON_DATA" "https://kuber.ninja360.ru/api/logs" > /dev/null 2>&1

done
