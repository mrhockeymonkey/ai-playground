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
| 1 | `Alt`+`SysRq`+`r`, **release every key**, then `Ctrl`+`Alt`+`F3` | Take keyboard back from X, try for a text console. **If you get a login prompt the kernel is alive** → GPU/display hang, not a lockup. Run `journalctl -k -n 50` right there. **No prompt? Carry on to step 2 anyway.** |
| 2 | `Alt`+`SysRq`+`l` | Backtrace of all active CPUs. This is the one that names the culprit. |
| 3 | `Alt`+`SysRq`+`w` | Dump tasks blocked in uninterruptible sleep. |
| 4 | `Alt`+`SysRq`+`s` | Sync — flushes steps 2–3 to disk. Wait a few seconds. |
| 5 | `Alt`+`SysRq`+`u` | Remount read-only. |
| 6 | `Alt`+`SysRq`+`b` | Reboot. |

Steps 4–6 (`s`-`u`-`b`) already worked at the stock mask, so they are not the
experiment. Steps 1–3 are.

**Step 1 notes (rehearsed on a healthy boot 2026-10-20):**

- `Ctrl`+`Alt`+`F3` (no `Fn`) gives the tty3 login prompt. Back to the desktop
  with `Ctrl`+`Alt`+`F2` — the GNOME session is on tty2.
- Without `r` first, F3 is read by X, which then asks the kernel to switch. A
  frozen X ignores it, so **F3 without `r` proves nothing**. Release `Fn`/`Alt`
  after `r`, or F3 becomes a media key.
- No prompt even after `r` is still ambiguous: the console may have switched but
  a hung GPU never repaints. **`b` is the real liveness test** — if it reboots,
  the kernel was alive.
- Verify on a healthy boot:
  ```bash
  journalctl -k -b 0 --no-pager | grep sysrq          # "Keyboard mode set to system default"
  systemctl status getty@tty3 --no-pager | head -3    # "active (running)" = prompt was drawn
  ```

**After a freeze, write down:** did you press `r` before F3? Did a login prompt
appear? Did `b` reboot, or did it need the power button?

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
All three sit within an hour of an NVIDIA power-state transition. A fourth
followed on **Oct 20 11:30** (below).

**Oct 2 (the freeze that started this).** Journal stops mid-line at
`11:42:20.530652`. No panic, no oops, no watchdog warning — nothing. Machine was
idle: 88.6% CPU idle, 40% memory, 0 swap, 0 blocked tasks, load 3.03. No MCE, no
thermal trip, no NVMe/ext4 errors, clean mount next boot. Had resumed from a
41-hour `deep` suspend at 11:02:50, ~40 min earlier. On battery at the time.

**Oct 20 (first freeze with SysRq 190 in place).** Journal stops at
`11:30:53.53`, last lines ordinary Chrome/VS Code chatter. Sequence:

| Time | Event |
|---|---|
| Oct 19 17:20:51 | `PM: suspend entry (deep)` |
| Oct 20 11:26:48 | resumed (~18 h) |
| 11:29:41 | `deep` suspend again |
| 11:29:53 | resumed (12 s) |
| 11:30:53 | **journal stops — ~60 s after resume** |

No hibernate, no NVIDIA WARN, no `PM:` errors, **no `sysrq:` lines at all**.
`Ctrl`+`Alt`+`F3` gave no console; unclear whether `r` was pressed first, so
this does not yet distinguish kernel-dead from display-hang. Hard power-off,
next boot 11:56:43.

**Hibernation: 7 successes, 2 failures, 1 fatal.** Hibernate is *not* broken --
it works ~70% of the time. A success shows `hibernation entry` and
`hibernation exit` separated by however long the machine was off; a failure
shows them seconds apart because the kernel aborted and unwound.

| Attempt | Entry -> Exit | Result |
|---|---|---|
| Sep 4 23:41 -> Sep 8 11:59 | 3.5 days | success |
| Sep 17 21:39 -> Sep 18 10:11 | overnight | success |
| **Sep 18 19:55:35 -> 19:55:54** | **19 sec** | FAILED `Image saving failed: -28` |
| Sep 20 13:23 -> 13:37 | 14 min | success |
| Sep 20 20:51 -> Sep 21 13:31 | overnight | success |
| **Sep 21 17:49:03 -> 17:49:16** | **13 sec** | FAILED `PM: Cannot get swap writer` |
| Sep 21 18:27:51 -> *never* | -- | DIED mid-hibernate |
| Sep 22 11:37 -> Sep 23 06:55 | overnight | success |
| Sep 23 21:50 -> Sep 24 11:06 | overnight | success |
| Sep 26 15:26 -> Sep 27 15:06 | overnight | success |

**The correlation is with hibernate ABORTING, not hibernating.**
Both failures were followed by the NVIDIA WARN pair and then a hard freeze
(Sep 18: failed 19:55, froze 20:17, 22 min. Sep 21: failed 17:49, dead by
18:27, 38 min). All 7 successes were followed by nothing. Boot -2 had three
successful hibernates, zero failures, and ended in a clean shutdown.
2-for-2 on failure->freeze; 0-for-7 on success->freeze.

### The failure chain

1. `nvidia-sleep.sh` writes `/proc/driver/nvidia/suspend`; driver saves VRAM,
   parks the GPU.
2. Kernel swap writer fails -> hibernation aborts.
3. Driver told to resume -> `nv_set_system_power_state` ->
   `nv_restore_user_channels` -> **WARN**, channels not restored
   (`RAX: 0x11` in both traces: an error where zero was expected).
4. `nvidia-modeset` can no longer enumerate displays. GPU in undefined state.
5. Work continues on a half-restored GPU; hard lockup 20-40 min later.

```
PM: Image saving failed: -28                   (Sep 18)
PM: Cannot get swap writer                     (Sep 21)
WARNING: nvidia/nv.c:4410 at nv_restore_user_channels+0x57/0x200 [nvidia]
WARNING: nvidia/nv.c:4638 at nv_set_system_power_state+0x2f2/0x490 [nvidia]
nvidia-modeset: ERROR: GPU:0: Failed detecting connected display devices  (x3)
```

### Why the swap writer fails: capacity, not corruption

```
Swap total:              16.76 GiB   (/dev/nvme0n1p7)
/sys/power/image_size:    5.42 GiB   (kernel target max image)
Observed image sizes:     3.8 - 4.8 GiB
RAM:                     15.5 GiB
```

Peak swap *usage* from retained sysstat files:

```
sa22  8.64 GiB (51.5%)    sa25 10.68 GiB (63.7%)    sa28 11.06 GiB (66.0%)
sa23  8.26 GiB (49.3%)    sa26  7.13 GiB (42.5%)    sa29 11.23 GiB (67.0%)
sa24 11.12 GiB (66.3%)    sa27 11.73 GiB (70.0%)
```

At the 11.73 GiB peak, free swap is 5.03 GiB and the image needs up to
4.81 GiB -- a 220 MB margin. The image must go to the `resume=` device and fit
in the portion not already holding swapped-out pages. Both errors are the same
wall hit at different moments: `Cannot get swap writer` = couldn't claim enough
blocks to start; `-28` = ENOSPC partway through (died at 70% of a 4.04 GiB
image, so ~2.8 GiB written, so swap was ~84% full).

**This is why it correlates with end-of-day hibernation** -- that is when a
day of Docker/Android Studio/Thunderbird/Chrome has swap at its fullest.
Light day: works. Heavy day: image doesn't fit, abort, GPU mangled, freeze.

Memory is tight in general: `Committed_AS 25433060 kB` vs
`CommitLimit 25692052 kB` (99%), 13 minutes into a fresh boot.

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

1. **~~Mask hibernate~~ -- WITHDRAWN.** Originally recommended on the false
   premise that hibernate was broken. It works ~70% of the time and is used
   daily; masking it would cost real function. The trigger is swap capacity,
   which is fixable while keeping hibernate.
1b. **Make the image always fit** (root fix, cheap). Lower
   `/sys/power/image_size` so the kernel frees pages harder before snapshotting
   and asks for less swap. Reduces the failure rate; does not eliminate it.
   ```bash
   cat /sys/power/image_size              # currently 5819949056
   # e.g. echo 3221225472 > /sys/power/image_size   (3 GiB); persist via tmpfiles.d
   ```
2. **Disable VRAM save/restore** — removes the exact code path that WARNs, so a
   failed hibernate becomes just a failed hibernate instead of a freeze.
   Cost: GPU apps may break across resume (annoying, recoverable).
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
5. **More RAM** — structural fix. The RZ09-0330 has two SO-DIMM slots; 16 -> 32 GB
   would largely stop the heavy swapping that causes the aborts.
6. **Report the NVIDIA bug** — 580.173.02 should unwind cleanly when hibernation
   fails rather than corrupting GPU state. File with both backtraces.
7. **efi-pstore** — *advise against.* Only 128 KB free in `efivarfs`, on a
   consumer UEFI with known-buggy ACPI tables. Bricking risk outweighs the value.

## Open questions

- **The Oct 2 and Oct 20 freezes are still unexplained.** No hibernate, no
  NVIDIA WARN, 40 min and ~1 min after a plain `deep` resume. Two of four
  freezes now fit this pattern, so a second cause in the plain suspend/resume
  path is increasingly likely, separate from the hibernate-abort chain. Both
  were preceded by a long suspend. This is what the SysRq setup is for.
- Something invokes **hybrid-sleep** that was never configured. GNOME says
  `sleep-inactive-battery-type: 'suspend'`, `sleep-inactive-ac-type: 'nothing'`,
  yet `systemd-hybrid-sleep.service` ran on Sep 18 and Sep 21. On Sep 21 it was
  preceded by `Delay lock is active (UID 1000/scott, PID 3873/gsd-power) but
  inhibitor timeout is reached`. Critical-battery handling is the plausible
  explanation -- unconfirmed. Note anacron was skipped for `ConditionACPower=true`
  at 11:32 on Oct 2, so the machine was on battery for that freeze too.
- `workqueue: delayed_fput hogged CPU for >10000us` appeared on the current boot.
  Benign alone; watch for it near future freezes.

## Corrections log

- **2026-10-02:** Initially claimed "hibernate is broken" from a single `-28`
  failure, and recommended masking it. Wrong: 7 of 10 hibernations succeeded.
  Corrected above -- the trigger is swap capacity and the damage is done by the
  NVIDIA abort path.
- **2026-10-02:** Initially blamed runtime D3 (`DynamicPowerManagement=2`).
  Wrong: Xorg pins the dGPU, `runtime_suspended_time` is 0, it never
  runtime-suspends. See "Ruled out".
- **2026-10-02:** Initially concluded "no serial port" partly from
  `dmesg | grep -c 8250` returning 0, which was really `dmesg_restrict=1`
  denying the read. Re-checked via `journalctl -k`; conclusion unchanged.
