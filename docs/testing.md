# Validation and limits

These results come from one physical Newmen GM840. They are observations,
not a population reliability study. No personal device dump or raw tracing
data is published.

| Firmware / setup | Idle or test | Result |
| --- | --- | --- |
| Original 3009, normal Windows settings | Short idle | `arbor`, H missing |
| Original 3009, keyboard power policy temporarily disabled | Short idle | `arbor` |
| Original 3009, adapter power policy temporarily disabled | About 48 s | `arbor` |
| Official 3010, original power settings restored | 48.366 s | `harbor` |
| Official 3010 | 82.611 s | `harbor` |
| Official 3010 | 375.545 s to received A | `arbor`, H missing |
| Official 3010, held H diagnostic | 482.232 s | Held H arrived, `hhharbor` |
| Custom wake-only revision | 47.577 s | `harbor`, H press/release captured |
| Custom wake-only revision | 363.827 s | `harbor`, H press/release captured |
| Custom wake + battery bar | Hold Fn+B | 1 through 7 green, user confirmed |
| Custom wake + battery bar | Release Fn+B | Normal lighting restored, user confirmed |

Precise idle values are measured from the last warm-up activity to the first
browser key event, not to physical switch closure. The successful wake-only
trials had no recorded early typing, editing or window focus loss. USB was
unplugged and Bluetooth selected according to the participant's confirmation.

The battery-bar revision contains the exact working wake patch. The six-minute
physical trial was not repeated after adding the LED overlay, and ordinary B
typing was not separately confirmed by the user on that revision. Do not present
those as completed hardware tests.

## Offline and installation checks

- Full independent application readback matched each installed image exactly.
  Bootloader and existing configuration were unchanged.
- The wake candidate matched stock held-key press/release packets for 84 ordinary
  and modifier keys, in 168 simulated comparisons with and without a pending
  connection-control command.
- The battery overlay passed 42 instruction-level cases covering all eight
  levels, inactive chords, lights switched off, unknown battery status, key
  processing and retained wake capture.
- GPIO levels and radio acknowledgements in the instruction-level harness were
  simulated. They cannot establish actual matrix timing or delivery to a host.
- The portable patcher is checked against the actual locally verified images
  as well as synthetic unit tests. Public CI needs no firmware or attached device.
- The Windows helper was exercised against a simulated flasher for successful
  preparation/installation and for read/code-validation failures. Preparation
  and failure cases performed no simulated write. This tests orchestration,
  not an additional hardware installation.
- Earlier larger custom 3009 buffering experiments failed physical tests and
  were removed. They are not included in this release.

## Remaining limits

The wake change retains one matrix snapshot; it is not a general FIFO for all
typing during a slow reconnection. A tap ending before clocks/GPIO are restored
can still escape capture. Battery consumption, all battery levels, other hosts,
Bluetooth 3.0, pairing transitions, all special Fn combinations and other
hardware revisions have not been exhaustively tested. Sleep instructions and
threshold are byte-preserved; this is not a measured battery-life claim.
