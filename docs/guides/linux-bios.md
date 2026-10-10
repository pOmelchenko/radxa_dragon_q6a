# Прямая прошивка BIOS для Linux

Запишите Linux BIOS в SPI через rawprogram и загрузите установленную Ubuntu
с NVMe. Рабочая конфигурация: Q6A 12 ГБ, NVMe 256 ГБ, ядро `7.0.11-7-qcom`.
Результат записи проверяется обратным чтением 18 payload.

## Подготовка

Выполните [общую подготовку и бэкап SPI](prepare-edl.md). Нужны все файлы
проверенного Linux BIOS. Укажите распакованный каталог:

```powershell
$bios = 'D:\firmware\linux-bios'
$linuxLock = Get-Content "$repo\firmware\linux-bios\files.lock.json" -Raw | ConvertFrom-Json
foreach ($entry in $linuxLock.files) {
    $path = Join-Path $bios $entry.path
    if ((Get-Item -LiteralPath $path).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Linux BIOS file mismatch: $path" }
}
```

Допустим также исходный каталог `flat_build\spinor\dragon-q6a` с теми же хешами.
Файл `prog_firehose_ddr.elf` лежит именно в этом подкаталоге, не в корне flat_build.

## Запись SPI

После свежего входа в EDL с DDR программатором:

```powershell
Set-Location $bios
& $edl --memory spinor --loader .\prog_firehose_ddr.elf rawprogram rawprogram0.xml patch0.xml
```

Ожидаются запись
XBL, XBL_CONFIG, AOP, TZ, ImageFv/PILFv и GPT, затем
`'rawprogram' command finished successfully`, без ERROR. Команда меняет SPI.
Система на NVMe и данные UFS сохраняются.

Выполните обратное чтение:

```powershell
& $edl --memory spinor --loader .\prog_firehose_ddr.elf read-sector 0 8192 "$run\spi-linux-readback.bin" --lun 0
Set-Location $repo
```

Чтение должно вернуть 33554432 байта. Сверьте все 18
непустых payload с исходными файлами, исключая отдельно меняющиеся GPT.
Полный старый SPI хеш нельзя использовать как обязательный итог нового rawprogram:
UEFI variables, DDR training и незаписанные области могут отличаться.

Для локальной проверки payload обратного чтения, без новых операций с платой:

```powershell
$dump = [IO.File]::ReadAllBytes("$run\spi-linux-readback.bin")
if ($dump.Length -ne 33554432) { throw 'Incomplete Linux SPI readback' }
[xml]$xml = Get-Content "$bios\rawprogram0.xml" -Raw
$sha = [Security.Cryptography.SHA256]::Create()
foreach ($entry in $xml.data.program) {
    if (-not $entry.filename -or $entry.label -in @('PrimaryGPT','BackupGPT')) { continue }
    $source = Join-Path $bios $entry.filename
    $size = [int](Get-Item $source).Length
    $offset = [int64]$entry.start_sector * [int]$entry.SECTOR_SIZE_IN_BYTES
    $actual = [BitConverter]::ToString($sha.ComputeHash($dump,[int]$offset,$size)).Replace('-','')
    if ($actual -ne (Get-FileHash $source -Algorithm SHA256).Hash) { throw "Readback mismatch: $($entry.label)" }
}
$sha.Dispose()
'Linux SPI payloads match'
```

Такая проверка повторяет сравнение сохранённого SPI с исходными payload.
Сами чтение и запись выполняются напрямую через edl-ng.

## Загрузка Linux

Выключите питание, подключите уже подготовленный NVMe и включите без EDL.
У рабочей Ubuntu было ядро `7.0.11-7-qcom`. В рабочем пункте загрузчика:

```text
module_blacklist=i2c_qcom_geni
```

Сохраните параметр в настройках рабочего пункта GRUB, затем выполните
`sudo update-grub`. После входа проверьте `cat /proc/cmdline`, `uname -r`
и `findmnt /`. Ожидается Ubuntu на NVMe с указанным параметром ядра.

Применимость: запись BIOS и запуск этой Ubuntu проверены на плате.
Руководство относится к уже установленной системе на NVMe. Автоматический
выбор пункта UEFI/GRUB зависит от настройки загрузчика; при необходимости
выберите рабочую запись через F12. Параметр отключает соответствующий I2C-драйвер.
