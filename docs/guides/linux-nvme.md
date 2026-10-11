# Установка Radxa OS R2 на NVMe через EDL

Установите Ubuntu 24.04 Noble с GNOME на NVMe из Windows, затем обновите
систему штатными пакетами. Путь проверен на Q6A 12 ГБ с KIOXIA
`KBG40ZNS256G` 256 ГБ: запись и полное обратное чтение образа, расширение
корня на весь SSD, доступ по SSH, программная перезагрузка и холодное
включение обновлённой системы. Дополнительные оверлеи не включались.

## Подготовить BIOS и образ

Выполните [подготовку EDL для Linux и бэкап SPI](prepare-edl.md), затем
[запишите Linux BIOS 260120](linux-bios.md). Сохраните переменные
`$repo`, `$edl`, `$bios` и `$run` в том же сеансе PowerShell.

Скачайте
[`radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz`](https://github.com/radxa-build/radxa-dragon-q6a/releases/download/rsdk-r2/radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz).
Проверьте архив, распакуйте через 7-Zip и проверьте полученный `.img`:

```powershell
$compressed = 'D:\firmware\radxa-dragon-q6a_noble_gnome_r2.output_512.img.xz'
python "$repo\tools\q6a.py" verify-linux-image --image $compressed --target nvme
if ($LASTEXITCODE -ne 0) { throw 'Compressed image verification failed' }
# Распакуйте проверенный .xz перед следующей командой.
$image = 'D:\firmware\radxa-dragon-q6a_noble_gnome_r2.output_512.img'
python "$repo\tools\q6a.py" verify-linux-image --image $image --target nvme --uncompressed
if ($LASTEXITCODE -ne 0) { throw 'Raw image verification failed' }
```

Образ занимает 6003352576 байт; столько же нужно для обратного чтения.
SHA-256 распакованного образа:
`6385ad766ca51214aa9e4ce08f3c367430310b27285164b71b143af341d53900`.
Файл с секторами 4096 байт предназначен для UFS.

## Записать NVMe

Обесточьте Q6A, установите NVMe и временно снимите SD/UFS. При нескольких
копиях одного образа совпадают UUID; самостоятельная загрузка проверяется
с единственным носителем. Включите плату в EDL.

Проверьте SSD через Linux DDR программатор, `Nvme`, LUN 0:

```powershell
& $edl --memory Nvme --loader "$bios\prog_firehose_ddr.elf" --loglevel Debug printgpt --lun 0 2>&1 |
    Tee-Object "$run\nvme-before-gpt.txt"
```

В проверенном сеансе определились `KBG40ZNS256G NVMe KIOXIA 256GB`,
`block_size: 512`, `total_blocks: 500118192`, всего 256060514304 байта.
У вашего SSD должны соответствовать модель, размер сектора и ёмкость.
При ошибке связи сначала восстановите EDL.

Следующая команда перезаписывает разметку и систему на NVMe:

```powershell
& $edl --memory Nvme --loader "$bios\prog_firehose_ddr.elf" write-sector 0 $image --lun 0 2>&1 |
    Tee-Object "$run\nvme-edl-flash.txt"
```

Ожидается `Successfully wrote 5725.24 MiB`, без `[ERROR]`.
Проверенная запись заняла 25,73 секунды.

## Проверить запись до первого запуска

Прочитайте обратно все 11725298 записанных секторов:

```powershell
& $edl --memory Nvme --loader "$bios\prog_firehose_ddr.elf" read-sector 0 11725298 "$run\nvme-readback.bin" --lun 0 2>&1 |
    Tee-Object "$run\nvme-edl-readback.txt"
python "$repo\tools\q6a.py" verify-linux-image --image "$run\nvme-readback.bin" --target nvme --uncompressed
if ($LASTEXITCODE -ne 0) { throw 'NVMe readback verification failed' }
```

Ожидается 6003352576 байт с SHA-256 исходного `.img`.
Проверенное обратное чтение заняло 137,51 секунды. Выполняйте сравнение
до первого запуска Ubuntu: работа системы изменяет содержимое SSD.

## Первый вход, обновление и SSH

Обесточьте Q6A, отсоедините USB к ПК, оставьте NVMe единственным носителем.
Подключите HDMI и клавиатуру, включите без EDL. Дождитесь экрана входа
и войдите как `radxa`, пароль `radxa`. Подключите Ethernet или Wi-Fi.

Исходный образ R2 содержит ядро `6.18.2-3-qcom`. Проверенный маршрут NVMe
включает обновление пакетов после входа. В терминале Ubuntu:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo reboot
```

После перезагрузки проверенная система использует:

| Пакет или компонент | Проверенная версия |
| --- | --- |
| Ядро | `7.0.11-7-qcom` |
| `linux-image-radxa-dragon-q6a` | `7.0.11-7` |
| `qcom-iot-defaults` | `1.21` |
| `radxa-overlays-dkms` | `0.2.31` |

Это версии из репозиториев на 10 октября 2026 года. Обновление пакетов
также добавило `clk_ignore_unused` в штатную запись загрузчика.
Вручную менять параметры ядра или включать оверлеи для этого маршрута
не потребовалось. Состав исходного образа и обновлённой системы различается.

На Q6A проверьте `systemctl is-active ssh` и `hostname -I`, затем подключитесь
с Windows: `ssh radxa@<IP-платы>`.

## Проверить установленную систему

В терминале Ubuntu или по SSH:

```bash
uname -r
findmnt /
findmnt /boot/efi
lsblk -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
df -h /
sudo sfdisk --verify /dev/nvme0n1
systemctl is-active graphical.target ssh
systemctl --failed
cat /proc/cmdline
sudo dmesg | grep -iE 'rpmh|soft lockup|I/O error'
```

Корень должен быть на `/dev/nvme0n1p3`, EFI — `/dev/nvme0n1p2`.
Если имя SSD отличается, подставьте его в проверку GPT.
На SSD 256060514304 байта раздел корня расширился до 254953201152 байт,
файловая система — до 250830680064 байт, около 234 ГиБ в `df -h`.
GPT: `No errors detected`; `graphical.target` и SSH: `active`.

Штатно выключите систему через `sudo poweroff`, отключите питание на
10 секунд и включите снова. Повторите проверки и убедитесь, что экран входа
и SSH доступны. В проверенном обновлённом запуске ошибок RPMh, soft lockup
и ввода-вывода NVMe не было. Наблюдения ядра и границы проверки сохранены
в [результатах загрузки](../reference/validation/nvme-boot-2026-10-10.json).

Контрольные суммы записи и полного обратного чтения:
[nvme-image-write-2026-10-10.json](../reference/validation/nvme-image-write-2026-10-10.json).
