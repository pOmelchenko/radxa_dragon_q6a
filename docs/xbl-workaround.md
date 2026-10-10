# Исправления XBL и edl-ng

## Что наблюдалось

XBL находил `TOSHIBA THGJFCT2T84BAKCB0100`, Boot LUN 1, UFS Gear 3 и
успешно инициализировал 12 ГБ DDR. Запуск прекращался после сообщения
`UFS 3.x Device Volt set to 2.5 volt`.

В коде XBL обнаружены SCSI START STOP UNIT с SLEEP, изменение питания и
START STOP UNIT с ACTIVE для версии UFS от `0x300`. В Linux чип сообщал
`specification_version=0x0300`; рабочий VCC там был 2960000 мкВ.

Успех обхода этой последовательности не различает проблему смены напряжения
и проблему SLEEP/ACTIVE. Точные допустимые напряжения данного Toshiba не
установлены. [Даташит QCS6490](https://dl.radxa.com/dragon/q6a/hw/datasheets/80-23889-1_REV_AW_QCS6490_and_QCS5430_Data_Sheet.pdf),
страница 57, описывает переход L7B с начальных 2,952 В на 2,5 В для UFS 3.1;
это не спецификация питания этого Toshiba.

## Изменение XBL

| Поле | Значение |
| --- | --- |
| Исходный XBL SHA-256 | `4c3e9eaa5bccf57fdd0f30233600276b25069fbbe019161331bfb75ed077c1f7` |
| Смещение инструкции | `0x43784`, VA `0x1485d784` |
| Было | `cmp w9, #0x300`, word `0x710c013f` |
| Стало | `cmp w9, #0x310`, word `0x710c413f` |
| Пересчитанный SHA-384 code segment | Смещение `0x1108` |
| Всего изменено | 49 байтов, длина ELF прежняя |
| Исправленный XBL SHA-256 | `347c5bfd376ee029ed60486ffb0d69ebbc82bd65111e418389fb724c482b3ed5` |
| Полный исправленный SPI SHA-256 | `d0e41c7d20efa0fffa7bf567a337b330038fb17c5d6f4c5502412a711921873c` |

Для наблюдаемой версии `0x0300` условие пропускает всю последовательность
SLEEP → изменение питания → ACTIVE. Начальное питание сохраняется.
Проверяются все заполненные SHA-384 сегменты, а SPI меняется только в области XBL,
начинающейся с `6 * 4096` байт.

Подпись производителя после изменения недействительна и заново не создаётся.
Проверенная плата с Secure Boot Off приняла этот образ; применение на другом
комплекте требует отдельной квалификации.

## Воспроизвести файлы без платы

После подключения [готового пакета](artifacts.md), Python 3.10 или новее:

```powershell
$bundle = (Get-Content .\artifacts\bundle-path.txt -Raw).Trim()
python .\scripts\prepare_xbl.py --xbl "$bundle\firmware\spinor\xbl.elf" --spi "$bundle\recovery\spi-before-linux-restore.bin" --output-dir .\artifacts\rebuilt
```

Скрипт не обращается к плате, принимает только точные исходные хеши и требует
совпадения итоговых хешей с зафиксированными. Неизвестный исходник не патчится.
Запись готовых файлов выполняется отдельными стадиями установщика.
Описание изменения находится в [patches/xbl-ufs30.json](../patches/xbl-ufs30.json).

## edl-ng v2

Основа — [strongtz/edl-ng](https://github.com/strongtz/edl-ng), commit
`4a658eee465a84b13c53b338edfd22bd08e4b211`, .NET 9.
Полный патч включает новые C# файлы и тесты:
[patches/edl-ng-q6a.patch](../patches/edl-ng-q6a.patch).

Исправлены:

- Передача `--maxpayload` в provisioning и обычный configure.
- Остановка при configure NAK.
- Ограничение чанка записи выбранным payload.
- Сохранение оставшихся байтов, когда Firehose XML и бинарные данные приходят вместе.

Для получения исходников:

```powershell
git clone https://github.com/strongtz/edl-ng.git .work/edl-ng
git -C .work/edl-ng checkout --detach 4a658eee465a84b13c53b338edfd22bd08e4b211
git -C .work/edl-ng apply ../../patches/edl-ng-q6a.patch
dotnet test .work/edl-ng/QCEDL.NET.Tests/QCEDL.NET.Tests.csproj -c Release
dotnet publish .work/edl-ng/QCEDL.CLI/QCEDL.CLI.csproj -c Release -r win-x64 --self-contained true -o artifacts/edl-ng-rebuilt
```

Native AOT проект требует соответствующего C++ toolchain на машине сборки.
Сборка исходников не обещает побайтово одинаковый EXE: в установке используется
замороженный проверенный бинарник с SHA-256
`2cfedece4030e3ba4e2742cc573b30e890d774504236a67f1b04131f22ab5646`.
Новый EXE требует своей проверки и не должен незаметно заменять этот файл.

Лицензия upstream сохранена в [third_party/edl-ng-LICENSE](../third_party/edl-ng-LICENSE).
Образы Radxa и программаторы Qualcomm не добавлены в Git; источник и происхождение
указаны в документации пакета.
