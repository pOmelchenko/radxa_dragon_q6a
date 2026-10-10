# Windows-автоматизация

Прототипы находятся в `tools/windows/experimental/`. Они используют общий
закреплённый комплект прошивки и Windows QDLoader. Аппаратные руководства
остаются [Linux BIOS](../guides/linux-bios.md) и [Android UFS](../guides/android-ufs.md).

## Точки входа

| Скрипт | Назначение |
| --- | --- |
| [Prepare-Bundle.ps1](../../tools/windows/experimental/Prepare-Bundle.ps1) | Проверить каталог комплекта либо распаковать точный ZIP; сохранить путь локально |
| [Install-Q6A-Android.ps1](../../tools/windows/experimental/Install-Q6A-Android.ps1) | Выполнить выбранную стадию: бэкап, запись, readback, reset или восстановление |
| [Switch-Q6A-Bios.ps1](../../tools/windows/experimental/Switch-Q6A-Bios.ps1) | Составить последовательность операций только с SPI для выбранного профиля |

По умолчанию выполняется `Check`, без USB. Для аппаратных стадий требуется
явный `Stage`/`Action`, `RunId` и совпадение EDL serial с проверенной платой.
Проверки без устройства проходят в CI; полный аппаратный прогон этих обёрток
является условием перевода автоматизации в основной маршрут.

## Проверка комплекта

```powershell
& .\tools\windows\experimental\Prepare-Bundle.ps1 -Source 'D:\firmware\Q6A-Android15-UFS-Toshiba-512'
& .\tools\windows\experimental\Install-Q6A-Android.ps1 -Stage Check
& .\tools\windows\experimental\Switch-Q6A-Bios.ps1 -Profile Linux -Action Check
```

Для общих проверок на других ОС используется [Python CLI](host-tools.md).

## Контракт стадий

| Стадия | Назначение |
| --- | --- |
| `BackupSpi` | Сохранить полный SPI 32 МиБ и SHA-256 |
| `Provision` | Настроить LUN; отдельная операция для неподготовленного модуля |
| `FlashUfs` | Записать Android rawprogram/patch |
| `PatchUfs` | Сохранить XBL, записать исправленный `xbl_a`, проверить readback |
| `FlashSpi` | Записать исправленный Android SPI и проверить readback |
| `Boot`, `BootLinux` | Проверить текущий SPI с платы перед reset |
| `RestoreSpi` | Вернуть SPI из бэкапа конкретного RunId |
| `RestoreUfs` | Вернуть сохранённый `xbl_a`; остальные данные UFS не восстанавливаются |
| `RecoveryLinux` | Записать сохранённый Linux SPI-снимок |

`Switch-Q6A-Bios.ps1 -Action Flash` сначала сохраняет SPI, затем вызывает
`RecoveryLinux` либо `FlashSpi`. Для каждой записи нужен новый RunId;
`Boot` и `Restore` используют запись того же профиля. Android SPI требует
уже установленного исправленного UFS XBL. Этот интерфейс не вызывает
provisioning или переустановку Android.

Для Linux аппаратно проверенный путь записывает **rawprogram**. Запись полного
Linux-снимка через `RecoveryLinux` требует отдельной аппаратной проверки.
Снимок включает сохранённую конфигурацию UEFI конкретной платы.

## Проверки без устройства

```powershell
& .\tests\windows\Test-Q6A-Offline.ps1
```

Проверяются остановка после ошибки EDL, неполное чтение, неправильный хеш
и serial, бэкап перед записью SPI, уникальность RunId и запрет UFS-стадий
в интерфейсе переключения BIOS. Перед reset заново проверяется SPI с платы.
