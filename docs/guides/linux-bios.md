# Прямая прошивка BIOS для Linux

Запишите BIOS для Linux в SPI через rawprogram. На Q6A 12 ГБ запись
наборов `260120` и `260916` проверена обратным чтением 18 payload.
Руководства по SD и NVMe используют `260120`: после его записи проверены
самостоятельные загрузки с этих носителей без дополнительных оверлеев.
BIOS `260916` опубликован для всей платформы QCS6490. Версии в руководствах
закрепляют проверенные конфигурации; история выпусков и основание выбора
для Toshiba приведены в [справочнике BIOS](../reference/boot-firmware.md#выбор-версии-linux-bios).

## Подготовка

Выполните [общую подготовку и бэкап SPI](prepare-edl.md). Для воспроизведения
проверенной конфигурации выберите версию из руководства установки ОС.

### Набор 260120 для SD и NVMe

Нужны все файлы BIOS `260120` из [официального архива](https://dl.radxa.com/dragon/q6a/images/dragon-q6a_flat_build_wp_260120.zip).
Источник и контрольная сумма архива указаны в [справочнике файлов](../reference/firmware-files.md).
Используйте `$bios`, заданный для SD/NVMe в общей подготовке.
Повторно проверьте выбранные файлы перед записью:

```powershell
$linuxLock = Get-Content "$repo\firmware\linux-bios\files.lock.json" -Raw | ConvertFrom-Json
foreach ($entry in $linuxLock.files) {
    $path = Join-Path $bios $entry.path
    if ((Get-Item -LiteralPath $path).Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Linux BIOS file mismatch: $path" }
}
```

Допустим также исходный каталог `flat_build\spinor\dragon-q6a` с теми же хешами.
Файл `prog_firehose_ddr.elf` лежит именно в этом подкаталоге, не в корне flat_build.

### Набор 260916

Используйте `$bios` из раздела Toshiba UFS общей подготовки: файлы
официального репозитория Radxa уже скачаны в отдельный каталог.
Повторно проверьте их перед записью:

```powershell
python "$repo\tools\q6a.py" verify-linux-bios --version 260916 --directory $bios
if ($LASTEXITCODE -ne 0) { throw 'BIOS verification failed' }
```

Команда сверяет размеры и SHA-256 26 файлов с закреплённого коммита.
Запись SPI и сравнение payload выполняются командами ниже для выбранного `$bios`.

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

Для чистой установки выполните запись Radxa OS R2 на [SD](linux-sd.md)
или [NVMe](linux-nvme.md) с BIOS `260120`, либо на [Toshiba UFS](linux-ufs.md)
с BIOS `260916` и постоянной настройкой питания модуля.
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
