# Документация Radxa Dragon Q6A

## Руководства

| Задача | Инструкция |
| --- | --- |
| Подготовить файлы и сохранить SPI | [EDL на Windows](guides/prepare-edl.md) |
| Подготовить загрузку Linux с NVMe | [Прошивка Linux BIOS](guides/linux-bios.md) |
| Развернуть Android 15 на Toshiba UFS | [Установка Android](guides/android-ufs.md) |
| Проверить подключение и этап загрузки | [Диагностика](guides/troubleshooting.md) |

## Справочник

- [Аппаратные интерфейсы, UART и питание](reference/hardware.md).
- [Накопители и расположение загрузочных компонентов](reference/storage.md).
- [Выбор BIOS для Linux и Android](reference/boot-firmware.md).
- [Файлы прошивки, версии и контрольные суммы](reference/firmware-files.md).
- [Исправление XBL для Toshiba UFS 3.0](reference/xbl-ufs30.md).
- [Конфигурация и результаты проверки решений](reference/validation/README.md).

## Оригиналы Radxa

[Каталог производителя](vendor/README.md): схема V1.21, размещение компонентов,
механические размеры и иллюстрация интерфейсов. Файлы сохранены вместе
с источниками и контрольными суммами.

## Разработка

[Инфраструктура инструментов и будущие дополнения](development/README.md):
общий Python CLI, платформенные точки входа, Windows-автоматизация и камерные работы.
