# Документация Radxa Dragon Q6A

## Руководства

| Задача | Инструкция |
| --- | --- |
| Подготовить файлы и сохранить SPI | [EDL на Windows](guides/prepare-edl.md) |
| Выбрать версию Linux BIOS и получить её файлы | [Единая подготовка Linux BIOS](guides/prepare-edl.md#linux) |
| Записать загрузочную прошивку для Linux | [Прошивка Linux BIOS](guides/linux-bios.md) |
| Установить штатную Ubuntu на SD из Windows | [Radxa OS R2 на SD](guides/linux-sd.md) |
| Установить Ubuntu на NVMe из Windows | [Radxa OS R2 на NVMe](guides/linux-nvme.md) |
| Установить Ubuntu на Toshiba UFS из Windows | [Radxa OS R2 на UFS](guides/linux-ufs.md) |
| Обновить Radxa OS на SD, NVMe или UFS | [Обновление Radxa OS](guides/linux-update.md) |
| Развернуть Android 15 на Toshiba UFS | [Установка Android](guides/android-ufs.md) |
| Использовать весь раздел userdata в Android | [Полный объём /data](guides/android-data-capacity.md) |
| Проверить подключение и этап загрузки | [Диагностика](guides/troubleshooting.md) |

## Справочник

- [Аппаратные интерфейсы, UART и питание](reference/hardware.md).
- [Накопители и расположение загрузочных компонентов](reference/storage.md).
- [Загрузочная прошивка Linux/Android и история BIOS](reference/boot-firmware.md).
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
