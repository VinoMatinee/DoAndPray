import sys
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QCheckBox,
    QProgressBar,
    QMainWindow,
    QWidget,
    QTextEdit,
)
from pymongo import MongoClient
import os
import datetime
import time
import subprocess
import shutil
import json

from mongoengine import Document, StringField, FileField
from mongoengine import connect

from django.conf import settings

settings.configure()
from django.contrib.auth.hashers import check_password

# MongoDB 연결 설정
client = MongoClient("mongodb+srv://admin:admin@cluster0.qs8u6xx.mongodb.net/")
db = client["dap-test1"]
users = db["auth_user"]

connect(
    "dap-test1",
    host="mongodb+srv://admin:admin@cluster0.qs8u6xx.mongodb.net/",
)


class UploadFiles(Document):
    email = StringField(required=True)
    txt_file = FileField()
    xlsx_file = FileField()
    created_at = StringField()
    # 점수 데이터 추가
    AscorePer = StringField()
    SscorePer = StringField()
    PscorePer = StringField()
    LscorePer = StringField()
    SescorePer = StringField()


class MainWindow(QMainWindow):
    def closeEvent(self, event):
        if hasattr(self, "execute_thread"):
            self.execute_thread.stop()
            self.execute_thread.wait()

        super(MainWindow, self).closeEvent(event)

    def __init__(self, user_email):
        super().__init__()

        self.user_email = user_email
        # self.report_src = os.path.dirname(os.path.realpath(__file__))
        self.report_src = os.getcwd()
        print(self.report_src)
        self.new_directory = ""
        self.date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("DAP_Security_v1.3")

        layout = QVBoxLayout()

        self.agreement_text = QTextEdit()
        self.agreement_text.setReadOnly(True)
        self.agreement_text.setPlaceholderText("약관내용")
        layout.addWidget(self.agreement_text)

        self.agreement_checkbox = QCheckBox("약관 동의")
        layout.addWidget(self.agreement_checkbox)

        self.executed = False
        run_button = QPushButton("진단 실행")
        layout.addWidget(run_button)
        run_button.clicked.connect(self.execute_program)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 4)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFormat("%v / %m")

        self.save_button = QPushButton("데이터베이스 저장")
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_to_database)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def copy_report(self, dst_folder):
        src = os.path.join(self.report_src, "W1~82", "report.txt")
        dst = os.path.join(self.report_src, dst_folder, f"report_{self.date_time}.txt")

        shutil.copy(src, dst)

    def save_directory(self):
        new_directory = os.path.join(
            "Report_file", f"{self.user_email}", self.date_time
        )
        os.makedirs(new_directory, exist_ok=True)
        self.copy_report(new_directory)

        return new_directory

    def save_to_database(self):
        email = self.user_email

        if not self.executed:
            QMessageBox.warning(self, "저장 실패", "프로그램을 다시 실행하십시오.")
        else:
            self.read_json()
            with open(
                os.path.join(self.new_directory, f"report_{self.date_time}.txt"), "rb"
            ) as txt_file, open(
                os.path.join(self.new_directory, f"report_{self.date_time}.xlsx"), "rb"
            ) as xlsx_file:
                # 파일 업로드 객체 생성
                uploaded_files = UploadFiles(
                    email=email,
                    AscorePer=self.AscorePer,
                    SscorePer=self.SscorePer,
                    PscorePer=self.PscorePer,
                    LscorePer=self.LscorePer,
                    SescorePer=self.SescorePer,
                    created_at=self.date_time,
                )

                # 파일 데이터 저장
                uploaded_files.txt_file.put(
                    txt_file,
                    filename=f"report_{self.date_time}.txt",
                )
                uploaded_files.xlsx_file.put(
                    xlsx_file,
                    filename=f"report_{self.date_time}.xlsx",
                )

                # MongoDB에 저장
                uploaded_files.save()

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("저장 완료")
            msg_box.setText("저장이 완료되었습니다.\n프로그램을 종료합니다. ")
            msg_box.setStandardButtons(QMessageBox.Ok)
            result = msg_box.exec()

            if result == QMessageBox.Ok:
                QApplication.instance().quit()

    def read_json(self):
        score_json_path = os.path.join(self.new_directory, "score.json")
        with open(score_json_path, "r") as file:
            data = json.load(file)
            if os.path.exists(score_json_path):
                print("score.json 파일을 찾았습니다.")
                (
                    self.AscorePer,
                    self.SscorePer,
                    self.PscorePer,
                    self.LscorePer,
                    self.SescorePer,
                ) = map(
                    str, data.values()
                )  # data.values()를 문자열로 변환
            else:
                print("score.json 파일을 찾지 못했습니다.")

    def execute_program(self):
        if not self.agreement_checkbox.isChecked():
            QMessageBox.warning(self, "실행 실패", "약관에 동의해주세요.")
            return

        try:
            self.progress_bar.setVisible(True)
            self.execute_thread = ExecuteThread()
            self.execute_thread.value_changed.connect(self.progress_bar.setValue)
            self.execute_thread.start()

            print("User email:", self.user_email)
            print("Date-Time:", self.date_time)
            subprocess.run(["Windo_main.bat"])
            subprocess.run(
                ["syne.exe", self.user_email, self.date_time],
            )

            self.execute_thread.finished.connect(
                lambda: self.progress_bar.setVisible(False)
            )

            self.new_directory = self.save_directory()
        except subprocess.TimeoutExpired:
            print("타임아웃: bat 파일 실행이 너무 길어 종료되었습니다")

        self.read_json()

        self.executed = True
        self.save_button.setEnabled(True)


class ExecuteThread(QThread):
    value_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.stop_flag = False

    def run(self):
        for i in range(1, 5):
            time.sleep(1)
            self.value_changed.emit(i)
            if self.stop_flag:
                break

    def stop(self):
        self.stop_flag = True


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.user_email = None

    def init_ui(self):
        self.setWindowTitle("DAP_Security_v1.3")

        layout = QVBoxLayout()

        self.label_email = QLabel("이메일")
        layout.addWidget(self.label_email)
        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        self.label_password = QLabel("비밀번호")
        layout.addWidget(self.label_password)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        login_button = QPushButton("로그인")
        layout.addWidget(login_button)
        login_button.clicked.connect(self.check_login)

        self.setLayout(layout)

    def check_login(self):
        input_email = self.email_input.text()
        input_password = self.password_input.text()

        user = users.find_one({"email": input_email})

        if user is None:
            QMessageBox.warning(self, "로그인 실패", "이메일이  없습니다.")
            return

        if check_password(input_password, user["password"]):
            QMessageBox.information(self, "로그인 성공", "성공적으로 로그인되었습니다.")
            self.close()

            self.user_email = input_email

            main_window = MainWindow(self.user_email)
            main_window.show()
        else:
            QMessageBox.warning(self, "로그인 실패", "비밀번호가 틀립니다.")


def main():
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    if app.exec_() == 0:
        main_window = MainWindow(login_window.user_email)
        main_window.show()

        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
