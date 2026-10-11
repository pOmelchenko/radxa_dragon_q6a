# Установка Radxa OS R2 на Toshiba UFS через EDL

Запишите Ubuntu 24.04 Noble с GNOME на UFS из Windows. Проверенная
конфигурация: Q6A 12 ГБ, Toshiba `THGJFCT2T84BAKCB rev 0100`, Linux BIOS
`260916`, Radxa OS R2 с ядром `6.18.2-3-qcom`. Дополнительные оверлеи
не включаются. Для этого модуля устанавливается настройка, которая сохраняет
контроллер UFS и его логические устройства активными, отключая переходы
в энергосберегающие состояния. Она увеличивает расход энергии в простое.

Проверены полное обратное чтение записанного образа, рабочий стол, SSH,
обычная перезагрузка и два холодных включения. На каждом повторном запуске
выполнено прямое чтение 4 ГиБ после 45 секунд простоя.

Нужны питание, HDMI, клавиатура, сеть и [UART](../reference/hardware.md).
UART используется для настройки первого запуска; следующие загрузки
проходят автоматически. На время установки снимите SD и NVMe.

## Подготовить BIOS и образ

Выполните [подготовку EDL и бэкап SPI](prepare-edl.md), затем
[запишите Linux BIOS **260916**](linux-bios.md#набор-260916).
Сохраните переменные `$repo`, `$edl`, `$bios` и `$run` в PowerShell.
Файлы BIOS проверяются по закреплённому коммиту Radxa.

Скачайте
[`radxa-dragon-q6a_noble_gnome_r2.output_4096.img.xz`](https://github.com/radxa-build/radxa-dragon-q6a/releases/download/rsdk-r2/radxa-dragon-q6a_noble_gnome_r2.output_4096.img.xz).
Для UFS нужен именно образ с секторами **4096 байт**.

```powershell
$compressed = 'D:\firmware\radxa-dragon-q6a_noble_gnome_r2.output_4096.img.xz'
python "$repo\tools\q6a.py" verify-linux-image --image $compressed --target ufs
if ($LASTEXITCODE -ne 0) { throw 'Compressed image verification failed' }
```

Распакуйте `.xz`, например через 7-Zip. Образ занимает 10737418240 байт;
потребуется ещё столько же места для полного обратного чтения.

```powershell
$image = 'D:\firmware\radxa-dragon-q6a_noble_gnome_r2.output_4096.img'
python "$repo\tools\q6a.py" verify-linux-image --image $image --target ufs --uncompressed
if ($LASTEXITCODE -ne 0) { throw 'Raw image verification failed' }
```

SHA-256 распакованного образа:
`0295d2a4cc5aa9a68c6d098cb9db740e1b28c5337ddaf8266d92ac07bf47bc41`.

## Записать UFS и проверить содержимое

После записи SPI обесточьте плату и вновь войдите в EDL. Загрузите
**Lite программатор из набора Linux BIOS 260916**. В журнале должна появиться
загрузка этого ELF через Sahara: параметр `--loader` не заменяет уже
работающий Firehose. Используйте payload 16384.

```powershell
& $edl --memory Ufs --maxpayload 16384 --loader "$bios\prog_firehose_lite.elf" --loglevel Debug printgpt --lun 0 2>&1 |
    Tee-Object "$run\ufs-before-gpt.txt"
```

Проверьте модель `TOSHIBA THGJFCT2T84BAKCB0100`, размер блока 4096 и
ёмкость LUN 0: 121268224 блока, 496714645504 байта. Проверенный модуль
уже имел восемь LUN и Boot LUN 1 после установки Android; эта конфигурация
сохраняется. Provisioning здесь не выполняется. Модуль с другой конфигурацией
требует отдельной проверки.

Следующая команда заменяет разметку и данные **LUN 0**:

```powershell
& $edl --memory Ufs --maxpayload 16384 --loader "$bios\prog_firehose_lite.elf" write-sector 0 $image --lun 0 2>&1 |
    Tee-Object "$run\ufs-edl-flash.txt"
```

Ожидается запись 10240 МиБ без `[ERROR]`, NAK и тайм-аутов.
В проверенном сеансе запись заняла около 5 минут 21 секунды.

До первого запуска ОС прочитайте все 2621440 записанных секторов:

```powershell
& $edl --memory Ufs --maxpayload 16384 --loader "$bios\prog_firehose_lite.elf" read-sector 0 2621440 "$run\ufs-readback.bin" --lun 0 2>&1 |
    Tee-Object "$run\ufs-edl-readback.txt"
python "$repo\tools\q6a.py" verify-linux-image --image "$run\ufs-readback.bin" --target ufs --uncompressed
if ($LASTEXITCODE -ne 0) { throw 'UFS readback verification failed' }
```

Файл должен иметь размер 10737418240 байт и SHA-256 исходного `.img`.
Обратное чтение заняло около 4 минут 36 секунд.

## Настроить первый запуск

Обесточьте Q6A, отсоедините USB к ПК и включите без EDL, оставив только
UFS. UART и HDMI подключены. В штатном embloader **0.4** выберите `1`
в `Select an option`, затем `y` в `Edit bootargs? (y/n):`.
Меню ждёт ввод три секунды.

Редактор уже содержит исходные параметры. Допишите в конец и нажмите Enter:

```text
 console=ttyMSM0,115200n8 init=/bin/bash
```

Параметры действуют на один запуск. После появления root-консоли в UART
выполните настройку питания и продолжите загрузку:

```bash
c=/sys/bus/platform/devices/1d84000.ufshc
echo on > "$c/power/control"
for p in "$c"/host*/target*/*/power/control; do echo on > "$p"; done
for a in rpm_lvl spm_lvl auto_hibern8 clkgate_enable; do echo 0 > "$c/$a"; done
exec /sbin/init
```

Войдите как `radxa` с паролем `radxa`, подключите сеть. В проверенном R2
OpenSSH уже установлен; включите сервер:

```bash
sudo systemctl enable --now ssh
systemctl is-active ssh
hostname -I
```

Ожидается `active`. До установки постоянной настройки оставьте плату
включённой. Этот маршрут сохраняет исходное ядро R2; `apt upgrade` в него
не входит.

## Установить постоянную настройку UFS

На Windows укажите полученный IP и скопируйте скрипт из репозитория:

```powershell
$board = '192.168.1.67'
scp "$repo\tools\target\linux\install-ufs-active-policy.sh" "radxa@${board}:/home/radxa/install-ufs-active-policy.sh"
if ($LASTEXITCODE -ne 0) { throw 'Policy upload failed' }
ssh -t "radxa@$board" 'sudo bash /home/radxa/install-ufs-active-policy.sh'
if ($LASTEXITCODE -ne 0) { throw 'Policy installation failed' }
```

[Скрипт](../../tools/target/linux/install-ufs-active-policy.sh) проверяет,
что корень находится на UFS LUN 0 и обнаружена нужная модель. Он устанавливает
правило udev, вспомогательную команду и hook initramfs, применяет настройку,
пересобирает initramfs текущего ядра и сравнивает его с копией на EFI.
Правило проверяет сохранённые SCSI vendor/model после обнаружения LUN.
Повторное выполнение допускается при совпадении установленных файлов.

Значения параметров питания описаны в
[ABI драйвера UFS Linux](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-driver-ufs):
уровень `0` оставляет устройство и линию связи активными, нулевые
`auto_hibern8` и `clkgate_enable` отключают соответствующие механизмы.

Ожидается `UFS active policy installation verified`. Изменение требуется
для этого Toshiba; с другими моделями скрипт прекращает работу.

## Проверить обычную загрузку и ёмкость

Выполните `sudo reboot`. Меню должно загрузить Ubuntu автоматически.
Временных `init=/bin/bash` и дополнительного последнего `console` больше нет.
BIOS 260916 сам добавляет `clk_ignore_unused` к штатной строке ядра.

```bash
uname -r
cat /proc/cmdline
findmnt /
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
df -h /
c=/sys/bus/platform/devices/1d84000.ufshc
for a in power/control power/runtime_status rpm_lvl spm_lvl auto_hibern8 clkgate_enable; do
    printf '%s: ' "$a"; cat "$c/$a"
done
```

Ожидаются ядро `6.18.2-3-qcom`, корень на третьем разделе UFS LUN 0,
EFI на втором, `power/control: on`, `power/runtime_status: active` и
четыре значения `0`. Буква `/dev/sd…` зависит от порядка обнаружения LUN.
Корневая файловая система расширяется автоматически: в проверенной
конфигурации 487458680832 байта, примерно 454 ГиБ.

Для проверки холодного запуска сначала выполните `sudo poweroff`, дождитесь
выключения, отключите питание на десять секунд и включите без EDL.
Проверьте экран входа и SSH. Результаты записи и аппаратных проверок
приведены в [справочнике решений](../reference/validation/README.md).
