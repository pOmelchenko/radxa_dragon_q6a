# BIOS для Linux и Android

Для двух систем используются отдельные загрузочные прошивки SPI:

| Система | Состав SPI | Рабочая команда и результат |
| --- | --- | --- |
| Linux на SD/NVMe | Linux `flat_build` 260120: XBL с LBA 925, XBL_CONFIG, AOP, TZ, UEFI и другие компоненты | [Rawprogram Linux BIOS](../guides/linux-bios.md); 18 payload совпали с readback, Radxa OS R2 запустилась с обоих носителей |
| Linux на Toshiba UFS | Официальный Linux BIOS 260916 | [Linux на UFS](../guides/linux-ufs.md); запись SPI проверена, в Linux устанавливается настройка питания модуля |
| Android на Toshiba UFS | Android SPI: GPT и исправленный XBL с LBA 6; следующие компоненты — на UFS | [Запись Android SPI](../guides/android-ufs.md#записать-исправленный-android-spi); полный SPI совпал с readback, Android завершил загрузку |

Сначала выберите ОС и подготовьте соответствующие файлы из
[справочника прошивок](firmware-files.md). Команда Linux записывает BIOS в SPI;
система устанавливается отдельно, например по [проверенному маршруту SD](../guides/linux-sd.md).
Android требует установленной системы и исправленного `xbl_a` в UFS.

При переходе к Linux используйте руководство Linux BIOS. Для уже установленного
Android доступна [запись только Android BIOS](../guides/android-ufs.md#вернуть-только-android-bios-при-установленной-системе).
Перед записью сохраняется полный SPI, затем проверяется обратное чтение.

В [bios-profiles.json](../../firmware/bios-profiles.json) перечислены хеши
сохранённых полных SPI-образов. Проверка пакета сверяет эти файлы.
Для Linux основная команда использует rawprogram, а полный снимок сохраняется
как артефакт восстановления.
