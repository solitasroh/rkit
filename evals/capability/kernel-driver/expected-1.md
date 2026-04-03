## Step 1: Header Includes and Data Structure

```c
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/of.h>
#include <linux/sysfs.h>

#define DRIVER_NAME "custom-sensor"

struct custom_sensor_data {
    struct spi_device *spi;
    uint16_t last_value;
    struct mutex lock;
};
```

## Step 2: SPI Read Function

```c
static int custom_sensor_read_reg(struct custom_sensor_data *data,
                                   uint8_t reg, uint16_t *value)
{
    uint8_t tx_buf[1] = { reg };
    uint8_t rx_buf[2] = { 0 };
    struct spi_transfer xfers[2] = {
        { .tx_buf = tx_buf, .len = 1 },
        { .rx_buf = rx_buf, .len = 2 },
    };

    int ret = spi_sync_transfer(data->spi, xfers, ARRAY_SIZE(xfers));
    if (ret == 0)
        *value = (rx_buf[0] << 8) | rx_buf[1];

    return ret;
}
```

## Step 3: Sysfs Attribute Interface

```c
static ssize_t sensor_value_show(struct device *dev,
                                  struct device_attribute *attr, char *buf)
{
    struct custom_sensor_data *data = dev_get_drvdata(dev);
    uint16_t value;
    int ret;

    mutex_lock(&data->lock);
    ret = custom_sensor_read_reg(data, 0x00, &value);
    if (ret == 0) {
        data->last_value = value;
    }
    mutex_unlock(&data->lock);

    if (ret)
        return ret;

    return sysfs_emit(buf, "%u\n", data->last_value);
}

static DEVICE_ATTR_RO(sensor_value);

static struct attribute *custom_sensor_attrs[] = {
    &dev_attr_sensor_value.attr,
    NULL,
};

static const struct attribute_group custom_sensor_attr_group = {
    .attrs = custom_sensor_attrs,
};
```

## Step 4: Probe and Remove Functions

```c
static int custom_sensor_probe(struct spi_device *spi)
{
    struct custom_sensor_data *data;
    int ret;

    data = devm_kzalloc(&spi->dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    data->spi = spi;
    mutex_init(&data->lock);
    spi_set_drvdata(spi, data);

    ret = sysfs_create_group(&spi->dev.kobj, &custom_sensor_attr_group);
    if (ret) {
        dev_err(&spi->dev, "Failed to create sysfs group\n");
        return ret;
    }

    dev_info(&spi->dev, "Custom sensor driver probed\n");
    return 0;
}

static void custom_sensor_remove(struct spi_device *spi)
{
    sysfs_remove_group(&spi->dev.kobj, &custom_sensor_attr_group);
    dev_info(&spi->dev, "Custom sensor driver removed\n");
}
```

## Step 5: Device Tree Match and Module Registration

```c
static const struct of_device_id custom_sensor_of_match[] = {
    { .compatible = "vendor,custom-sensor" },
    { /* sentinel */ },
};
MODULE_DEVICE_TABLE(of, custom_sensor_of_match);

static struct spi_driver custom_sensor_driver = {
    .driver = {
        .name           = DRIVER_NAME,
        .of_match_table = custom_sensor_of_match,
    },
    .probe  = custom_sensor_probe,
    .remove = custom_sensor_remove,
};

module_spi_driver(custom_sensor_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Embedded Team");
MODULE_DESCRIPTION("Custom SPI sensor platform driver");
```

## Driver Architecture Summary
- The probe function allocates driver data, initializes mutex, and creates sysfs interface
- The remove function cleans up sysfs group on device unbind
- Device Tree matching uses the compatible string "vendor,custom-sensor"
- All memory allocation uses devm_kzalloc for automatic cleanup
- The sysfs attribute provides a read-only interface to userspace
