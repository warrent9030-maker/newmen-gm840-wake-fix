import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import gm840_patch as fw
from tools.assemble_battery import assemble


class PatcherTests(unittest.TestCase):
    def setUp(self):
        # Synthetic fixtures only. Production fingerprints stay fixed in source;
        # this isolated test substitutes hashes of generated dummy ROMs.
        app = bytearray(fw.APP_SIZE)
        for offset, original, _ in fw.WAKE_PATCHES + fw.BATTERY_PATCHES:
            app[offset:offset + len(original)] = original
        app[fw.CODE_END:] = bytes((i * 29 + 7) % 256 for i in range(fw.APP_SIZE - fw.CODE_END))
        wake = bytearray(app)
        fw._apply_hunks(wake, fw.WAKE_PATCHES)
        battery = bytearray(wake)
        fw._apply_hunks(battery, fw.BATTERY_PATCHES)
        old = bytearray(app)
        old[123] = 3
        self.boot = bytes(range(256)) * 16
        self.images = {'3010': bytes(app), 'wake': bytes(wake), 'battery': bytes(battery), '3009': bytes(old)}
        hashes = {name: fw.digest(data[:fw.CODE_END]) for name, data in self.images.items()}
        self.hash_patch = patch.object(fw, 'CODE_HASHES', hashes)
        self.boot_patch = patch.object(fw, 'BOOT_SHA256', fw.digest(self.boot))
        self.hash_patch.start()
        self.boot_patch.start()
        self.addCleanup(self.hash_patch.stop)
        self.addCleanup(self.boot_patch.stop)

    def full(self, name):
        return self.images[name] + self.boot

    def test_all_supported_transitions_and_idempotence(self):
        for source in ('3010', 'wake', 'battery'):
            for target in ('wake', 'battery'):
                with self.subTest(source=source, target=target):
                    actual = fw.patch_backup(self.full(source), target)
                    self.assertEqual(actual, self.images[target])
                    self.assertEqual(actual[fw.CODE_END:], self.images[source][fw.CODE_END:])

    def test_owner_configuration_is_preserved(self):
        data = bytearray(self.full('3010'))
        data[fw.CODE_END:fw.APP_SIZE] = bytes([0xCC]) * (fw.APP_SIZE - fw.CODE_END)
        actual = fw.patch_backup(data, 'battery')
        self.assertEqual(actual[fw.CODE_END:], data[fw.CODE_END:fw.APP_SIZE])

    def test_reject_unknown_code_and_bootloader(self):
        for position in (124, 0x9001, 0xF000):
            data = bytearray(self.full('3010'))
            data[position] ^= 1
            with self.assertRaises(ValueError):
                fw.patch_backup(data, 'wake')

    def test_reject_wrong_sizes(self):
        for size in (0, fw.APP_SIZE, fw.FULL_SIZE - 1, fw.FULL_SIZE + 1):
            with self.assertRaises(ValueError):
                fw.inspect_backup(bytes(size))

    def test_old_firmware_is_identified_but_not_patched(self):
        self.assertEqual(fw.inspect_backup(self.full('3009'))['variant'], '3009')
        with self.assertRaisesRegex(ValueError, 'official 3010'):
            fw.patch_backup(self.full('3009'), 'wake')

    def test_readback_requires_application_and_bootloader_match(self):
        expected = self.images['wake']
        self.assertTrue(fw.verify_readback(self.full('3010'), expected, expected + self.boot)['application_exact_match'])
        for position in (123, fw.CODE_END + 1, fw.APP_SIZE + 1):
            actual = bytearray(expected + self.boot)
            actual[position] ^= 1
            with self.assertRaises(ValueError):
                fw.verify_readback(self.full('3010'), expected, actual)

    def test_never_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'backup.bin'
            target.write_bytes(b'keep this')
            with self.assertRaises(FileExistsError):
                fw.write_new(target, b'replacement')
            self.assertEqual(target.read_bytes(), b'keep this')

    def test_overlay_assembles_to_reviewed_payload(self):
        self.assertEqual(assemble(), fw.BATTERY_CODE)
        self.assertEqual(len(fw.BATTERY_CODE), 218)

    def test_patch_definitions_stay_outside_configuration(self):
        spans = []
        for offset, original, replacement in fw.WAKE_PATCHES + fw.BATTERY_PATCHES:
            self.assertEqual(len(original), len(replacement))
            self.assertLessEqual(offset + len(replacement), fw.CODE_END)
            spans.append(set(range(offset, offset + len(replacement))))
        self.assertEqual(sum(map(len, spans)), len(set().union(*spans)))


if __name__ == '__main__':
    unittest.main()
