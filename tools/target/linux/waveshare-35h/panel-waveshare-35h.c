// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/of.h>
#include <linux/regulator/consumer.h>

#include <drm/drm_connector.h>
#include <drm/drm_mipi_dsi.h>
#include <drm/drm_modes.h>
#include <drm/drm_panel.h>
#include <drm/drm_probe_helper.h>

struct ws35h_panel {
	struct drm_panel panel;
	struct drm_display_mode mode;
};

static int ws35h_get_modes(struct drm_panel *panel,
			   struct drm_connector *connector)
{
	struct ws35h_panel *lcd = container_of(panel, struct ws35h_panel, panel);

	connector->display_info.bpc = 8;
	return drm_connector_helper_get_modes_fixed(connector, &lcd->mode);
}

static const struct drm_panel_funcs ws35h_funcs = {
	.get_modes = ws35h_get_modes,
};

static int ws35h_probe(struct mipi_dsi_device *dsi)
{
	struct device *dev = &dsi->dev;
	struct ws35h_panel *lcd;
	int ret;

	lcd = devm_drm_panel_alloc(dev, struct ws35h_panel, panel, &ws35h_funcs,
				   DRM_MODE_CONNECTOR_DSI);
	if (IS_ERR(lcd))
		return PTR_ERR(lcd);

	ret = of_get_drm_panel_display_mode(dev->of_node, &lcd->mode, NULL);
	if (ret)
		return dev_err_probe(dev, ret, "invalid panel geometry or timing\n");
	lcd->mode.type = DRM_MODE_TYPE_DRIVER;

	/* The vendor's 35H profile streams video without DCS setup commands. */
	dsi->lanes = 1;
	dsi->format = MIPI_DSI_FMT_RGB888;
	dsi->mode_flags = MIPI_DSI_MODE_VIDEO;

	ret = devm_regulator_get_enable(dev, "power");
	if (ret)
		return dev_err_probe(dev, ret, "failed to power the display\n");

	mipi_dsi_set_drvdata(dsi, lcd);
	drm_panel_add(&lcd->panel);
	ret = mipi_dsi_attach(dsi);
	if (ret) {
		drm_panel_remove(&lcd->panel);
		return dev_err_probe(dev, ret, "failed to attach DSI panel\n");
	}

	return 0;
}

static void ws35h_remove(struct mipi_dsi_device *dsi)
{
	struct ws35h_panel *lcd = mipi_dsi_get_drvdata(dsi);

	mipi_dsi_detach(dsi);
	drm_panel_remove(&lcd->panel);
}

static const struct of_device_id ws35h_of_match[] = {
	{ .compatible = "waveshare,35h-dsi" },
	{}
};
MODULE_DEVICE_TABLE(of, ws35h_of_match);

static struct mipi_dsi_driver ws35h_driver = {
	.driver = {
		.name = "panel-waveshare-35h",
		.of_match_table = ws35h_of_match,
	},
	.probe = ws35h_probe,
	.remove = ws35h_remove,
};
module_mipi_dsi_driver(ws35h_driver);

MODULE_DESCRIPTION("Waveshare 3.5inch DSI LCD (H) panel");
MODULE_LICENSE("GPL");
