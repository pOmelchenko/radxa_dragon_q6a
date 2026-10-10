# Документы производителя Radxa Dragon Q6A

Материалы получены **23 сентября 2026 года** из
[официального каталога](https://docs.radxa.com/en/dragon/q6a/download)
и репозитория документации Radxa. Оригинальные файлы сохранены без
преобразований. Разбор приведён в [аппаратном справочнике](../research/hardware-reference.md),
[заметках об ОС и накопителях](../research/system-and-storage.md)
и [камерных экспериментах](../camera-research.md).

## Сохранённые оригиналы

| Файл | Версия и содержание |
| --- | --- |
| [Принципиальная схема](radxa-q6a-schematic-v1.21.pdf) | **V1.21**, 35 страниц PDF. В изученных основных надписях указано **2025-09-12**; внутренняя нумерация листов относится к схеме из 37 листов и отличается от номеров страниц PDF. |
| [Размещение компонентов](radxa-q6a-components-v1.21.pdf) | Опубликовано как **V1.21**, две страницы: верхняя и нижняя стороны. В метаданных создания и изменения PDF указано **2025-06-21**. |
| [Механические размеры](radxa-q6a-dimensions-v1.21.pdf) | Опубликовано как **V1.21**, одна страница с обеими сторонами платы. В метаданных создания и изменения PDF указано **2025-09-15**. |
| [Иллюстрация разъёмов](interfaces.webp) | Нумерованные интерфейсы платы из зафиксированной версии репозитория документации. Версия самого изображения не указана; оно служит для ориентации на плате. |

При изучении схемы рассмотрены блок-схема, отладочный UART и камерные цепи.
Визуально проверены обе страницы размещения компонентов, размеры
и иллюстрация разъёмов. Сохранение всей схемы не означает полного
электрического аудита. Ревизию имеющейся платы и установленные
необязательные компоненты ещё нужно определить. Даты метаданных
не считаются датами публикации.

## Источники и зафиксированная версия

Документация Radxa изучалась на коммите
[`c44bfe6c70845dd265b50436a6b3a52f0d107377`](https://github.com/radxa-docs/docs/tree/c44bfe6c70845dd265b50436a6b3a52f0d107377/i18n/en/docusaurus-plugin-content-docs/current/dragon/q6a)
с временем фиксации **2026-09-22T03:42:06Z**. Манифест содержит пути
исходников, URL, размеры и хеши. Исходные Markdown-файлы читались
во временной копии репозитория и здесь не дублируются с неразрешёнными
импортами и путями к ресурсам. Для страниц, подключающих общие руководства,
в манифесте отдельно отмечено, что импортированные инструкции полностью
не проверялись.

- [Обзор платы](https://docs.radxa.com/en/dragon/q6a),
  [аппаратные интерфейсы](https://docs.radxa.com/en/dragon/q6a/hardware-use/hardware-info),
  [CSI](https://docs.radxa.com/en/dragon/q6a/hardware-use/mipi-csi),
  [GPIO](https://docs.radxa.com/en/dragon/q6a/hardware-use/pin-gpio),
  [питание](https://docs.radxa.com/en/dragon/q6a/hardware-use/power-header)
  и [отладочный UART](https://docs.radxa.com/en/dragon/q6a/system-config/uart-debug).
- [NVMe](https://docs.radxa.com/en/dragon/q6a/hardware-use/nvme),
  [eMMC/UFS](https://docs.radxa.com/en/dragon/q6a/hardware-use/ufs-emmc-com),
  [варианты загрузки](https://docs.radxa.com/en/dragon/q6a/hardware-use/boot),
  [восстановление BIOS](https://docs.radxa.com/en/dragon/q6a/low-level-dev/spi-fw)
  и [загрузка Radxa OS](https://docs.radxa.com/en/dragon/q6a/low-level-dev/radxa-os-boot).
- [Установка Android](https://docs.radxa.com/en/dragon/q6a/other-system/android),
  [руководство Radxa по Armbian](https://docs.radxa.com/en/dragon/q6a/other-system/armbian),
  [каталог Q6A на Armbian](https://armbian.com/boards/radxa-dragon-q6a),
  [пример Camera 4K](https://docs.radxa.com/en/dragon/q6a/accessories/camera-4k)
  и [частые вопросы](https://docs.radxa.com/en/dragon/q6a/faq).

Образы ОС и архивы прошивок доступны по ссылкам из каталога, но
**не скачивались и не изучались изнутри**. Имя файла не подтверждает его хеш,
успех прошивки или поддержку оборудования. Каталог Armbian изучался онлайн;
проверка контрольной суммы и подписи образа остаётся этапом установки.

Дополнительные механические материалы, **не скачанные и не изученные**:
[архив 2D DXF](https://dl.radxa.com/dragon/q6a/hw/radxa_dragon_q6a_2d_dxf_v1.21.zip)
и [архив 3D STEP](https://dl.radxa.com/dragon/q6a/hw/radxa_dragon_q6a_3d_stp_v1.21.zip).

## Происхождение и проверка целостности

[sources.json](sources.json) содержит URL, даты получения, версии, размеры,
число страниц и SHA-256. [SHA256SUMS](SHA256SUMS) покрывает
**четыре сохранённых оригинала**. Проверка из этого каталога:

```sh
sha256sum -c SHA256SUMS
```

На macOS:

```sh
shasum -a 256 -c SHA256SUMS
```

Хеши определяют полученные байты, но не являются подписями издателя.
Оригиналы сохраняют сведения о правообладателях и уведомления издателей.
Временные извлечения текста и растровые изображения страниц PDF
в репозиторий не включены.
