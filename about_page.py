# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
# about page
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMainWindow, QStackedWidget, QPushButton, QTextBrowser
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os

class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # logo
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        if os.path.exists(logo_path):
            logo = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(logo_path).scaledToWidth(120, mode=Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
            layout.addWidget(logo)

        # title
        title = QLabel("<h1>About ReCell<\h1>", alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # version and auther info
        version = QLabel("Version 0.0", alignment=Qt.AlignmentFlag.AlignCenter)
        author = QLabel("Srikar, Yuan-Yuan, Miles, Andrew", alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        layout.addWidget(author)

        # description
        description = QTextBrowser()
        description.setReadOnly(True)
        description.setHtml("""
            <p>Finding the best place to recycle your batteries.</p>
                <p>Features:</p>
                    <ul>
                        <li> Location Page </li>
                        <li> About Page </li>
                    </ul>
        """)
        layout.addWidget(description)

        self.home_btn = QPushButton("Back")
        layout.addWidget(self.home_btn, alignment=Qt.AlignmentFlag.AlignCenter)