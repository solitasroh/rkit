#!/usr/bin/env node
/**
 * mcukit 전체 통합 테스트
 */

const fs = require('fs');
const path = require('path');

let totalPass = 0, totalFail = 0;
const failures = [];

function pass(name) { totalPass++; console.log('  PASS: ' + name); }
function fail(name, reason) { totalFail++; failures.push(name + ': ' + reason); console.log('  FAIL: ' + name + ' → ' + reason); }
function assert(name, condition, reason) { condition ? pass(name) : fail(name, reason || 'assertion failed'); }

// ============================================================
console.log('\n===== TEST 1: 전체 lib/ 모듈 require 테스트 =====');
// ============================================================

function findAllJs(dir) {
  const results = [];
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isFile() && e.name.endsWith('.js')) results.push(full);
      else if (e.isDirectory()) results.push(...findAllJs(full));
    }
  } catch(_) {}
  return results;
}

const libFiles = findAllJs('lib');
let modOk = 0, modFail = 0;
for (const f of libFiles) {
  const rel = './' + f.split(path.sep).join('/');
  try { require(rel); modOk++; }
  catch(e) { modFail++; fail('require(' + rel + ')', e.message.split('\n')[0].substring(0, 60)); }
}
console.log('  Summary: ' + modOk + '/' + (modOk+modFail) + ' modules loaded');

// ============================================================
console.log('\n===== TEST 2: MCU .ioc 파싱 테스트 =====');
// ============================================================

const testIoc = `#MicroXplorer Configuration
Mcu.UserName=STM32F407VGTx
Mcu.PinsNb=4
Mcu.Pin0=PA9
Mcu.Pin1=PA10
Mcu.Pin2=PA5
Mcu.Pin3=PB6
Mcu.IP0=USART1
Mcu.IP1=SPI1
PA9.Signal=USART1_TX
PA9.Mode=Asynchronous
PA9.GPIO_Label=DEBUG_TX
PA9.Locked=true
PA10.Signal=USART1_RX
PA5.Signal=SPI1_SCK
PB6.Signal=I2C1_SCL
RCC.HSEState=RCC_HSE_ON
RCC.PLLSource=RCC_PLLSOURCE_HSE
RCC.HSE_VALUE=8000000
RCC.PLLM=8
RCC.PLLN=336
RCC.PLLP=RCC_PLLP_DIV2
RCC.PLLQ=7
RCC.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK
RCC.AHBCLKDivider=RCC_SYSCLK_DIV1
RCC.APB1CLKDivider=RCC_HCLK_DIV4
RCC.APB2CLKDivider=RCC_HCLK_DIV2
`;
fs.writeFileSync('_test.ioc', testIoc);

const pc = require('./lib/mcu/pin-config');
const iocData = pc.parseIocFile('_test.ioc');
assert('iocData is Map', iocData instanceof Map);
assert('chip name', pc.extractChipName(iocData) === 'STM32F407VGTx');

const pins = pc.extractPinAssignments(iocData);
assert('pin count', pins.length === 4, 'got ' + pins.length);
const pa9 = pins.find(p => p.pin === 'PA9');
assert('PA9 signal', pa9 && pa9.signal === 'USART1_TX');
assert('PA9 label', pa9 && pa9.label === 'DEBUG_TX');
assert('PA9 locked', pa9 && pa9.locked === true);

const peripherals = pc.extractPeripheralList(iocData);
assert('peripheral count', peripherals.length === 2, 'got ' + peripherals.length);

const conflicts = pc.detectPinConflicts(pins);
assert('no pin conflicts', conflicts.length === 0);

// ============================================================
console.log('\n===== TEST 3: 클럭 트리 계산 테스트 =====');
// ============================================================

const ct = require('./lib/mcu/clock-tree');
const clock = ct.extractClockConfig(iocData);

// HSE=8MHz, PLLM=8, PLLN=336, PLLP=2 → VCO = (8M/8)*336 = 336MHz, SYSCLK = 336/2 = 168MHz
assert('PLL source', clock.pll.source === 'HSE');
assert('PLL VCO = 336MHz', clock.pll.vco === 336000000, 'got ' + clock.pll.vco);
assert('SYSCLK = 168MHz', clock.sysclk.frequency === 168000000, 'got ' + clock.sysclk.frequency);
assert('AHB = 168MHz (div1)', clock.ahb.frequency === 168000000);
assert('APB1 = 42MHz (div4)', clock.apb1.frequency === 42000000, 'got ' + clock.apb1.frequency);
assert('APB2 = 84MHz (div2)', clock.apb2.frequency === 84000000, 'got ' + clock.apb2.frequency);

const clockVal = ct.validateClockLimits(clock);
assert('clock limits valid', clockVal.valid, clockVal.issues.join(', '));

// Test invalid clock (APB1 too high)
const badIoc = new Map(iocData);
badIoc.set('RCC.APB1CLKDivider', 'RCC_HCLK_DIV1'); // APB1 = 168MHz > 42MHz max
const badClock = ct.extractClockConfig(badIoc);
const badVal = ct.validateClockLimits(badClock);
assert('detect APB1 over-clock', !badVal.valid, 'should detect APB1 > 42MHz');

fs.unlinkSync('_test.ioc');

// ============================================================
console.log('\n===== TEST 4: 메모리 분석기 테스트 =====');
// ============================================================

const ma = require('./lib/mcu/memory-analyzer');

// Test arm-none-eabi-size output parsing
const sizeOutput = `   text\t   data\t    bss\t    dec\t    hex\tfilename
  24576\t   1024\t   4096\t  29696\t   7400\tfirmware.elf`;
const tc = require('./lib/mcu/toolchain');
const sizeResult = tc.parseSizeOutput(sizeOutput);
assert('size parse text', sizeResult.text === 24576);
assert('size parse data', sizeResult.data === 1024);
assert('size parse bss', sizeResult.bss === 4096);
assert('size flash = text+data', sizeResult.text + sizeResult.data === 25600);
assert('size ram = data+bss', sizeResult.data + sizeResult.bss === 5120);

// Test memory budget check
const usage = { flash: { used: 870000, total: 1048576, percent: 83.0 }, ram: { used: 80000, total: 131072, percent: 61.0 } };
const budget = ma.checkMemoryBudget(usage);
assert('memory budget pass (83% < 85%)', budget.passed);

const overUsage = { flash: { used: 950000, total: 1048576, percent: 90.6 }, ram: { used: 80000, total: 131072, percent: 61.0 } };
const overBudget = ma.checkMemoryBudget(overUsage);
assert('memory budget fail (90.6% > 85%)', !overBudget.passed);

// Test memory report format
const report = ma.formatMemoryReport(usage, null);
assert('memory report contains Flash', report.includes('Flash'));
assert('memory report contains RAM', report.includes('RAM'));

// ============================================================
console.log('\n===== TEST 5: 도메인 감지 테스트 =====');
// ============================================================

const detector = require('./lib/domain/detector');

// Test on current project (no MCU/MPU/WPF files)
const result = detector.detectDomain();
assert('current project = unknown', result.domain === 'unknown');

// Test marker definitions
assert('MCU markers include .ioc', detector.MCU_MARKERS.files.includes('*.ioc'));
assert('MCU markers include fsl_device_registers.h', detector.MCU_MARKERS.files.includes('fsl_device_registers.h'));
assert('MCU markers NOT include sdk_config.h', !detector.MCU_MARKERS.files.includes('sdk_config.h'), 'sdk_config.h is Nordic nRF');
assert('MPU markers include *.dts', detector.MPU_MARKERS.files.includes('*.dts'));
assert('MPU markers include bblayers.conf', detector.MPU_MARKERS.files.includes('bblayers.conf'));

// ============================================================
console.log('\n===== TEST 6: 도메인 라우터 테스트 =====');
// ============================================================

const router = require('./lib/domain/router');

// Destructive patterns
const mcuPatterns = router.MCU_DANGEROUS_PATTERNS;
assert('MCU has st-flash erase', mcuPatterns.some(p => p.pattern.includes('st-flash erase')));
assert('MCU has STM32_Programmer_CLI', mcuPatterns.some(p => p.pattern.includes('STM32_Programmer_CLI')));
assert('MCU has JLinkExe', mcuPatterns.some(p => p.pattern.includes('JLinkExe')));
assert('MCU has JLink.exe (Windows)', mcuPatterns.some(p => p.pattern.includes('JLink.exe')));

const mpuPatterns = router.MPU_DANGEROUS_PATTERNS;
assert('MPU has dd if=', mpuPatterns.some(p => p.pattern.includes('dd if=')));
assert('MPU has mkfs', mpuPatterns.some(p => p.pattern.includes('mkfs')));

// Build patterns
assert('MCU build has make', router.BUILD_COMMAND_PATTERNS.mcu.includes('make'));
assert('MPU build has bitbake', router.BUILD_COMMAND_PATTERNS.mpu.includes('bitbake'));
assert('WPF build has dotnet build', router.BUILD_COMMAND_PATTERNS.wpf.includes('dotnet build'));

// Pipeline guide
const guide = router.getPipelineGuide();
assert('pipeline has Phase 1', guide['Phase 1'] !== undefined);
assert('pipeline has Phase 9', guide['Phase 9'] !== undefined);

// ============================================================
console.log('\n===== TEST 7: WPF XAML 분석 테스트 =====');
// ============================================================

const testXaml = `<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">
    <StackPanel>
        <TextBox Text="{Binding UserName, Mode=TwoWay}" />
        <TextBlock Text="{Binding StatusMessage}" />
        <Button Command="{Binding SaveCommand}" Content="Save" />
        <Label Content="{Binding Count}" />
        <TextBlock Style="{StaticResource HeaderStyle}" />
        <Border Background="{DynamicResource AccentBrush}" />
        <ContentControl Content="{TemplateBinding Content}" />
    </StackPanel>
</Window>`;
fs.writeFileSync('_test.xaml', testXaml);

const xa = require('./lib/wpf/xaml-analyzer');
const bindings = xa.extractBindings('_test.xaml');
assert('XAML binding count', bindings.length >= 4, 'got ' + bindings.length);

const userNameBinding = bindings.find(b => b.path === 'UserName');
assert('UserName binding found', userNameBinding !== undefined);
assert('UserName mode = TwoWay', userNameBinding && userNameBinding.mode === 'TwoWay');

const saveBinding = bindings.find(b => b.path === 'SaveCommand');
assert('SaveCommand binding found', saveBinding !== undefined);

const templateBinding = bindings.find(b => b.type === 'TemplateBinding');
assert('TemplateBinding found', templateBinding !== undefined);

fs.unlinkSync('_test.xaml');

// ============================================================
console.log('\n===== TEST 8: WPF MVVM 검증 테스트 =====');
// ============================================================

const testViewModel = `using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    private string _userName = "";

    [ObservableProperty]
    private int _count;

    [RelayCommand]
    private void Save()
    {
        // save logic
    }

    [RelayCommand]
    private async Task LoadAsync()
    {
        UserName = "loaded";
    }
}`;
fs.writeFileSync('_test_vm.cs', testViewModel);

const mv = require('./lib/wpf/mvvm-validator');
const vmResult = mv.validateViewModel('_test_vm.cs');
assert('MVVM score >= 80', vmResult.score >= 80, 'score=' + vmResult.score);
assert('no MVVM issues', vmResult.issues.length === 0, vmResult.issues.join('; '));

// Test binding validation against ViewModel
const testXaml2 = `<Window>
    <TextBox Text="{Binding UserName}" />
    <TextBlock Text="{Binding Count}" />
    <Button Command="{Binding SaveCommand}" />
    <Button Command="{Binding LoadCommand}" />
    <TextBlock Text="{Binding NonExistentProp}" />
</Window>`;
fs.writeFileSync('_test2.xaml', testXaml2);

const bindings2 = xa.extractBindings('_test2.xaml');
const validation = xa.validateBindings(bindings2, '_test_vm.cs');
assert('matched bindings >= 3', validation.matched.length >= 3, 'matched: ' + validation.matched.join(','));
assert('unmatched has NonExistentProp', validation.unmatched.includes('NonExistentProp'), 'unmatched: ' + validation.unmatched.join(','));

// Check Source Generator awareness
assert('matched includes UserName (from [ObservableProperty] _userName)', validation.matched.includes('UserName'));
assert('matched includes Count (from [ObservableProperty] _count)', validation.matched.includes('Count'));
assert('matched includes SaveCommand (from [RelayCommand] Save)', validation.matched.includes('SaveCommand'));

fs.unlinkSync('_test_vm.cs');
fs.unlinkSync('_test2.xaml');

// ============================================================
console.log('\n===== TEST 9: WPF .csproj 분석 테스트 =====');
// ============================================================

const testCsproj = `<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWPF>true</UseWPF>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="CommunityToolkit.Mvvm" Version="8.2.2" />
    <PackageReference Include="System.IO.Ports" Version="8.0.0" />
  </ItemGroup>
</Project>`;
fs.writeFileSync('_test.csproj', testCsproj);

const csprojResult = mv.analyzeCsproj('_test.csproj');
assert('csproj isWpf', csprojResult.isWpf === true);
assert('csproj framework', csprojResult.framework === 'net8.0-windows');
assert('csproj not .NET FW', csprojResult.isNetFramework === false);
assert('csproj has CommunityToolkit.Mvvm', csprojResult.packages.some(p => p.name === 'CommunityToolkit.Mvvm'));
assert('csproj has System.IO.Ports', csprojResult.packages.some(p => p.name === 'System.IO.Ports'));
assert('no warnings for good project', csprojResult.warnings.length === 0, csprojResult.warnings.join('; '));

fs.unlinkSync('_test.csproj');

// ============================================================
console.log('\n===== TEST 10: MPU cross-compile 테스트 =====');
// ============================================================

const cc = require('./lib/mpu/cross-compile');
const sdk = cc.detectSdkEnvironment();
assert('SDK detection returns object', typeof sdk === 'object');
assert('SDK has sdkPath field', 'sdkPath' in sdk);
assert('SDK has envVars field', typeof sdk.envVars === 'object');

// ============================================================
console.log('\n===== TEST 11: MPU Device Tree 테스트 =====');
// ============================================================

const dt = require('./lib/mpu/device-tree');
// DTS syntax test (dtc may not be installed on Windows)
const testDts = `
/dts-v1/;
/ {
    model = "Test Board";
    compatible = "test,board";
    chosen { bootargs = "console=ttymxc0,115200"; };
};
`;
fs.writeFileSync('_test.dts', testDts);
const dtResult = dt.validateDeviceTree('_test.dts');
assert('DTS validation returns result', typeof dtResult.valid === 'boolean');
assert('DTS has errors array', Array.isArray(dtResult.errors));
assert('DTS has warnings array', Array.isArray(dtResult.warnings));

const nodes = dt.parseDtsNodes('_test.dts');
assert('DTS node parsing returns object', typeof nodes === 'object');

fs.unlinkSync('_test.dts');

// ============================================================
console.log('\n===== TEST 12: MPU Yocto 분석 테스트 =====');
// ============================================================

const ya = require('./lib/mpu/yocto-analyzer');

const testLocalConf = `MACHINE ??= "imx6qsabresd"
DISTRO ?= "poky"
IMAGE_FEATURES += "ssh-server-openssh"
EXTRA_IMAGE_FEATURES += "debug-tweaks"
`;
fs.writeFileSync('_test_local.conf', testLocalConf);
const confResult = ya.parseLocalConf('_test_local.conf');
assert('local.conf MACHINE', confResult.machine === 'imx6qsabresd', 'got: ' + confResult.machine);
assert('local.conf DISTRO', confResult.distro === 'poky');
assert('local.conf features', confResult.imageFeatures.includes('ssh-server-openssh'));
fs.unlinkSync('_test_local.conf');

const testBbLayers = `BBLAYERS ?= " \\
  /opt/yocto/poky/meta \\
  /opt/yocto/poky/meta-poky \\
  /opt/yocto/sources/meta-freescale \\
  /opt/yocto/sources/meta-imx/meta-bsp \\
"`;
fs.writeFileSync('_test_bblayers.conf', testBbLayers);
const layers = ya.parseBbLayers('_test_bblayers.conf');
assert('bblayers count >= 3', layers.length >= 3, 'got ' + layers.length);
assert('has meta-freescale', layers.some(l => l.includes('meta-freescale')));
assert('has meta-imx', layers.some(l => l.includes('meta-imx')));
fs.unlinkSync('_test_bblayers.conf');

// ============================================================
console.log('\n===== TEST 13: Cross-Domain 시리얼 검증 테스트 =====');
// ============================================================

const cross = require('./lib/domain/cross');

const testMcuUart = `huart1.Init.BaudRate = 115200;
huart1.Init.WordLength = UART_WORDLENGTH_8B;
huart1.Init.StopBits = UART_STOPBITS_1;
huart1.Init.Parity = UART_PARITY_NONE;`;
fs.writeFileSync('_test_mcu.c', testMcuUart);

const testWpfSerial = `var port = new SerialPort("COM3");
port.BaudRate = 115200;
port.DataBits = 8;
port.StopBits = StopBits.One;
port.Parity = Parity.None;`;
fs.writeFileSync('_test_wpf.cs', testWpfSerial);

const serialResult = cross.validateSerialProtocol('_test_mcu.c', '_test_wpf.cs');
assert('serial match (same params)', serialResult.matched === true, 'mismatches: ' + serialResult.mismatches.join(', '));

// Test mismatch
const testWpfBad = `var port = new SerialPort("COM3");
port.BaudRate = 9600;
port.Parity = Parity.Even;`;
fs.writeFileSync('_test_wpf_bad.cs', testWpfBad);
const badResult = cross.validateSerialProtocol('_test_mcu.c', '_test_wpf_bad.cs');
assert('serial mismatch detected', badResult.matched === false);
assert('baud mismatch found', badResult.mismatches.some(m => m.includes('BaudRate')));

fs.unlinkSync('_test_mcu.c');
fs.unlinkSync('_test_wpf.cs');
fs.unlinkSync('_test_wpf_bad.cs');

// ============================================================
// SUMMARY
// ============================================================

console.log('\n' + '='.repeat(60));
console.log('TOTAL: ' + totalPass + ' PASS, ' + totalFail + ' FAIL');
if (totalFail > 0) {
  console.log('\nFAILURES:');
  failures.forEach(f => console.log('  ' + f));
}
console.log('='.repeat(60));

process.exit(totalFail > 0 ? 1 : 0);
