import glob
import json
import os
import re
import subprocess
import sys

import pkg

TOOLCHAIN = os.getenv("OO_PS4_TOOLCHAIN", "/Users/vic/OpenOrbis/PS4Toolchain")
PKGTOOL = os.path.join(TOOLCHAIN, "bin/macos/PkgTool.Core")
TMP_FILE = "/tmp/ps4-pkg-db-tmp"

if len(sys.argv) < 2:
    print(
        "please specify the root URL (e.g. 'http://my.domain' or 'http://192.168.0.123:8000') from which files will be served"
    )
    exit()

root_url = sys.argv[1]


def read_sfo(param_sfo: bytes):
    with open(TMP_FILE, "wb+") as file:
        file.write(param_sfo)
    out = subprocess.check_output([PKGTOOL, "sfo_listentries", TMP_FILE]).decode()
    os.remove(TMP_FILE)
    key_values = {}
    key_value_re = re.compile(r"^([A-Z_]+)(?:.* = )(.*)$", re.RegexFlag.M)
    for match in key_value_re.finditer(out):
        key_values[match.groups()[0]] = match.groups()[1]

    return key_values


pkgs_json_contents = []
digests = set()


def find_by_title_id(title_id: str):
    for game in pkgs_json_contents:
        if game["titleID"] == title_id:
            return game
    return None


for i in glob.iglob("**/*.pkg", recursive=True):
    print("->", i)
    with open(i, "rb") as file:
        hdr = pkg.read_pkg_header(file)
        # print(hdr)

    if "backport" in i.lower():
        continue  # ignore backports. too confusing...

    sfo_data = read_sfo(hdr.entries["param.sfo"])

    game = find_by_title_id(sfo_data["TITLE_ID"])
    if game is None:
        game = {
            "name": sfo_data.get("TITLE"),
            "titleID": sfo_data.get("TITLE_ID"),
            "contentID": hdr.content_id,
            "pkgs": [],
        }
        pkgs_json_contents.append(game)

    str_digest = "".join([f"{b:02X}" for b in hdr.digest])
    if str_digest in digests:
        print("WARNING: digests aren't unique! duplicate file?")
    digests.add(str_digest)

    data_dir = f"pkg_db_data/{str_digest[:2]}/{str_digest[2:]}"
    json_path = f"{data_dir}/install.json"
    icon0_path = f"{data_dir}/icon0.png" if "icon0.png" in hdr.entries else None
    pic1_path = f"{data_dir}/pic1.png" if "pic1.png" in hdr.entries else None

    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    if icon0_path is not None:
        with open(icon0_path, "wb+") as file:
            file.write(hdr.entries["icon0.png"])

    with open(json_path, "w+") as file:
        json.dump(
            {
                "originalFileSize": hdr.original_size,
                "packageDigest": str_digest,
                "numberOfSplitFiles": 1,
                "pieces": [
                    {
                        "url": f"{root_url}/{i}",
                        "fileOffset": 0,
                        "fileSize": os.lstat(i).st_size,
                        "hashValue": "0000000000000000000000000000000000000000",
                    }
                ],
            },
            file,
        )

    game["pkgs"].append(
        {
            "name": sfo_data["TITLE"],
            "pkgPath": f"{root_url}/{i}",
            "jsonPath": f"{root_url}/{json_path}",
            "icon0Path": f"{root_url}/{icon0_path}" if icon0_path is not None else None,
            "size": os.lstat(i).st_size,
            "originalSize": hdr.original_size,
            "digest": str_digest,
            "version": sfo_data.get("APP_VER", sfo_data.get("VERSION")),
            "type": "PS4GD"
            if hdr.content_type == pkg.PKG_CONTENT_TYPE_GD
            else "PS4AC"
            if hdr.content_type == pkg.PKG_CONTENT_TYPE_AC
            else "PS4AL"
            if hdr.content_type == pkg.PKG_CONTENT_TYPE_AL
            else "PS4DP"
            if hdr.content_type == pkg.PKG_CONTENT_TYPE_DP
            else f"unknown_{hdr.content_flags:x}",
            "isPatch": hdr.isPatch(),
        }
    )

    if hdr.content_type == pkg.PKG_CONTENT_TYPE_GD and icon0_path:
        # might be incorrect due to a DLC loading first. let's correct just in case
        game["name"] = sfo_data["TITLE"]
        game["icon0_path"] = f"{root_url}/{icon0_path}"

    if hdr.content_type == pkg.PKG_CONTENT_TYPE_GD and pic1_path:
        game["pic1_path"] = f"{root_url}/{pic1_path}"
        # write pic1
        with open(pic1_path, "wb+") as file:
            file.write(hdr.entries["pic1.png"])

    sfo_data = read_sfo(hdr.entries["param.sfo"])
    version = sfo_data.get("APP_VER", sfo_data.get("VERSION"))

with open("pkgs.json", "w+") as file:
    json.dump(pkgs_json_contents, file, indent=2)
