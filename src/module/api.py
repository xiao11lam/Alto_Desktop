import requests
import json
import time
import re


# Anilist
# https://anilist.github.io/ApiV2-GraphQL-Docs/
def anilistSearch(romaji_name):
    query = "query ($id: String) {Media (search: $id, type: ANIME) {title {native}}}"
    js = {"query": query, "variables": {"id": romaji_name}}
    headers = {'accept': 'application/json'}
    url = "https://graphql.anilist.co"
    print(f"1 ==> 搜索{romaji_name}")

    for retry in range(3):
        response = requests.post(url, json=js, headers=headers)

        if response.status_code != 200:
            time.sleep(0.5)
            continue

        result = json.loads(response.text.encode().decode('unicode_escape'))  # 特殊转码
        print(f"1 ==> 获取{romaji_name}数据")

        jp_name_anilist = result["data"]["Media"]["title"]["native"]

        # 移除括号内容，例 22/7 （ナナブンノニジュウニ）
        jp_name_anilist = re.sub(r'（[^）]*）', '', jp_name_anilist).strip()

        return jp_name_anilist

    print(f"1 ==> 搜索{romaji_name}失败")


# Bangumi ID
# https://bangumi.github.io/api/
def bangumiSearchId(jp_name):
    jp_name = jp_name.replace("!", " ").replace("-", " ").replace("/", " ").strip()  # 搜索时移除特殊符号避免报错

    headers = {"accept": "application/json", "User-Agent": "nuthx/bangumi-renamer"}
    url = "https://api.bgm.tv/search/subject/" + jp_name + "?type=2&responseGroup=large&max_results=25"
    print(f"2 ==> 搜索{jp_name}")

    for retry in range(3):
        response = requests.post(url, headers=headers)

        if response.status_code != 200:
            time.sleep(0.5)
            continue

        if response.text.startswith("<!DOCTYPE html>"):
            return

        result = json.loads(response.text)
        print(f"2 ==> 获取{jp_name}数据")

        # 未搜索到内容停止
        if "code" in result and result["code"] == 404:
            return

        bgm_id = result["list"][0]["id"]

        return bgm_id

    print(f"2 ==> 搜索{jp_name}失败")


# Bangumi 条目
def bangumiSubject(bgm_id):
#     headers = {"accept": "application/json", "User-Agent": "nuthx/bangumi-renamer"}
#     url = "https://api.bgm.tv/v0/subjects/" + str(bgm_id)
#     print(f"3 ==> 搜索{bgm_id}")

#     for retry in range(3):
#         response = requests.get(url, headers=headers)
#
#         if response.status_code != 200:
#             time.sleep(0.5)
#             continue
#
#         result = json.loads(response.text)
#         print(f"3 ==> 获取{bgm_id}数据")
#
#         # 不存在 bgm_id 时停止
#         if "code" in result and result["code"] == 404:
#             return
#         poster = result["images"]["medium"]
        poster = "https://lain.bgm.tv/r/800/pic/cover/l/82/4d/412353_I9liL.jpg"
#         jp_name = result["name"]
        jp_name = "ピューと吹く!ジャガー ～いま、吹きにゆきます～"
#         cn_name = result["name_cn"] if result["name_cn"] else result["name"]
        cn_name = ">>>>>> Processing Finished"
#         release = result["date"] if result["date"] else "1000-01-01"
        release = "2009-01-01"
#         episodes = result["eps"] if result["eps"] else "0"
        episodes = "1"
#         score = format(float(result["rating"]["score"]), ".1f")
        score = "0.0"
#         types = result["platform"]
        types = "02"
#         if types in ["TV"]:
#             typecode = "01"
#         elif types in ["剧场版"]:
#             typecode = "02"
#         elif types in ["OVA", "OAD"]:
#             typecode = "03"
#         else:
#             typecode = "XBD"
        typecode = "XBD"
        return poster, jp_name, cn_name, types, typecode, release, episodes, score

#     print(f"3 ==> 搜索{bgm_id}失败")


# Bangumi 前传
def bangumiPrevious(init_id, init_name):
    headers = {"accept": "application/json", "User-Agent": "nuthx/bangumi-renamer"}
    url = "https://api.bgm.tv/v0/subjects/" + str(init_id) + "/subjects"
    print(f"4 ==> 搜索{init_name}前传")

    for retry in range(3):
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            time.sleep(0.5)
            continue

        result = json.loads(response.text)
        print(f"4 ==> 获取{init_name}前传")

        # 如果有前传，返回前传 prev_id 和 prev_name
        # 如果没有前传，返回原始 init_id 和 not_now_bro
        for data in result:
            if data["relation"] in ["前传", "主线故事", "全集"]:
                prev_id = str(data["id"])
                prev_name = data["name_cn"] if data["name_cn"] else data["name"]
                return prev_id, prev_name
        else:
            return init_id, init_name

    print(f"4 ==> 搜索{init_name}前传失败")


# Bangumi 搜索
def bangumiSearch(jp_name):
    jp_name = jp_name.replace("!", " ").replace("-", " ").replace("/", " ").strip()  # 搜索时移除特殊符号避免报错

    headers = {"accept": "application/json", "User-Agent": "nuthx/bangumi-renamer"}
    url = "https://api.bgm.tv/search/subject/" + jp_name + "?type=2&responseGroup=large&max_results=25"
    print(f"2 ==> 搜索{jp_name}")

    for retry in range(3):
        response = requests.post(url, headers=headers)

        if response.status_code != 200:
            time.sleep(0.5)
            continue

        if response.text.startswith("<!DOCTYPE html>"):
            return []

        result = json.loads(response.text)
        print(f"2 ==> 获取{jp_name}数据")

        # 未搜索到内容停止
        if "code" in result and result["code"] == 404:
            return

        result_full = []
        result_len = len(result['list'])

        for i in range(result_len):
            # 跳过无日期的条目
            if not result["list"][i]["air_date"] or result["list"][i]["air_date"] == "0000-00-00":
                continue

            # 跳过无内容的条目
            if result["list"][i]["name_cn"] == "":
                continue

            # 添加字典
            entry = {"bgm_id": result["list"][i]["id"],
                     "cn_name": result["list"][i]["name_cn"],
                     "release": result["list"][i]["air_date"]}
            result_full.append(entry)

        result_full = [item for item in result_full if item]  # 移除空字典
        result_full = sorted(result_full, key=lambda x: x["release"])  # 按放送日期排序

        return result_full

    print(f"2 ==> 搜索{jp_name}失败")
