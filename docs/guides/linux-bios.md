# Прямая прошивка BIOS для Linux

Запишите основной Linux BIOS `260916` в SPI через rawprogram. Одна прошивка в SPI
обслуживает Linux на SD, NVMe и UFS. Эта инструкция содержит общую команду
записи и проверку обратного чтения.

## Подготовка

Выполните [общую подготовку и бэкап SPI](prepare-edl.md).
[Получение файлов основного BIOS](prepare-edl.md#linux) выполняется там один раз.
Сохраните `$repo`, `$run`, `$edl`, `$biosVersion` и `$bios` в том же сеансе
PowerShell. Повторно проверьте выбранный набор перед записью:

```powershell
python "$repo\tools\q6a.py" verify-linux-bios --version $biosVersion --directory $bios
if ($LASTEXITCODE -ne 0) { throw 'BIOS verification failed' }
```

Команда сверяет размеры и SHA-256 файлов выбранной версии. Запись SPI и
сравнение payload выполняются командами ниже для того же `$bios`.

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

После записи SPI установите Radxa OS R2 на [SD](linux-sd.md),
[NVMe](linux-nvme.md) или [Toshiba UFS](linux-ufs.md).
Для Toshiba дополнительно устанавливается постоянная настройка питания модуля.
Если система уже записана, выключите питание, оставьте её носитель,
отсоедините USB к ПК и включите плату без кнопки EDL.

В штатной Radxa OS R2 используется embloader 0.4 и ядро `6.18.2-3-qcom`.
Пакеты и ядро на SD, NVMe и UFS обновляются по
[общей инструкции Radxa OS](linux-update.md). На NVMe отдельно зафиксирован
успешный APT-прогон с ядром `7.0.11-7-qcom`.
Для проверенных запусков дополнительные оверлеи и ручной параметр
`module_blacklist=i2c_qcom_geni` не потребовались.
После входа проверьте `uname -r`, `findmnt /` и доступный объём через `df -h /`.

Результаты записи SPI и загрузок Linux приведены в
[справочнике проверки решений](../reference/validation/README.md).
