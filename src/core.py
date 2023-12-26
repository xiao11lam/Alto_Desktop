import sys
import os
import time
import threading
import shutil
import arrow
import nltk
import requests
from PySide6.QtWidgets import QMainWindow, QTableWidgetItem, QDialog, QListWidgetItem
from PySide6.QtCore import Qt, QUrl, Signal, QPoint
from PySide6.QtGui import QDesktopServices, QTextCursor
from qfluentwidgets import InfoBar, InfoBarPosition, Flyout, InfoBarIcon, RoundMenu, Action, FluentIcon

from src.gui.mainwindow import MainWindow
from src.gui.about import AboutWindow
from src.gui.setting import SettingWindow

from src.function import initList, addTimes, openFolder
from src.module.analysis import getRomajiName, getApiInfo, downloadPoster, getFinalName
from src.module.api import bangumiSubject
from src.module.config import configFile, posterFolder, formatCheck, readConfig
from src.module.version import newVersion
from src.module.resource import getResource


class MyMainWindow(QMainWindow, MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUI(self)
        self.initConnect()
        self.initList()
        self.poster_folder = posterFolder()
        addTimes("open_times")
        sys.stdout = PrintCapture(self.logs)
        nltk.data.path.append(getResource("lib/nltk_data"))

    def initConnect(self):
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)  # 自定义右键菜单
        self.table.customContextMenuRequested.connect(self.showMenu)
        self.table.itemSelectionChanged.connect(self.selectTable)

        self.searchList.setContextMenuPolicy(Qt.CustomContextMenu)  # 自定义右键菜单
        self.searchList.customContextMenuRequested.connect(self.showMenu2)

        self.aboutButton.clicked.connect(self.openAbout)
        self.settingButton.clicked.connect(self.openSetting)

        self.idEdit.clicked.connect(self.editBgmId)

        self.showLogs.clicked.connect(self.logAction)
        self.clearButton.clicked.connect(self.cleanTable)
        self.analysisButton.clicked.connect(self.startAnalysis)
        self.renameButton.clicked.connect(self.startRename)

    def initList(self):
        self.list_id = 0
        self.anime_list = []
        self.table.clearContents()
        self.table.setRowCount(0)
        self.searchList.clear()
#         self.searchList.addItem(QListWidgetItem("暂无搜索结果"))

#         self.cnName.setText("暂无动画")
#         self.jpName.setText("请先选中一个动画以展示详细信息")
#         self.typeLabel.setText("类型：")
#         self.dateLabel.setText("放送日期：")
#         self.scoreLabel.setText("当前评分：")
        self.fileName.setText("File Name:")
#         self.finalName.setText("重命名结果：")
#         self.image.updateImage(getResource("src/image/empty.png"))
#         self.idLabel.setText("")

    def openAbout(self):
        about = MyAboutWindow()
        about.exec()

    def openSetting(self):
        setting = MySettingWindow()
        setting.save_notice.connect(self.closeSetting)
        setting.exec()

    def editBgmId(self):
        row = self.RowInTable()

        if row is None:
            self.showInfo("warning", "", "请选择要修改的动画")
            return

        if not self.anime_list or "bgm_id" not in self.anime_list[row]:
            self.showInfo("warning", "", "请先开始分析")
            return
        else:
            id_now = self.anime_list[row]["bgm_id"]
            print(self.anime_list[row])
            id_want = self.idLabel.text()

        if not id_want or not id_want.isdigit():
            self.showInfo("warning", "", "ID格式不正确")
            return

        if str(id_now) == str(id_want):
            print(id_now)
            self.showInfo("warning", "未修改", "新的ID与当前ID一致")
            return

        self.correctThisAnime(row, id_want)

    def logAction(self, checked):
        if checked:
            self.showLogs.setText("隐藏日志")
            self.logFrame.setHidden(False)
            if not self.isMaximized():
                width = self.width()
                height = self.height()
                self.resize(width, height + 200)
        else:
            self.showLogs.setText("显示日志")
            self.logFrame.setHidden(True)
            if not self.isMaximized():
                width = self.width()
                height = self.height()
                self.resize(width, height - 200)

    def closeSetting(self, title):
        for anime in self.anime_list:
            getFinalName(anime)
        self.selectTable()
        self.showInfo("success", title, "配置修改成功")

    def RowInTable(self):
        for selected in self.table.selectedRanges():
            row = selected.topRow()
            return row

    def cleanTable(self):
        if not self.anime_list:
            self.showInfo("warning", "", "列表为空")
        else:
            self.initList()
            self.showInfo("success", "", "列表已清空")

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # 获取并格式化本地路径
        raw_list = event.mimeData().urls()
        result = initList(self.list_id, self.anime_list, raw_list)

        self.list_id = result[0]  # 此处的 list_id 已经比实际加了 1
        self.anime_list = result[1]

        self.showInTable()

    def showInTable(self):
        self.table.setRowCount(len(self.anime_list))

        for anime in self.anime_list:
            list_id = anime["list_id"]
            anime_id = str(list_id + 1)

            if "list_id" in anime:
                self.table.setItem(list_id, 0, QTableWidgetItem(anime_id))

            if "file_name" in anime:
                self.table.setItem(list_id, 1, QTableWidgetItem(anime["file_name"]))

            if "cn_name" in anime:
                self.table.setItem(list_id, 2, QTableWidgetItem(anime["cn_name"]))
#                 self.table.setItem(list_id, 2, QTableWidgetItem("This is the output text"))

            if "init_name" in anime:
                self.table.setItem(list_id, 3, QTableWidgetItem(anime["init_name"]))

    def startAnalysis(self):
        self.start_time = time.time()

        # 是否存在文件
        if not self.anime_list:
            self.showInfo("warning", "", "请先添加文件夹")
            return

        # 标出分析中
        anime_len = len(self.anime_list)
        for i in range(anime_len):
            self.table.setItem(i, 2, QTableWidgetItem("==> Processing"))

        # 显示进度条
        self.spinner.setVisible(True)

        # 多线程分析
        addTimes("analysis_times")
        for anime in self.anime_list:
            thread = threading.Thread(target=self.analysisThread, args=(anime,))
            thread.start()

        # 检测是否结束并隐藏进度条
        thread = threading.Thread(target=self.ThreadFinishedCheck)
        thread.start()

    def ThreadFinishedCheck(self):
        list_count = len(self.anime_list)
        while True:
            if threading.active_count() == 2:
                self.spinner.setVisible(False)
                used_time = "{:.1f}".format(time.time() - self.start_time)  # 保留一位小数
                print(f"【分析成功】 共{list_count}个动画，耗时{used_time}秒")
                return
            else:
                time.sleep(0.5)

    def analysisThread(self, anime):
        # 获取并写入罗马名
        file_name = anime["file_name"]
        romaji_name = getRomajiName(file_name)
        anime["romaji_name"] = romaji_name

        # 获取并写入分析信息
        getApiInfo(anime)
        # 使用 init_name 判断是否分析成功
        if "init_name" not in anime:
            self.table.setItem(anime["list_id"], 2, QTableWidgetItem("==> The Processing Failed"))
            return

        # 下载图片
        downloadPoster(anime)

        # 获取并写入重命名
        getFinalName(anime)

        # 重新排序 anime_list 列表，避免串行
        self.anime_list = sorted(self.anime_list, key=lambda x: x["list_id"])

        # In here it returned all the output result
        self.showInTable()

    # This is the section that if you selected the file folder, so you can get this
    def selectTable(self):
        row = self.RowInTable()

        # 应对重命名完成后的 initList 操作
        if row is None:
            return

#         if "cn_name" in self.anime_list[row]:
#             cn_name = self.anime_list[row]["cn_name"]
#             self.cnName.setText(cn_name)
#         else:
#             self.cnName.setText("暂无动画")
#
#         if "jp_name" in self.anime_list[row]:
#             jp_name = self.anime_list[row]["jp_name"]
#             self.jpName.setText(jp_name)
#         else:
#             self.jpName.setText("请先选中一个动画以展示详细信息")

#         if "types" in self.anime_list[row] and "typecode" in self.anime_list[row]:
#             types = self.anime_list[row]["types"]
#             typecode = self.anime_list[row]["typecode"]
#             self.typeLabel.setText(f"类型：{types} ({typecode})")
#         else:
#             self.typeLabel.setText("类型：")

#         if "release" in self.anime_list[row]:
#             release = self.anime_list[row]["release"]
#             release = arrow.get(release).format("YYYY年M月D日")
#             self.dateLabel.setText(f"放送日期：{release}")
#         else:
#             self.dateLabel.setText("放送日期：")

#         if "score" in self.anime_list[row]:
#             score = str(self.anime_list[row]["score"])
#             self.scoreLabel.setText(f"当前评分：{score}")
#         else:
#             self.scoreLabel.setText("当前评分：")

        # In here it controls the the "Folder Name section"
        if "file_name" in self.anime_list[row]:
            file_name = self.anime_list[row]["file_name"]
            self.fileName.setText(f"File Name:{file_name}")
        else:
            self.fileName.setText("File Name:")

        ###################################################

#         if "final_name" in self.anime_list[row]:
#             final_name = self.anime_list[row]["final_name"].replace("/", " / ")
#             self.fileName.setText(f"文件名：{file_name}")
#         else:
#             self.finalName.setText("重命名：")

#         if "poster" in self.anime_list[row]:
#             poster_name = os.path.basename(self.anime_list[row]["poster"])
#             poster_path = os.path.join(self.poster_folder, poster_name)
#             self.image.updateImage(poster_path)
#         else:
#             self.image.updateImage(getResource("src/image/empty.png"))
#
#         if "bgm_id" in self.anime_list[row]:
#             bgm_id = str(self.anime_list[row]["bgm_id"])
#             self.idLabel.setText(bgm_id)
#         else:
#             self.idLabel.setText("")
#
#         if "result" in self.anime_list[row]:
#             self.searchList.clear()
#             for this in self.anime_list[row]["result"]:
#                 release = arrow.get(this['release']).format("YY-MM-DD")
#                 cn_name = this['cn_name']
#                 item = f"[{release}] {cn_name}"
#                 self.searchList.addItem(QListWidgetItem(item))
#         else:
#             self.searchList.clear()
#             self.searchList.addItem(QListWidgetItem("暂无搜索结果"))

    def showMenu(self, pos):
        # force_bgm_id = Action(FluentIcon.SYNC, "强制根据 Bangumi ID 分析")
        view_on_bangumi = Action(FluentIcon.LINK, "在 Bangumi 中查看")
        open_this_folder = Action(FluentIcon.FOLDER, "打开此文件夹")
        open_parent_folder = Action(FluentIcon.FOLDER, "打开上级文件夹")
        delete_this_anime = Action(FluentIcon.DELETE, "删除此动画")

        menu = RoundMenu(parent=self)
        menu.addAction(view_on_bangumi)
        menu.addSeparator()
        menu.addAction(open_this_folder)
        menu.addAction(open_parent_folder)
        menu.addSeparator()
        menu.addAction(delete_this_anime)

        # 必须选中单元格才会显示
        if self.table.itemAt(pos) is not None:
            menu.exec(self.table.mapToGlobal(pos) + QPoint(0, 30), ani=True)  # 在微调菜单位置

            row = self.RowInTable()
            view_on_bangumi.triggered.connect(lambda: self.openBgmUrl(row))
            open_this_folder.triggered.connect(lambda: self.openThisFolder(row))
            open_parent_folder.triggered.connect(lambda: self.openParentFolder(row))
            delete_this_anime.triggered.connect(lambda: self.deleteThisAnime(row))

    def openBgmUrl(self, row):
        if "bgm_id" in self.anime_list[row]:
            bgm_id = str(self.anime_list[row]["bgm_id"])
            url = QUrl("https://bgm.tv/subject/" + bgm_id)
            QDesktopServices.openUrl(url)
        else:
            self.showInfo("warning", "链接无效", "请先进行动画分析")
            return

    def openThisFolder(self, row):
        path = self.anime_list[row]["file_path"]
        openFolder(path)

    def openParentFolder(self, row):
        this_path = self.anime_list[row]["file_path"]
        parent_path = os.path.dirname(this_path)
        openFolder(parent_path)

    def deleteThisAnime(self, row):
        # 删除此行
        self.anime_list.pop(row)

        # 此行后面的 list_id 重新排序
        for i in range(row, len(self.anime_list)):
            self.anime_list[i]["list_id"] -= 1

        # 全局 list_id 减一
        self.list_id -= 1

        self.showInTable()

    def showMenu2(self, pos):
        instead_this_anime = Action(FluentIcon.LABEL, "更正为这个动画")
        view_on_bangumi = Action(FluentIcon.LINK, "在 Bangumi 中查看")

        menu = RoundMenu(parent=self)
        menu.addAction(instead_this_anime)
        menu.addSeparator()
        menu.addAction(view_on_bangumi)

        # 必须选中才会显示
        if self.searchList.itemAt(pos) is not None:
            clicked_item = self.searchList.itemAt(pos)  # 计算坐标
            list_row = self.searchList.row(clicked_item)  # 计算行数
            table_row = self.RowInTable()

            # 不出现在默认列表中
            if self.searchList.item(list_row).text() != "暂无搜索结果":
                menu.exec(self.searchList.mapToGlobal(pos), ani=True)

                bgm_id = self.anime_list[table_row]["result"][list_row]["bgm_id"]
                instead_this_anime.triggered.connect(lambda: self.correctThisAnime(table_row, bgm_id))
                view_on_bangumi.triggered.connect(lambda: self.openBgmUrl(table_row))

    def correctThisAnime(self, row, bgm_id):
        result = bangumiSubject(bgm_id)

        self.anime_list[row]["bgm_id"] = bgm_id
        self.anime_list[row]["poster"] = result[0]
        self.anime_list[row]["jp_name"] = result[1].replace("/", " ")  # 移除结果中的斜杠
        self.anime_list[row]["cn_name"] = result[2].replace("/", " ")  # 移除结果中的斜杠
        self.anime_list[row]["types"] = result[3]
        self.anime_list[row]["typecode"] = result[4]
        self.anime_list[row]["release"] = result[5]
        self.anime_list[row]["episodes"] = result[6]
        self.anime_list[row]["score"] = result[7]

        downloadPoster(self.anime_list[row])
        getFinalName(self.anime_list[row])
        self.showInTable()
        self.selectTable()

    def startRename(self):
        # anime_list 是否有数据
        if not self.anime_list:
            self.showInfo("warning", "", "请先添加动画")
            return

        # 是否开始过分析
        if self.table.item(0, 2) is None:
            self.showInfo("warning", "", "请先开始分析")
            return

        # 列出 anime_list 中有 final_name 的索引
        rename_order_list = []
        final_name_check = []
        for index, dictionary in enumerate(self.anime_list):
            if "final_name" in dictionary:
                rename_order_list.append(index)
                final_name_check.append(dictionary["final_name"])

        # 检查重命名的结果是否相同
        if len(set(final_name_check)) == 1 and len(final_name_check) != 1:
            self.showInfo("warning", "", "存在重复的重命名结果")
            return

        # 是否有需要命名的动画
        if not rename_order_list:
            self.showInfo("warning", "", "没有可以命名的动画")
            return

        # 开始命名
        for order in rename_order_list:
            this_anime = self.anime_list[order]

            # 拆分 final_name 文件夹结构
            final_name = this_anime["final_name"]
            if '/' in final_name:
                final_name_list = final_name.split('/')
                final_name_1 = final_name_list[0]
                final_name_2 = final_name_list[1]
            else:
                final_name_1 = ""
                final_name_2 = final_name

            # 更名当前文件夹
            file_path = this_anime["file_path"]
            file_dir = os.path.dirname(file_path)
            final_path_2 = os.path.join(file_dir, final_name_2)
            os.rename(file_path, final_path_2)

            # 是否有父文件夹
            if final_name_1 == "":
                return

            # 创建父文件夹
            final_path_1 = os.path.join(file_dir, final_name_1)
            if not os.path.exists(final_path_1):
                os.makedirs(final_path_1)

            # 移动至父文件夹
            final_path_1 = os.path.join(file_dir, final_name_1)
            shutil.move(final_path_2, final_path_1)

        self.initList()
        addTimes("rename_times")
        self.showInfo("success", "", "重命名完成")

    def showInfo(self, state, title, content):
        info_state = {
            "info": InfoBar.info,
            "success": InfoBar.success,
            "warning": InfoBar.warning,
            "error": InfoBar.error
        }

        if state in info_state:
            info_state[state](
                title=title, content=content,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000, parent=self
            )


class MyAboutWindow(QDialog, AboutWindow):
    def __init__(self):
        super().__init__()
        self.setupUI(self)
        self.checkPing()
        self.checkVersion()
        self.config = readConfig()
        self.loadConfig()

    def loadConfig(self):
        self.openTimes.setText(self.config.get("Counter", "open_times"))
        self.analysisTimes.setText(self.config.get("Counter", "analysis_times"))
        self.renameTimes.setText(self.config.get("Counter", "rename_times"))

    def checkVersion(self):
        thread0 = threading.Thread(target=self.checkVersionThread)
        thread0.start()

    def checkVersionThread(self):
        newnew = newVersion()

        if newnew[2]:
            current_version = newnew[0]
            latest_version = newnew[1]
            self.versionLabel.setText(f"Version {current_version} (有新版本: {latest_version})")

    def checkPing(self):
        thread1 = threading.Thread(target=self.checkPingThread, args=("anilist.co", self.anilistPing))
        thread2 = threading.Thread(target=self.checkPingThread, args=("api.bgm.tv", self.bangumiPing))
        thread1.start()
        thread2.start()

    def checkPingThread(self, url, label):
        for retry in range(3):
            try:
                response = requests.get(f"http://{url}/")
                if response.status_code == 200:
                    label.setText("Online")
                    return
            except requests.ConnectionError:
                pass
            time.sleep(0.1)
        label.setText("Offline")
        label.setStyleSheet("color: #F44336")


class MySettingWindow(QDialog, SettingWindow):
    save_notice = Signal(str)

    def __init__(self):
        super().__init__()
        self.setupUI(self)
        self.initConnect()
        self.config = readConfig()
        self.loadConfig()

    def initConnect(self):
        self.posterFolderButton.clicked.connect(self.openPosterFolder)
        self.applyButton.clicked.connect(self.saveConfig)  # 保存配置
        self.cancelButton.clicked.connect(lambda: self.close())  # 关闭窗口

    def loadConfig(self):
        self.renameType.setText(self.config.get("Format", "rename_format"))
        self.dateType.setText(self.config.get("Format", "date_format"))

    def saveConfig(self):
        # 格式检查
        result = str(formatCheck(self.renameType.currentText()))
        if result != "True":
            Flyout.create(
                icon=InfoBarIcon.ERROR,
                title="",
                content=result,
                target=self.renameType,
                parent=self,
                isClosable=False
            )
            return

        self.config.set("Format", "rename_format", self.renameType.currentText())
        self.config.set("Format", "date_format", self.dateType.currentText())

        with open(configFile(), "w", encoding="utf-8") as content:
            self.config.write(content)

        self.save_notice.emit("配置已保存")
        self.close()

    def openPosterFolder(self):
        poster_folder = posterFolder()
        if poster_folder != "N/A":
            openFolder(poster_folder)


class PrintCapture:
    def __init__(self, target_widget):
        self.target_widget = target_widget

    def write(self, text):
        # text = text.replace("\n", "<br>")  # 修改为 HTML 语法的换行
        cursor = self.target_widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.target_widget.setTextCursor(cursor)

    def flush(self):
        pass
