import enum
import struct
from io import BufferedIOBase
from multiprocessing import RLock

# enum sfo_value_format {
# 	SFO_FORMAT_STRING_SPECIAL = 0x4,
# 	SFO_FORMAT_STRING = 0x204,
# 	SFO_FORMAT_UINT32 = 0x404,
# };


class Format(enum.Enum):
    StringSpecial = 0x4
    String = 0x204
    UInt32 = 0x404


def __rd_packed(file, format: str, size: int, offset: int | None = None):
    if offset is not None:
        file.seek(offset)
    return struct.unpack(format, file.read(size))


def __rd_zero_str(file: BufferedIOBase) -> bytes:
    ret_val = b""
    while True:
        inspected = file.read(1)
        if inspected == b"\0":
            return ret_val
        ret_val += inspected


def read_sfo(file: BufferedIOBase) -> dict[str, str | int | bytes]:
    magic, _version, key_table_offset, value_table_offset, entry_count = __rd_packed(
        file, "<4sIIII", 0x14
    )

    if magic != b"\0PSF":
        raise Exception("File is not an SFO file (invalid magic)")

    entries = {}

    # entries directly follow the header
    for _ in range(entry_count):
        key_offset, format, size, _max_size, value_offset = __rd_packed(
            file, "<HHIII", 0x10
        )

        format_enum: Format
        try:
            format_enum = Format(format)
        except ValueError:
            print(f"unknown format {format:#x}, skipping (key=")
            continue

        old_pos = file.tell()
        # read the key and value manually
        file.seek(key_table_offset + key_offset)
        key = __rd_zero_str(file).decode()
        file.seek(value_table_offset + value_offset)
        value = file.read(size)
        file.seek(old_pos)  # restore position before the seeks

        # decode value by format
        if format_enum == Format.UInt32:
            if size != 4:
                raise Exception("value of type UINT32 is >4 bytes in size (wut?)")
            value = struct.unpack("<I", value)[0]
        if format_enum == Format.String:
            value = value.decode()

        entries[key] = value

    return entries
