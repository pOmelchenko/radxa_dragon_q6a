# Radxa Dragon Q6A

Практическая документация для Radxa Dragon Q6A: установка ОС, загрузочная
прошивка, аппаратные интерфейсы и инструменты подготовки файлов.
Репозиторий дополняет официальные руководства воспроизводимыми решениями,
проверенными на плате.

## Начать работу

| Задача | Руководство |
| --- | --- |
| Подготовить Windows, файлы прошивки и EDL | [Подготовка к прошивке](docs/guides/prepare-edl.md) |
| Записать BIOS для Linux | [Linux BIOS](docs/guides/linux-bios.md) |
| Установить штатную Ubuntu на SD из Windows | [Radxa OS R2 на SD](docs/guides/linux-sd.md) |
| Установить и обновить Ubuntu на NVMe из Windows | [Radxa OS R2 на NVMe](docs/guides/linux-nvme.md) |
| Установить Ubuntu на Toshiba UFS из Windows | [Radxa OS R2 на UFS](docs/guides/linux-ufs.md) |
| Установить Android 15 на Toshiba UFS 512 ГБ | [Android на UFS](docs/guides/android-ufs.md) |
| Подключить UART, определить разъёмы и питание | [Аппаратный справочник](docs/reference/hardware.md) |
| Выбрать прошивку и проверить файлы | [BIOS](docs/reference/boot-firmware.md), [файлы прошивки](docs/reference/firmware-files.md) |

[Полный каталог документации](docs/README.md) включает оригиналы Radxa,
описание исправления XBL и диагностику.

## Проверенная конфигурация

| Компонент | Конфигурация и результат |
| --- | --- |
| SBC | Dragon Q6A, 12 ГБ LPDDR5 |
| Linux на SD | Radxa OS R2, SD 32 ГБ, ядро `6.18.2-3-qcom`, штатные параметры, рабочий стол и SSH |
| Linux на NVMe | Radxa OS R2 с обновлением пакетов, SSD 256 ГБ, ядро `7.0.11-7-qcom`, SSH и холодная загрузка |
| Linux на UFS | Radxa OS R2, BIOS `260916`, ядро `6.18.2-3-qcom`, Toshiba с постоянной настройкой питания, рабочий стол и SSH |
| UFS | TOSHIBA THGJFCT2T84BAKCB rev 0100, UFS 3.0, 512 ГБ |
| Android | Android 15, воспроизводимые XBL/SPI и ext4 metadata; HDMI, ADB, обычная перезагрузка, два холодных включения и чтение UFS после простоя |
| Хост прошивки | Windows, исправленный edl-ng v2 |

Каждое руководство задаёт применимую конфигурацию, нужные файлы, команды
и проверяемый результат. Особенности запуска и объёма `/data` приведены
в руководстве Android. Новые платформы и автоматизация проходят отдельную проверку.

## Структура репозитория

```text
docs/                  руководства, справочник, оригиналы Radxa, разработка
firmware/              закреплённые версии и хеши файлов прошивки
tools/
  common/              общая логика Python
  windows/             Windows, включая экспериментальную автоматизацию
  linux/               точка входа Linux
  macos/               точка входа macOS
  target/              настройки, выполняемые в ОС самой Q6A
  dependencies/edl-ng/  источник, версия, патч и лицензия зависимости
tests/                 проверки инструментов без подключения SBC
```

В `firmware/` хранится описание точных входных файлов; сами образы, бэкапы
и результаты сборки остаются в локальных `artifacts/` и `runs/`.
Назначение каждого JSON описано в [справочнике файлов](docs/reference/firmware-files.md).

## Инструменты

Общая точка входа требует Python 3.10 или новее:

```sh
python tools/q6a.py check-repo
python -m unittest discover -s tests -v
```

Одинаковые проверки файлов и подготовка XBL доступны в Windows, macOS и Linux.
Сборка edl-ng использует закреплённый upstream и патч из репозитория.
Команды и требования: [инструменты хоста](docs/development/host-tools.md).
Аппаратный маршрут прошивки описан для Windows.

```sh
git clone https://github.com/pOmelchenko/radxa_dragon_q6a.git
cd radxa_dragon_q6a
```

## Развитие документации

Новое руководство добавляется вместе с рабочими командами, точной версией
прошивки и способом проверки результата. Незавершённые работы находятся
в [разделе разработки](docs/development/README.md); после проверки на SBC
решение переносится в руководства.

Официальные источники: [Radxa Q6A](https://docs.radxa.com/en/dragon/q6a),
[образы и аппаратные материалы](https://docs.radxa.com/en/dragon/q6a/download).
