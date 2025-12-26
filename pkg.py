import io
import struct

PKG_MAGIC = b"\x7fCNT"

PKG_ENTRY_SIZE = 0x20

PKG_CONTENT_TYPE_GD = 0x1A  # pkg_ps4_app, pkg_ps4_patch, pkg_ps4_remaster
PKG_CONTENT_TYPE_AC = 0x1B  # pkg_ps4_ac_data, pkg_ps4_sf_theme, pkg_ps4_theme
PKG_CONTENT_TYPE_AL = 0x1C  # pkg_ps4_ac_nodata
PKG_CONTENT_TYPE_DP = 0x1E  # pkg_ps4_delta_patch

PKG_CONTENT_FLAGS_FIRST_PATCH = 0x00100000
PKG_CONTENT_FLAGS_PATCHGO = 0x00200000
PKG_CONTENT_FLAGS_REMASTER = 0x00400000
PKG_CONTENT_FLAGS_PS_CLOUD = 0x00800000
PKG_CONTENT_FLAGS_GD_AC = 0x02000000
PKG_CONTENT_FLAGS_NON_GAME = 0x04000000
PKG_CONTENT_FLAGS_0X8000000 = 0x08000000  # has data?
PKG_CONTENT_FLAGS_SUBSEQUENT_PATCH = 0x40000000
PKG_CONTENT_FLAGS_DELTA_PATCH = 0x41000000
PKG_CONTENT_FLAGS_CUMULATIVE_PATCH = 0x60000000


class PkgHeader:
    def __init__(
        self,
        content_id: bytes,
        digest: bytes,
        original_size: int,
        entries: dict[str, bytes],
        content_type: int,
        content_flags: int,
    ):
        self.content_id = content_id.decode()
        self.digest = digest
        self.original_size = original_size
        self.entries = entries
        self.content_type = content_type
        self.content_flags = content_flags

    def __repr__(self) -> str:
        return f"PkgHeader[{self.content_id}, {self.original_size} bytes, {len(self.entries)} entries]"

    def isPatch(self) -> bool:
        return (
            bool(self.content_flags & PKG_CONTENT_FLAGS_FIRST_PATCH)
            or bool(self.content_flags & PKG_CONTENT_FLAGS_SUBSEQUENT_PATCH)
            or bool(self.content_flags & PKG_CONTENT_FLAGS_DELTA_PATCH)
            or bool(self.content_flags & PKG_CONTENT_FLAGS_CUMULATIVE_PATCH)
        )


def __rd_packed(file, format: str, size: int, offset: int):
    file.seek(offset)
    return struct.unpack(format, file.read(size))


def read_pkg_header(file: io.BufferedIOBase) -> PkgHeader:
    magic = __rd_packed(file, "4s", 4, 0)
    if magic[0] != PKG_MAGIC:
        raise Exception("Not a PKG file")

    entry_count = __rd_packed(file, ">I", 4, 0x10)[0]
    # sc_entry_count = __rd_packed(file, ">H", 2, 0x14)[0]
    entry_table_offset = __rd_packed(file, ">I", 4, 0x18)[0]
    content_id = __rd_packed(file, "36s", 36, 0x40)[0]
    content_type = __rd_packed(file, ">I", 4, 0x74)[0]
    content_flags = __rd_packed(file, ">I", 4, 0x78)[0]
    package_size = __rd_packed(file, ">Q", 8, 0x430)[0]
    pkg_digest = __rd_packed(file, "32s", 32, 0xFE0)[0]

    entries: dict[str, bytes] = {}
    for i in range(0, entry_count):
        entry = read_pkg_entry(file, entry_table_offset + PKG_ENTRY_SIZE * i)
        if entry is not None:
            key, value = entry
            entries[key] = value

    return PkgHeader(
        content_id, pkg_digest, package_size, entries, content_type, content_flags
    )


def read_pkg_entry(file: io.BufferedIOBase, offset: int) -> tuple[str, bytes] | None:
    entry_id = __rd_packed(file, ">I", 4, offset + 0)[0]
    entry_offset = __rd_packed(file, ">I", 4, offset + 0x10)[0]
    entry_size = __rd_packed(file, ">I", 4, offset + 0x14)[0]
    if entry_id < 0x400:  # we only want the files :P
        return None

    file.seek(entry_offset)

    entry_file_name = ""
    match entry_id:
        case 0x1000:
            entry_file_name = "param.sfo"
        case 0x1006:
            entry_file_name = "pic1.png"
        case 0x1200:
            entry_file_name = "icon0.png"
        case 0x1220:
            entry_file_name = "pic0.png"
        case _:
            # print(f"WARNING: Unknown entry id {entry_id:#x}")
            entry_file_name = f"{entry_id:x}"

    return (entry_file_name, file.read(entry_size))
