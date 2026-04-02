"""make/ 디렉토리에 통합 Makefile 생성.

Kconfig(kconfiglib) + 플랫폼별 cross-build + 하위 폴더 빌드 오케스트레이션.
"""
import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description="통합 Makefile 생성")
parser.add_argument("--output", default=".", help="make/ 디렉토리 경로")
args = parser.parse_args()

output = Path(args.output)
makefile = output / "Makefile"

if makefile.exists():
    print(f"EXISTS: {makefile}")
    print(f"기존 Makefile이 있습니다. 삭제 후 재실행하세요.")
    sys.exit(0)

# platform/ 디렉토리
platform_dir = output / "platform"
platform_dir.mkdir(parents=True, exist_ok=True)

# native.mk
native_mk = platform_dir / "native.mk"
if not native_mk.exists():
    native_mk.write_text('''# platform/native.mk — x86 native build
PLATFORM_NAME    := native
CROSS_COMPILE    :=
ARCH             := $(shell uname -m | sed 's/x86_64/x86_64/' | sed 's/aarch64/arm64/')
SYSROOT          :=
TOOLCHAIN_FILE   :=
KERNEL_MAKE_OPTS := ARCH=$(ARCH)
PLATFORM_CFLAGS  :=
PLATFORM_LDFLAGS :=
''', encoding="utf-8")

# configs/ 디렉토리
(output / "configs").mkdir(parents=True, exist_ok=True)

# cmake/ 디렉토리
(output / "cmake").mkdir(parents=True, exist_ok=True)

content = r'''# ══════════════════════════════════════════════════════════════
# Project Build System
# ══════════════════════════════════════════════════════════════
#
# Kconfig + 멀티 플랫폼 cross-build + 하위 폴더 빌드 오케스트레이션
#
# 사용법:
#   make menuconfig                    대화형 프로젝트 설정
#   make stm32mp2_full_defconfig       저장된 설정 로드
#   make savedefconfig NAME=xxx        현재 설정을 configs/에 저장
#   make all                           전체 빌드
#   make kernel                        커널 빌드
#   make kernel-menuconfig             커널 menuconfig
#   make application                   앱 빌드
#   make deploy                        타겟 배포
#   make help                          도움말

MAKE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# ══════════════════════════════════════════════════════════════
# Kconfig 설정 로드
# ══════════════════════════════════════════════════════════════

KCONFIG    := $(MAKE_DIR)Kconfig
DOT_CONFIG := $(MAKE_DIR).config

# .config가 있으면 로드
ifneq ($(wildcard $(DOT_CONFIG)),)
  include $(MAKE_DIR)include.mk
endif

# ── Kconfig 타겟 ──
.PHONY: menuconfig guiconfig oldconfig defconfig savedefconfig

menuconfig:
	@KCONFIG_CONFIG=$(DOT_CONFIG) python3 -m menuconfig $(KCONFIG)
	@$(MAKE) --no-print-directory _gen_include

guiconfig:
	@KCONFIG_CONFIG=$(DOT_CONFIG) python3 -m guiconfig $(KCONFIG)
	@$(MAKE) --no-print-directory _gen_include

oldconfig:
	@KCONFIG_CONFIG=$(DOT_CONFIG) python3 -m oldconfig $(KCONFIG)
	@$(MAKE) --no-print-directory _gen_include

# configs/ 에서 defconfig 로드: make xxx_defconfig
%_defconfig:
	@if [ ! -f $(MAKE_DIR)configs/$@ ]; then \
		echo "오류: configs/$@ 파일이 없습니다."; \
		echo "사용 가능한 defconfig:"; \
		ls $(MAKE_DIR)configs/*_defconfig 2>/dev/null | sed 's|.*/||' | sed 's|^|  |'; \
		exit 1; \
	fi
	@KCONFIG_CONFIG=$(DOT_CONFIG) python3 -m defconfig $(KCONFIG) $(MAKE_DIR)configs/$@
	@$(MAKE) --no-print-directory _gen_include
	@echo "설정 로드 완료: configs/$@"

# 현재 .config를 configs/에 저장
savedefconfig:
ifndef NAME
	$(error NAME을 지정하세요. 예: make savedefconfig NAME=stm32mp2_full)
endif
	@KCONFIG_CONFIG=$(DOT_CONFIG) python3 -m savedefconfig $(KCONFIG) $(MAKE_DIR)configs/$(NAME)_defconfig
	@echo "설정 저장 완료: configs/$(NAME)_defconfig"

# .config → include.mk 변환 (Makefile에서 사용할 수 있도록)
_gen_include:
	@python3 -c "\
import sys; \
lines = open('$(DOT_CONFIG)').readlines(); \
out = open('$(MAKE_DIR)include.mk', 'w'); \
[out.write(l.replace('=y\n','=y\n').replace('=m\n','=m\n')) for l in lines \
 if l.strip() and not l.startswith('#') and '=' in l]; \
out.close()" 2>/dev/null || true

# ══════════════════════════════════════════════════════════════
# 플랫폼 설정 로드
# ══════════════════════════════════════════════════════════════

# .config에서 CONFIG_PLATFORM 값 추출 (또는 커맨드라인 PLATFORM= 사용)
ifndef PLATFORM
  ifdef CONFIG_PLATFORM
    PLATFORM := $(patsubst "%",%,$(CONFIG_PLATFORM))
  endif
endif

ifdef PLATFORM
  -include $(MAKE_DIR)platform/$(PLATFORM).mk
endif

NPROC := $(shell nproc 2>/dev/null || echo 4)
ifdef CONFIG_PARALLEL_JOBS
  ifneq ($(CONFIG_PARALLEL_JOBS),0)
    NPROC := $(patsubst "%",%,$(CONFIG_PARALLEL_JOBS))
  endif
endif

# Verbose
ifdef CONFIG_VERBOSE
  ifeq ($(CONFIG_VERBOSE),y)
    V := 1
  endif
endif

# ccache
CCACHE :=
ifeq ($(CONFIG_USE_CCACHE),y)
  ifneq ($(shell which ccache 2>/dev/null),)
    CCACHE := ccache
    ifdef CROSS_COMPILE
      KERNEL_MAKE_OPTS += CC="ccache $(CROSS_COMPILE)gcc"
    else
      KERNEL_MAKE_OPTS += CC="ccache gcc"
    endif
  endif
endif

# Output 디렉토리
OUTPUT_DIR := $(MAKE_DIR)$(patsubst "%",%,$(CONFIG_OUTPUT_DIR))
ifeq ($(OUTPUT_DIR),$(MAKE_DIR))
  OUTPUT_DIR := $(MAKE_DIR)output
endif

# ══════════════════════════════════════════════════════════════
# 빌드 변수 (하위 Makefile에 전달)
# ══════════════════════════════════════════════════════════════

export PLATFORM
export CROSS_COMPILE
export ARCH
export SYSROOT
export NPROC
export CCACHE

ifdef KERNEL_MAKE_OPTS
  export KERNEL_MAKE_OPTS
endif

ifdef TOOLCHAIN_FILE
  export TOOLCHAIN_FILE
endif

ifdef PLATFORM_CFLAGS
  export PLATFORM_CFLAGS
endif

ifdef PLATFORM_LDFLAGS
  export PLATFORM_LDFLAGS
endif

# ══════════════════════════════════════════════════════════════
# 컴포넌트 빌드 타겟
# ══════════════════════════════════════════════════════════════

# .config에서 컴포넌트 경로 추출
KERNEL_DIR      := $(patsubst "%",%,$(CONFIG_KERNEL_DIR))
UBOOT_DIR       := $(patsubst "%",%,$(CONFIG_UBOOT_DIR))
APP_DIR         := $(patsubst "%",%,$(CONFIG_APPLICATION_DIR))
KERNEL_DEFCONFIG:= $(patsubst "%",%,$(CONFIG_KERNEL_DEFCONFIG))
UBOOT_DEFCONFIG := $(patsubst "%",%,$(CONFIG_UBOOT_DEFCONFIG))

# 활성화된 컴포넌트 목록
COMPONENTS :=
ifeq ($(CONFIG_BUILD_KERNEL),y)
  COMPONENTS += kernel
endif
ifeq ($(CONFIG_BUILD_UBOOT),y)
  COMPONENTS += uboot
endif
ifeq ($(CONFIG_BUILD_APPLICATION),y)
  COMPONENTS += application
endif

.PHONY: all clean $(COMPONENTS)

all: _check_config $(COMPONENTS)
	@echo ""
	@echo "══════════════════════════════════"
	@echo " 빌드 완료: $(COMPONENTS)"
	@echo " 플랫폼: $(PLATFORM)"
	@echo "══════════════════════════════════"

# ── 설정 체크 ──
.PHONY: _check_config _check_platform

_check_config:
	@if [ ! -f $(DOT_CONFIG) ]; then \
		echo ""; \
		echo "╔══════════════════════════════════════════════╗"; \
		echo "║  .config가 없습니다.                          ║"; \
		echo "║                                              ║"; \
		echo "║  먼저 설정을 생성하세요:                      ║"; \
		echo "║    make menuconfig                           ║"; \
		echo "║    make xxx_defconfig                        ║"; \
		echo "║                                              ║"; \
		echo "║  사용 가능한 defconfig:                       ║"; \
		ls $(MAKE_DIR)configs/*_defconfig 2>/dev/null | sed 's|.*/||' | sed 's|^|║    |;s|$$| ║|' || echo "║    (없음)                                  ║"; \
		echo "╚══════════════════════════════════════════════╝"; \
		echo ""; \
		exit 1; \
	fi

_check_platform:
	@if [ -z "$(PLATFORM)" ]; then \
		echo "오류: PLATFORM이 설정되지 않았습니다."; \
		echo ".config의 CONFIG_PLATFORM 또는 make PLATFORM=xxx 를 확인하세요."; \
		exit 1; \
	fi

# ══════════════════════════════════════════════════════════════
# Kernel
# ══════════════════════════════════════════════════════════════

.PHONY: kernel kernel-menuconfig kernel-defconfig kernel-dtbs kernel-modules kernel-modules-dir kernel-clean

kernel: _check_config _check_platform
ifeq ($(KERNEL_DIR),)
	$(error CONFIG_KERNEL_DIR이 설정되지 않았습니다. menuconfig에서 설정하세요)
endif
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) -j$(NPROC) Image dtbs modules

kernel-menuconfig: _check_platform
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) menuconfig

kernel-defconfig: _check_platform
ifneq ($(KERNEL_DEFCONFIG),)
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) $(KERNEL_DEFCONFIG)
else
	$(error CONFIG_KERNEL_DEFCONFIG이 설정되지 않았습니다)
endif

kernel-dtbs: _check_platform
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) -j$(NPROC) dtbs

kernel-modules: _check_platform
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) -j$(NPROC) modules

# 특정 디렉토리만: make kernel-modules-dir M=drivers/misc/mycompany/
kernel-modules-dir: _check_platform
ifndef M
	$(error M을 지정하세요. 예: M=drivers/misc/mycompany/)
endif
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) -j$(NPROC) modules M=$(M)

kernel-clean: _check_platform
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) clean

# ══════════════════════════════════════════════════════════════
# U-Boot
# ══════════════════════════════════════════════════════════════

.PHONY: uboot uboot-menuconfig uboot-defconfig uboot-clean

uboot: _check_config _check_platform
ifeq ($(UBOOT_DIR),)
	$(error CONFIG_UBOOT_DIR이 설정되지 않았습니다)
endif
	$(MAKE) -C $(UBOOT_DIR) $(KERNEL_MAKE_OPTS) -j$(NPROC)

uboot-menuconfig: _check_platform
	$(MAKE) -C $(UBOOT_DIR) $(KERNEL_MAKE_OPTS) menuconfig

uboot-defconfig: _check_platform
ifneq ($(UBOOT_DEFCONFIG),)
	$(MAKE) -C $(UBOOT_DIR) $(KERNEL_MAKE_OPTS) $(UBOOT_DEFCONFIG)
else
	$(error CONFIG_UBOOT_DEFCONFIG이 설정되지 않았습니다)
endif

uboot-clean: _check_platform
	$(MAKE) -C $(UBOOT_DIR) $(KERNEL_MAKE_OPTS) clean

# ══════════════════════════════════════════════════════════════
# Application (make 또는 cmake)
# ══════════════════════════════════════════════════════════════

APP_BUILD_DIR := $(MAKE_DIR)build/app-$(PLATFORM)

.PHONY: application application-clean

application: _check_config
ifeq ($(APP_DIR),)
	$(error CONFIG_APPLICATION_DIR이 설정되지 않았습니다)
endif
	@# CMakeLists.txt가 있으면 cmake, Makefile이 있으면 make
	@if [ -f $(APP_DIR)/CMakeLists.txt ]; then \
		if [ -n "$(TOOLCHAIN_FILE)" ]; then \
			cmake -B $(APP_BUILD_DIR) -S $(APP_DIR) -DCMAKE_TOOLCHAIN_FILE=$(MAKE_DIR)$(TOOLCHAIN_FILE); \
		else \
			cmake -B $(APP_BUILD_DIR) -S $(APP_DIR); \
		fi; \
		cmake --build $(APP_BUILD_DIR) -j$(NPROC); \
	elif [ -f $(APP_DIR)/Makefile ]; then \
		$(MAKE) -C $(APP_DIR) \
			CROSS_COMPILE=$(CROSS_COMPILE) \
			ARCH=$(ARCH) \
			SYSROOT=$(SYSROOT) \
			CFLAGS="$(PLATFORM_CFLAGS)" \
			LDFLAGS="$(PLATFORM_LDFLAGS)" \
			-j$(NPROC); \
	else \
		echo "오류: $(APP_DIR)에 CMakeLists.txt 또는 Makefile이 없습니다."; \
		exit 1; \
	fi

application-clean:
	@rm -rf $(APP_BUILD_DIR)
	@if [ -f $(APP_DIR)/Makefile ]; then \
		$(MAKE) -C $(APP_DIR) clean 2>/dev/null || true; \
	fi

# ══════════════════════════════════════════════════════════════
# 범용 컴포넌트 빌드 (Kconfig에 추가한 임의 컴포넌트)
# ══════════════════════════════════════════════════════════════

# make build-{dirname}: 해당 디렉토리의 Makefile 또는 CMakeLists.txt를 빌드
build-%: _check_config _check_platform
	@DIR="../$*"; \
	if [ -f $$DIR/CMakeLists.txt ]; then \
		if [ -n "$(TOOLCHAIN_FILE)" ]; then \
			cmake -B $(MAKE_DIR)build/$*-$(PLATFORM) -S $$DIR -DCMAKE_TOOLCHAIN_FILE=$(MAKE_DIR)$(TOOLCHAIN_FILE); \
		else \
			cmake -B $(MAKE_DIR)build/$*-$(PLATFORM) -S $$DIR; \
		fi; \
		cmake --build $(MAKE_DIR)build/$*-$(PLATFORM) -j$(NPROC); \
	elif [ -f $$DIR/Makefile ]; then \
		$(MAKE) -C $$DIR CROSS_COMPILE=$(CROSS_COMPILE) ARCH=$(ARCH) \
			CFLAGS="$(PLATFORM_CFLAGS)" LDFLAGS="$(PLATFORM_LDFLAGS)" -j$(NPROC); \
	else \
		echo "오류: $$DIR에 빌드 파일이 없습니다."; \
		exit 1; \
	fi

# ══════════════════════════════════════════════════════════════
# 배포
# ══════════════════════════════════════════════════════════════

TARGET_IP   := $(patsubst "%",%,$(CONFIG_TARGET_IP))
DEPLOY_PATH := $(patsubst "%",%,$(CONFIG_DEPLOY_PATH))
BOOT_PATH   := $(patsubst "%",%,$(CONFIG_DEPLOY_BOOT_PATH))

.PHONY: deploy deploy-kernel deploy-modules deploy-dtbs deploy-module deploy-app

deploy: deploy-kernel deploy-modules deploy-dtbs
	@echo ""
	@echo "배포 완료 → $(TARGET_IP)"

deploy-kernel: _check_platform
	scp $(KERNEL_DIR)/arch/$(ARCH)/boot/Image root@$(TARGET_IP):$(BOOT_PATH)/

deploy-modules: _check_platform
	$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) INSTALL_MOD_PATH=/tmp/_modules modules_install
	rsync -avz /tmp/_modules/lib/modules/ root@$(TARGET_IP):/lib/modules/
	ssh root@$(TARGET_IP) depmod -a
	rm -rf /tmp/_modules

deploy-dtbs: _check_platform
	@find $(KERNEL_DIR)/arch/$(ARCH)/boot/dts/ -name "*.dtb" -newer $(KERNEL_DIR)/arch/$(ARCH)/boot/dts/.timestamp 2>/dev/null \
		| xargs -r scp {} root@$(TARGET_IP):$(BOOT_PATH)/ 2>/dev/null || \
		echo "DTB 변경 없음 (또는 경로 확인 필요)"

deploy-module: _check_platform
ifndef M
	$(error M을 지정하세요. 예: M=drivers/misc/mycompany/my_sensor.ko)
endif
	scp $(KERNEL_DIR)/$(M) root@$(TARGET_IP):/tmp/
	ssh root@$(TARGET_IP) "rmmod $$(basename $(M) .ko) 2>/dev/null; insmod /tmp/$$(basename $(M))"

deploy-app:
	@if [ -d $(APP_BUILD_DIR) ]; then \
		ssh root@$(TARGET_IP) "mkdir -p $(DEPLOY_PATH)"; \
		rsync -avz $(APP_BUILD_DIR)/ root@$(TARGET_IP):$(DEPLOY_PATH)/; \
	else \
		echo "앱 빌드 결과가 없습니다. 먼저 make application을 실행하세요."; \
	fi

# ══════════════════════════════════════════════════════════════
# 산출물 수집
# ══════════════════════════════════════════════════════════════

COLLECT_DIR := $(OUTPUT_DIR)/$(PLATFORM)

.PHONY: collect collect-clean

collect: _check_config _check_platform
	@echo "산출물 수집 → $(COLLECT_DIR)"
	@mkdir -p $(COLLECT_DIR)/{boot,modules,app}
	@# ── Kernel Image ──
	@if [ -n "$(KERNEL_DIR)" ] && [ -f $(KERNEL_DIR)/arch/$(ARCH)/boot/Image ]; then \
		cp $(KERNEL_DIR)/arch/$(ARCH)/boot/Image $(COLLECT_DIR)/boot/; \
		echo "  [boot] Image"; \
	fi
	@if [ -n "$(KERNEL_DIR)" ] && [ -f $(KERNEL_DIR)/arch/$(ARCH)/boot/zImage ]; then \
		cp $(KERNEL_DIR)/arch/$(ARCH)/boot/zImage $(COLLECT_DIR)/boot/; \
		echo "  [boot] zImage"; \
	fi
	@# ── DTB ──
	@if [ -n "$(KERNEL_DIR)" ]; then \
		find $(KERNEL_DIR)/arch/$(ARCH)/boot/dts/ -name "*.dtb" -newer $(KERNEL_DIR)/arch/$(ARCH)/boot/Image 2>/dev/null \
			| while read f; do cp "$$f" $(COLLECT_DIR)/boot/; echo "  [boot] $$(basename $$f)"; done; \
	fi
	@# ── Modules ──
	@if [ -n "$(KERNEL_DIR)" ]; then \
		$(MAKE) -C $(KERNEL_DIR) $(KERNEL_MAKE_OPTS) INSTALL_MOD_PATH=$(COLLECT_DIR)/modules modules_install 2>/dev/null \
			&& echo "  [modules] installed" || true; \
	fi
	@# ── U-Boot ──
	@if [ -n "$(UBOOT_DIR)" ] && [ -f $(UBOOT_DIR)/u-boot.bin ]; then \
		cp $(UBOOT_DIR)/u-boot.bin $(COLLECT_DIR)/boot/; \
		echo "  [boot] u-boot.bin"; \
	fi
	@# ── Application ──
	@if [ -d $(APP_BUILD_DIR) ]; then \
		cp -r $(APP_BUILD_DIR)/* $(COLLECT_DIR)/app/ 2>/dev/null || true; \
		echo "  [app] copied"; \
	fi
	@# ── 버전 정보 ──
	@echo "Platform: $(PLATFORM)" > $(COLLECT_DIR)/version.txt
	@echo "Date: $$(date -Iseconds)" >> $(COLLECT_DIR)/version.txt
	@echo "ARCH: $(ARCH)" >> $(COLLECT_DIR)/version.txt
	@if [ -n "$(KERNEL_DIR)" ]; then \
		echo "Kernel: $$(cd $(KERNEL_DIR) && git describe --always --dirty 2>/dev/null || echo unknown)" >> $(COLLECT_DIR)/version.txt; \
	fi
	@if [ -n "$(UBOOT_DIR)" ]; then \
		echo "U-Boot: $$(cd $(UBOOT_DIR) && git describe --always --dirty 2>/dev/null || echo unknown)" >> $(COLLECT_DIR)/version.txt; \
	fi
	@echo ""
	@echo "════════════════════════════════════"
	@echo " 산출물 수집 완료"
	@echo " 위치: $(COLLECT_DIR)"
	@echo "════════════════════════════════════"
	@cat $(COLLECT_DIR)/version.txt

collect-clean:
	rm -rf $(OUTPUT_DIR)

# ══════════════════════════════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════════════════════════════

.PHONY: info clean platforms configs help

info:
	@echo "══════════════════════════════════════"
	@echo " Platform:       $(PLATFORM)"
	@echo " ARCH:           $(ARCH)"
	@echo " CROSS_COMPILE:  $(CROSS_COMPILE)"
	@echo " SYSROOT:        $(SYSROOT)"
	@echo " Components:     $(COMPONENTS)"
	@echo " KERNEL_DIR:     $(KERNEL_DIR)"
	@echo " UBOOT_DIR:      $(UBOOT_DIR)"
	@echo " APP_DIR:        $(APP_DIR)"
	@echo " TARGET_IP:      $(TARGET_IP)"
	@echo " JOBS:           $(NPROC)"
	@echo " ccache:         $(if $(CCACHE),ON ($(shell ccache --version 2>/dev/null | head -1)),OFF)"
	@echo " OUTPUT_DIR:     $(OUTPUT_DIR)"
	@echo "══════════════════════════════════════"

clean: kernel-clean uboot-clean application-clean collect-clean

platforms:
	@echo "사용 가능한 플랫폼:"
	@ls $(MAKE_DIR)platform/*.mk 2>/dev/null | sed 's|.*/||;s|\.mk||' | sed 's|^|  |'

configs:
	@echo "사용 가능한 defconfig:"
	@ls $(MAKE_DIR)configs/*_defconfig 2>/dev/null | sed 's|.*/||' | sed 's|^|  |' || echo "  (없음)"

help:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════════════╗"
	@echo "║ Project Build System                                             ║"
	@echo "╠═══════════════════════════════════════════════════════════════════╣"
	@echo "║                                                                   ║"
	@echo "║ 설정:                                                             ║"
	@echo "║   make menuconfig              프로젝트 설정 (대화형)              ║"
	@echo "║   make xxx_defconfig           configs/에서 설정 로드              ║"
	@echo "║   make savedefconfig NAME=xxx  현재 설정 저장                     ║"
	@echo "║   make configs                 사용 가능한 defconfig 목록          ║"
	@echo "║                                                                   ║"
	@echo "║ 커널:                                                             ║"
	@echo "║   make kernel                  전체 커널 빌드                     ║"
	@echo "║   make kernel-menuconfig       커널 menuconfig                   ║"
	@echo "║   make kernel-defconfig        커널 defconfig 생성                ║"
	@echo "║   make kernel-modules          모듈 전체                          ║"
	@echo "║   make kernel-modules-dir M=path  특정 디렉토리 모듈              ║"
	@echo "║   make kernel-dtbs             DTB 빌드                          ║"
	@echo "║                                                                   ║"
	@echo "║ U-Boot:                                                           ║"
	@echo "║   make uboot                   U-Boot 빌드                       ║"
	@echo "║   make uboot-menuconfig        U-Boot menuconfig                 ║"
	@echo "║   make uboot-defconfig         U-Boot defconfig 생성              ║"
	@echo "║                                                                   ║"
	@echo "║ 앱:                                                               ║"
	@echo "║   make application             앱 빌드 (cmake/make 자동 감지)     ║"
	@echo "║   make build-{dirname}         임의 디렉토리 빌드                  ║"
	@echo "║                                                                   ║"
	@echo "║ 빌드:                                                             ║"
	@echo "║   make all                     활성화된 컴포넌트 전체 빌드         ║"
	@echo "║   make clean                   전체 clean                         ║"
	@echo "║                                                                   ║"
	@echo "║ 배포:                                                             ║"
	@echo "║   make deploy                  커널+모듈+DTB 전체 배포            ║"
	@echo "║   make deploy-module M=path    모듈 하나 배포+insmod              ║"
	@echo "║   make deploy-app              앱 배포                            ║"
	@echo "║                                                                   ║"
	@echo "║ 산출물:                                                           ║"
	@echo "║   make collect                 빌드 산출물을 output/에 수집        ║"
	@echo "║   make collect-clean           output/ 삭제                       ║"
	@echo "║                                                                   ║"
	@echo "║ 유틸:                                                             ║"
	@echo "║   make info                    현재 설정 출력 (ccache 상태 포함)   ║"
	@echo "║   make platforms               플랫폼 목록                        ║"
	@echo "║   make help                    이 도움말                          ║"
	@echo "║                                                                   ║"
	@echo "║ 플랫폼 전환: make PLATFORM=xxx (또는 menuconfig에서 설정)          ║"
	@echo "╚═══════════════════════════════════════════════════════════════════╝"
	@echo ""
'''

makefile.write_text(content, encoding="utf-8")
print(f"CREATED: {makefile}")
