# Прямая установка Android 15 на Toshiba UFS 512 ГБ

Установите Android 15 на **Q6A 12 ГБ с TOSHIBA THGJFCT2T84BAKCB rev 0100,
UFS 3.0, 512 ГБ**. Рабочее решение использует исправленный XBL в UFS и SPI.
Результат: завершённая загрузка Android и интерфейс HDMI, успешная обычная
перезагрузка, два холодных включения и чтение UFS после простоя.

Условия применимости: Secure Boot Off, закреплённый комплект Android 15,
исправленный edl-ng v2 на Windows. Проверен переход с Linux на уже настроенном
UFS: полная запись Android, подготовленная ext4 metadata, исправленные XBL/SPI
и повторные загрузки с UFS как единственного носителя. На каждом из четырёх
проверенных запусков прочитан 1 ГиБ после сброса буферов и 45 секунд простоя;
ошибок UFS и изменения ID загрузки за время чтения нет.
Provisioning существующего модуля сохранён.
Результаты: [запись и обратное чтение](../reference/validation/android-image-write-2026-10-11.json),
[проверенные запуски](../reference/validation/android-boot-2026-10-11.json).

## Подготовка

Выполните [общую подготовку, проверку файлов и бэкап SPI](prepare-edl.md).
Отключите SD/NVMe на время проверки Android, включите UART логирование.
`rawprogram` перезаписывает Android и userdata. Для уже рабочего Android,
если нужно вернуть только BIOS, используйте последний раздел этой инструкции.

## Проверить UFS и загрузить Lite

После общего бэкапа SPI переведите текущий DDR Firehose обратно в Sahara:

```powershell
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" reset --mode Edl --delay 1
Start-Sleep -Seconds 3
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" --loglevel Debug printgpt --lun 0
```

В логе должна быть загрузка `prog_firehose_lite.elf` через Sahara.
Проверьте модель `TOSHIBA THGJFCT2T84BAKCB0100`, сектор 4096 байт,
восемь LUN и `bBootPartitionEnabled=0x1`. LUN 0 проверенного модуля содержит
121268224 сектора, 496714645504 байта. Существующая GPT Linux или Android
не требует повторного provisioning.

## Provisioning: только не настроенный UFS

Для уже настроенного модуля пропустите этот раздел. Для модуля с подтверждённым
отсутствием нужной конфигурации скачайте и проверьте официальный XML.
Он использован в первоначальной успешной настройке этого модуля:

```powershell
$provisionXml = Join-Path $run 'provision_ufs31.xml'
Invoke-WebRequest -Uri 'https://dl.radxa.com/dragon/q6a/images/android/provision_ufs31.xml' -OutFile $provisionXml
if ((Get-FileHash $provisionXml -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2eca74731049bfb399ec88bdbb830b5163910c471902d15dc3bfa6e9c1889c3e') { throw 'Unexpected provisioning XML' }
```

После свежего EDL с Lite:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" --loglevel Debug provision $provisionXml
```

Ожидаемый результат: `All 10/10 commands sent and ACKed successfully`.
Все десять команд, включая commit, должны получить ACK.
После commit снимите питание и снова войдите в EDL. При 9/10, NAK или тайм-ауте
запись системы не начинайте. Наименование ufs31 не меняет версию чипа: он сообщает 0x0300.

## Записать Android на UFS

После свежего EDL с Lite, выполняйте эту операцию отдельно:

```powershell
Set-Location $ufs
& $edl --memory ufs --maxpayload 16384 --loader .\prog_firehose_lite.elf rawprogram rawprogram_unsparse0.xml patch0.xml rawprogram1.xml patch1.xml rawprogram2.xml patch2.xml rawprogram3.xml patch3.xml rawprogram4.xml patch4.xml rawprogram5.xml patch5.xml
Set-Location $repo
```

Ожидается запись LUN 0–5 и
`'rawprogram' command finished successfully`, без ERROR. Затем установите
исправленный XBL, необходимый для этого Toshiba.

## Создать metadata при полной установке

После записи всех XML запишите пустую ext4 в 16 МиБ `metadata`, где Android хранит
служебные данные шифрования. `rawprogram` создаёт этот раздел, но не записывает
в него образ. Файл `$metadata` создан командой `prepare-android` при подготовке.
Он позволяет начать установку с новой конфигурацией,
в том числе после Linux на UFS. Выполняйте эту запись только вместе с полной
перезаписью Android и userdata:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" write-part metadata $metadata --lun 0
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part metadata "$run\metadata-readback.bin" --lun 0
if ((Get-Item "$run\metadata-readback.bin").Length -ne 16777216 -or (Get-FileHash "$run\metadata-readback.bin" -Algorithm SHA256).Hash.ToLowerInvariant() -ne '5be1630bc6c3098c49cb7e6dbbf8fbdba314af9e886ca3716dcd3a937b2e061b') { throw 'Metadata readback mismatch' }
```

Ожидаются `Successfully wrote`, `Successfully read` и совпадение хеша.
При первом запуске Android заполнит подготовленную служебную файловую систему.
Для этой сборки одного `erase-part metadata` недостаточно: автоматического
создания ext4 при запуске нет.

## Сохранить и исправить UFS XBL

Продолжайте с Lite. Для исключения затруднений поиска указываются точные LUN:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part xbl_a "$run\xbl_a-before.bin" --lun 1
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part xbl_b "$run\xbl_b-before.bin" --lun 2
```

Ожидаемый размер каждого раздела — 3690496
байт. A содержит оригинальный XBL, B нулевой. Подготовьте полный A раздел,
сохраняя его хвост. Подготовьте кандидат:

```powershell
$a = [IO.File]::ReadAllBytes("$run\xbl_a-before.bin")
$b = "$run\xbl_b-before.bin"
if ($a.Length -ne 3690496 -or (Get-Item $b).Length -ne 3690496) { throw 'Unexpected XBL partition size' }
if ((Get-FileHash $b -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2c87824365571a09163a53a362d95b2f9edecb82e358807f265e50a9e0d85ee3') { throw 'B slot is not the tested empty image' }
$sha = [Security.Cryptography.SHA256]::Create()
$sourceSize = [int](Get-Item "$ufs\xbl.elf").Length
$prefix = [BitConverter]::ToString($sha.ComputeHash($a,0,$sourceSize)).Replace('-','').ToLowerInvariant()
$sha.Dispose()
if ($prefix -ne '4c3e9eaa5bccf57fdd0f30233600276b25069fbbe019161331bfb75ed077c1f7') { throw 'A slot does not contain the tested original XBL' }
(Get-FileHash "$run\xbl_a-before.bin" -Algorithm SHA256).Hash | Set-Content "$run\xbl_a-before.bin.sha256"
(Get-FileHash $b -Algorithm SHA256).Hash | Set-Content "$run\xbl_b-before.bin.sha256"
$patch = [IO.File]::ReadAllBytes($xbl)
[Array]::Copy($patch,0,$a,0,$patch.Length)
[IO.File]::WriteAllBytes("$run\xbl_a-candidate.bin",$a)
```

Запишите кандидат и прочитайте раздел обратно:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" write-part xbl_a "$run\xbl_a-candidate.bin" --lun 1
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part xbl_a "$run\xbl_a-readback.bin" --lun 1
```

После `Successfully` обеих операций:

```powershell
if ((Get-FileHash "$run\xbl_a-readback.bin" -Algorithm SHA256).Hash -ne (Get-FileHash "$run\xbl_a-candidate.bin" -Algorithm SHA256).Hash) { throw 'UFS XBL readback mismatch' }
'UFS xbl_a verified; empty xbl_b unchanged'
```

B не записывается. Не повторяйте rawprogram после исправления: он вернёт stock XBL.
Подпись изменённого XBL недействительна; проверенная плата приняла его при
Secure Boot Off. Файлы и [описание патча](../reference/xbl-ufs30.md) зафиксированы по SHA-256.

## Записать исправленный Android SPI

**Снова войдите в EDL с полностью новым Sahara**, теперь нужен DDR программатор.
Из текущей Lite Firehose-сессии:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" reset --mode Edl --delay 1
Start-Sleep -Seconds 3
```

Запишите весь SPI и выполните обратное чтение:

```powershell
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" write-sector 0 $androidSpi --lun 0
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" read-sector 0 8192 "$run\spi-android-readback.bin" --lun 0
```

В логе записи подтвердите загрузку DDR ELF через Sahara.
Ожидается 33554432 байта. Проверенная запись заняла около пяти минут, поэтому
не прерывайте её из-за нескольких минут ожидания. Затем:

```powershell
if ((Get-FileHash "$run\spi-android-readback.bin" -Algorithm SHA256).Hash.ToLowerInvariant() -ne '51511ceb1043f89d187d0847a089f86fc49f6174f1ff15a7f9e5ba902e4b506b') { throw 'Android SPI readback mismatch' }
'Android SPI verified'
```

## Загрузить и подтвердить Android

Из текущей SPI Firehose сессии:

```powershell
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" reset --mode Reset --delay 1
```

Ожидается XBL → UEFI → ядро → интерфейс Android 15. Сообщение о разблокированном
загрузчике соответствует проверенной конфигурации Secure Boot Off.
С подключённым USB и ADB из подготовленного SDK:

```powershell
$adb = Join-Path $sdk 'adb.exe'
& $adb devices -l
& $adb shell getprop ro.build.version.release
& $adb shell getprop sys.boot_completed
& $adb shell getprop init.svc.bootanim
& $adb shell 'cat /proc/mounts | grep " /metadata "'
& $adb shell bootctl get-current-slot
& $adb shell bootctl is-slot-marked-successful 0
```

Ожидаемые значения: `15`, `1`, `stopped`; `metadata` — ext4 с `rw`.
Активный слот — `0` (A), отметка успешной загрузки — `1`.
На проверенном HDMI активен режим 3840×2160 @ 30 Hz.

### Проверить UFS после простоя

В этой userdebug-сборке доступен диагностический ADB root. Штатный Toybox `dd`
не поддерживает `iflag=direct`: используйте чтение блочного устройства после
сброса его буферов, затем 45 секунд простоя:

```powershell
& $adb root
Start-Sleep -Seconds 2
& $adb shell cat /sys/block/sda/device/model
& $adb shell 'sync && blockdev --flushbufs /dev/block/sda'
Start-Sleep -Seconds 45
& $adb shell 'dd if=/dev/block/sda of=/dev/null bs=1048576 count=1024 skip=1024'
& $adb shell 'dmesg | grep -iE "ufshcd.*(timed.out|failed|eh_fatal|force_reset.*1|OCS invalid)|I/O error|Kernel panic|soft lockup|watchdog.*BUG"'
```

Модель должна быть `THGJFCT2T84BAKCB`. Ожидаются `1024+0 records in/out`
и 1073741824 прочитанных байта; последняя команда не должна вывести ошибок.
Это чтение через буферизированный блочный интерфейс, а не измерение O_DIRECT.

### Проверить повторные включения

Выполните обычную перезагрузку, дождитесь интерфейса Android и повторите
проверки ADB и чтения:

```powershell
& $adb reboot
```

Затем штатно выключите систему:

```powershell
& $adb shell reboot -p
```

После выключения снимите питание и отсоедините USB к ПК на 10 секунд.
Включите без EDL; после появления интерфейса подключите USB к ПК и повторите
проверки. Для второго холодного включения повторите выключение и этот порядок.

### Активировать записанный слот A при исчерпанных попытках

Если загрузчик уже остановился в Fastboot после предыдущих попыток запуска,
проверьте состояние слота. Эти команды применяются после полной записи и
проверки `metadata`, XBL и SPI по этому руководству:

```powershell
$fastboot = Join-Path $sdk 'fastboot.exe'
& $fastboot devices
& $fastboot getvar current-slot
& $fastboot getvar slot-unbootable:a
& $fastboot getvar slot-retry-count:a
```

Для записанного A с `slot-unbootable:a=yes` и `slot-retry-count:a=0`
восстановите попытки и запустите его:

```powershell
& $fastboot set_active a
& $fastboot reboot
```

Ожидается `OKAY` обеих операций, затем завершение загрузки и успешная отметка A.
Этот переход проверен на плате; штатная полная установка с подготовленным
`metadata` выполняется без ожидания циклов перезапуска.

## Ёмкость userdata

Раздел userdata занимает около 444,36 ГиБ, а файловая система F2FS `/data`
из исходной сборки — 45 ГиБ. После установки выполните
[создание /data полного размера](android-data-capacity.md) через штатный сброс
в recovery: проверены 444,36 ГиБ, запись файла и повторная загрузка.
Сброс удаляет данные пользователя, поэтому выполняется до настройки Android
либо после сохранения нужных файлов.

## Вернуть только Android BIOS при установленной системе

После общей подготовки и бэкапа, с Lite прочитайте текущий A:

Если бэкап выполнялся через DDR, сначала выполните переход DDR → Lite
из начала инструкции. Проверка модели остаётся обязательной; запись XML
и очистка metadata для возврата только BIOS не выполняются.

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part xbl_a "$run\xbl_a-current.bin" --lun 1
```

Проверьте наличие исправленного XBL:

```powershell
$a = [IO.File]::ReadAllBytes("$run\xbl_a-current.bin")
$length = [int](Get-Item $xbl).Length
if ($a.Length -ne 3690496) { throw 'Incomplete current XBL' }
$sha = [Security.Cryptography.SHA256]::Create()
$prefix = [BitConverter]::ToString($sha.ComputeHash($a,0,$length)).Replace('-','').ToLowerInvariant()
$sha.Dispose()
if ($prefix -ne '347c5bfd376ee029ed60486ffb0d69ebbc82bd65111e418389fb724c482b3ed5') { throw 'Patched Android UFS XBL is required' }
```

После этого выполняются только разделы «Записать исправленный Android SPI»
и «Загрузить и подтвердить Android». Для этого варианта предварительно требуется установленный Android
с исправленным `xbl_a`. Операции записи SPI и reset проверены; повторный
цикл переключения ОС проверяется отдельно.
