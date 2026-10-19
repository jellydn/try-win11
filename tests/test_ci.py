"""Hosted-CI contracts; no VM fixtures, firmware, Microsoft media or network."""

import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_package
import ci_sources


class CITests(unittest.TestCase):
    def test_lock_rejects_moving_sources_missing_hashes_and_unreviewed_inputs(self):
        original = json.loads(ci_sources.LOCK.read_text())
        ci_sources.validate(original)
        for mutate in (
            lambda m: m["sources"]["swtpm"].update(revision="main"),
            lambda m: m["sources"]["qemu"].update(sha256=""),
            lambda m: m["sources"]["qemu"].update(url="https://example.org/archive.tar.xz"),
            lambda m: m["sources"].update(windows={"url": "https://example.org/Windows.iso"}),
            lambda m: m["sources"]["qemu"].update(configure=["--enable-tpm"]),
        ):
            lock = copy.deepcopy(original)
            mutate(lock)
            with self.assertRaises(ValueError):
                ci_sources.validate(lock)

    def test_checksum_rejects_changed_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "source.tar"
            archive.write_bytes(b"abc")
            ci_sources.verify(archive, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            archive.write_bytes(b"abd")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                ci_sources.verify(archive, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_source_extraction_omits_unbuilt_roms_but_rejects_other_absolute_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "source.tar"
            for link_path, accepted in (("qemu-test/roms/edk2/X11IncludeHack", True),
                                        ("qemu-test/src/unsafe", False)):
                with tarfile.open(archive, "w") as output:
                    regular = tarfile.TarInfo("qemu-test/configure")
                    regular.size = 2
                    output.addfile(regular, io.BytesIO(b"ok"))
                    link = tarfile.TarInfo(link_path)
                    link.type = tarfile.SYMTYPE
                    link.linkname = "/usr/include/X11"
                    output.addfile(link)
                destination = root / ("accepted" if accepted else "rejected")
                destination.mkdir()
                if accepted:
                    ci_sources.extract(archive, destination, {"root": "qemu-test"}, "qemu")
                    self.assertEqual((destination / "qemu-test/configure").read_bytes(), b"ok")
                    self.assertFalse((destination / "qemu-test/roms").exists())
                else:
                    with self.assertRaises(tarfile.AbsoluteLinkError):
                        ci_sources.extract(archive, destination, {"root": "qemu-test"}, "qemu")
                    self.assertFalse((destination / link_path).exists())

    def test_package_is_deterministic_and_excludes_unlisted_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Use real original sources, plus an unlisted private-looking file.
            for name in ci_package.FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ci_package.ROOT / name).read_bytes())
            (root / "do-not-upload.iso").write_bytes(b"sentinel, not Microsoft content")
            ci_package.build(root, root / "one")
            ci_package.build(root, root / "two")
            first = root / "one/try-win11-source.tar"
            self.assertEqual(first.read_bytes(), (root / "two/try-win11-source.tar").read_bytes())
            with tarfile.open(first) as archive:
                self.assertEqual(archive.getnames(), sorted(ci_package.FILES))
                self.assertTrue(all(m.isfile() and m.uid == 0 and m.mtime == 0 for m in archive))

    def test_package_rejects_symlink_and_binary_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "README.md"
            path.symlink_to(ci_package.ROOT / "README.md")
            with self.assertRaisesRegex(ValueError, "non-regular"):
                ci_package.source_bytes(root, "README.md")
            path.unlink()
            path.write_bytes(b"MZ\0unsafe")
            with self.assertRaisesRegex(ValueError, "binary"):
                ci_package.source_bytes(root, "README.md")


if __name__ == "__main__":
    unittest.main()
