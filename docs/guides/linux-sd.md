# Установка Radxa OS R2 на SD через EDL

Запишите штатный образ Ubuntu 24.04 Noble с GNOME на microSD из Windows.
Путь проверен на Q6A 12 ГБ с картой 32 ГБ: запись через EDL, полное обратное
чтение записанного образа, запуск рабочего стола после подачи питания,
автоматическое расширение корневого раздела и доступ по SSH после установки
сервера. Дополнительные оверлеи для этого запуска не включались.

## Подготовить BIOS и образ

Выполните [общую подготовку EDL и бэкап SPI](prepare-edl.md).
[Выбор версии и получение Linux BIOS](prepare-edl.md#linux) общие для всех
носителей; затем [запишите выбранный BIOS в SPI](linux-bios.md).
Сохраните `$repo`, `$edl`, `$bios` и `$run` в том же сеансе PowerShell.

Скачайте образ
[`radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz`](https://github.com/radxa-build/radxa-dragon-q6a/releases/download/rsdk-r2/radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz)
и проверьте его перед распаковкой:

```powershell
$compressed = 'D:\firmware\radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz'
python "$repo\tools\q6a.py" verify-linux-image --image $compressed --target sd
if ($LASTEXITCODE -ne 0) { throw 'Compressed image verification failed' }
```

Распакуйте `.xz`, например через 7-Zip. Полученный `.img` занимает
6003352576 байт. На ПК нужно место для распакованного образа и такого же
по размеру файла обратного чтения. Проверьте распакованный файл:

```powershell
$image = 'D:\firmware\radxa-dragon-q6a_noble_gnome_r2.output_512.img'
python "$repo\tools\q6a.py" verify-linux-image --image $image --target sd --uncompressed
if ($LASTEXITCODE -ne 0) { throw 'Raw image verification failed' }
```

Ожидаемый SHA-256:
`6385ad766ca51214aa9e4ce08f3c367430310b27285164b71b143af341d53900`.
Версии, ссылки и суммы закреплены в [справочнике файлов](../reference/firmware-files.md).

## Записать карту

Обесточьте Q6A, установите SD и временно снимите NVMe/UFS. Это позволит
проверить самостоятельную загрузку с карты. Вновь включите плату в EDL.
Карта находится в самой Q6A; кардридер на ПК не нужен.

Проверьте, что программатор обращается к SD: `Sdcc`, **слот 1**, LUN 0.
Слот 0 относится к eMMC.

```powershell
& $edl --memory Sdcc --slot 1 --loader "$bios\prog_firehose_ddr.elf" --loglevel Debug printgpt --lun 0 2>&1 |
    Tee-Object "$run\sd-before-gpt.txt"
```

Для проверенной карты информация о носителе показала `block_size: 512`,
`total_blocks: 61071360`, то есть 31268536320 байт. У другой карты ёмкость
будет отличаться. Не начинайте запись при ошибке связи или неверном слоте.

Следующая команда перезаписывает разметку и систему на SD:

```powershell
& $edl --memory Sdcc --slot 1 --loader "$bios\prog_firehose_ddr.elf" write-sector 0 $image --lun 0 2>&1 |
    Tee-Object "$run\sd-edl-flash.txt"
```

Ожидается `Successfully wrote 5725.24 MiB`, без `[ERROR]`.
В проверенном сеансе запись заняла около 7 минут 37 секунд.

## Проверить запись до первого запуска

Прочитайте обратно все 11725298 записанных секторов:

```powershell
& $edl --memory Sdcc --slot 1 --loader "$bios\prog_firehose_ddr.elf" read-sector 0 11725298 "$run\sd-readback.bin" --lun 0 2>&1 |
    Tee-Object "$run\sd-edl-readback.txt"
python "$repo\tools\q6a.py" verify-linux-image --image "$run\sd-readback.bin" --target sd --uncompressed
if ($LASTEXITCODE -ne 0) { throw 'SD readback verification failed' }
```

Ожидается файл 6003352576 байт с тем же SHA-256, что у `.img`.
Обратное чтение проверенного сеанса заняло около 4 минут 26 секунд.
После первого запуска ОС содержимое карты меняется, поэтому это сравнение
выполняется до загрузки Ubuntu.

## Первый вход и сеть

Обесточьте плату и отсоедините USB к ПК. Подключите HDMI, клавиатуру
и Ethernet либо используйте Wi-Fi после входа. Включите без кнопки EDL.
Оставьте SD единственным накопителем на время проверки.

Дождитесь экрана входа Ubuntu. В проверенном запуске использовалась
учётная запись `radxa` с паролем `radxa`; рабочий стол открылся, Wi-Fi подключился.
Штатная запись systemd-boot запускает ядро `6.18.2-3-qcom`.

Подключите Ethernet или Wi-Fi и убедитесь, что интернет доступен для установки
пакетов. Для дальнейшей работы с ПК установите сервер SSH в терминале самой Q6A:

```bash
sudo apt update && sudo apt install -y openssh-server && sudo systemctl enable --now ssh
systemctl is-active ssh
hostname -I
```

Ожидается `active` и адрес платы в вашей сети. Установка пакета описана
в [документации Ubuntu](https://ubuntu.com/server/docs/openssh-server/).
В PowerShell подключитесь к адресу из `hostname -I`:

```powershell
ssh radxa@<IP-платы>
```

## Проверить систему

В терминале Ubuntu или по SSH:

```bash
uname -r
findmnt /
lsblk -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
df -h /
sudo sfdisk --verify /dev/mmcblk1
systemctl is-active graphical.target ssh
systemctl --failed
cat /proc/cmdline
```

Корень `/` должен находиться на разделе `mmcblk…p3` установленной SD,
ядро — `6.18.2-3-qcom`. В проверенной конфигурации карта определилась как
`/dev/mmcblk1`, EFI раздел — `/dev/mmcblk1p2`, корень — `/dev/mmcblk1p3`.
Если имя карты отличается, подставьте его в команду проверки GPT.

На карте 31268536320 байт корневой раздел автоматически расширился
до 30161223168 байт; файловая система — 29575102464 байт, около 28 ГиБ
в `df -h`. Перенос GPT в конец карты проверен `sfdisk`: `No errors detected`.
Службы `graphical.target` и `ssh` показывают `active`, SSH включён при загрузке.
Параметры ядра совпадают с исходной записью загрузчика, активных дополнительных
оверлеев нет.

После проверки установки обновляйте пакеты и ядро по
[общей инструкции Radxa OS для SD, NVMe и UFS](linux-update.md).
Указанные выше версия ядра и параметры относятся к исходному R2;
после обновления используйте проверки и ожидаемую версию из общей инструкции.

Контрольные суммы записи и полного обратного чтения:
[sd-image-write-2026-10-10.json](../reference/validation/sd-image-write-2026-10-10.json).
Результат первого запуска и проверки системы:
[sd-boot-2026-10-10.json](../reference/validation/sd-boot-2026-10-10.json).
