# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup
from PyQt6.QtCore import Qt, QSignalBlocker

class SideBar(QWidget):
    steps = ["Location", "Data", "Facility", "Settings", "Results"]
    
    def __init__(self, on_step_clicked):
        super().__init__()
        self.on_step_clicked = on_step_clicked
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(4)

        self.btn_group = QButtonGroup(self)
        self.buttons = {}

        for idx, name in enumerate(self.steps):
            btn = QPushButton(name)
            btn.setCheckable(True)
            # btn.setEnabled(idx==0) 
            if idx > 0:
                btn.setEnabled(False)
            btn.clicked.connect(lambda _, n=name: self._emit(n))
            self.btn_group.addButton(btn, idx)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)
            self.buttons[name] = btn

        self.buttons["Location"].setChecked(True)

    def set_active(self, name:str):
        if name in self.buttons:
            with QSignalBlocker(self.btn_group):
                self.buttons[name].setChecked(True)
        # un-check others
        for other, btn in self.buttons.items():
            if other != name:
                btn.setChecked(False)


    def unlock_next(self, curr:str):
        try:
            nxt = self.steps[self.steps.index(curr) + 1]
            self.buttons[nxt].setEnabled(True)
        except(ValueError, IndexError):
            pass
    
    def _emit(self, name:str):
        self.set_active(name)
        self.on_step_clicked(name)