# Radxa Dragon Q6A: BIOS, Linux и Android на UFS Toshiba 512 ГБ

Рабочий маршрут для **Radxa Dragon Q6A с 12 ГБ RAM** и модуля
**TOSHIBA THGJFCT2T84BAKCB, rev 0100, UFS 3.0, 512 ГБ**. Основа — официальный
`Q6A-Android15-spi-ufs-boot-20260630-b1` с исправленной утилитой EDL и изменённым XBL.

Исходный XBL находил UFS и инициализировал DDR, затем останавливался после
`UFS 3.x Device Volt set to 2.5 volt`. Пропуск последовательности
SLEEP → смена напряжения → ACTIVE для наблюдаемого UFS 3.0 позволил загрузить
Android 15 до интерфейса. Исправленный XBL установлен **в UFS и SPI**.

Основные инструкции содержат прямые команды **edl-ng**, выполнявшиеся в
успешном аппаратном сеансе. Для Linux это rawprogram из Linux flat_build;
для Android — запись системы, исправленного UFS XBL и полного Android SPI.
Каждый маршрут описывает свои точные файлы, бэкапы и признаки успеха.

## Выбрать инструкцию

| Задача | Инструкция | Проверенный результат |
| --- | --- | --- |
| Прошить BIOS для Linux с NVMe | [docs/linux-bios.md](linux-bios.md) | Rawprogram прошёл; 18 payload сверены с SPI; Ubuntu запускалась с I2C blacklist |
| Выбрать маршрут BIOS | [docs/bios-profiles.md](bios-profiles.md) | Две отдельные прошивки, с разными загрузочными компонентами |
| Установить Android на этот UFS | [docs/android-ufs.md](android-ufs.md) | Отдельные операции записи и обратного чтения выполнены; Android загрузился после программного reset |
| Получить готовые файлы и проверить их | [docs/artifacts.md](artifacts.md) | Архив и все 119 файлов проверены по SHA-256 |
| Понять или воспроизвести изменение XBL | [docs/xbl-workaround.md](xbl-workaround.md) | 49 изменённых байтов; XBL и полный SPI воспроизводятся с теми же хешами |
| Разобрать ошибку EDL или пустой экран | [docs/troubleshooting.md](troubleshooting.md) | Зафиксированы фактические ошибки и точки остановки |
| Изучить новые скрипты автоматизации | [docs/android-scripted.md](android-scripted.md), [docs/bios-scripted.md](bios-scripted.md) | Проверены без платы; аппаратный прогон ещё не выполнен |

Отдельные операции выше подтверждены журналами и результатом загрузки.
Повторный полный прогон с пустого UFS, цикл переключений, холодный старт Android
и длительная стабильность ещё не подтверждены.
F2FS `/data` остаётся **45 ГиБ** внутри раздела около **444,36 ГиБ**; расширение
в этот маршрут не включено. Это результат для одного проверенного комплекта,
а не подтверждение совместимости всех сторонних UFS 512 ГБ.

**Подпись изменённого XBL недействительна.** Проверенная плата приняла его при
`Secure Boot: Off`. Пакет и установщик сохраняют привязку к проверенной плате;
защиту от другого EDL серийного номера не следует обходить для непроверенного устройства.

## Структура каталога

```text
.
├── README.md                       точка входа
├── docs/                           установка, диагностика, восстановление
├── scripts/
│   ├── Prepare-Bundle.ps1           подключение проверенного пакета файлов
│   ├── Install-Q6A-Android.ps1      установка по стадиям, бэкапы и readback
│   ├── Switch-Q6A-Bios.ps1         Linux / Android: бэкап, SPI и возврат
│   ├── Test-Q6A-Offline.ps1         проверки остановки при ошибках
│   ├── prepare_xbl.py              воспроизводимое создание XBL и SPI
│   └── check_repository.py         целостность и локальные ссылки
├── patches/
│   ├── xbl-ufs30.json              точное описание изменения XBL
│   └── edl-ng-q6a.patch            полный патч edl-ng, включая новые файлы
├── manifests/
│   ├── bundle-lock.json            хеши готового архива и manifest
│   ├── hardware-results.json       результаты аппаратного сеанса
│   ├── direct-route-evidence.json  подтверждения прямых операций
│   ├── linux-bios-files.json       точные файлы Linux BIOS
│   ├── bios-profiles.json          образы, схема SPI и состояние проверки
│   ├── source-checksums.json       хеши файлов этого проекта
│   └── edl-ng-provenance.json       исходный commit и бинарник EDL
├── third_party/edl-ng-LICENSE      лицензия upstream edl-ng
└── artifacts/                      локальные образы и путь к пакету; вне Git
```

Все команды ниже выполняются **из корня этого каталога**. Репозиторий можно
перенести отдельно от исходной рабочей папки. Бинарные файлы прошивки хранятся
в готовом архиве, описанном в [docs/artifacts.md](artifacts.md).

## Начать с проверки

На Windows следуйте [общей подготовке](direct-edl.md): задайте пути,
проверьте точный пакет и сохраните текущий SPI. Затем откройте
[Linux BIOS](linux-bios.md) или [Android на UFS](android-ufs.md).
Аппаратные команды приведены прямо в инструкциях, без установщика-обёртки.
Не настроенный UFS требует отдельного provisioning; работающий модуль повторно
провиженить не нужно. Запись системы на UFS перезаписывает Android и его данные.

Новые `Install-Q6A-Android.ps1` и `Switch-Q6A-Bios.ps1` сохранены отдельно как
разработка. Их проверки без USB не считаются успешной прошивкой на плате.
Источники подтверждений перечислены в
[direct-route-evidence.json](../manifests/direct-route-evidence.json).

## Проверить исходники без платы

```powershell
python .\scripts\check_repository.py
& .\scripts\Test-Q6A-Offline.ps1
```

Готовая установка не требует Python или .NET SDK. Они нужны только для работы
с исходниками и отдельной проверки проекта. Аппаратные результаты сохранены в
[manifests/hardware-results.json](../manifests/hardware-results.json); там явно
разделены успешный запуск и ещё не выполненные проверки.

## Аппаратная документация

- [Radxa Q6A: ресурсы и образы](https://docs.radxa.com/en/dragon/q6a/download)
- [Radxa Q6A: вход в EDL](https://docs.radxa.com/en/dragon/q6a/getting-started/install-system/usb-system/edl-mode)
- [Radxa Q6A: UART](https://docs.radxa.com/en/dragon/q6a/system-config/uart-debug)
- [Официальный каталог Android образов](https://dl.radxa.com/dragon/q6a/images/android/)
- [Upstream edl-ng](https://github.com/strongtz/edl-ng)
