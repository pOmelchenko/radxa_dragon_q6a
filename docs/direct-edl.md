# Подготовка к прямым командам EDL

Основной путь использует исправленный **edl-ng v2** и отдельные команды.
Установка через Qualcomm GUI в нашем сеансе завершалась ошибками. Команды записи
и чтения ниже выполнялись на Q6A; подтверждение описано в инструкциях конкретной ОС.
Это не подтверждение нового полного повторного прогона с пустого модуля.

## Файлы и PowerShell

Нужен распакованный [проверенный Android пакет](artifacts.md). У него уже есть
edl-ng v2, оба программатора, оригинальные Android файлы и исправленные XBL/SPI.
Для Linux дополнительно нужен каталог из `Q6A-Linux-BIOS-tested-files.zip` или
точный исходный `flat_build/spinor/dragon-q6a`. Его файлы фиксирует
[linux-bios-files.json](../manifests/linux-bios-files.json).

Откройте PowerShell от администратора **в корне репозитория**. Задайте свои пути:

```powershell
$ErrorActionPreference = 'Stop'
$bundle = 'D:\firmware\Q6A-Android15-UFS-Toshiba-512'
$edl = "$bundle\tools\edl-ng.exe"
$ufs = "$bundle\firmware\ufs\asic"
$spi = "$bundle\firmware\spinor"
$xbl = "$bundle\images\xbl-ufs30-power-test.elf"
$androidSpi = "$bundle\images\spi-android-ufs30-power-test.bin"
$repo = (Get-Location).Path
$run = Join-Path $repo 'runs\direct-001'
if (Test-Path -LiteralPath $run) { throw 'Choose a new run directory; preserve previous backups.' }
New-Item -ItemType Directory -Path $run | Out-Null
```

Для следующей попытки выберите новый каталог вместо `direct-001`.
Проверьте точные файлы без обращения к плате:

```powershell
$lock = Get-Content "$repo\manifests\bundle-lock.json" -Raw | ConvertFrom-Json
if ((Get-FileHash "$bundle\manifest.json" -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.manifest_sha256) { throw 'Wrong bundle manifest' }
$manifest = Get-Content "$bundle\manifest.json" -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $path = Join-Path $bundle $entry.path
    if ((Get-Item -LiteralPath $path).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "File mismatch: $path" }
}
'119 bundle files checked'
```

Замороженный EXE имеет SHA-256
`2cfedece4030e3ba4e2742cc573b30e890d774504236a67f1b04131f22ab5646`.
Первоначальный edl-ng игнорировал `--maxpayload` в provisioning; Lite получал
1048576 вместо 16384. Исправленная версия устранила именно эту ошибку.

## EDL и смена программатора

Подключите отдельное питание 12 В 3 А, USB ПК к нижнему USB A OTG порту,
HDMI и уже настроенный UART. До подачи питания удерживайте EDL, подайте питание,
отпустите кнопку. Windows должна определить `05C6:9008` / QDLoader 9008.
У проверенной платы EDL serial `7B57A3EB`. COM номер может меняться.

**Перед переходом SPI ↔ UFS нужен новый Sahara.** Снимите питание, вновь войдите
в EDL, затем выполняйте команду с нужным программатором. В журнале должна появиться
загрузка выбранного ELF через Sahara. Если виден уже работающий Firehose,
один `--loader` его не заменит. Повторите физический вход в EDL при отключённом
питании; учитывайте питание через USB соединения.

Для SPI используется DDR программатор; для UFS — Lite и `--maxpayload 16384`.
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
