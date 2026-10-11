# Подготовка к прямым командам EDL

Подготовьте закреплённые файлы, подключите Q6A в EDL и сохраните полный SPI.
Для рабочего маршрута используется Windows и исправленный edl-ng v2.

## Файлы и PowerShell

Ниже выберите ОС: раздел Linux готовит основной BIOS `260916` для SD, NVMe
и UFS. Android использует свой проверенный комплект.
Нужен исправленный edl-ng v2.
Источники и контрольные суммы приведены в [справочнике файлов](../reference/firmware-files.md).

Откройте PowerShell от администратора **в корне репозитория**. Задайте свои пути:

```powershell
$ErrorActionPreference = 'Stop'
$repo = (Get-Location).Path
$run = Join-Path $repo 'runs\direct-001'
if (Test-Path -LiteralPath $run) { throw 'Choose a new run directory; preserve previous backups.' }
New-Item -ItemType Directory -Path $run | Out-Null
```

Для следующей установки выберите новый каталог вместо `direct-001`.

### Linux

Основной Linux BIOS для SD, NVMe и UFS — **`260916`**. На плате хранится
одна загрузочная прошивка в SPI; смена системного носителя не требует
выбора другого набора BIOS.

Ниже используется закреплённый официальный набор Radxa для QCS6490.
Опубликованные аппаратные результаты сохраняют фактические версии:
полный прогон SD/NVMe с основным BIOS ещё не зафиксирован.
После установки выполните проверки из руководства выбранного носителя.
История выпусков и changelog приведены в
[справочнике BIOS](../reference/boot-firmware.md#история-версий-linux-bios).

Блок подготовки задаёт `$biosVersion`, `$bios` и `$spi` для проверки файлов,
бэкапа и общей команды записи SPI.

Укажите проверенный edl-ng v2:

```powershell
$edl = 'D:\tools\edl-ng.exe'
```

#### Получить набор 260916

Получите закреплённые файлы официального репозитория Radxa в отдельный каталог:

```powershell
$biosVersion = '260916'
$bios = 'D:\firmware\linux-bios-260916'
python "$repo\tools\q6a.py" fetch-linux-bios --directory $bios
if ($LASTEXITCODE -ne 0) { throw 'BIOS download or verification failed' }
python "$repo\tools\q6a.py" verify-linux-bios --version $biosVersion --directory $bios
if ($LASTEXITCODE -ne 0) { throw 'Linux BIOS file verification failed' }
$spi = $bios
```

Проверяются 26 файлов с закреплённого коммита по
[files.lock.json](../../firmware/linux-bios-260916/files.lock.json).
DDR и Lite программаторы берутся из этого же набора.

Исходники и способ сборки edl-ng доступны в [описании зависимости](../../tools/dependencies/edl-ng/README.md).
Для Linux пакет Android не нужен.

### Android

Скачайте и распакуйте официальный
[Android 15 для SPI + UFS, 20260630-b1](https://dl.radxa.com/dragon/q6a/images/android/Q6A-Android15-spi-ufs-boot-20260630-b1.7z).
Нужен каталог с `spinor` и `ufs/asic`. Подготовьте исправленный edl-ng v2
по [описанию зависимости](../../tools/dependencies/edl-ng/README.md).
Скачайте [Android SDK Platform-Tools 37.0.1 для Windows](https://dl.google.com/android/repository/platform-tools_r37.0.1-win.zip)
и распакуйте `platform-tools` целиком: для служебного раздела нужны
`mke2fs.exe`, `mke2fs.conf` и `libwinpthread-1.dll`.
Соберите исправленные XBL и полный SPI из официальных файлов:

```powershell
$android = 'D:\firmware\Q6A-Android15-spi-ufs-boot-20260630-b1'
$edl = 'D:\tools\edl-ng.exe'
$sdk = 'D:\tools\platform-tools'
$adb = Join-Path $sdk 'adb.exe'
$prepared = Join-Path $run 'android-prepared'
python "$repo\tools\q6a.py" prepare-android --directory $android --output-dir $prepared --mke2fs "$sdk\mke2fs.exe"
if ($LASTEXITCODE -ne 0) { throw 'Android preparation failed' }
$ufs = "$android\ufs\asic"
$spi = "$android\spinor"
$xbl = "$prepared\xbl-ufs30-power-test.elf"
$androidSpi = "$prepared\spi-android-toshiba512.bin"
$metadata = "$prepared\metadata-ext4.img"
```

Команда проверяет размер и SHA-256 82 входных файлов, SHA-384 сегментов XBL
и CRC обеих GPT. Она создаёт SPI размером 33554432 байта, заполняя
неиспользуемые области нулями. Образы и отчёт `prepared.json` сохраняются
в новом каталоге запуска. Также создаётся пустой ext4 `metadata` размером
16 МиБ, нужный для полной установки Android. Его UUID, время создания,
параметры и SHA-256 закреплены; исходные `mke2fs.exe`, конфигурация и DLL
проверяются перед запуском. Снимок SPI с другой платы для сборки не требуется.
Контрольные суммы закреплены в [files.lock.json](../../firmware/android15-ufs-toshiba512/files.lock.json).

Проверенный Windows EXE имеет SHA-256
`2cfedece4030e3ba4e2742cc573b30e890d774504236a67f1b04131f22ab5646`.
Исправления утилиты и её исходная версия описаны в
[зависимости edl-ng](../../tools/dependencies/edl-ng/README.md).

## EDL и смена программатора

Подключите отдельное питание 12 В 3 А и USB ПК к нижнему USB A OTG порту.
HDMI нужен для проверки загрузки; UART можно подключить для журнала.
До подачи питания удерживайте EDL, подайте питание,
отпустите кнопку. Windows должна определить `05C6:9008` / QDLoader 9008.
У проверенной платы EDL serial `7B57A3EB`. COM номер может меняться.

**Перед переходом SPI ↔ UFS нужен новый Sahara.** Снимите питание, вновь войдите
в EDL, затем выполняйте команду с нужным программатором. В журнале должна появиться
загрузка выбранного ELF через Sahara. Если виден уже работающий Firehose,
один `--loader` его не заменит. Повторите физический вход в EDL при отключённом
питании; учитывайте питание через USB соединения.

В проверенном Android-маршруте новый Sahara также получен командой
`reset --mode Edl --delay 1` из текущей Firehose-сессии и паузой 3 секунды.
Команда reset должна использовать текущие тип памяти, программатор и размер
payload. Затем следующая операция загружает новый ELF; подтвердите строку
`Uploading loader:` с нужным путём. Обе смены DDR → Lite и Lite → DDR
проверены на Windows. Прямые команды приведены в руководстве Android.

Для SPI и проверенной записи Linux на SD используется DDR программатор.
Маршруты Android и Linux на Toshiba UFS используют Lite из соответствующего
набора прошивки и `--maxpayload 16384`.
Выполняйте операции по одной и проверяйте вывод: `[ERROR]`, NAK, тайм-аут,
неполное чтение или несовпадение хеша означают остановку. Нулевой код выхода
или одна строка `finished successfully` не отменяют ERROR.

## Общий бэкап SPI

После свежего EDL с DDR программатором:

```powershell
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" read-sector 0 8192 "$run\spi-before.bin" --lun 0
```

Ожидаются `Successfully read 32.00 MiB` и файл 33554432 байта. Сохраните хеш:

```powershell
if ((Get-Item "$run\spi-before.bin").Length -ne 33554432) { throw 'Incomplete SPI backup' }
(Get-FileHash "$run\spi-before.bin" -Algorithm SHA256).Hash | Set-Content "$run\spi-before.bin.sha256"
```

Чтение полного SPI этой командой выполнено в успешном аппаратном сеансе.
Дальше выберите [Linux BIOS](linux-bios.md) или [Android на UFS](android-ufs.md).
