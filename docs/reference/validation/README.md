# Конфигурация и проверка решений

## Linux BIOS

На Dragon Q6A 12 ГБ запись Linux rawprogram завершилась успешно.
Обратное чтение SPI совпало с 18 исходными payload; Ubuntu с NVMe 256 ГБ
запустилась с `module_blacklist=i2c_qcom_geni`, ядро `7.0.11-7-qcom`.

## Android на Toshiba UFS

На модуле `THGJFCT2T84BAKCB rev 0100`, UFS 3.0, 512 ГБ выполнены provisioning,
запись Android 15, исправление `xbl_a` и запись исправленного SPI.
Readback UFS XBL и полного SPI совпал с кандидатами.
После программного reset получены `sys.boot_completed=1`, остановленная
boot animation и изображение HDMI 3840×2160 @ 30 Hz.

Машиночитаемые параметры успешного сеанса:
[hardware-results.json](hardware-results.json),
[direct-route-evidence.json](direct-route-evidence.json).
Условия применимости приведены в соответствующих руководствах.

## Проверка инфраструктуры

CI выполняет проверку документации и общих инструментов на Windows, macOS
и Linux. Отдельно выполняются проверки Windows-автоматизации без USB.
Актуальный результат:
[GitHub Actions](https://github.com/pOmelchenko/radxa_dragon_q6a/actions).

[offline-2026-10-10.json](offline-2026-10-10.json) фиксирует исходную проверку
патча edl-ng, сборки XBL, пакетов и Windows-обёрток. Это техническая запись
для разработки; руководство по прошивке использует прямые команды.
