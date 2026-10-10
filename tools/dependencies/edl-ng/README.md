# edl-ng: закреплённая зависимость

| Поле | Значение |
| --- | --- |
| Upstream | [strongtz/edl-ng](https://github.com/strongtz/edl-ng) |
| Версия исходников | [`4a658eee465a84b13c53b338edfd22bd08e4b211`](https://github.com/strongtz/edl-ng/tree/4a658eee465a84b13c53b338edfd22bd08e4b211) |
| Локальные исправления | [q6a.patch](q6a.patch) |
| Лицензия upstream | [LICENSE](LICENSE) |
| Конфигурация сборки | [source.lock.json](source.lock.json), .NET `net9.0` |
| Рабочий Windows EXE SHA-256 | `2cfedece4030e3ba4e2742cc573b30e890d774504236a67f1b04131f22ab5646` |

Патч исправляет передачу `--maxpayload` при provisioning и configure,
обработку configure NAK, ограничение чанков записи и сохранение бинарных
данных, полученных вместе с Firehose XML. В нём сохранены новые C# файлы и тесты.

Исходники получает общий инструмент из указанного upstream, затем выбирает
точный коммит и применяет этот патч. Копия создаётся в локальном `.work/`;
результаты сборки — в `artifacts/`. Источник, версия, патч и лицензия составляют
одну зависимость. Проверка репозитория сверяет SHA-256 патча и лицензии.

Из корня репозитория:

```sh
python tools/q6a.py build-edl --plan
python tools/q6a.py build-edl
```

Требования к сборке и платформам:
[инструменты хоста](../../../docs/development/host-tools.md).
Новая сборка может иметь другой хеш бинарника; для аппаратного рецепта
она проверяется отдельно от зафиксированного Windows EXE.
