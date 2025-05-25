import sys
import socketio
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtGui import QPainter, QPen
from PyQt5.QtCore import Qt, QPoint

sio = socketio.Client()
sio.connect("http://localhost:5000")

class DisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laptop Display Screen")
        self.setGeometry(200, 100, 600, 400)
        self.canvas = DisplayCanvas(self)
        self.setCentralWidget(self.canvas)

class DisplayCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines = []

        @sio.on("draw")
        def receive_draw(data):
            self.lines.append(data)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(Qt.black, 3, Qt.SolidLine))

        for line in self.lines:
            painter.drawLine(line["x1"], line["y1"], line["x2"], line["y2"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DisplayApp()
    window.show()
    sys.exit(app.exec_())
