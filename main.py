import glob
import hashlib
import io
import json
import os
import sys
from os.path import dirname
from urllib.parse import quote

import pkg
import sfo

DATA_DIR = ".pkgdata"

if len(sys.argv) < 2:
    print(
        "please specify the root URL (e.g. 'http://my.domain' or 'http://192.168.0.123:8000') from which files will be served"
    )
    exit()

root_url = sys.argv[1]
pkgs_json_contents = []
digests = set()


def get_split_path(digest: str):
    return f"{DATA_DIR}/{digest[0]}/{digest[1]}/{digest[2:]}"


def get_hash_for_file(data: bytes) -> str:
    md5obj = hashlib.md5()
    md5obj.update(data)
    return md5obj.hexdigest().upper()


def find_by_title_id(title_id: str):
    for game in pkgs_json_contents:
        if game["titleID"] == title_id:
            return game
    return None


def clean_ver(version) -> str:
    if version is None:
        raise Exception("PKG version is None")
    return version.lstrip("0")


for i in glob.iglob("**/*.pkg", recursive=True):
    print("->", i)
    with open(i, "rb") as file:
        hdr = pkg.read_pkg_header(file)
        # print(hdr)

    if "backport" in i.lower():
        continue  # ignore backports. too confusing...

    sfo_data = sfo.read_sfo(io.BytesIO(hdr.entries["param.sfo"]))

    game = find_by_title_id(str(sfo_data["TITLE_ID"]))
    if game is None:
        game = {
            "name": sfo_data.get("TITLE"),
            "titleID": sfo_data.get("TITLE_ID"),
            "pkgs": [],
        }
        pkgs_json_contents.append(game)

    str_digest = "".join([f"{b:02X}" for b in hdr.digest])
    if str_digest in digests:
        print("WARNING: digests aren't unique! duplicate file?")
    digests.add(str_digest)

    data_dir = get_split_path(str_digest)
    json_path = f"{data_dir}/install.json"
    icon0_path = (
        f"{get_split_path(get_hash_for_file(hdr.entries['icon0.png']))}/icon0.png"
        if "icon0.png" in hdr.entries
        else None
    )
    pic1_path = (
        f"{get_split_path(get_hash_for_file(hdr.entries['pic1.png']))}/pic1.png"
        if "pic1.png" in hdr.entries
        else None
    )

    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    if icon0_path is not None:
        os.makedirs(dirname(icon0_path), exist_ok=True)
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
                        "url": f"{root_url}/{quote(i)}",
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
            "contentId": sfo_data["CONTENT_ID"],
            "pkgPath": f"{root_url}/{quote(i)}",
            "jsonPath": f"{root_url}/{quote(json_path)}",
            "icon0Path": f"{root_url}/{quote(icon0_path)}"
            if icon0_path is not None
            else None,
            "size": os.lstat(i).st_size,
            "version": clean_ver(sfo_data.get("APP_VER", sfo_data.get("VERSION"))),
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

    # these might be incorrect due to a DLC loading first. let's correct just in case
    if hdr.content_type == pkg.PKG_CONTENT_TYPE_GD and icon0_path:
        game["name"] = sfo_data["TITLE"]
        game["icon0Path"] = f"{root_url}/{quote(icon0_path)}"

    if hdr.content_type == pkg.PKG_CONTENT_TYPE_GD and pic1_path:
        game["pic1Path"] = f"{root_url}/{quote(pic1_path)}"
        # write pic1
        os.makedirs(dirname(pic1_path), exist_ok=True)
        with open(pic1_path, "wb+") as file:
            file.write(hdr.entries["pic1.png"])

with open("pkgs.json", "w+") as file:
    json.dump(pkgs_json_contents, file, indent=2)
