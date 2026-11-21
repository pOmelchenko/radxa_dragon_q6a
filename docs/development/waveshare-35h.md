# Waveshare 3.5inch DSI LCD (H) на Dragon Q6A

Эксперимент для Radxa OS (Linux), платы Q6A V1.21 и дисплея Waveshare
**SKU 33087**. Режим 35H задаёт 480×800 при 60 Гц, RGB888, одну линию DSI
и pixel clock 33,6 МГц. Контроллер касаний Goodix GT911 находится на I²C13.
Сборка модуля arm64 и применение оверлея к штатному DTB проверены для
`6.18.2-3-qcom` и `7.0.11-7-qcom`. Изображение, касания и холодный старт
на физической связке Q6A + 35H ещё предстоит проверить.

## Подключение

Подключайте при выключенном питании через переходник **J10 (39 контактов,
шаг 0,3 мм) → Raspberry Pi DISPLAY (15 контактов)**. Перед включением
сверьте нумерацию и прозвоните переходник. 15-контактные разъёмы на самой
Q6A предназначены для камер. Контакты ниже пронумерованы со стороны
соответствующего разъёма, ориентация шлейфа зависит от переходника.

| Waveshare 15 pin | Сигнал | Q6A J10 по схеме V1.21 |
| --- | --- | --- |
| 1, 4, 7, 10, 13 | GND | Общая земля, например 6, 9, 12, 15, 28 |
| 2, 3 | D1−, D1+ | 10, 11 (пара выведена на разъём, профиль 35H её не использует) |
| 5, 6 | CLK−, CLK+ | 13, 14 |
| 8, 9 | D0−, D0+ | 7, 8 |
| 11, 12 | SCL, SDA | 27, 26 (TP_SCL, TP_SDA, сторона 3,3 В преобразователя U8) |
| 14, 15 | 3,3 В | Например, 30 и 31, оба на VCC_3V3_LCD |

GPIO80 включает питание модуля через U14. По данным Waveshare, потребление
составляет 180 мА при 3,3 В. Контакты J10 для 1,8 В и LED± оставьте
свободными. В 15-pin разъёме нет отдельных INT и RESET. Штатный драйвер
Goodix в обоих ядрах умеет опрашивать контроллер по I²C без IRQ. Управление
яркостью производитель для этой модели не заявляет.

## Файлы для текущего ядра

Команды выполняются на Q6A из корня репозитория. При использовании
готового архива распакуйте его и перейдите в каталог с `artifacts/`.
Сначала определите версию запущенного ядра и каталог файлов.

```sh
k=$(uname -r)
out="$PWD/artifacts/waveshare-35h"
printf '%s\n' "$k"
```

**Готовый комплект.** Проверьте файлы командой `sha256sum -c SHA256SUMS`
из корня распакованного архива. Для установки нужны общий
`q6a-waveshare-35h.dtbo` и модуль `panel-waveshare-35h.ko` из каталога
с точным именем текущего ядра. Перейдите к следующему разделу.

**Сборка из исходников.** [Оверлей, Kbuild и драйвер](../../tools/target/linux/waveshare-35h)
собираются без дерева исходников Linux. Для каждой версии ядра нужны
её заголовки. После обновления ядра повторите сборку и проверку.

```sh
sudo apt install build-essential device-tree-compiler kmod "linux-headers-$k"
src="$PWD/tools/target/linux/waveshare-35h"
mkdir -p "$out/$k"
dtc -@ -I dts -O dtb -o "$out/q6a-waveshare-35h.dtbo" "$src/q6a-waveshare-35h.dts"
make -C "/lib/modules/$k/build" M="$src" MO="$out/$k" modules
```

В пакете Radxa 6.18.2-3 отсутствует OF-привязка `panel-dsi`. В источниках
7.0.11-7 функция `panel_simple_dsi_probe()` разбирает параметры в новый
дескриптор, но `panel->desc` продолжает указывать на пустой дескриптор.
Поэтому используется отдельный модуль с привязкой только к этой модели.
Он читает `panel-timing` из DT и регистрирует режим в DRM. Драйвер
тачскрина входит в оба штатных пакета.

## Пробная загрузка

В Radxa OS R2 параметры ядра и дерево устройств заданы в записи на EFI.
Для испытания подготовьте отдельный пункт меню. Это позволяет вернуться к
рабочей конфигурации, в том числе если через тот же переходник использовался
BTT Pi TFT50. Понадобятся `device-tree-compiler` и `kmod`.

1. Найдите штатную запись текущего ядра. Проверьте, что строки `linux` и
   `devicetree` относятся к нему. Для образов R2 ниже используется
   `/boot/efi` и идентификатор из `/etc/kernel/entry-token`.

   ```sh
   esp=/boot/efi
   token=$(cat /etc/kernel/entry-token)
   entry="$esp/loader/entries/$token-$k.conf"
   findmnt --mountpoint "$esp"
   sudo cat "$entry"
   ```

2. Извлеките путь к базовому DTB из этой записи. Проверьте применимость
   оверлея и версию модуля **до установки**. Успешный `fdtoverlay` завершается
   без вывода. Первое слово в `vermagic` должно точно совпадать с `uname -r`.

   ```sh
   dtb=$(sudo awk '$1 == "devicetree" {print $2}' "$entry")
   dtbo="$(dirname "$dtb")/dtbo/q6a-waveshare-35h.dtbo"
   sudo fdtoverlay -i "$esp$dtb" -o /dev/null "$out/q6a-waveshare-35h.dtbo"
   modinfo -F vermagic "$out/$k/panel-waveshare-35h.ko"
   printf 'Путь для devicetree-overlay: %s\n' "$dtbo"
   ```

3. Установите модуль и DTBO, затем подготовьте копию загрузочной записи
   вне EFI.

   ```sh
   sudo install -Dm644 "$out/$k/panel-waveshare-35h.ko" "/lib/modules/$k/updates/panel-waveshare-35h.ko"
   sudo depmod -a "$k"
   sudo cp "$out/q6a-waveshare-35h.dtbo" "$esp$dtbo"
   trial=$(mktemp)
   sudo cat "$entry" > "$trial"
   nano "$trial"
   ```

   В копии задайте `title Waveshare 35H test`. В конец строки
   `devicetree-overlay` добавьте путь, выведенный на шаге 2. Если строки ещё
   нет, создайте её. Оставьте пути камер и других используемых устройств
   в исходном порядке. Уберите из копии оверлеи другого дисплея DSI
   и питания GPIO80, включая оба `q6a-btt-tft50-*.dtbo` и оверлей
   штатного Raspberry Pi 7-inch, если они включены. Сохраните файл.

4. Проверьте **весь** список из пробной записи и установите её только при
   успешном объединении. Блок выполняется в Bash.

   ```bash
   (
       set -eu
       overlays=()
       while read -r path; do
           overlays+=("$esp$path")
       done < <(awk '$1 == "devicetree-overlay" {for (i=2; i<=NF; i++) print $i}' "$trial")
       printf '%s\n' "${overlays[@]}" | grep -Fx -- "$esp$dtbo"
       sudo fdtoverlay -i "$esp$dtb" -o /dev/null "${overlays[@]}"
       sudo cp "$trial" "$esp/loader/entries/waveshare-35h-$k.conf"
   )
   ```

   Перезагрузите Q6A и выберите **Waveshare 35H test** в меню embloader
   через UART. Для отката выберите штатный пункт. Когда испытание закончено,
   пробную запись можно удалить по имени `waveshare-35h-$k.conf`.

## Проверка на плате

```sh
for d in /sys/class/drm/card*-DSI-*; do
    [ -d "$d" ] && cat "$d/status" "$d/modes"
done
sudo journalctl -b -k | grep -iE 'waveshare|goodix|ae94000|dsi'
ls -l /sys/bus/i2c/devices/*-0014/driver
sudo evtest
```

Ожидаются режим `480x800`, устойчивое изображение, а в `evtest` у
`Goodix Capacitive TouchScreen` — касания и отпускания по четырём углам.
Проверьте их после холодного включения. При необходимости установите
`evtest` одноимённым пакетом.

Для 35H производитель показывает Goodix по адресу `0x14`. В его общем
DTBO указана также альтернатива `0x5d`. Если изображение есть, а GT911
не отвечает, проверьте питание и I²C переходника. При подтверждённом
адресе `0x5d` измените в исходнике оверлея **оба** значения,
`touchscreen@14` → `touchscreen@5d` и `reg = <0x14>` → `reg = <0x5d>`.
Пересоберите DTBO и скопируйте его на место пробного.

## Источники

- [Waveshare 3.5inch DSI LCD (H), распиновка и профиль 35H](https://www.waveshare.com/wiki/3.5inch_DSI_LCD_%28H%29).
  [Оверлей производителя](https://files.waveshare.com/wiki/common/Waveshare_35DSI.dtbo),
  SHA-256 `ae09deaccceb80ced72519977fedc6d7becbd548a3043538c147ad40633b4611`.
  В профиле `35H` действует одна линия по умолчанию. Видимая область
  45,36 × 75,8 мм по [чертежу Waveshare](https://files.waveshare.com/wiki/3.5inch_DSI_LCD_H/3.5_inch_DSI_LCD_H-2D-PDF.pdf).
- [Схема Q6A V1.21](../vendor/radxa-q6a-schematic-v1.21.pdf), печатные листы 6 и 31.
  [Оверлей Radxa для J10](https://github.com/radxa-pkg/radxa-overlays/blob/8fce109f183455d95dc13d6ad7071ab28f55be5f/arch/arm64/boot/dts/qcom/overlays/qcs6490-radxa-dragon-q6a-raspberry-pi-7-inch-touchscreen-2.dtso).
- Базовые DTB и заголовки взяты из пакетов Radxa
  [6.18.2-3](https://github.com/radxa-pkg/linux-qcom/releases/tag/6.18.2-3)
  и [7.0.11-7](https://github.com/radxa-pkg/linux-qcom/releases/tag/7.0.11-7).
  [panel-simple.c в 7.0.11-7](https://github.com/radxa/kernel/blob/a50eb5b71984bd82b49cd5d31b1e2eb5505c6512/drivers/gpu/drm/panel/panel-simple.c)
  и [Goodix с polling](https://github.com/radxa/kernel/blob/a50eb5b71984bd82b49cd5d31b1e2eb5505c6512/drivers/input/touchscreen/goodix.c).
