import sys
from PyQt5.QtWidgets import (QMainWindow, QLabel, QApplication, QMessageBox)
from PyQt5 import QtCore
import xls2lua
import os

class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.lbl = QLabel('拖文件上来', self)
        self.lbl.adjustSize()
        self.lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.setCentralWidget(self.lbl)

        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, False)
        self.setAcceptDrops(True)
        self.setGeometry(300, 300, 350, 300)
        self.setWindowTitle('导表')
        self.show()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        results = []
        suc = 0
        for input_file in files:
            pre, ext = os.path.splitext(input_file)
            output_file = pre + '.lua'
            try:
                xls2lua.xls2lua(input_file, output_file)
                results.append((input_file,None))
                suc += 1
            except (xls2lua.ParseError,xls2lua.EvalError,xls2lua.FileFormatError,IOError) as e:
                results.append((input_file,e))
            except Exception as e:
                results.append((input_file,e))

        # 逐一提示错误
        for r in results:
            (f,e) = r
            if e is not None:
                title = None
                if isinstance(e, xls2lua.ParseError):
                    title = '解析错误'
                elif isinstance(e, xls2lua.EvalError):
                    title = '数据错误'
                elif isinstance(e, xls2lua.FileFormatError):
                    title = '文件错误'
                else:
                    title = '未知错误'
                QMessageBox.question(self, '%s:%s' % (title, f), str(e), QMessageBox.Yes)

        # 修改标题
        self.setWindowTitle('导表[%d/%d]' % (suc, len(files)))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    wnd = AppWindow()
    sys.exit(app.exec_())
