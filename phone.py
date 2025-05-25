import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QPixmap, QColor


class TransparentDrawingOverlay(QWidget):
    def __init__(self):
        super().__init__()

        # ✅ Set as Transparent Overlay
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowTitle("Transparent Drawing Overlay")
        self.showFullScreen()

        # ✅ Initialize Drawing Variables
        self.drawing = False
        self.last_point = QPoint()
        self.eraser_mode = False  

        # ✅ Create Transparent Canvas
        self.canvas = QPixmap(self.size())
        self.canvas.fill(Qt.transparent)

        # ✅ Add Floating Control Buttons
        self.control_panel = QWidget(self)
        self.control_panel.setGeometry(20, 20, 220, 120)
        layout = QVBoxLayout()

        self.toggle_btn = QPushButton("Stop Drawing", self)
        self.toggle_btn.clicked.connect(self.toggle_overlay)
        layout.addWidget(self.toggle_btn)

        self.eraser_btn = QPushButton("Eraser OFF", self)
        self.eraser_btn.clicked.connect(self.toggle_eraser)
        layout.addWidget(self.eraser_btn)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self.clear_canvas)
        layout.addWidget(self.clear_btn)

        self.control_panel.setLayout(layout)

    def toggle_overlay(self):
        """Toggles overlay visibility"""
        if self.isVisible():
            self.hide()
            self.toggle_btn.setText("Start Drawing")
        else:
            self.showFullScreen()
            self.toggle_btn.setText("Stop Drawing")

    def toggle_eraser(self):
        """Toggles eraser mode"""
        self.eraser_mode = not self.eraser_mode
        self.eraser_btn.setText("Eraser ON" if self.eraser_mode else "Eraser OFF")

    def clear_canvas(self):
        """Clears the entire canvas"""
        self.canvas.fill(Qt.transparent)
        self.update()

    def paintEvent(self, event):
        """Paint event to render the drawing"""
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas)

    def mousePressEvent(self, event):
        """Start drawing on mouse press"""
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        """Draw as the mouse moves"""
        if self.drawing:
            painter = QPainter(self.canvas)
            pen = QPen(Qt.black if not self.eraser_mode else Qt.white, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Stop drawing on mouse release"""
        if event.button() == Qt.LeftButton:
            self.drawing = False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = TransparentDrawingOverlay()
    overlay.show()
    sys.exit(app.exec_())
