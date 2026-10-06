import sys
from PyQt5 import QtWidgets, QtWebEngineWidgets, QtCore, QtGui

app = QtWidgets.QApplication(sys.argv)
view = QtWebEngineWidgets.QWebEngineView()
view.page().setBackgroundColor(QtGui.QColor("#030611"))
view.setStyleSheet("background-color: #030611;")
view.setWindowFlags(QtCore.Qt.FramelessWindowHint)
view.setGeometry(app.desktop().screenGeometry())
view.showFullScreen()
view.lower()
view.titleChanged.connect(lambda t: app.quit() if t == "EXIT" else None)
view.load(QtCore.QUrl.fromLocalFile("/opt/cyber-welcome/index.html"))
sys.exit(app.exec_())
