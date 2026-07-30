from sidebar import SideBar
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QComboBox, QSlider, QLabel,
      QTabWidget, QListWidget, QAbstractItemView, QGroupBox, QRadioButton, QButtonGroup,
      QStackedWidget
    )
from PyQt6.QtCore import Qt, QSignalBlocker, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import json
import os
import base64
from execution_page import ResultsPage
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 
class LocationPage(QWidget): 
    def __init__(self, done_callback, parent=None): 
        super().__init__(parent) 
        self._done = done_callback

        self.regions = {
                "None Selected": ["None Selected"],
                "Northeast": 
                ["Maine", "New Hampshire", "Vermont", "Massachusetts", "Rhode Island", "Connecticut", "New York", "New Jersey", "Pennsylvania"],
                "Midwest":
                ["North Dakota", "South Dakota", "Nebraska", "Kansas", "Minnesota", "Iowa", "Missouri", "Wisconsin", "Illinois", "Indiana", "Ohio", "Michigan"],
                "South":
                ["Delaware", "Maryland", "Virginia", "West Virginia", "North Carolina", "South Carolina", "Georgia", "Florida", "Alabama", "Mississippi", "Tennessee", "Kentucky", "Arkansas", "Louisiana", "Texas", "Oklahoma"],
                "West":
                ["Montana", "Idaho", "Wyoming", "Colorado", "New Mexico", "Arizona", "Utah", "Nevada", "Washington", "Oregon", "California", "Hawaii", "Alaska"],
        }

        print(os.getcwd())
        with open(os.path.join(BASE_DIR, "location_data.json")) as f:
            self.location_data = json.load(f)

        self.selected_regions : list[str] = []
        self.selected_states : list[str] = []
        self.selected_county: str | None = None
        self.selected_city: str | None = None

        self._build_ui() 
        self._on_state_changed(self.state_cb.currentText()) 
     

    def _build_ui(self): 
        # main content
        content = QVBoxLayout() 

        # title
        title = QLabel("<h2>Location<\h2>", alignment=Qt.AlignmentFlag.AlignCenter)
        content.addWidget(title)

        # select mode
        mode_box = QGroupBox("Selection Mode")
        mb_layout = QHBoxLayout(mode_box)
        self.rb_regions = QRadioButton("Regions")
        self.rb_states = QRadioButton("States")
        self.rb_single = QRadioButton("County/City")
        mb_layout.addWidget(self.rb_regions)
        mb_layout.addWidget(self.rb_states)
        mb_layout.addWidget(self.rb_single)
        content.addWidget(mode_box)

        btn_group = QButtonGroup(self)
        for rb in (self.rb_regions, self.rb_states, self.rb_single):
            btn_group.addButton(rb)
        self.rb_regions.setChecked(True)

        # select multi region
        self.region_w = QWidget()
        rlay = QVBoxLayout(self.region_w)
        rlay.addWidget(QLabel("Pick one or more"))
        self.region_list = QListWidget()
        self.region_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.region_list.itemSelectionChanged.connect(self._on_multi_region_changed)
        region_names = list(self.regions.keys())
        self.region_list.addItems(region_names)
        rlay.addWidget(self.region_list)

        # select multi states
        self.states_w = QWidget()
        slay = QVBoxLayout(self.states_w)
        slay.addWidget(QLabel("Pick one or more states"))
        self.state_list = QListWidget()
        self.state_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.state_list.itemSelectionChanged.connect(self._on_multi_state_changed)
        self.state_list.addItems(self.location_data.keys())
        slay.addWidget(self.state_list)

        # single state & county/city
        self.single_w = QWidget()
        clay = QVBoxLayout(self.single_w)
        clay.setSpacing(2)
        clay.setContentsMargins(0, 4, 0, 0)

        clay.addWidget(QLabel("Select State:"))
        self.state_cb = QComboBox()
        self.state_cb.addItems(self.location_data.keys())
        self.state_cb.currentTextChanged.connect(self._on_state_changed)
        clay.addWidget(self.state_cb)
        clay.addSpacing(8)

        clay.addWidget(QLabel("Select County:"))
        self.county_cb = QComboBox()
        self.county_cb.currentTextChanged.connect(self._on_county_changed)
        clay.addWidget(self.county_cb)
        clay.addSpacing(8)

        clay.addWidget(QLabel("Select City:"))
        self.city_cb = QComboBox()
        self.city_cb.currentTextChanged.connect(self._on_city_changed)
        clay.addWidget(self.city_cb)
        clay.addStretch()

        self.stack = QStackedWidget()
        self.stack.addWidget(self.region_w)
        self.stack.addWidget(self.states_w)
        self.stack.addWidget(self.single_w)
        content.addWidget(self.stack)

        self.rb_regions.toggled.connect(lambda: self._show_mode(0))
        self.rb_states.toggled.connect(lambda: self._show_mode(1))
        self.rb_single.toggled.connect(lambda: self._show_mode(2))
        self._show_mode(0)

        # Use QWebEngineView so the map fills its panel the same way as Data/Settings pages.
        # Encode the image as base64 so it embeds directly in the HTML —
        # local file:// src paths are blocked by WebEngine security when using setHtml().
        self.map_view = QWebEngineView()
        map1_path = Path(BASE_DIR) / "map1.png"
        if map1_path.exists():
            img_b64 = base64.b64encode(map1_path.read_bytes()).decode()
            self.map_view.setHtml(
                f'<html><body style="margin:0;padding:0;background:#f0f0f0;">'
                f'<img src="data:image/png;base64,{img_b64}" '
                f'style="width:100%;height:100vh;object-fit:contain;">'
                f'</body></html>'
            )
        else:
            self.map_view.setHtml('<html><body style="margin:0;padding:0;background:#f0f0f0;">'
                                  '<p style="color:gray;text-align:center;padding-top:40px;">Map image not found</p>'
                                  '</body></html>')
        map_hbox = QHBoxLayout()
        map_hbox.setSpacing(0)
        map_hbox.addLayout(content, 1)
        map_hbox.addWidget(self.map_view, 2)

        # nav buttons
        self.home_btn = QPushButton("Home") 
        btn_next = QPushButton("Next")
        btn_next.clicked.connect(self._finish)
        nav_row = QHBoxLayout()
        nav_row.addWidget(self.home_btn)
        nav_row.addStretch()
        nav_row.addWidget(btn_next)
        content.addLayout(nav_row)
        self.data_btn = QPushButton("Go add data") 
        # content.addWidget(self.data_btn)

        footer = QLabel("Copyright 2026, Battelle Energy Alliance, LLC. All Rights Reserved")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #555; font-size: 10px; padding: 3px 0;"
            "border-top: 1px solid #ccc; margin-top: 2px;"
        )

        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        page_layout.addLayout(map_hbox, 1)
        page_layout.addWidget(footer)
        self.setLayout(page_layout)

    # Abstraction: encapsulates "what it means to reset a mode's data" in one place.
    # _show_mode calls this cleanly instead of doing it inline.
    def _clear_mode_data(self, index: int):
        """Clear the stored selections for the given mode index."""
        if index == 0:
            self.selected_regions = []
            with QSignalBlocker(self.region_list):
                self.region_list.clearSelection()
        elif index == 1:
            self.selected_states = []
            with QSignalBlocker(self.state_list):
                self.state_list.clearSelection()
        elif index == 2:
            self.selected_county = None
            self.selected_city = None

    # Used in: Connected to the toggled signals of the rb_regions, rb_states, and rb_single radio buttons
    def _show_mode(self, index: int):
        self.stack.setCurrentIndex(index)
        # Clear data for every mode except the one being switched to
        for mode in (0, 1, 2):
            if mode != index:
                self._clear_mode_data(mode)

    # Used in: Connected to the itemSelectionChanged signal of the region_list QListWidget.
    def _on_multi_region_changed(self):
        self.selected_regions = [i.text() for i in self.region_list.selectedItems()]

    # Used in: Connected to the currentTextChanged signal of the state_cb QComboBox.
    def _on_state_changed(self, state:str): 
        if not state: 
            return 
        counties = list(self.location_data[state].keys()) 
        with QSignalBlocker(self.county_cb): 
            self.county_cb.clear() 
        if counties: 
            self.county_cb.setCurrentIndex(0) 
            self.county_cb.addItems(counties) 

    # Used in: Connected to the currentTextChanged signal of the county_cb QComboBox.
    def _on_county_changed(self, county:str):
        state = self.state_cb.currentText()
        if not state or not county:
            return
        if county not in self.location_data[state]:
            return
        # Only record the selection when the user is actually in County/City mode.
        # The county_cb also fires during auto-population in other modes (e.g. on startup),
        # so without this guard selected_county would be set even in Regions/States mode.
        if self.rb_single.isChecked():
            self.selected_county = county
        cities = self.location_data[state][county]
        with QSignalBlocker(self.city_cb):
            self.city_cb.clear()
            self.city_cb.addItems(cities)
        if cities:
            self.city_cb.setCurrentIndex(0)

    # Used in: Connected to the currentTextChanged signal of the city_cb QComboBox.
    def _on_city_changed(self, city:str):
        # Same guard as _on_county_changed — only store when County/City mode is active.
        if self.rb_single.isChecked():
            self.selected_city = city

    # Currently not connected to any signal.
    def _on_radius_changed(self, mi:int): 
        self.radius_label.setText(f"{mi}mi") 

    # Used in: Connected to the itemSelectionChanged signal of the state_list QListWidget.
    def _on_multi_state_changed(self):
        self.selected_states = [i.text() for i in self.state_list.selectedItems()]

    # Used in: Connected to the clicked signal of the btn_next button.
    def _finish(self):
        payload = {
            "regions": self.selected_regions,
            "states": self.selected_states,
            "county": self.selected_county,
            "city": self.selected_city,
            "region_map": self.regions
        }
        self._done(payload)

    def on_done(payload):
        results_page = ResultsPage(payload)  # Pass the payload to the ResultsPage
        results_page.show()  # Show the results page