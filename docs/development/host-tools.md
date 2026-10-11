# Инструменты хоста

Общий Python CLI находится в `tools/q6a.py`. Он объединяет проверку файлов,
подготовку XBL и сборку зависимости edl-ng. Требуется Python 3.10 или новее;
для файловых операций используются только модули стандартной библиотеки.

## Точки входа

Все команды выполняются из корня репозитория:

| Хост | Команда |
| --- | --- |
| Windows | `python tools/q6a.py check-repo` или `& .\tools\windows\q6a.ps1 check-repo` |
| Linux | `python3 tools/q6a.py check-repo` или `sh tools/linux/q6a.sh check-repo` |
| macOS | `python3 tools/q6a.py check-repo` или `sh tools/macos/q6a.sh check-repo` |

Платформенные точки входа вызывают одну общую реализацию и передают аргументы.
Они не запускают прошивку автоматически.

Команды, которые выполняются в Linux на самой Q6A, находятся отдельно в
[`tools/target`](../../tools/target/README.md). Здесь размещён установщик
настройки питания Toshiba UFS; компьютер Windows, macOS или Linux только
передаёт этот скрипт на плату.

## Команды

```sh
python tools/q6a.py check-repo
python tools/q6a.py verify-bundle --bundle /path/to/Q6A-Android15-UFS-Toshiba-512
python tools/q6a.py fetch-linux-bios --directory /path/to/linux-bios-260916
python tools/q6a.py verify-linux-bios --version 260916 --directory /path/to/linux-bios-260916
python tools/q6a.py verify-linux-image --image /path/to/radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz --target sd
python tools/q6a.py prepare-xbl --xbl /path/to/xbl.elf --output-dir artifacts/rebuilt
python tools/q6a.py prepare-android --directory /path/to/Q6A-Android15-spi-ufs-boot-20260630-b1 --output-dir artifacts/android-prepared --mke2fs /path/to/platform-tools/mke2fs.exe
python tools/q6a.py build-edl --plan
```

Для `prepare-xbl` параметр `--spi` дополнительно создаёт полный Android SPI;
исходные файлы описаны в [справочнике XBL](../reference/xbl-ufs30.md).
`verify-bundle` принимает распакованный пакет и сверяет 119 файлов с закреплённым
manifest. Образцы путей замените своими. На macOS/Linux используйте `python3`.

`prepare-android` проверяет 82 официальных файла, создаёт исправленный XBL,
полный SPI с нулевыми неиспользуемыми областями и новую пустую ext4 `metadata`.
Для metadata используется `mke2fs` с конфигурацией из Android SDK 37.0.1.
На Windows проверяются также хеши EXE, конфигурации и DLL. Команда
нормализует время в закреплённом формате ext4 без metadata/inode checksums
и требует точного совпадения трёх результатов с SHA-256 в `files.lock.json`.
Чужие существующие результаты сохраняются: при отличии команда останавливается.
Подготовка не обращается к USB. Сборка этих файлов проверена на Windows;
для других хостов нужна отдельная проверка `mke2fs` и аппаратного маршрута.

`fetch-linux-bios` получает 26 файлов BIOS `260916` из закреплённого коммита
официального репозитория Radxa и сверяет размер и SHA-256 каждого файла до
сохранения. Повторный запуск использует уже проверенные файлы и скачивает
недостающие. При отличающемся существующем файле команда останавливается,
сохраняя его. Загрузка и проверка этой команды выполнены на Windows.
Команда не обращается к SBC. `verify-linux-bios` без `--version` проверяет
основной набор `260916`; в инструкциях параметр задаётся явно. Файлы готовятся
в [едином разделе подготовки Linux BIOS](../guides/prepare-edl.md#linux).

`verify-linux-image` принимает сжатый `.img.xz` и носитель `sd`, `nvme` или `ufs`.
Команда сверяет размер, SHA-256 и SHA-512 с официальным Radxa OS R2:
для SD/NVMe нужен образ с секторами 512 байт, для UFS — 4096 байт.
Для распакованного `.img` добавьте `--uncompressed`: будут проверены
размер и SHA-256 исходного дискового образа. Этим же способом можно проверить
обратное чтение записанной области до первого запуска ОС.

## Сборка edl-ng

Происхождение зависимости: [edl-ng](../../tools/dependencies/edl-ng/README.md).
Команда `build-edl --plan` показывает закреплённые git/dotnet команды без
скачивания файлов и запуска сборки. Для выполнения:

```sh
python tools/q6a.py build-edl
```

Нужны Git, .NET SDK с поддержкой `net9.0` и native toolchain для Native AOT
на текущем хосте. Исходники создаются в `.work/edl-ng/<runtime>`,
результат — в `artifacts/edl-ng/<runtime>`. Перед сборкой применяются проверки
патча, затем выполняются тесты upstream и publish. Существующие каталоги
сборки сохраняются; повторная команда останавливается.

Автоматически выбираются ОС и архитектура хоста: `win-x64`, `win-arm64`,
`linux-x64`, `linux-arm64`, `osx-x64`, `osx-arm64`. Команда собирает для текущего
хоста; кросс-компиляция в этот рецепт не включена.

На Linux и macOS транспорт edl-ng использует libusb; на Windows доступны
QDLoader и libusb. Зависимости Native AOT и USB описаны в
[закреплённом README upstream](https://github.com/strongtz/edl-ng/blob/4a658eee465a84b13c53b338edfd22bd08e4b211/README.md).
Доступ к USB и аппаратные команды проверяются отдельно на каждом хосте.
Windows EXE из рабочего комплекта остаётся точным проверенным бинарником;
новые сборки получают собственную аппаратную проверку.

## Проверки

```sh
python tools/q6a.py check-repo
python -m unittest discover -s tests -v
```

CI запускает эти команды на Windows, macOS и Linux и проверяет платформенные
точки входа. Для Windows-обёрток дополнительно:

```powershell
& .\tests\windows\Test-Q6A-Offline.ps1
```

Эти проверки не подключаются к SBC. Они проверяют хеши, пути пакета,
сохранение прежних файлов, закреплённость сборки и остановку автоматизации
при неполных или отличающихся результатах.
