# Freeze diagnostics — scott-Blade-15

Intermittent full-system hard lockups: screen freezes, no input, requires hard
power-off. Roughly weekly. Started investigating 2026-10-02.

## Machine

| | |
|---|---|
| Model | Razer Blade 15 Advanced (Early 2020), RZ09-033/CH551 |
| BIOS | **1.06, 09/16/2020** — newest offered by fwupd (`version 106`) |
| CPU | i7-10875H |
| GPU | Intel UHD (CometLake-H GT2) + NVIDIA RTX 2070 SUPER Max-Q |
| OS | Ubuntu 24.04.4, kernel 7.0.0-31-generic (HWE) |
| NVIDIA | 580.173.02 proprietary, X11, `prime-select on-demand` |
| Keyboard | USB HID (`1532:0253`) — **no i8042/PS/2 controller** |
| Network | Intel CNVi Wi-Fi only, no ethernet |
| Serial | none (8250 driver registers 32 slots, no UART discovered) |

## SysRq emergency cheat sheet

**Keep a copy on your phone — the screen will be dead when you need this.**

Hold `Alt` the whole time. `SysRq` = `Fn`+`PrtSc`. Tap letters one at a time.

| Step | Keys | Why |
|---|---|---|
| 1 | `Alt`+`SysRq`+`r`, then `Ctrl`+`Alt`+`F3` | Take keyboard back from X, try for a text console. **If you get a login prompt the kernel is alive** → GPU/display hang, not a lockup. Run `journalctl -k -n 50` right there. |
| 2 | `Alt`+`SysRq`+`l` | Backtrace of all active CPUs. This is the one that names the culprit. |
| 3 | `Alt`+`SysRq`+`w` | Dump tasks blocked in uninterruptible sleep. |
| 4 | `Alt`+`SysRq`+`s` | Sync — flushes steps 2–3 to disk. Wait a few seconds. |
| 5 | `Alt`+`SysRq`+`u` | Remount read-only. |
| 6 | `Alt`+`SysRq`+`b` | Reboot. |

Steps 4–6 (`s`-`u`-`b`) already worked at the stock mask, so they are not the
experiment. Steps 1–3 are.

### After it comes back up

```bash
journalctl -k -b -1 -n 200 --no-pager
```

Note: plain `dmesg` will not work (`kernel.dmesg_restrict = 1`). Use
`journalctl -k` — readable because the user is in the `adm` group.

### Interpreting the outcome

| Outcome | Means | Next step |
|---|---|---|
| Backtraces present | We have the answer | Read the stack |
| Nothing logged, but `b` rebooted | Kernel alive, too wedged to reach disk. Rules out dead PCIe fabric → software deadlock | kdump becomes viable |
| No response at all | Hang is below the software layer | Nothing software-side will catch it. Shift to BIOS + `PreserveVideoMemoryAllocations` |

## Change applied 2026-10-02

`/etc/sysctl.d/99-sysrq-debug.conf` — sets `kernel.sysrq = 190`, overriding
`176` from `10-magic-sysrq.conf` (owned by `procps`, a dpkg conffile — hence the
drop-in rather than an edit).

```
190 = 128 reboot/poweroff + 32 remount-ro + 16 sync
    +   8 debugging dumps   <-- enables SysRq l / w / t
    +   4 keyboard control  <-- enables SysRq r (unraw)
    +   2 console loglevel
```

Bit **64 (signalling) deliberately omitted** — it allows SIGKILLing the screen
lock from the physical keyboard, and `s`-`u`-`b` does not need it.

Revert: `sudo rm /etc/sysctl.d/99-sysrq-debug.conf && sudo sysctl --system`

Verified working before the change (at mask 176, bit 16):
```
sysrq: Emergency Sync
Emergency Sync complete
```

## Evidence so far

Three of the last 19 boots ended with no shutdown sequence — **Sep 18 20:17,
Sep 21 18:28, Oct 2 11:42** (confirmed independently by `last -x`).
All three sit within an hour of an NVIDIA power-state transition.

**Oct 2 (the freeze that started this).** Journal stops mid-line at
`11:42:20.530652`. No panic, no oops, no watchdog warning — nothing. Machine was
idle: 88.6% CPU idle, 40% memory, 0 swap, 0 blocked tasks, load 3.03. No MCE, no
thermal trip, no NVMe/ext4 errors, clean mount next boot. Had resumed from a
41-hour `deep` suspend at 11:02:50, ~40 min earlier. On battery at the time.

**Sep 18 — the informative one.** Hibernate failed, then the NVIDIA driver could
not restore GPU state:

```
PM: Image saving failed: -28
WARNING: nvidia/nv.c:4410 at nv_restore_user_channels+0x57/0x200 [nvidia]
WARNING: nvidia/nv.c:4638 at nv_set_system_power_state+0x2f2/0x490 [nvidia]
nvidia-modeset: ERROR: GPU:0: Failed detecting connected display devices  (x3)
```

Ran 21 more minutes, then froze hard.

**Sep 21.** Entered hibernation 18:27:51, log ends 17s later, never came back.

### Chronic background faults

Every resume, from the 2020 firmware:
```
ACPI Error: No handler for Region [VRTC] [SystemCMOS]
ACPI Error: Aborting method \_SB.PCI0.LPCB.EC0.RTEC (AE_NOT_EXIST)
ACPI Error: Aborting method \_WAK (AE_NOT_EXIST)     <-- the ACPI wake handler
ACPI: thermal: [Firmware Bug]: Invalid critical threshold (-274000)
```

Every boot:
```
nvidia-gpu 0000:01:00.3: i2c timeout error e0000000
ucsi_ccg 1-0008: probe with driver ucsi_ccg failed with error -110
```

## Ruled out

- **Resource exhaustion** — sysstat sampled to within 2 min of the freeze, idle.
- **Storage/filesystem** — no I/O errors, no ext4 recovery needed.
- **Thermal** — no throttling or critical-temp events.
- **Runtime D3 / `DynamicPowerManagement=2`** — *inert on this setup.* Xorg holds
  a reference on the dGPU for the whole session, so it never runtime-suspends:
  `runtime_suspended_time: 0`, `runtime_active_time` == uptime, `runtime_usage: 1`.
  Toggling it would test nothing.
- **netconsole** — software is present (`CONFIG_NETCONSOLE=m`, `CONFIG_NETPOLL=y`)
  but `mac80211`/`iwlwifi` does not implement netpoll, and there is no ethernet.
  USB-C dongles do not help; the USB stack cannot be polled at panic time.
- **Serial console** — no physical port.

## Still on the table (not done)

1. **Mask hibernate.** Two of three freezes were hibernate-related and hibernate
   is *already broken* (`-28`). Zero functional loss, instantly reversible.
   ```bash
   sudo systemctl mask systemd-hybrid-sleep.service systemd-hibernate.service \
     hibernate.target hybrid-sleep.target suspend-then-hibernate.target
   sudo systemctl disable nvidia-hibernate.service
   ```
2. **Disable VRAM save/restore** — the path that actually threw the Sep 18 WARNs.
   Cost: GPU apps may break across resume (annoying, recoverable) instead of
   locking up.
   ```bash
   sudo sed -i 's/NVreg_PreserveVideoMemoryAllocations=1/NVreg_PreserveVideoMemoryAllocations=0/' \
     /etc/modprobe.d/nvidia-graphics-drivers-kms.conf
   sudo update-initramfs -u    # required — initramfs carries a copy
   # reboot, then verify:
   grep PreserveVideo /proc/driver/nvidia/params    # want 0
   ```
3. **Boot an older kernel** from the GRUB advanced menu (6.14.0-37 or 6.8.0-52
   are installed). Zero config, revert by rebooting.
4. **kdump** — only worth it if a freeze shows the kernel was still alive.
   Needs `kdump-tools`, a `crashkernel=` reservation (~256–512 MB permanently),
   and `hardlockup_panic=1` / `panic_on_oops=1` to convert hangs into panics.
5. **efi-pstore** — *advise against.* Only 128 KB free in `efivarfs`, on a
   consumer UEFI with known-buggy ACPI tables. Bricking risk outweighs the value.

## Open questions

- `PM: Image saving failed: -28` (ENOSPC) makes no sense on its face: swap is a
  16.8 G partition, empty, `resume=/dev/nvme0n1p7` set correctly, and the image
  was only ~3.4 G. It failed at 70% written. Something is wrong in the
  image-write path, not capacity.
- Something invokes **hybrid-sleep** that was never configured. GNOME says
  `sleep-inactive-battery-type: 'suspend'`, `sleep-inactive-ac-type: 'nothing'`,
  yet `systemd-hybrid-sleep.service` ran on Sep 18 and Sep 21. On Sep 21 it was
  preceded by `Delay lock is active (UID 1000/scott, PID 3873/gsd-power) but
  inhibitor timeout is reached`. Critical-battery handling is the plausible
  explanation — unconfirmed. Note anacron was skipped for `ConditionACPower=true`
  at 11:32 on Oct 2, so the machine was on battery for that freeze too.
- `workqueue: delayed_fput hogged CPU for >10000us` appeared on the current boot.
  Benign alone; watch for it near future freezes.
