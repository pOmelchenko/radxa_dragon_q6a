# Android 15 на Toshiba UFS 512 ГБ

**Разработка: команды новых обёрток ещё не проверены на плате.**
Основной маршрут: [прямой Linux](linux-bios.md) и [прямой Android](android-ufs.md).

Этот порядок воспроизводит операции, которые дали рабочий Android на Q6A
с 12 ГБ RAM и `THGJFCT2T84BAKCB 0100`. Новый скрипт объединяет их в стадии,
но полный повторный прогон через него пока не выполнялся.

## Перед установкой

1. Подключите и проверьте [готовый пакет](artifacts.md).
2. Сохраните нужные данные Android. `FlashUfs` перезаписывает систему и userdata.
   Бэкапы скрипта сохраняют SPI и XBL, а не весь Android.
3. Отключите SD и NVMe на время проверки загрузки Android.
4. Подключите HDMI, клавиатуру и UART с логированием всего запуска.
5. Подключите отдельное питание 12 В 3 А и USB к ПК через **нижний USB A OTG порт**.

Для EDL удерживайте кнопку EDL до подачи питания, подайте питание и отпустите
кнопку. Windows должна показать `Qualcomm HS-USB QDLoader 9008`.
Номер COM может меняться; установщик выбирает устройство по USB ID и проверяет
EDL серийный номер. Порядок и порт описаны в [инструкции Radxa](https://docs.radxa.com/en/dragon/q6a/getting-started/install-system/usb-system/edl-mode).

Для записи откройте PowerShell от администратора. Команды выполняются из корня
репозитория. Путь к пакету сохранён стадией Prepare-Bundle; при необходимости
каждой команде можно передать `-Bundle 'D:\firmware\Q6A-Android15-UFS-Toshiba-512'`.

## Уже настроенный UFS

Для модуля из рабочего сеанса **не повторяйте provisioning**. Сначала выполните:

```powershell
$run = 'reinstall-001'
& .\scripts\Install-Q6A-Android.ps1 -Stage Check
& .\scripts\Install-Q6A-Android.ps1 -Stage BackupSpi -RunId $run
```

Ожидаются `CHECK PASSED` и `SAVED: full pre-installation SPI`.
Все дальнейшие стадии используют тот же RunId. Для другой установки выберите
новый RunId; старые бэкапы не перезаписываются.

Выполняйте следующие команды **по одной**. Если команда завершилась с ошибкой,
не запускайте следующую строку.

```powershell
& .\scripts\Install-Q6A-Android.ps1 -Stage FlashUfs -RunId $run
```

FlashUfs использует Lite программатор, payload 16384 и ровно эти XML:
`rawprogram_unsparse0.xml`, `patch0.xml`, затем пары `rawprogram1.xml`/`patch1.xml`
до `rawprogram5.xml`/`patch5.xml`. Все упомянутые в них образы входят в пакет.
Успех — `'rawprogram' command finished successfully` без ERROR.

```powershell
& .\scripts\Install-Q6A-Android.ps1 -Stage PatchUfs -RunId $run
```

PatchUfs сохраняет полный `xbl_a` на LUN 1 и `xbl_b` на LUN 2. Исходный `xbl_a`
должен начинаться с оригинального XBL из этой прошивки. `xbl_b` должен быть
нулевым, как в проверенном сеансе и официальном XML без образа B слота.
Скрипт заменяет только содержимое XBL в A слоте, сохраняет хвост раздела и
сравнивает SHA-256 полного обратного чтения. Успех — `VERIFIED: full UFS xbl_a`.

```powershell
& .\scripts\Install-Q6A-Android.ps1 -Stage FlashSpi -RunId $run
```

FlashSpi сначала заново читает XBL **с платы** и проверяет наличие исправления.
Затем через DDR программатор записывает полный исправленный SPI образ,
8192 сектора по 4096 байт, и проверяет все 32 МиБ обратным чтением.
В аппаратном сеансе запись заняла около пяти минут. Успех —
`VERIFIED: full 32 MiB Android SPI`.

```powershell
& .\scripts\Install-Q6A-Android.ps1 -Stage Boot -RunId $run
```

Boot требует проверенного SPI readback, заново проверяет полный SPI с платы
и отправляет обычный reset.
Не запускайте обычный rawprogram после PatchUfs: он вернёт исходный XBL.

## Не настроенный UFS

Provisioning меняет конфигурацию аппаратных LUN. Этот шаг нужен только при
подтверждённом отсутствии нужной конфигурации. Для уже работающего модуля выше
он не нужен.

После BackupSpi, перед FlashUfs:

```powershell
& .\scripts\Install-Q6A-Android.ps1 -Stage Provision -RunId $run
```

Успех — `All 10/10 commands sent and ACKed successfully`, включая последний
`<ufs LUNtoGrow="0" commit="1"/>`. ACK первых девяти команд не означает успех.
После commit полностью снимите питание на 10 секунд, снова войдите в EDL,
затем выполните FlashUfs → PatchUfs → FlashSpi → Boot.

Сохранённый `provision_ufs31.xml` успешно применялся через исправленный edl-ng
и Lite. Имя XML не меняет версию чипа: Toshiba сообщает `0x0300`, UFS 3.0.
Конфигурация использует Boot LUN 1, LUN 4 на 6 ГиБ, LUN 6 и 7 по 4 ГиБ;
остальная ёмкость отдаётся LUN 0. Новый единый прогон первичной установки с
таким циклом питания ещё не проверен.

## Что проверяет установщик

Перед любой аппаратной стадией проверяются SHA-256 и размеры всех 119 файлов
пакета. Серийный номер EDL должен совпадать с проверенным комплектом; при двух
EDL устройствах работа прекращается. ERROR в логе считается ошибкой даже при
нулевом коде выхода edl-ng. Неполное чтение, неверный XBL или несовпавший readback
останавливают стадию.

Параметр `--loader` не заменяет уже работающий Firehose. Установщик перед
сменой программатора возвращает плату в новый Sahara через `reset --mode Edl`.
Для UFS нужен Lite с `--maxpayload 16384`, для SPI — DDR. При тайм-ауте
вручную восстановите EDL и повторите только остановившуюся стадию.

Логи и бэкапы находятся в `runs/<RunId>` **внутри пакета**, а не в Git.
Если PowerShell закрыт, снова задайте `$run` с прежним значением.

## Подтверждение загрузки

В UART после DDR должны пройти APDP, AOP, QSEE, APPSBL, `UEFI Start`,
`Booting from slot (_a)` и `Booting Linux`. На исправленном пути для этого
UFS 3.0 сообщение переключения на 2,5 В пропускается.
Появление ядра ещё не подтверждает завершение Android.

Используйте [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools):

```powershell
adb devices -l
# Подставьте serial из adb devices, если подключено больше одного устройства.
adb shell getprop ro.build.version.release
adb shell getprop sys.boot_completed
adb shell getprop init.svc.bootanim
```

Ожидаются `15`, `1`, `stopped` и интерфейс на HDMI мониторе.
EDL serial и Android ADB serial отличаются; это само по себе не ошибка.

После программной перезагрузки отдельно проверьте холодный старт: штатно
выключите Android, полностью снимите питание на 10 секунд и включите без EDL.
Сохраните UART. Этот тест пока не подтверждён в записанном результате.

## Ёмкость и Ethernet

Готовая F2FS имеет размер 45 ГиБ, хотя раздел userdata занимает примерно
444,36 ГиБ. Поэтому установка пока не использует всю ёмкость 512 ГБ модуля.
Проверенного расширения зашифрованного `/data` нет; форматирование или resize
работающей системы в этот маршрут не входят.

В этой сборке не найден штатный редактор статического IP Ethernet;
`cmd ethernet` отвечает `No shell command implementation`.
Это отдельная задача настройки уже запущенной ОС.

При ошибке используйте [диагностику](troubleshooting.md), для возврата BIOS —
[восстановление](linux-recovery.md).
