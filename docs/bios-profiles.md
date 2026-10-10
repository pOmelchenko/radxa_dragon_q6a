# Какой BIOS прошивать

В основном маршруте две прямые реализации:

| Система | Файлы и команда | Результат на плате |
| --- | --- | --- |
| [Linux с NVMe](linux-bios.md) | Linux flat_build, `edl-ng --memory spinor ... rawprogram rawprogram0.xml patch0.xml` | Запись прошла; payload совпали с readback; Ubuntu запускалась с I2C blacklist |
| [Android на Toshiba UFS](android-ufs.md) | Исправленный UFS XBL, затем `edl-ng --memory spinor ... write-sector 0 <patched-spi>` | XBL и SPI совпали с readback; Android 15 запустился после reset |

Для Android сначала нужна установленная система и исправленный XBL в UFS.
Linux команда записывает BIOS; она не устанавливает ОС на NVMe.
Общие пути, точная версия EDL и бэкап: [direct-edl.md](direct-edl.md).

Это зафиксированные операции успешного сеанса. Нового повторного полного
прогона и повторного круга переключений ещё не было. Общего BIOS для обеих ОС
в проекте нет. Официальный Qualcomm GUI не входит в этот рабочий маршрут.

Новые обёртки сохранены как разработка: [bios-scripted.md](bios-scripted.md)
и [android-scripted.md](android-scripted.md). Они проверены без USB, но пока
не получили аппаратного подтверждения. Основные инструкции не требуют их запуска.
