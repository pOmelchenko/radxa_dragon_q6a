# Прямая установка Android 15 на Toshiba UFS 512 ГБ

На **Q6A 12 ГБ, TOSHIBA THGJFCT2T84BAKCB rev 0100** отдельно выполнены
provisioning, запись Android, исправление UFS XBL, запись исправленного SPI
и обратное чтение. После обычного reset Android 15 завершил загрузку и появился
на HDMI. Ниже записаны эти операции через edl-ng, с проверками результата.
Пути приведены к сохранённому пакету; вся последовательность как новый единый
прогон с пустого модуля ещё не повторялась.

## Подготовка

Выполните [общую подготовку, проверку файлов и бэкап SPI](direct-edl.md).
Отключите SD/NVMe на время проверки Android, включите UART логирование.
`rawprogram` перезаписывает Android и userdata. Для уже рабочего Android,
если нужно вернуть только BIOS, используйте последний раздел этой инструкции.

## Provisioning: только не настроенный UFS

Наш работающий модуль уже настроен: этот раздел при повторной установке
пропускается. Для модуля с подтверждённым отсутствием нужной конфигурации,
после свежего EDL с Lite:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" --loglevel Debug provision "$bundle\provision_ufs31.xml"
```

Успех в сохранённом журнале: `All 10/10 commands sent and ACKed successfully`
в 19:19:23. Все десять команд, включая commit, должны получить ACK.
После commit снимите питание и снова войдите в EDL. При 9/10, NAK или тайм-ауте
запись системы не начинайте. Наименование ufs31 не меняет версию чипа: он сообщает 0x0300.

## Записать Android на UFS

После свежего EDL с Lite, выполняйте эту операцию отдельно:

```powershell
Set-Location $ufs
& $edl --memory ufs --maxpayload 16384 --loader .\prog_firehose_lite.elf rawprogram rawprogram_unsparse0.xml patch0.xml rawprogram1.xml patch1.xml rawprogram2.xml patch2.xml rawprogram3.xml patch3.xml rawprogram4.xml patch4.xml rawprogram5.xml patch5.xml
Set-Location $repo
```

В успешном журнале прошли LUN 0–5, затем
`'rawprogram' command finished successfully` в 19:22:05, без ERROR.
Это ещё не рабочая загрузка: исходный XBL на этом Toshiba зависал после
`UFS 3.x Device Volt set to 2.5 volt`.

## Сохранить и исправить UFS XBL

Продолжайте с Lite. Для исключения затруднений поиска указываются точные LUN:

```powershell
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part xbl_a "$run\xbl_a-before.bin" --lun 1
& $edl --memory ufs --maxpayload 16384 --loader "$ufs\prog_firehose_lite.elf" read-part xbl_b "$run\xbl_b-before.bin" --lun 2
```

Оба чтения выполнены в аппаратном сеансе; ожидаемый размер каждого — 3690496
байт. A содержит оригинальный XBL, B нулевой. Подготовьте полный A раздел,
сохраняя его хвост. Этот способ использовался в успешном эксперименте:

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

Запись и чтение, выполненные в успешном сеансе:

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
Secure Boot Off. Файлы и [описание патча](xbl-workaround.md) зафиксированы по SHA-256.

## Записать исправленный Android SPI

**Снова войдите в EDL с полностью новым Sahara**, теперь нужен DDR программатор.
Запись всего SPI и его обратное чтение выполнены в успешном эксперименте:

```powershell
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" write-sector 0 $androidSpi --lun 0
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" read-sector 0 8192 "$run\spi-android-readback.bin" --lun 0
```

Ожидается 33554432 байта. В эксперименте запись заняла 286 секунд, поэтому
не прерывайте её из-за нескольких минут ожидания. Затем:

```powershell
if ((Get-FileHash "$run\spi-android-readback.bin" -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'd0e41c7d20efa0fffa7bf567a337b330038fb17c5d6f4c5502412a711921873c') { throw 'Android SPI readback mismatch' }
'Android SPI verified'
```

## Загрузить и подтвердить Android

Из текущей SPI Firehose сессии:

```powershell
& $edl --memory spinor --loader "$spi\prog_firehose_ddr.elf" reset --mode Reset --delay 1
```

Именно после такого reset подтверждены XBL → UEFI → ядро → интерфейс Android 15.
С подключённым ADB:

```powershell
adb shell getprop ro.build.version.release
adb shell getprop sys.boot_completed
adb shell getprop init.svc.bootanim
```

Получены `15`, `1`, `stopped`, активный HDMI 3840×2160 @ 30 Hz.
Короткое чтение 256 МиБ UFS также прошло. Повторный холодный старт и длительная
стабильность пока не подтверждены; F2FS `/data` осталось 45 ГиБ в большом userdata.

## Вернуть только Android BIOS при установленной системе

После общей подготовки и бэкапа, с Lite прочитайте текущий A:

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
и «Загрузить и подтвердить Android». Они используют проверенные отдельные операции.
Повторный круг Linux → Android с сохранением системы ещё не выполнен;
это не заявляется как отдельный проверенный результат переключения.
