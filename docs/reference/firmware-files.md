# Файлы прошивки и версии

Рабочий набор состоит из Android 15 Radxa, исправленного edl-ng v2,
исправленных XBL/SPI и файлов Linux BIOS. Каждое руководство использует
закреплённый набор; проверка хешей выполняется до обращения к SBC.

## Android 15 и исправления

Основа: `Q6A-Android15-spi-ufs-boot-20260630-b1` из
[каталога Radxa](https://dl.radxa.com/dragon/q6a/images/android/).
[Описание XBL](xbl-ufs30.md) и [зависимость edl-ng](../../tools/dependencies/edl-ng/README.md)
содержат исходные версии и способ воспроизведения исправлений.

Сохранённый полный комплект:

```text
Q6A-Android15-UFS-Toshiba-512.zip
1697316624 bytes
SHA256 94cf5947c6d6af85ea499108d8b74d6e4c3d6c86abf1521b75ca05bf2970008a
```

Для инструкции нужен распакованный каталог этого комплекта:

| Каталог | Назначение |
| --- | --- |
| `firmware/ufs/asic` | Android-образы, 6 rawprogram XML, 6 patch XML и Lite Firehose |
| `firmware/spinor` | Исходные Android SPI-файлы и DDR Firehose |
| `tools` | Проверенный Windows edl-ng v2 |
| `images` | Исправленные XBL и полный SPI 32 МиБ |
| `recovery` | Сохранённые оригинальный Android SPI и Linux SPI |

Комплект содержит 119 файлов и `manifest.json`, занимает около 4,10 ГБ
после распаковки. Он пока хранится локально; публичный Release с этим комплектом
не опубликован. Личный архив также содержит журналы и бэкапы платы.
При подготовке публичного пакета эти данные выделяются отдельно.

## Linux BIOS

```text
Q6A-Linux-BIOS-tested-files.zip
11067838 bytes
SHA256 49a615adbad48c6af558825bc1d72e3ee1be62ec2a49f8480e11552a04507497
```

Каталог `linux-bios/` содержит 23 файла: XML, DDR Firehose и все используемые
образы. Можно использовать исходный `flat_build/spinor/dragon-q6a` с теми же хешами.
Список фиксирует [files.lock.json](../../firmware/linux-bios/files.lock.json).

## Зачем нужны JSON-файлы

| Файл | Для чего используется |
| --- | --- |
| [Android bundle.lock.json](../../firmware/android15-ufs-toshiba512/bundle.lock.json) | Закрепляет хеш архива, внутреннего manifest, размер и число файлов; используется проверкой пакета |
| [Linux files.lock.json](../../firmware/linux-bios/files.lock.json) | Закрепляет размеры и SHA-256 23 файлов; используется перед Linux rawprogram |
| [XBL xbl-patch.json](../../firmware/android15-ufs-toshiba512/xbl-patch.json) | Задаёт исходный ELF, смещение инструкции и ожидаемые хеши; используется подготовкой XBL |
| [BIOS profiles](../../firmware/bios-profiles.json) | Закрепляет сохранённые SPI-образы внутри пакета; используется его проверкой |
| [edl-ng source.lock.json](../../tools/dependencies/edl-ng/source.lock.json) | Задаёт upstream, коммит, хеш патча и целевые платформы сборки |
| [Radxa sources.json](../vendor/sources.json) | Указывает происхождение и хеши оригинальных аппаратных документов |

Это входные данные инструментов и сведения о внешних файлах.
Исходники самого репозитория версионирует Git; отдельный список их хешей не требуется.
Результаты проверки решений находятся в [справочном разделе](validation/README.md).

## Проверка на любой ОС хоста

Из корня репозитория, с Python 3.10 или новее:

```sh
python tools/q6a.py verify-bundle --bundle /path/to/Q6A-Android15-UFS-Toshiba-512
python tools/q6a.py verify-linux-bios --directory /path/to/linux-bios
```

На macOS и Linux используйте `python3`, если команда `python` не установлена.
На Windows задайте свои пути, например `D:\firmware\linux-bios`.
Проверка читает файлы и не подключается к USB.
