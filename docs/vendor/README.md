# Оригинальные материалы Radxa

Файлы производителя получены 23 сентября 2026 года из
[каталога Q6A](https://docs.radxa.com/en/dragon/q6a/download) и репозитория
документации Radxa. Они сохранены без преобразования.

| Материал | Версия и содержание |
| --- | --- |
| [Принципиальная схема](radxa-q6a-schematic-v1.21.pdf) | V1.21, 35 страниц PDF; основные надписи 2025-09-12 |
| [Размещение компонентов](radxa-q6a-components-v1.21.pdf) | V1.21, верхняя и нижняя стороны; 2 страницы |
| [Механические размеры](radxa-q6a-dimensions-v1.21.pdf) | V1.21, обе стороны; 1 страница |
| [Иллюстрация интерфейсов](interfaces.webp) | Нумерация компонентов и разъёмов |

Аппаратный разбор и номера нужных страниц:
[справочник Q6A](../reference/hardware.md).
Печатные номера листов схемы отличаются от номеров страниц PDF.

[sources.json](sources.json) содержит исходные URL, версии, размеры,
даты получения и SHA-256. Зафиксированная версия документации Radxa:
[`c44bfe6c70845dd265b50436a6b3a52f0d107377`](https://github.com/radxa-docs/docs/tree/c44bfe6c70845dd265b50436a6b3a52f0d107377/i18n/en/docusaurus-plugin-content-docs/current/dragon/q6a).

## Проверка файлов

Из корня репозитория на Windows, macOS и Linux:

```sh
python tools/q6a.py check-repo
```

Либо из `docs/vendor` на Linux:

```sh
sha256sum -c SHA256SUMS
```

На macOS:

```sh
shasum -a 256 -c SHA256SUMS
```

[SHA256SUMS](SHA256SUMS) покрывает четыре сохранённых оригинала.
Файлы сохраняют уведомления и сведения о правообладателях.
