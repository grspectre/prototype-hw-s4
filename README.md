## Запуск тестирования в докере

```
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test
```

## Удаление контейнеров

```
docker-compose -f docker-compose.test.yml down
```
