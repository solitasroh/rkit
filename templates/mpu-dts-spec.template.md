# {feature} Device Tree Specification

## 1. Board Info
| Item | Value |
|------|-------|
| SoC | {soc} |
| Board | {board_name} |
| DTS File | {dts_filename} |
| Base DTSI | {base_dtsi} |

## 2. Pin Mux Configuration
| Pad | Signal | Config Value | Node |
|-----|--------|:------------:|------|
| {pad_name} | {signal} | 0x{config} | &{pinctrl_node} |

## 3. Peripheral Nodes
| Peripheral | DT Node | Status | Pins |
|-----------|---------|:------:|------|
| {periph} | &{node} | okay | pinctrl-0 = <&{grp}> |

## 4. Clock Configuration
| Clock | Provider | Consumer |
|-------|----------|----------|
| {clock_name} | &{clk_node} | &{consumer} |

## 5. GPIO/LED/Button Nodes
```dts
leds {
    compatible = "gpio-leds";
    led0 { gpios = <&gpio1 2 GPIO_ACTIVE_LOW>; default-state = "off"; };
};
```
