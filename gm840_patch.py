#!/usr/bin/env python3
"""Offline, fingerprint-checked Newmen GM840 3010 firmware patcher.

No device access, network access, third-party dependencies or vendor firmware.
Input must be the owner's full 65536-byte sinowisp USB backup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

APP_SIZE = 61440
FULL_SIZE = 65536
CODE_END = 0xC600
BOOT_SHA256 = '14c1e7070569e0d2546b34a09f151e3b696d2821c228667775b37034661f7289'
CODE_HASHES = {
    '3009': '6df9f89f7e72ca2e49ba24164cfffca677acf7e16197a07ae6eb38cd8011d8ef',
    '3010': 'b22aba5d4f5cfc66d97d2140295eb2992723a72415574b858815cefee67368a0',
    'wake': '8a42f64aba0055f030d83f732003ea061d5367ca9106f785c30c96b38744c92b',
    'battery': '6cc2722da5a63eb71b5f887cbcc2a6c79d4d8edb2040be0503daea8be4f517cb',
}

# Offset, stock bytes, replacement bytes. All changes lie below configuration.
WAKE_PATCHES = (
    (0x44CB, bytes.fromhex('12 00 0e'), bytes.fromhex('12 90 00')),
    (0x4CD3, bytes.fromhex('80 29'), bytes.fromhex('80 2b')),
    (0x9000, bytes(12), bytes.fromhex('12 00 0e 20 04 05 c2 53 12 7f 88 22')),
)

# Authored 8051 overlay, disassembled and explained in docs/patch-design.md.
# Fn matrix index 65 => IRAM 0x5e bit 5; B index 34 => IRAM 0x59 bit 4.
# LED indices 22..31 correspond to number keys 1..0. No new RAM allocation.
BATTERY_CODE = bytes.fromhex('''
e55e20e5030291ade55920e4030291ade518c3941650030291aae518c3942040030291aa
900f10e064bb6003029189900f3ae020e703029189900f80e0c3135407f99091d2e993f8
e518c39416c39840030291aae9c394025003029172e9c39404500302917ce51964016003
0291aa0291a4e51960030291aa0291a4e519c3940240030291aa0291a4e51964026003
0291aae518641670030291a4e518641f60030291aa751502751680021e58202903021c50
021c44e55e20e5030291c9e55920e4030291c9021e66301a03021e6f021e6601010304
0607090a
''')
BATTERY_PATCHES = (
    (0x1C41, bytes.fromhex('30 29 0c'), bytes.fromhex('02 91 00')),
    (0x1E63, bytes.fromhex('20 1a 09'), bytes.fromhex('02 91 b6')),
    (0x9100, bytes(len(BATTERY_CODE)), BATTERY_CODE),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect_backup(data):
    if len(data) != FULL_SIZE:
        raise ValueError('Expected a full 65536-byte sinowisp USB backup, including bootloader.')
    if digest(data[APP_SIZE:]) != BOOT_SHA256:
        raise ValueError('Unsupported bootloader. Do not flash this device using these instructions.')
    code_hash = digest(data[:CODE_END])
    version = next((name for name, value in CODE_HASHES.items() if value == code_hash), None)
    if version is None:
        raise ValueError('Unsupported program fingerprint. The model name/USB ID alone is insufficient.')
    return {'variant': version, 'full_backup_sha256': digest(data),
            'application_sha256': digest(data[:APP_SIZE]), 'code_sha256': code_hash,
            'bootloader_sha256': BOOT_SHA256, 'application_size': APP_SIZE}


def _apply_hunks(data, hunks, reverse=False):
    for offset, original, replacement in hunks:
        expected, new = (replacement, original) if reverse else (original, replacement)
        if len(expected) != len(new) or offset + len(new) > CODE_END:
            raise ValueError('Invalid patch definition.')
        if data[offset:offset + len(expected)] != expected:
            raise ValueError(f'Unexpected bytes at 0x{offset:04x}; no output written.')
        data[offset:offset + len(new)] = new


def patch_backup(backup, feature):
    info = inspect_backup(backup)
    if info['variant'] == '3009':
        raise ValueError('3009 is recognized for backup/recovery only. Install official 3010 first, then make a new backup.')
    if feature not in ('wake', 'battery'):
        raise ValueError('Feature must be wake or battery.')
    app = bytearray(backup[:APP_SIZE])
    # Normalize known patches so re-running or selecting wake-only is reversible.
    if info['variant'] == 'battery':
        _apply_hunks(app, BATTERY_PATCHES, reverse=True)
    if info['variant'] in ('wake', 'battery'):
        _apply_hunks(app, WAKE_PATCHES, reverse=True)
    if digest(app[:CODE_END]) != CODE_HASHES['3010']:
        raise ValueError('Normalization failed.')
    _apply_hunks(app, WAKE_PATCHES)
    if feature == 'battery':
        _apply_hunks(app, BATTERY_PATCHES)
    if digest(app[:CODE_END]) != CODE_HASHES[feature]:
        raise ValueError('Generated program fingerprint does not match the reviewed patch.')
    if app[CODE_END:] != backup[CODE_END:APP_SIZE]:
        raise ValueError('Configuration was altered.')
    return bytes(app)


def verify_readback(backup, expected, readback):
    inspect_backup(backup)
    if len(expected) != APP_SIZE or len(readback) != FULL_SIZE:
        raise ValueError('Expected a 61440-byte application and a 65536-byte readback.')
    if readback[:APP_SIZE] != expected:
        raise ValueError('Application readback differs. Keep USB connected and investigate; verification failed.')
    if readback[APP_SIZE:] != backup[APP_SIZE:]:
        raise ValueError('Bootloader differs from the backup; verification failed.')
    return {'application_exact_match': True, 'bootloader_unchanged': True,
            'application_sha256': digest(expected)}


def write_new(path, data):
    # Never silently replace an owner's existing firmware/backup.
    with Path(path).open('xb') as stream:
        stream.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect', help='Validate and identify a full USB backup')
    inspect.add_argument('backup', type=Path)
    patch = commands.add_parser('patch', help='Create application-only patched firmware offline')
    patch.add_argument('backup', type=Path)
    patch.add_argument('output', type=Path)
    patch.add_argument('--feature', choices=('wake', 'battery'), default='wake')
    restore = commands.add_parser('extract-restore', help='Extract the original application from your full backup')
    restore.add_argument('backup', type=Path)
    restore.add_argument('output', type=Path)
    verify = commands.add_parser('verify', help='Verify full application readback and unchanged bootloader')
    verify.add_argument('backup', type=Path)
    verify.add_argument('application', type=Path)
    verify.add_argument('readback', type=Path)
    args = parser.parse_args(argv)
    try:
        backup = args.backup.read_bytes()
        info = inspect_backup(backup)
        if args.command == 'patch':
            app = patch_backup(backup, args.feature)
            write_new(args.output, app)
            info.update(output_variant=args.feature, output_sha256=digest(app), output_bytes=len(app))
        elif args.command == 'extract-restore':
            write_new(args.output, backup[:APP_SIZE])
        elif args.command == 'verify':
            info.update(verify_readback(backup, args.application.read_bytes(), args.readback.read_bytes()))
        print(json.dumps(info, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
