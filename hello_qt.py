import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout

def on_click():
    label.setText("Hello, World!")

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("My Test App")
window.resize(300, 150)

layout = QVBoxLayout()

label = QLabel("Click the button")
layout.addWidget(label)

button = QPushButton("Say Hello")
button.clicked.connect(on_click)
layout.addWidget(button)

window.setLayout(layout)
window.show()

sys.exit(app.exec_())
