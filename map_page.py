# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QComboBox, QSlider, QLabel, QTabWidget, QListWidget, QAbstractItemView
from PyQt6.QtCore import Qt, QSignalBlocker 

class MapPage(QWidget):
    def __init__(self, done_callback, parent=None):
        super().__init__(parent) 
        self._done = done_callback
        self._build_ui()

    def _build_ui(self):
        # main content
        content = QVBoxLayout() 

        # title
        title = QLabel("<h2>Map<\h2>", alignment=Qt.AlignmentFlag.AlignCenter)
        content.addWidget(title)

        # nav buttons
        self.home_btn = QPushButton("Home") 
        self.data_btn = QPushButton("Prev")
        btn_next = QPushButton("Next")
        btn_next.clicked.connect(self._finish)
        nav_row = QHBoxLayout()
        nav_row.addWidget(self.home_btn)
        nav_row.addStretch()
        nav_row.addWidget(self.data_btn)
        nav_row.addWidget(btn_next)
        content.addLayout(nav_row)

        # self.home_btn = QPushButton("Back home")
        self.Location_btn = QPushButton("Go back to city Location")
        # self.data_btn = QPushButton("Go back add data")
        self.settings_btn = QPushButton("Go enter settings")
        # content.addWidget(self.home_btn)
        # content.addWidget(self.Location_btn)
        # content.addWidget(self.data_btn)
        # content.addWidget(self.settings_btn)

        self.setLayout(content)

    def _finish(self):
        self._done()