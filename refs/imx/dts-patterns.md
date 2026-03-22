# i.MX Device Tree Patterns Reference

## pinctrl Node (i.MX6)
```dts
&iomuxc {
    pinctrl_uart1: uart1grp {
        fsl,pins = <
            MX6QDL_PAD_CSI0_DAT10__UART1_TX_DATA  0x1b0b1
            MX6QDL_PAD_CSI0_DAT11__UART1_RX_DATA  0x1b0b1
        >;
    };
    pinctrl_i2c1: i2c1grp {
        fsl,pins = <
            MX6QDL_PAD_CSI0_DAT8__I2C1_SDA  0x4001b8b1
            MX6QDL_PAD_CSI0_DAT9__I2C1_SCL  0x4001b8b1
        >;
    };
};
```

## UART Node
```dts
&uart1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart1>;
    status = "okay";
};
```

## I2C Node with Sensor
```dts
&i2c1 {
    clock-frequency = <100000>;
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c1>;
    status = "okay";

    sensor@68 {
        compatible = "invensense,mpu6050";
        reg = <0x68>;
        interrupt-parent = <&gpio1>;
        interrupts = <18 IRQ_TYPE_EDGE_FALLING>;
    };
};
```

## GPIO LED
```dts
leds {
    compatible = "gpio-leds";
    heartbeat { gpios = <&gpio1 2 GPIO_ACTIVE_LOW>; linux,default-trigger = "heartbeat"; };
    user      { gpios = <&gpio1 4 GPIO_ACTIVE_HIGH>; default-state = "off"; };
};
```

## Pad Config Value (0x1b0b1)
```
Bit[16]: HYS (Hysteresis) = 1
Bit[15:14]: PUS (Pull Up/Down) = 10 (100K pull-up)
Bit[13]: PUE (Pull/Keep Select) = 1 (Pull)
Bit[12]: PKE (Pull/Keep Enable) = 1
Bit[11]: ODE (Open Drain) = 0
Bit[7:6]: SPEED = 10 (100MHz)
Bit[5:3]: DSE (Drive Strength) = 110 (40 ohm)
Bit[0]: SRE (Slew Rate) = 1 (Fast)
```

## i.MX6ULL Specifics
- Pad prefix: MX6UL_PAD_ (shared with i.MX6UL)
- Dual Ethernet: fec1, fec2
- No GPU: use PXP for 2D operations

## i.MX28 Specifics
- Pad prefix: MX28_PAD_
- pinctrl compatible: "fsl,imx28-pinctrl"
- Boot: mxs-bootlets or U-Boot SPL
- ARM926EJ-S → no NEON, no hard float
