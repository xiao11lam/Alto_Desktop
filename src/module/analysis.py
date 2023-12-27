import os
import anitopy
import arrow
import jieba
from fuzzywuzzy import fuzz
from nltk.corpus import words

from src.module.api import *
from src.module.config import posterFolder, readConfig
import fitz  # PyMuPDF


def getRomajiName(file_name):
    # 忽略文件名中特殊字符
    pattern_ignored = '|'.join(["BD-BOX", "BD"])
    file_name = re.sub(pattern_ignored, '', file_name)

    # anitopy 识别动画名
    aniparse_options = {'allowed_delimiters': ' .-+[]'}
    romaji_name = anitopy.parse(file_name, options=aniparse_options)

    # 如果没识别到动画名返回 None
    if "anime_title" in romaji_name:
        anime_title = romaji_name["anime_title"]
        return anime_title


# def isPureEnglish(name):
#     name = name.replace(".", " ")
#     try:
#         for word in name.split():
#             if word.lower() not in words.words():
#                 return False
#     except Exception as e:
#         # print(f"nltk异常，即将重试 ({e})")
#         time.sleep(0.2)
#         return isPureEnglish(name)
#     return True


##################################################Real Output##############################################
def extract_text_from_pdfs(folder_path):
    if not folder_path or not os.path.exists(folder_path):
        print("Invalid or non-existent folder path.")
        return

    all_files = os.listdir(folder_path)
    pdf_files = [file for file in all_files if file.endswith('.pdf')]

    extracted_text = ""
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
        with fitz.open(pdf_path) as doc:
#             print(f"Text from {pdf_file}:")
            for page in doc:
                extracted_text += page.get_text()

    return extracted_text


def getApiInfo(anime):
#     romaji_name = anime["romaji_name"]

    # Anilist
#     if isPureEnglish(romaji_name):
#         anime["jp_name_anilist"] = romaji_name
#     else:
#         jp_name_anilist = anilistSearch(romaji_name)
#         if jp_name_anilist:
#             anime["jp_name_anilist"] = jp_name_anilist
#         else:
#             return

    anime["jp_name_anilist"] = 'ナガハマラジャ'




    # Bangumi ID
#     bangumi_search_id = bangumiSearchId(anime["jp_name_anilist"])
#     if bangumi_search_id:
#         anime["bgm_id"] = bangumi_search_id
#     else:
#         return

    anime["bgm_id"] = '412353'
#     # Bangumi 条目
#     bangumi_subject = bangumiSubject(anime["bgm_id"])

    bangumi_subject = "('https://lain.bgm.tv/r/800/pic/cover/l/82/4d/412353_I9liL.jpg', 'ピューと吹く!ジャガー ～いま、吹きにゆきます～', '>>>>>> Processing Finished', '02', 'XBD', '2009-01-01', '1', '0.0')"
    if bangumi_subject:
#         anime["poster"] = bangumi_subject[0]
        anime["poster"] = 'https://lain.bgm.tv/r/800/pic/cover/l/82/4d/412353_I9liL.jpg'
#         anime["jp_name"] = bangumi_subject[1].replace("/", " ")  # 移除结果中的斜杠
        anime["jp_name"] = 'ピューと吹く!ジャガー ～いま、吹きにゆきます～'
#         anime["cn_name"] = bangumi_subject[2].replace("/", " ")  # 移除结果中的斜杠
        anime["cn_name"] = '>>>>>> Processing Finished'
#         anime["types"] = bangumi_subject[3]
        anime["types"] = '02'
#         anime["typecode"] = bangumi_subject[4]
        anime["typecode"] = 'XBD'
#         anime["release"] = bangumi_subject[5]
        anime["release"] = '2009-01-01'
#         anime["episodes"] = bangumi_subject[6]
        anime["episodes"] = '1'
#         anime["score"] = bangumi_subject[7]
        anime["score"] = '0.0'
    else:
        return

    # Bangumi 前传
    bgm_id = anime["bgm_id"]
#     bangumi_previous = bangumiPrevious(bgm_id, anime["cn_name"])
#     bangumi_previous = "('114808', 'Output Folder')"
#     prev_id = bangumi_previous[0]
    prev_id = '114808'
#     prev_name = bangumi_previous[1]


    prev_name = extract_text_from_pdfs(anime["file_path"])

#     while bgm_id != prev_id:  # 如果 ID 不同，说明有前传
#         bgm_id = prev_id
#         bangumi_previous = bangumiPrevious(bgm_id, prev_name)
#         prev_id = bangumi_previous[0]
#         prev_name = bangumi_previous[1]

    anime["init_id"] = prev_id
    anime["init_name"] = prev_name.replace("/", " ")  # 移除结果中的斜杠

    # Bangumi 搜索
#     search_result = bangumiSearch(anime["init_name"])
#     search_result = "[{'bgm_id': 114808, 'cn_name': '搞怪吹笛手', 'release': '2007-11-19'}, {'bgm_id': 412353, 'cn_name': '搞怪吹笛手：立刻开吹', 'release': '2009-01-01'}]"
#     search_clean = removeTrash(anime["init_name"], search_result)
    search_clean = "[{'bgm_id': 114808, 'cn_name': '搞怪吹笛手', 'release': '2007-11-19'}, {'bgm_id': 412353, 'cn_name': '搞怪吹笛手：立刻开吹', 'release': '2009-01-01'}]"
    if search_clean:
        anime["result"] = search_clean
    else:
        return


# def removeTrash(init_name, search_list):
#     if not search_list:
#         return
#
#     # 获取列表
#     init_name = init_name.lower()
#     name_list = []
#     for item in search_list:
#         anime = item["cn_name"].lower()
#         name_list.append(anime)
#
#     result_yes1 = []
#     result_no1 = []
#     result_yes2 = []
#     result_no2 = []
#
#     # jieba 余弦相似度
#     for name in name_list:
#         t1 = set(jieba.cut(init_name))
#         t2 = set(jieba.cut(name))
#         result1 = len(t1 & t2) / len(t1 | t2)
#
#         if result1 >= 0.15:
#             result_yes1.append(name)
#         else:
#             result_no1.append(name)
#
#     # fuzzywuzzy 模糊匹配
#     for name in name_list:
#         ratio = fuzz.partial_ratio(init_name, name)
#         if ratio > 90:
#             result_yes2.append(name)
#         else:
#             result_no2.append(name)
#
#     # print(f"yes1:{result_yes1}")
#     # print(f"no1:{result_no1}")
#     # print(f"yes2:{result_yes2}")
#     # print(f"no2:{result_no2}")
#
#     # 在 search_list 中删除排除的动画
#     result = set(result_yes1 + result_yes2)  # 合并匹配的结果
#     result_remove = set(result_no1 + result_no2)  # 合并排除的结果
#     search_list = [item for item in search_list if item["cn_name"].lower() in result]
#     return search_list


def downloadPoster(df):
#     poster_url = anime["poster"]
#     poster_name = os.path.basename(poster_url)
    poster_folder = posterFolder()
#     poster_path = os.path.join(poster_folder, poster_name)
    poster_path = poster_folder
    # poster_url: https://lain.bgm.tv/r/800/pic/cover/l/82/4d/412353_I9liL.jpg
    # poster_name: 412353_I9liL.jpg
    # poster_folder: C:\Users\xiaoe\Desktop\Alto_Health_Results
    # poster_path: C:\Users\xiaoe\Desktop\Alto_Health_Results\412353_I9liL.jpg

    # Define the full path for the Excel file
    excel_filename = os.path.join(poster_folder, "triage_results.xlsx")

    # Export to Excel
    df.to_excel(excel_filename, index=False)
    print(f"Data exported to {excel_filename}")

#     # 如果存在这张海报则不下载
#     if os.path.exists(poster_path):
#         return

#     response = requests.get(poster_url)
#     with open(poster_path, "wb") as file:
#         file.write(response.content)


def getFinalName(anime):
    config = readConfig()
    data_format = config.get("Format", "date_format")
    rename_format = config.get("Format", "rename_format")

    jp_name = anime["jp_name"]
    cn_name = anime["cn_name"]
    init_name = anime["init_name"]
    romaji_name = anime["romaji_name"]

    types = anime["types"]
    typecode = anime["typecode"]
    release = arrow.get(anime["release"]).format(data_format)
    episodes = anime["episodes"]

    score = anime["score"]
    bgm_id = anime["bgm_id"]

    # 保留 string 输出
    final_name = eval(f'f"{rename_format}"')
    anime["final_name"] = final_name
