# Инструменты Q6A

`q6a.py` — общий CLI; `common/` содержит платформенно независимую логику.
`windows/`, `linux/`, `macos/` предоставляют точки входа соответствующих хостов.

Команды и требования: [руководство инструментов](../docs/development/host-tools.md).
Источник edl-ng: [закреплённая зависимость](dependencies/edl-ng/README.md).
Источник драйвера TFT50: [Linux и два патча](dependencies/linux-tft50/README.md).
Настройка самой платы: [инструменты Q6A](target/README.md), включая TFT50 и питание UFS.
Windows-автоматизация в `windows/experimental/` проходит отдельную аппаратную проверку.
