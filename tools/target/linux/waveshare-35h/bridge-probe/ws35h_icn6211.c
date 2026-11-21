// SPDX-License-Identifier: GPL-2.0-only
#include <linux/device.h>
#include <linux/module.h>
#include <linux/of.h>
#include <drm/drm_mipi_dsi.h>
#include <video/mipi_display.h>

/* The ICN6211 takes the register offset and the byte count as two
 * parameters. Set LP mode on this request only, leaving the panel's
 * video flags untouched. Use single-byte replies as in the DRM driver.
 */
static ssize_t icn_read_byte(struct mipi_dsi_device *dsi, u8 reg, u8 *value)
{
	const u8 request[] = { reg, 1 };
	const struct mipi_dsi_msg msg = {
		.channel = dsi->channel,
		.type = MIPI_DSI_GENERIC_READ_REQUEST_2_PARAM,
		.flags = MIPI_DSI_MSG_USE_LPM,
		.tx_buf = request,
		.tx_len = sizeof(request),
		.rx_buf = value,
		.rx_len = 1,
	};

	return dsi->host->ops->transfer(dsi->host, &msg);
}

static int snapshot_get(char *buf, const struct kernel_param *kp)
{
	static const struct {
		const char *name;
		u8 start, count;
	} groups[] = {
		{ "ID", 0x00, 4 },
		{ "MIPI_ERR_VECTOR", 0x80, 2 },
		{ "DSI_CTRL", 0x86, 1 },
		{ "TIMING_AND_BIST", 0x20, 11 },
	};
	static const u8 expected[] = { 0xc1, 0x62, 0x11 };
	struct device_node *np;
	struct mipi_dsi_device *dsi;
	u8 values[11];
	int i, j, len = 0;

	np = of_find_compatible_node(NULL, NULL, "waveshare,35h-dsi");
	if (!np)
		return sysfs_emit(buf, "Waveshare 35H overlay is not active\n");
	dsi = of_find_mipi_dsi_device_by_node(np);
	of_node_put(np);
	if (!dsi)
		return sysfs_emit(buf, "Waveshare 35H DSI device not found\n");

	device_lock(&dsi->dev);
	if (!dsi->attached || !dsi->dev.driver ||
	    strcmp(dsi->dev.driver->name, "panel-waveshare-35h")) {
		len = sysfs_emit(buf, "Waveshare 35H panel driver is not attached\n");
		goto out;
	}

	for (i = 0; i < ARRAY_SIZE(groups); i++) {
		for (j = 0; j < groups[i].count; j++) {
			u8 reg = groups[i].start + j;
			ssize_t ret = icn_read_byte(dsi, reg, &values[j]);

			if (ret != 1) {
				len += sysfs_emit_at(buf, len,
					"DSI read 0x%02x returned %zd (expected 1 byte)\n",
					reg, ret);
				goto out;
			}
		}
		len += sysfs_emit_at(buf, len, "%s [0x%02x]: %*ph\n",
				     groups[i].name, groups[i].start,
				     (int)groups[i].count, values);
		if (i == 0 && memcmp(values, expected, sizeof(expected))) {
			len += sysfs_emit_at(buf, len, "Unexpected ID (expected c1 62 11)\n");
			goto out;
		}
	}
out:
	device_unlock(&dsi->dev);
	put_device(&dsi->dev);
	return len;
}

static const struct kernel_param_ops snapshot_ops = { .get = snapshot_get };
module_param_cb(snapshot, &snapshot_ops, NULL, 0400);
MODULE_PARM_DESC(snapshot, "Read the Waveshare 35H ICN6211 registers over DSI");

static int __init ws35h_probe_init(void)
{
	return of_machine_is_compatible("radxa,dragon-q6a") ? 0 : -ENODEV;
}
module_init(ws35h_probe_init);

static void __exit ws35h_probe_exit(void)
{
}
module_exit(ws35h_probe_exit);

MODULE_DESCRIPTION("Read-only ICN6211 diagnostics for the Dragon Q6A Waveshare 35H trial");
MODULE_LICENSE("GPL");
