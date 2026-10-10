# Прямая прошивка BIOS для Linux

Проверенная операция — **rawprogram из Linux flat_build**, затем запуск
имеющейся Ubuntu с NVMe. Она завершилась успешно в `linux-spi-restore.txt`;
записанные payload сверены с `spi-after-linux-restore.bin`.
Это прошивка BIOS; установка нового Linux образа и Linux на UFS не проверялись.

## Подготовка

Выполните [общую подготовку и бэкап SPI](direct-edl.md). Нужны все файлы
проверенного Linux BIOS. Укажите распакованный каталог:

```powershell
$bios = 'D:\firmware\linux-bios'
$linuxLock = Get-Content "$repo\manifests\linux-bios-files.json" -Raw | ConvertFrom-Json
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

Это операция, давшая успешную запись Linux BIOS на нашей плате. Ожидаются запись
XBL, XBL_CONFIG, AOP, TZ, ImageFv/PILFv и GPT, затем
`'rawprogram' command finished successfully`, без ERROR. В записанном сеансе —
03:25:31–03:29:23. UFS и NVMe этой командой не прошиваются.

Выполните обратное чтение:

```powershell
& $edl --memory spinor --loader .\prog_firehose_ddr.elf read-sector 0 8192 "$run\spi-linux-readback.bin" --lun 0
Set-Location $repo
```

Чтение должно вернуть 33554432 байта. В сохранённом результате все 18
непустых payload, кроме отдельно меняющихся GPT, совпали с исходными файлами.
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

Пункт no camera без этого параметра ещё приводил к I2C ошибке. Если параметр
вводился однократно, сохраните его в настройках GRUB, затем `sudo update-grub`.
После входа проверьте `cat /proc/cmdline`, `uname -r` и `findmnt /`.
Ubuntu с этим обходом запускалась. Автозагрузка нужного пункта без F12 и
повторные холодные старты отдельно пока не подтверждены.

Сохранённый полный SPI snapshot также есть в Android пакете, но его запись
новым `RecoveryLinux`/`Switch-Q6A-Bios.ps1` на плате ещё не проверялась.
Поэтому основной маршрут здесь использует реально выполненный rawprogram.
