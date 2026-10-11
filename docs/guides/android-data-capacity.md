# Полный объём /data на Toshiba UFS 512 ГБ

Штатный recovery создаёт `/data` на всём разделе `userdata`: для проверенного
Toshiba `THGJFCT2T84BAKCB` получается **444,36 ГиБ вместо 45 ГиБ**. Разметка UFS
уже содержит раздел нужного размера; менять GPT и повторять provisioning не требуется.
Остальная ёмкость модуля занята другими LUN и разделами Android.

Проверено на Windows, Q6A 12 ГБ и комплекте
`Q6A-Android15-spi-ufs-boot-20260630-b1` с исправленными XBL/SPI из
[руководства установки](android-ufs.md). После сброса проверены загрузка,
выделение 64 ГиБ, запись в конец этого файла, сохранность отдельного файла
после перезагрузки и чтение UFS после простоя.
[Результаты проверки](../reference/validation/android-data-capacity-2026-10-11.json).

**Операция удаляет приложения, настройки, файлы пользователя и ключи шифрования
Android.** Выполняйте её сразу после установки либо после сохранения нужных данных.
Для этой сборки используйте создание новой файловой системы через recovery;
`resize.f2fs` для сохранения существующего зашифрованного `/data` не применяется.

## Проверить установленный Android

Откройте PowerShell в корне репозитория. Укажите установленный Android SDK
Platform-Tools и задайте `$adb` явно:

```powershell
$ErrorActionPreference = 'Stop'
$sdk = 'D:\tools\platform-tools'
$adb = Join-Path $sdk 'adb.exe'
if (-not (Test-Path -LiteralPath $adb -PathType Leaf)) { throw 'adb.exe not found; check the SDK path' }
```

В том же сеансе после установки Android используйте `$run` из
[подготовки](prepare-edl.md). Если открыли новый сеанс, создайте новый каталог
для файлов этой операции; измените `android-data-001`, если он уже существует:

```powershell
$repo = (Get-Location).Path
$run = Join-Path $repo 'runs\android-data-001'
if (Test-Path -LiteralPath $run) { throw 'Choose a new run directory; preserve previous backups.' }
New-Item -ItemType Directory -Path $run | Out-Null
```

В `adb devices` должно быть одно устройство.
Подключите USB к нижнему USB-A порту Q6A; SD и NVMe на время проверки снимите.

```powershell
& $adb devices
& $adb root
Start-Sleep -Seconds 2
& $adb shell getprop ro.build.version.release
& $adb shell cat /sys/block/sda/device/model
& $adb shell blockdev --getsize64 /dev/block/by-name/userdata
& $adb shell df -k /data
```

Ожидаются Android `15`, модель `THGJFCT2T84BAKCB` и раздел
`477124964352` байта. Исходная файловая система занимает `47183872` КиБ.
Если `df` уже показывает `465940300` КиБ, полный объём создан и сброс не нужен.

## Выполнить штатный сброс

Перезагрузите плату в recovery. Дождитесь состояния `recovery` в `adb devices`,
затем включите root. Если плата уже в recovery, начните с `adb root`.

```powershell
& $adb reboot recovery
```

```powershell
& $adb devices
& $adb root
Start-Sleep -Seconds 2
& $adb shell id
```

Ожидается `uid=0(root)`. Подготовьте стандартное сообщение recovery размером
2048 байт. Оно запрашивает `--wipe_data`, который форматирует `userdata` и
`metadata`, затем автоматически запускает Android. Сведения о слотах A/B
расположены за этой областью и проверяются отдельно.

```powershell
$wipeFile = Join-Path $run 'recovery-wipe-data.bin'
$wipe = [byte[]]::new(2048)
$command = [Text.Encoding]::ASCII.GetBytes('boot-recovery')
$options = [Text.Encoding]::ASCII.GetBytes("recovery`n--wipe_data`n--reason=q6a-full-ufs`n")
[Array]::Copy($command,0,$wipe,0,$command.Length)
[Array]::Copy($options,0,$wipe,64,$options.Length)
[IO.File]::WriteAllBytes($wipeFile,$wipe)
if ((Get-FileHash $wipeFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'fe6d0f552357c38027be0b1831b4a06306d287d27f419c9d3c9ae39162f8f64b') { throw 'Unexpected recovery message' }

& $adb shell 'dd if=/dev/block/by-name/misc of=/tmp/q6a-misc-before.bin bs=4096 count=1'
& $adb pull /tmp/q6a-misc-before.bin "$run\misc-before-reset.bin"
& $adb push $wipeFile /tmp/q6a-wipe-data-bcb.bin
& $adb shell 'dd if=/tmp/q6a-wipe-data-bcb.bin of=/dev/block/by-name/misc bs=2048 count=1 conv=fsync'
& $adb shell 'dd if=/dev/block/by-name/misc of=/tmp/q6a-misc-after.bin bs=4096 count=1'
& $adb pull /tmp/q6a-misc-after.bin "$run\misc-after-reset.bin"

$before = [IO.File]::ReadAllBytes("$run\misc-before-reset.bin")
$after = [IO.File]::ReadAllBytes("$run\misc-after-reset.bin")
if ($before.Length -ne 4096 -or $after.Length -ne 4096) { throw 'Incomplete misc readback' }
for ($i = 0; $i -lt 4096; $i++) {
    $expected = if ($i -lt 2048) { $wipe[$i] } else { $before[$i] }
    if ($after[$i] -ne $expected) { throw "misc readback mismatch at byte $i" }
}
& $adb reboot recovery
```

Все команды копирования должны завершиться без ошибок. Проверенный запрос
меняет только первые 2048 байт `misc`; не стирайте весь раздел. Recovery
выполнит сброс без выбора пунктов меню. Первый запуск может занять несколько минут.
BIOS и установленная система сохраняются; Android начинает с чистыми данными.

## Проверить результат

После появления интерфейса Android:

```powershell
& $adb root
Start-Sleep -Seconds 2
& $adb shell getprop sys.boot_completed
& $adb shell getprop init.svc.bootanim
& $adb shell df -k /data
& $adb shell getprop ro.crypto.state
& $adb shell getprop ro.crypto.type
& $adb shell getenforce
& $adb shell bootctl is-slot-marked-successful 0
```

Ожидаются `1`, `stopped`, размер `/data` **465940300 КиБ**,
`encrypted`, `file`, `Enforcing` и успешный слот A (`1`). Это около 444,36 ГиБ
или 477,12 ГБ в десятичных единицах; свободное место зависит от созданных
Android файлов. Повторите проверки после обычной перезагрузки:

```powershell
& $adb reboot
```

Повторная запись исходного `userdata.img` вернёт файловую систему на 45 ГиБ.
После полной переустановки Android эту процедуру выполняют заново.

Формат сообщения и действие `--wipe_data` описаны в исходниках AOSP:
[bootloader message](https://android.googlesource.com/platform/bootable/recovery/+/refs/heads/android15-release/bootloader_message/include/bootloader_message/bootloader_message.h),
[форматирование userdata и metadata](https://android.googlesource.com/platform/bootable/recovery/+/refs/heads/android15-release/install/wipe_data.cpp).
