# Обновление Radxa OS на SD, NVMe и UFS

Radxa OS R2 на [SD](linux-sd.md), [NVMe](linux-nvme.md) и
[UFS](linux-ufs.md) — один дистрибутив Ubuntu 24.04 Noble с GNOME.
Обновление пакетов и ядра выполняется одинаково в установленной системе.
Различие образов с секторами 512 и 4096 байт относится к записи и разметке
носителя. Для Toshiba UFS дополнительно проверяется настройка питания,
необходимая при загрузке нового ядра.

| Операция | Руководство |
| --- | --- |
| Обновить пакеты и ядро установленной Radxa OS | Эта инструкция |
| Записать загрузочную прошивку в SPI | [Linux BIOS](linux-bios.md); [версию выбирайте по проверенной конфигурации](../reference/boot-firmware.md#выбор-версии-linux-bios) |
| Полностью заменить систему дисковым образом | Установка на [SD](linux-sd.md), [NVMe](linux-nvme.md) или [UFS](linux-ufs.md); запись образа заменяет разметку и данные |
| Установить Android 15 | [Android на UFS](android-ufs.md); это отдельная ОС и отдельный комплект прошивки |

## Подготовить установленную систему

Сначала завершите установку на выбранный носитель и проверьте рабочий стол,
сеть и SSH. Сохраните нужные файлы на другом устройстве. На время проверки
загрузки оставьте один системный носитель: копии одного образа имеют
одинаковые UUID. Для Toshiba UFS сначала установите и проверьте
[постоянную настройку питания](linux-ufs.md#установить-постоянную-настройку-ufs).

Команды выполняются в Bash на Q6A, в терминале Ubuntu или по SSH:

```bash
cat /etc/os-release
uname -r
findmnt /
findmnt /boot/efi
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL
df -h / /boot /boot/efi
dpkg-query -W -f='${Package} ${Version}\n' linux-image-radxa-dragon-q6a qcom-iot-defaults radxa-overlays-dkms
sudo dpkg --audit
systemctl --failed
```

Корень и EFI должны находиться на выбранном носителе; EFI монтируется как
vfat в `/boot/efi`. Сохраните вывод и версию рабочего ядра для сравнения
после обновления. `dpkg --audit` не должен сообщать о незавершённой установке
пакетов. Проверьте свободное место, включая EFI: обновление устанавливает
ядро и initramfs. До проверки нового запуска сохраните файлы и загрузочную
запись прежнего рабочего ядра.

Для Toshiba выполните также
[проверку питания и чтения после простоя](#toshiba-ufs-питание-и-чтение-после-простоя).
Если она не проходит на текущем ядре, сначала восстановите рабочую настройку.

## Обновить через rsetup

[Radxa рекомендует](https://docs.radxa.com/en/dragon/q6a/system-config/system-update)
обновлять Q6A через `rsetup` и предупреждает, что обычный
`apt update && apt upgrade` может привести к неполному обновлению или
проблемам системы. В терминале Q6A:

```bash
sudo rsetup
```

Выберите **System → System Update**, проверьте предложенные изменения
пакетов и дождитесь успешного завершения. При ошибках загрузки пакетов,
настройки ядра, DKMS или initramfs сначала разберите ошибку; к перезагрузке
переходите после её устранения. Если инструмент предлагает перезагрузиться,
отложите её до проверок ниже. Управление BIOS находится в отдельном пункте
Bootloader Management; для обновления пакетов его выбирать не требуется.

После выхода из `rsetup` проверьте:

```bash
sudo dpkg --audit
dpkg-query -W -f='${Package} ${Version}\n' linux-image-radxa-dragon-q6a qcom-iot-defaults radxa-overlays-dkms
ls -1 /boot/vmlinuz-*
sudo grep -H -E '^(title|version|linux|initrd|options) ' /boot/efi/loader/entries/*.conf
```

`dpkg --audit` должен завершиться без сообщений. В записи загрузчика должны
быть пути к установленному ядру и его initramfs. `uname -r` до перезагрузки
показывает прежнее запущенное ядро. Определите версию для следующей загрузки
по установленным файлам и записи загрузчика; версии зависят от текущих
репозиториев. Для Toshiba выполните следующий раздел до перезагрузки.

## Toshiba UFS: проверить initramfs нового ядра

Этот раздел относится к Toshiba `THGJFCT2T84BAKCB rev 0100` на Q6A
с Linux BIOS `260916`. Установленные правило udev, помощник и hook
initramfs должны сохраниться при обновлении. Hook включает помощник в
последующие сборки initramfs; наличие правила и помощника в конкретном
образе проверяется отдельно.

[Установщик настройки](../../tools/target/linux/install-ufs-active-policy.sh)
пересобирает и проверяет initramfs только для `uname -r`. Повторный запуск
установщика сразу после обновления проверит прежнее ядро. Поэтому ниже
версия следующего ядра задаётся явно.

В том же терминале Bash выполните блок целиком. На запрос введите версию
из предыдущего раздела, например `7.0.11-7-qcom`, если установлено именно
это ядро. Подстановка отделяет новое ядро от ещё работающего прежнего:

```bash
(
    set -euo pipefail
    read -r -p 'Версия ядра для следующей загрузки: ' new_kernel
    test -n "$new_kernel"
    test -s "/boot/vmlinuz-$new_kernel"
    test -d "/lib/modules/$new_kernel"
    sudo test -s /etc/udev/rules.d/99-z-q6a-toshiba-ufs-active.rules
    sudo test -x /usr/lib/q6a/ufs-active-policy
    sudo test -x /etc/initramfs-tools/hooks/q6a-ufs-active
    sudo test -s "/boot/initrd.img-$new_kernel"
    sudo update-initramfs -u -k "$new_kernel"
    initrd="/boot/initrd.img-$new_kernel"
    sudo lsinitramfs "$initrd" | grep -Fx 'usr/lib/udev/rules.d/99-z-q6a-toshiba-ufs-active.rules'
    sudo lsinitramfs "$initrd" | grep -Fx 'usr/lib/q6a/ufs-active-policy'
    sudo cmp "$initrd" "/boot/efi/RadxaOS/$new_kernel/initrd.img-$new_kernel"
    printf 'Toshiba UFS initramfs verified: %s\n' "$new_kernel"
)
```

Ожидаются обе строки с путями внутри initramfs и сообщение
`Toshiba UFS initramfs verified` с выбранной версией. `cmp` при совпадении
ничего не выводит. Убедитесь, что запись следующей загрузки использует
проверенную копию initramfs на EFI. При отсутствии файлов, изменении
их расположения или несовпадении копий сначала восстановите настройку
и установку загрузочных файлов; не переходите к загрузке нового ядра.

## Перезагрузить и проверить систему

После успешных проверок:

```bash
sudo reboot
```

Дождитесь экрана входа и снова подключитесь по SSH. Проверьте:

```bash
uname -r
findmnt /
findmnt /boot/efi
df -h /
systemctl is-active graphical.target ssh
systemctl --failed
cat /proc/cmdline
sudo journalctl -b -k --no-pager | grep -iE 'I/O error|Kernel panic|soft lockup|Error sending AMC RPMH|ufshcd.*(timed.out|failed|eh_fatal|OCS invalid|force_reset)'
```

Версия `uname -r` должна соответствовать выбранному ядру, а корень и EFI —
прежнему системному носителю. Рабочий стол и SSH должны быть доступны,
службы — `active`. Сравните неработающие службы с выводом до обновления.
Последняя команда не должна находить перечисленные ошибки; отсутствие
совпадений даёт код выхода `grep` 1. Для Toshiba повторите проверку ниже.

Затем выполните `sudo poweroff`, дождитесь выключения, отключите питание
и USB к ПК на десять секунд. Включите без EDL и повторите проверки.
Для Toshiba выполните два холодных включения с проверкой питания и чтения
после каждого. Эти проверки оценивают обновлённую систему на вашем носителе.

## Toshiba UFS: питание и чтение после простоя

Выполняйте блок до обновления, после обычной перезагрузки и после каждого
холодного включения. Он определяет UFS LUN 0 по устройству корневого раздела,
проверяет модель и только читает накопитель. Имя `/dev/sda` не фиксируется.

```bash
(
    set -euo pipefail
    c=/sys/bus/platform/devices/1d84000.ufshc
    root_device=$(readlink -f "$(findmnt -n -o SOURCE /)")
    disk=$(lsblk -dn -o PKNAME "$root_device")
    test -n "$disk"
    disk_sysfs=$(readlink -f "/sys/class/block/$disk/device")
    case "$disk_sysfs" in
        */1d84000.ufshc/host*/target*/*:0) ;;
        *) echo 'Root filesystem must be on UFS LUN 0' >&2; exit 1 ;;
    esac
    test "$(tr -d '[:space:]' < "$disk_sysfs/vendor")" = TOSHIBA
    test "$(tr -d '[:space:]' < "$disk_sysfs/model")" = THGJFCT2T84BAKCB
    test "$(cat "$c/power/control")" = on
    test "$(cat "$c/power/runtime_status")" = active
    for a in rpm_lvl spm_lvl auto_hibern8 clkgate_enable; do
        test "$(cat "$c/$a")" = 0
    done
    for p in "$c"/host*/target*/*/power/control; do
        test "$(cat "$p")" = on
    done
    boot_before=$(cat /proc/sys/kernel/random/boot_id)
    sudo -v
    sleep 45
    test "$(cat "$c/power/runtime_status")" = active
    sudo timeout 30s dd if="/dev/$disk" of=/dev/null bs=1M count=4096 iflag=direct status=progress
    test "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_before"
    printf 'Toshiba UFS active policy and 4 GiB read verified\n'
)
```

Ожидается чтение 4294967296 байт, `4096+0 records in/out` и последнее
сообщение `verified`. При ошибке блока оно не выводится. Затем проверьте
журнал ядра командой из предыдущего раздела: тайм-аутов UFS, сбросов,
ошибок ввода-вывода и перезапуска системы за время чтения быть не должно.
Значения питания соответствуют
[ABI драйвера UFS](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-driver-ufs).

## Сохранённые результаты проверки

Общий способ обновления применим к трём носителям; аппаратные результаты
фиксируют конкретные версии и конфигурации:

| Носитель | Опубликованный результат |
| --- | --- |
| SD | [Исходное ядро R2 `6.18.2-3-qcom`, рабочий стол и SSH](../reference/validation/sd-boot-2026-10-10.json); отдельный прогон обновления не зафиксирован |
| NVMe | [APT-обновление, ядро `7.0.11-7-qcom`, обычная перезагрузка и холодный запуск](../reference/validation/nvme-boot-2026-10-10.json) |
| Toshiba UFS | [BIOS `260916`, исходное ядро `6.18.2-3-qcom` и настройка питания](../reference/validation/ufs-boot-2026-10-10.json); проверка нового ядра с этой окончательной настройкой не зафиксирована |

В успешном сеансе NVMe 10 октября 2026 года использовались
`sudo apt update` и `sudo apt upgrade -y`. После перезагрузки были установлены:

| Пакет или компонент | Проверенная версия |
| --- | --- |
| Ядро | `7.0.11-7-qcom` |
| `linux-image-radxa-dragon-q6a` | `7.0.11-7` |
| `qcom-iot-defaults` | `1.21` |
| `radxa-overlays-dkms` | `0.2.31` |

Обновлённые пакеты добавили `clk_ignore_unused` в запись загрузчика;
ручная правка параметров ядра и включение дополнительных оверлеев не
потребовались. Это результат того APT-сеанса. Рекомендуемый здесь маршрут
через `rsetup` следует документации Radxa; его полный аппаратный прогон
и проверки нового ядра Toshiba из этой инструкции ещё не зафиксированы.
