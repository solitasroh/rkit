## Step 1: Pinctrl Group Definitions

Define pin mux and pad control settings in the iomuxc node:

```dts
&iomuxc {
    pinctrl_uart4: uart4grp {
        fsl,pins = <
            MX6UL_PAD_UART4_TX_DATA__UART4_DCE_TX  0x1b0b1
            MX6UL_PAD_UART4_RX_DATA__UART4_DCE_RX  0x1b0b1
        >;
    };

    pinctrl_i2c2: i2c2grp {
        fsl,pins = <
            MX6UL_PAD_GPIO1_IO00__I2C2_SCL  0x4001b8b0
            MX6UL_PAD_GPIO1_IO01__I2C2_SDA  0x4001b8b0
        >;
    };
};
```

## Step 2: UART4 Node Configuration

Enable UART4 with pinctrl reference, clock, and interrupt settings:

```dts
&uart4 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart4>;
    status = "okay";
};
```

The UART4 node inherits the following from the SoC-level dtsi:
- compatible = "fsl,imx6ul-uart", "fsl,imx21-uart"
- clocks = <&clks IMX6UL_CLK_UART4_IPG>, <&clks IMX6UL_CLK_UART4_SERIAL>
- interrupts = <GIC_SPI 29 IRQ_TYPE_LEVEL_HIGH>

## Step 3: I2C2 Node with BME280 Sensor

Enable I2C2 bus and add the sensor child node:

```dts
&i2c2 {
    clock-frequency = <100000>;
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c2>;
    status = "okay";

    bme280: bme280@76 {
        compatible = "bosch,bme280";
        reg = <0x76>;
    };
};
```

## Step 4: Clock and Interrupt Verification

Verify the SoC-level clock assignment is correct:
- UART4 uses IMX6UL_CLK_UART4_IPG and IMX6UL_CLK_UART4_SERIAL
- I2C2 uses IMX6UL_CLK_I2C2
- Interrupt controller is GIC (Generic Interrupt Controller)
- Interrupt specifier format: <GIC_SPI irq_num trigger_type>

## Step 5: DTS Compilation Check

Validate the Device Tree source before committing:

```bash
dtc -I dts -O dtb -o test.dtb -W no-unit_address_vs_reg \
    arch/arm/boot/dts/imx6ull-custom-board.dts
```

Expected Result: no errors, warnings only for upstream nodes if any.

## BSP Porting Notes
- Always reference the SoC-level dtsi for available nodes and their compatible strings
- Pad control values (e.g., 0x1b0b1) encode pull-up/down, drive strength, slew rate
- The I2C node uses clock-frequency property to set bus speed (100kHz standard mode)
- Sensor child node uses reg property for I2C slave address
