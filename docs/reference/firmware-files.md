# Файлы прошивки и версии

Для Linux закреплены два набора файлов загрузочной прошивки и образы
Radxa OS R2. [Выбор версии BIOS](../guides/prepare-edl.md#linux) и команды
получения находятся в общей подготовке. Для Android 15
на Toshiba UFS используются исправленные XBL/SPI. Оба маршрута используют
исправленный edl-ng v2. Входные файлы закреплены в JSON;
проверка хешей выполняется до обращения к SBC.

## Android 15 и исправления

Основа: `Q6A-Android15-spi-ufs-boot-20260630-b1` из
[каталога Radxa](https://dl.radxa.com/dragon/q6a/images/android/).
[Описание XBL](xbl-ufs30.md) и [зависимость edl-ng](../../tools/dependencies/edl-ng/README.md)
содержат исходные версии и способ воспроизведения исправлений.

Для прямой установки используется официальный
[архив UFS 20260630-b1](https://dl.radxa.com/dragon/q6a/images/android/Q6A-Android15-spi-ufs-boot-20260630-b1.7z),
2190816768 байт. Размеры и SHA-256 82 нужных файлов закреплены в
[files.lock.json](../../firmware/android15-ufs-toshiba512/files.lock.json).
Их имена, размеры и CRC-32 также сверены с индексом опубликованного архива.
Ссылки и проверка файлов находятся в [подготовке EDL](../guides/prepare-edl.md).

Команда `prepare-android` создаёт три файла:

| Файл | Размер, байт | SHA-256 |
| --- | --- | --- |
| `xbl-ufs30-power-test.elf` | 3665840 | `347c5bfd376ee029ed60486ffb0d69ebbc82bd65111e418389fb724c482b3ed5` |
| `spi-android-toshiba512.bin` | 33554432 | `51511ceb1043f89d187d0847a089f86fc49f6174f1ff15a7f9e5ba902e4b506b` |
| `metadata-ext4.img` | 16777216 | `5be1630bc6c3098c49cb7e6dbbf8fbdba314af9e886ca3716dcd3a937b2e061b` |

Полный SPI собирается из официальных GPT/XML и исправленного XBL;
неиспользуемые области заполняются нулями. `metadata` — новая пустая ext4,
созданная `mke2fs 1.47.2` из официальных
[Android SDK Platform-Tools 37.0.1](https://developer.android.com/tools/releases/platform-tools).
Файлы Windows SDK, конфигурация и контрольная сумма ZIP закреплены в том же
`files.lock.json`. UUID, hash seed и время ext4 фиксированы; образ не содержит
ключей, настроек или файлов пользователя.

### Архив первоначального успешного решения

Сохранённый полный комплект:

```text
Q6A-Android15-UFS-Toshiba-512.zip
1697316624 bytes
SHA256 94cf5947c6d6af85ea499108d8b74d6e4c3d6c86abf1521b75ca05bf2970008a
```

Этот локальный комплект сохранён как архив первоначального решения:

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
Прямая инструкция выше использует официальные входные файлы и сборку
в репозитории; этот личный архив для неё не требуется.

## Linux BIOS

Официальный источник проверенных файлов — [Linux BIOS 260120](https://dl.radxa.com/dragon/q6a/images/dragon-q6a_flat_build_wp_260120.zip).
Архив занимает 11434972 байта, SHA-256:
`cf23a1742ae5d51c451947d82cb21fd3f1c10bbcd621d611f55520673e3f90ca`.
После распаковки нужен каталог `flat_build/spinor/dragon-q6a`.
Все 23 файла этого каталога совпадают с закреплённым набором.

Также сохранён локальный архив с теми же файлами:

```text
Q6A-Linux-BIOS-tested-files.zip
11067838 bytes
SHA256 49a615adbad48c6af558825bc1d72e3ee1be62ec2a49f8480e11552a04507497
```

Каталог `linux-bios/` содержит 23 файла: XML, DDR Firehose и все используемые
образы. Можно использовать исходный `flat_build/spinor/dragon-q6a` с теми же хешами.
Список фиксирует [files.lock.json](../../firmware/linux-bios/files.lock.json).

Отдельно закреплены 26 файлов BIOS `260916` из
[официального репозитория edk2-qualcomm](https://github.com/radxa-pkg/edk2-qualcomm/tree/48835fa3de36ea80597cf39e7a41a9ddf9648f52/src/qcs6490):
[размеры и SHA-256](../../firmware/linux-bios-260916/files.lock.json).
Получение и проверка обоих наборов описаны в
[едином разделе подготовки Linux BIOS](../guides/prepare-edl.md#linux).

## Radxa OS R2

Образы Ubuntu 24.04 Noble с GNOME взяты из [официального выпуска rsdk-r2](https://github.com/radxa-build/radxa-dragon-q6a/releases/tag/rsdk-r2).
Версия пакета ядра — `6.18.2-3`, минимальная дата Linux BIOS — `20251230`.

| Носитель | Файл | Размер `.xz`, байт | Логический сектор |
| --- | --- | --- | --- |
| SD и NVMe | `radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz` | 1582866836 | 512 байт |
| UFS | `radxa-dragon-q6a_noble_gnome_r2.output_4096.img.xz` | 1578528436 | 4096 байт |

Точные ссылки, размеры, SHA-256 и опубликованные SHA-512 находятся в
[images.lock.json](../../firmware/radxa-os-r2/images.lock.json).
Команда `verify-linux-image` проверяет выбор образа для носителя и обе суммы
сжатого файла. Для записи через EDL образ нужно распаковать в `.img`.
Размеры и SHA-256 распакованных `.img` также закреплены в этом файле;
они получены из архивов после проверки опубликованных сумм.
Для их проверки добавьте `--uncompressed`.

В штатном образе используется embloader 0.4, запись Ubuntu 24.04.4 LTS
с ядром `6.18.2-3-qcom`. Загрузчик читает записи Boot Loader Specification
из `loader/entries` и установлен в том числе по пути
`EFI/systemd/systemd-bootaa64.efi`. Все файлы дополнительных оверлеев в каталоге
`RadxaOS/6.18.2-3-qcom/dtbo` имеют суффикс `.disabled`.

## Зачем нужны JSON-файлы

| Файл | Для чего используется |
| --- | --- |
| [Android bundle.lock.json](../../firmware/android15-ufs-toshiba512/bundle.lock.json) | Закрепляет хеш архива, внутреннего manifest, размер и число файлов; используется проверкой пакета |
| [Android files.lock.json](../../firmware/android15-ufs-toshiba512/files.lock.json) | Закрепляет 82 официальных входных файла, Windows mke2fs и хеши воспроизводимых SPI/metadata; используется `prepare-android` |
| [Linux files.lock.json](../../firmware/linux-bios/files.lock.json) | Закрепляет размеры и SHA-256 23 файлов; используется перед Linux rawprogram |
| [Linux BIOS 260916 files.lock.json](../../firmware/linux-bios-260916/files.lock.json) | Закрепляет коммит официального источника, размеры и SHA-256 26 файлов; используется загрузкой и проверкой набора 260916 |
| [Radxa OS images.lock.json](../../firmware/radxa-os-r2/images.lock.json) | Закрепляет выпуск, ссылки, размеры и SHA-256/SHA-512 образов с секторами 512 и 4096 байт; используется проверкой образа для выбранного носителя |
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
python tools/q6a.py verify-linux-image --image /path/to/radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz --target sd
python tools/q6a.py verify-linux-image --image /path/to/radxa-dragon-q6a_noble_gnome_r2.output_4096.img.xz --target ufs
python tools/q6a.py verify-linux-image --image /path/to/radxa-dragon-q6a_noble_gnome_r2.output_512.img --target sd --uncompressed
```

На macOS и Linux используйте `python3`, если команда `python` не установлена.
На Windows задайте свои пути, например `D:\firmware\linux-bios`.
Проверка читает файлы и не подключается к USB.
