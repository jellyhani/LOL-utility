from datetime import datetime
import json
import subprocess
import time
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QUrl, QTimer, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton
from bs4 import BeautifulSoup

import pyperclip
import requests
import urllib3
import urllib

process_name = 'LeagueClientUx.exe'

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AutoReadyThread(QThread):
    autoready = pyqtSignal(bool, str, str, str, str, str, str)
    def __init__(self, main_window, proc_search_thread, delay_spinbox):
        super().__init__()
        self.main_window = main_window
        self.proc_search_thread = proc_search_thread
        self.proc_search_thread.process_info_updated.connect(self.process_info_updated)
        self.delay_spinbox = delay_spinbox
    def run(self):
        while True:
            output = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True).decode('iso-8859-1')
            if process_name in output:
                try:
                    Status_url = requests.get(self.riot_api + '/lol-gameflow/v1/gameflow-phase', verify=False)
                    Status_url_response = json.loads(Status_url.text)
                    Status = Status_url_response
                    if Status == "ReadyCheck":
                        delay_seconds = self.delay_spinbox.value()
                        QThread.msleep(delay_seconds * 1000)
                        requests.post(self.riot_api + '/lol-matchmaking/v1/ready-check/accept', verify=False)
                        QThread.msleep(100)
                except Exception as e:
                    print(f"Error: {e}")
                    error_message = str(e)
                    pyperclip.copy(error_message)
                except requests.exceptions.RequestException as e:
                    print(f"An error occurred during the request: {e}")
                    error_message = str(e)
                    pyperclip.copy(error_message)
            else:
                self.quit()
    def process_info_updated(self, client_api, client_token, riot_api, riot_port, riot_token, client_port, region):
        self.client_api = client_api
        self.client_token = client_token
        self.riot_api = riot_api
        self.riot_port = riot_port
        self.riot_token = riot_token
        self.client_port = client_port
        self.region = region
    
class DodgeThread(QThread):
    dodge_signal = pyqtSignal()
    process_info_updated = pyqtSignal(str, str, str, str, str, str, str)
    def __init__(self, main_window, proc_search_thread):
        super().__init__()
        self.main_window = main_window
        self.proc_search_thread = proc_search_thread
        self.proc_search_thread.process_info_updated.connect(self.process_info_updated)
    def run(self):
        self.power = True
        zero_dodge = True
        lobby_check = requests.get(self.riot_api + '/lol-gameflow/v1/gameflow-phase', verify=False)
        lobby_check_json = json.loads(lobby_check.text)

        while self.power and lobby_check_json == 'ChampSelect':
            check = requests.get(self.riot_api + '/lol-champ-select/v1/session', verify=False)
            check_json = json.loads(check.text)
            phase = check_json['timer']['phase']
            
            if phase == 'FINALIZATION' and zero_dodge:
                QApplication.processEvents()
                self.checker = self.riot_api + "/lol-champ-select/v1/session/my-selection"
                response = requests.get(self.checker, verify=False).json()
                self.spell_1Id = response.get("spell1Id")
                self.spell_2Id = response.get("spell2Id")
                print(self.spell_1Id, self.spell_2Id)
                recovery_spell  = {
                    "spell1Id": self.spell_2Id,
                    "spell2Id": self.spell_1Id
                }
                response = requests.patch(self.checker, json=recovery_spell, verify=False)
                r = requests.get(self.riot_api + '/lol-champ-select/v1/session', verify=False)
                jsondata = json.loads(r.text)
                remaining_time_ms = jsondata["timer"]["adjustedTimeLeftInPhase"]
                remaining_time_ms -= 400
                print(remaining_time_ms)
                QThread.msleep(remaining_time_ms)
                dodge = self.riot_api + '/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&args=[\"\",\"teambuilder-draft\",\"quitV2\",\"\"]'
                body = "[\"\",\"teambuilder-draft\",\"quitV2\",\"\"]"
                response = requests.post(dodge, data=body, verify=False)
                zero_dodge = False
                self.power = False
                break
            else:
                if lobby_check_json != 'ChampSelect':
                    self.power = True
                    break
                pass
        self.quit()
    def process_info_updated(self, client_api, client_token, riot_api, riot_port, riot_token, client_port, region):
        self.client_api = client_api
        self.client_token = client_token
        self.riot_api = riot_api
        self.riot_port = riot_port
        self.riot_token = riot_token
        self.client_port = client_port
        self.region = region
    def stop(self):
        self.power = False
        self.quit()

class statusThread(QThread):
    status_updated = pyqtSignal(str)
    process_info_updated = pyqtSignal(str, str, str, str, str, str, str)
    def __init__(self, main_window, proc_search_thread):
        super(statusThread, self).__init__()
        self.main_window = main_window
        self.proc_search_thread = proc_search_thread
        self.proc_search_thread.process_info_updated.connect(self.process_info_updated)
        
    def run(self):
        loadset = False
        while True:
            output = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True).decode('iso-8859-1')
            if process_name in output:                
                if process_name in output and not loadset:
                    loadset = True
                if loadset:
                    self.main_window.load_settings()
                try:
                    Status_url = requests.get(self.riot_api + '/lol-gameflow/v1/gameflow-phase', verify=False)
                    Status_url_response = json.loads(Status_url.text)
                    Status = Status_url_response
                    self.status_updated.emit(Status)
                    QThread.msleep(100)

                except Exception as e:
                    print(f"Error: {e}")
                    self.status_updated.emit(f"Status: {e}")
                    error_message = str(e)
                    pyperclip.copy(error_message)
                except requests.exceptions.RequestException as e:
                    print(f"An error occurred during the request: {e}")
                    self.status_updated.emit(f"Status: {e}")
                    error_message = str(e)
                    pyperclip.copy(error_message)
            else:
                    self.status_updated.emit("Not Connected")
                    loadset = False
                    QThread.msleep(100)
    def process_info_updated(self, client_api, client_token, riot_api, riot_port, riot_token, client_port, region):
        self.client_api = client_api
        self.client_token = client_token
        self.riot_api = riot_api
        self.riot_port = riot_port
        self.riot_token = riot_token
        self.client_port = client_port
        self.region = region


class proc_searchThread(QThread):
    process_info_updated = pyqtSignal(str, str, str, str, str, str, str)
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.client_api = ""
        self.client_token = ""
        self.riot_api = ""
        self.riot_port = ""
        self.riot_token = ""
        self.client_port = ""
        self.region = ""
        self.process_name = 'LeagueClientUx.exe'
    def run(self):
        while True:
            try:
                output = subprocess.check_output(f'tasklist /fi "imagename eq {self.process_name}"', shell=True).decode('iso-8859-1')
                if self.process_name in output:
                    command = f'wmic PROCESS WHERE name=\'{self.process_name}\' GET commandline'
                    output = subprocess.check_output(command, shell=True).decode('iso-8859-1')
                    tokens = ["--riotclient-auth-token=", "--riotclient-app-port=", "--remoting-auth-token=", "--app-port=", "--region="]
                    for token in tokens:
                        value = output.split(token)[1].split()[0].strip('"')
                        if token == "--riotclient-app-port=":
                            self.client_port = value
                        if token == "--riotclient-auth-token=":
                            self.client_token = value
                        if token == "--app-port=":
                            self.riot_port = value
                        if token == "--remoting-auth-token=":
                            self.riot_token = value
                        if token == "--region=":
                            self.region = "oce" if value.lower() == "oc1" else value
                    self.riot_api = f'https://riot:{self.riot_token}@127.0.0.1:{self.riot_port}'
                    self.client_api = f'https://riot:{self.client_token}@127.0.0.1:{self.client_port}'
                    self.process_info_updated.emit(
                        self.client_api, self.client_token,
                        self.riot_api, self.riot_port,
                        self.riot_token, self.client_port,
                        self.region
                    )

                else:
                    self.riot_api = ""
                    self.client_api = ""
                    self.client_token = ""
                    self.client_port = ""
                    self.riot_token = ""
                    self.riot_port = ""
                    self.region = ""
                    self.process_info_updated.emit("", "", "", "", "", "", "")
            except Exception as e:
                print(f"Error: {e}")
                error_message = str(e)
                pyperclip.copy(error_message)
                self.riot_api = ""
                self.client_api = ""
                self.client_token = ""
                self.client_port = ""
                self.riot_token = ""
                self.riot_port = ""
                self.region = ""
                self.process_info_updated.emit("", "", "", "", "", "", "")

        self.msleep(100)
        return self.client_api, self.client_token, self.riot_api, self.riot_port, self. riot_token, self.client_port,self.region
            

class Ui_lolUtil(QtWidgets.QDialog):
    def setupUi(self, lolUtil):        
        self.process_name = "LeagueClientUx.exe"
        self.riot_api = ""
        self.client_api = ""
        self.client_token = ""
        self.client_port = ""
        self.riot_token = ""
        self.riot_port = ""
        self.region = ""
        
        lolUtil.setObjectName("lolUtil")
        lolUtil.resize(200, 100)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(lolUtil.sizePolicy().hasHeightForWidth())
        lolUtil.setSizePolicy(sizePolicy)
        self.verticalLayout = QtWidgets.QVBoxLayout(lolUtil)
        # self.verticalLayout_3.setAlignment(QtCore.Qt.AlignTop|QtCore.Qt.AlignLeft)
        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.status = QtWidgets.QLabel(lolUtil)
        self.status.setText("")
        self.status.setObjectName("status")
        self.verticalLayout_4.addWidget(self.status)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.verticalLayout_5.addLayout(self.verticalLayout_4)
        self.label_4 = QtWidgets.QLabel(lolUtil)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)
        self.label_4.setText("")
        self.label_4.setObjectName("label_4")
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.verticalLayout.addLayout(self.verticalLayout_5)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.Now_version_label = QtWidgets.QLabel(lolUtil)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Now_version_label.sizePolicy().hasHeightForWidth())
        self.Now_version_label.setSizePolicy(sizePolicy)
        self.Now_version_label.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.Now_version_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.Now_version_label.setOpenExternalLinks(False)
        self.Now_version_label.setObjectName("Now_version_label")
        self.horizontalLayout_2.addWidget(self.Now_version_label)
        self.Update_version_label = QtWidgets.QLabel(lolUtil)
        self.Update_version_label.setText("")
        self.Update_version_label.setObjectName("Update_version_label")
        self.horizontalLayout_2.addWidget(self.Update_version_label)
        self.Restart = QtWidgets.QPushButton(lolUtil)
        self.Restart.setObjectName("Restart")
        self.horizontalLayout_2.addWidget(self.Restart)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.Dodge = QtWidgets.QPushButton(lolUtil)
        self.Dodge.setObjectName("Dodge")
        self.horizontalLayout_2.addWidget(self.Dodge)
        self.Github_btn = QtWidgets.QPushButton(lolUtil)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Github_btn.sizePolicy().hasHeightForWidth())
        self.Github_btn.setSizePolicy(sizePolicy)
        self.Github_btn.setObjectName("Github_btn")
        self.horizontalLayout_2.addWidget(self.Github_btn)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontal_layout_within_vertical = QtWidgets.QHBoxLayout()
        # Add the horizontal layout to verticalLayout_4
        self.verticalLayout_4.addLayout(self.horizontal_layout_within_vertical)

        self.Auto_Ready = QtWidgets.QCheckBox(lolUtil)
        self.Auto_Ready.setObjectName("Auto_Ready")
        self.horizontal_layout_within_vertical.addWidget(self.Auto_Ready)

        self.spinBox = QtWidgets.QSpinBox(lolUtil)
        self.spinBox.setMaximum(99999)
        self.spinBox.setValue(0)
        self.horizontal_layout_within_vertical.addWidget(self.spinBox)

        self.empty_label = QtWidgets.QLabel(lolUtil)
        self.empty_label.setText("")
        self.empty_label.setObjectName("empty_label")
        self.empty_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.horizontal_layout_within_vertical.addWidget(self.empty_label)

        self.dodge_check = QtWidgets.QCheckBox(lolUtil)
        self.dodge_check.setObjectName("dodge_check")
        self.verticalLayout_4.addWidget(self.dodge_check)
        
        # Add two buttons horizontally
        self.matching_layout = QtWidgets.QHBoxLayout()
        description_label = QtWidgets.QLabel('Auto Matching', self)
        self.verticalLayout_4.addWidget(description_label)
        self.Auto_Matching_spinbox = QtWidgets.QSpinBox(lolUtil)
        self.Auto_Matching_spinbox.setMaximum(99999)
        self.Auto_Matching_spinbox.setValue(180)
        self.verticalLayout_4.addWidget(self.Auto_Matching_spinbox)
        self.verticalLayout_4.addLayout(self.matching_layout)
        self.start_button = QtWidgets.QPushButton('Matching Start', self)
        self.matching_layout.addWidget(self.start_button)
        self.cancel_button = QtWidgets.QPushButton('Matching Cancel', self)
        self.matching_layout.addWidget(self.cancel_button)

        self.match_timer = QTimer(self)
        self.match_timer.timeout.connect(self.matching_timeout)
        self.delay_timer = QTimer(self)
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self.delay_timer_timeout)
        self.timer_paused_time = 0  # Variable to store paused time
        self.match_start_time = None  # Variable to store the start time
        self.match_timer_duration = 0  # Variable to store the duration set in the spin box
        # Initialize riot_api attribute
        self.match_timer_duration = self.Auto_Matching_spinbox.value() * 1000
        
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.Auto_Ready.stateChanged.connect(self.Auto_Ready_Changed)
        self.retranslateUi(lolUtil)
        QtCore.QMetaObject.connectSlotsByName(lolUtil)
        
        self.proc_searchThread = proc_searchThread(self)
        self.proc_search_thread = proc_searchThread(self)
        self.status_thread = statusThread(self, self.proc_search_thread)
        self.status_thread.status_updated.connect(self.update_status_label)
        self.status_thread.start()
        self.proc_search_thread.process_info_updated.connect(self.update_process_info)
        self.proc_search_thread.start()
        self.autoreadythread = AutoReadyThread(self, self.proc_search_thread, self.spinBox)
        self.dodgethread = DodgeThread(self, self.proc_search_thread)
        
        self.Auto_Ready.stateChanged.connect(self.save_settings)
        self.dodge_check.stateChanged.connect(self.save_settings)

    def update_status_label(self, status):
        self.status.setText(f"Status: {status}")

    def start_matching(self):
        search_url = f'{self.riot_api}/lol-lobby/v2/lobby/matchmaking/search'
        response = requests.post(search_url, verify=False)
        self.match_start_time = datetime.now()
        self.match_timer_duration = self.Auto_Matching_spinbox.value() * 1000
        self.match_timer.start(self.match_timer_duration - self.timer_paused_time)

    def cancel_matching(self):
        self.match_timer.stop()
        search_url = f'{self.riot_api}/lol-lobby/v2/lobby/matchmaking/search'
        response = requests.delete(search_url, verify=False)
        self.timer_paused_time = 0
        print('Matching canceled')

    def matching_timeout(self):
        output = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True).decode('iso-8859-1')
        if process_name in output:
            Status_url = requests.get(self.riot_api+'/lol-gameflow/v1/gameflow-phase', verify=False)
            Status_url_response = json.loads(Status_url.text)
            Status = Status_url_response
            new_Status = Status
            self.timer_paused_time = self.match_timer.remainingTime()

            elapsed_time = datetime.now() - self.match_start_time
            
            if Status == 'Matchmaking':
                if self.match_timer.isActive() and new_Status == 'ChampSelect':
                    # Timer is already running, pause it
                    self.timer_paused_time = self.match_timer.remainingTime()
                    self.match_timer.start()
                    print(f'Timer paused at {self.timer_paused_time} milliseconds.')
            elif Status == 'ChampSelect':
                print('In champselect state. Stopping the timer briefly.')
                self.match_timer.stop()
                new_Status = Status
            elif Status == 'ReadyCheck':
                print('In champselect state. Stopping the timer briefly.')
                self.match_timer.stop()
            elif Status == 'InProgress':
                self.match_timer.stop()
                self.timer_paused_time = 0
                new_Status = Status
            if elapsed_time.total_seconds() * 1000 >= self.match_timer_duration:
                print('test')
                search_url = f'{self.riot_api}/lol-lobby/v2/lobby/matchmaking/search'
                response = requests.delete(search_url, verify=False)
                self.match_timer.stop()
                self.timer_paused_time = 0

                self.delay_timer.start(10000)  # 10000 milliseconds = 10 seconds

        else:
            pass
    def delay_timer_timeout(self):
        # Your code to be executed after the delay
        search_url = f'{self.riot_api}/lol-lobby/v2/lobby/matchmaking/search'
        response = requests.post(search_url, verify=False)
        self.match_timer.start(self.match_timer_duration - self.timer_paused_time)
    
    
    def save_settings(self):
        settings = QSettings('LOLutil', 'CheckBoxsetting')
        settings.setValue('Auto_Ready', self.Auto_Ready.isChecked())
        settings.setValue('dodge_check', self.dodge_check.isChecked())
    
    def load_settings(self):
        settings = QSettings('LOLutil', 'CheckBoxsetting')
        self.Auto_Ready.setChecked(settings.value('Auto_Ready', False, type=bool))
        self.dodge_check.setChecked(settings.value('dodge_check', False, type=bool))
        

    def retranslateUi(self, lolUtil):
        _translate = QtCore.QCoreApplication.translate
        lolUtil.setWindowTitle(_translate("lolUtil", "lolUtil"))
        self.Auto_Ready.setText(_translate("lolUtil", "Auto Ready"))
        update_url = "https://raw.githubusercontent.com/jellyhani/LOL-utility/main/version"
        update_url_response = requests.get(update_url)
        update_version_number = update_url_response.text.strip()
        self.dodge_check.setText(_translate("lolUtil", "0s dodge"))
        self.Now_version_label.setText(_translate("lolUtil", "현재버전 : 1.2  | 최신버전 : " + format(update_version_number)))
        self.Github_btn.setText(_translate("lolUtil", "Github"))
        self.Restart.setText(_translate("lolUtil", "Restart"))
        self.Dodge.setText(_translate("lolUtil", "Dodge"))
        self.Restart.clicked.connect(self.Restart_action)
        self.Github_btn.clicked.connect(self.open_github)
        self.Dodge.clicked.connect(self.dodge)

    def update_process_info(self, client_api, client_token, riot_api, riot_port, riot_token, client_port, region):
        self.client_api = client_api
        self.client_token = client_token
        self.riot_api = riot_api
        self.riot_port = riot_port
        self.riot_token = riot_token
        self.client_port = client_port
        self.region = region

    def Auto_Ready_Changed(self):
        output = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True).decode('iso-8859-1')
        if process_name in output and self.Auto_Ready.isChecked():
            self.autoreadythread.autoready.connect(self.autoreadythread.start)
            self.autoreadythread.start()
        else:
            self.autoreadythread.quit()
            self.autoreadythread.terminate()

    def Restart_action(self):
        output = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True).decode('iso-8859-1')
        if process_name in output:
            requests.post(self.riot_api + '/riotclient/kill-and-restart-ux', verify=False)
        else:
            QMessageBox.about(self,'error','Client not found')

    def dodge(self):
        lobby_check = requests.get(self.riot_api + '/lol-gameflow/v1/gameflow-phase', verify=False)
        lobby_check_json = json.loads(lobby_check.text)

        output = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True).decode('iso-8859-1')
        if process_name in output and lobby_check_json == 'ChampSelect':
            if self.dodge_check.isChecked():
                self.dodgethread.dodge_signal.connect(self.dodgethread.run)
                self.dodgethread.start()
                QMessageBox.about(self,'0s dodge','게임시작 0.3초 전 닷지를 진행합니다.')
            else:
                self.dodgethread.stop()
                self.dodgethread.quit()
                print("not zero-dodge checked")
                dodge = self.riot_api + '/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&args=[\"\",\"teambuilder-draft\",\"quitV2\",\"\"]'
                body = "[\"\",\"teambuilder-draft\",\"quitV2\",\"\"]"
                response = requests.post(dodge, data=body, verify=False)
                print(response)     
        else:
            print("not found " + process_name + " or ChampSelect")
            pass

    def open_github(self):
        url = QUrl("https://github.com/jellyhani/LOL-utility")
        QDesktopServices.openUrl(url)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_lolUtil()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())
