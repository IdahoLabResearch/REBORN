# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
# Importing the libraries
import sys
import random
import numpy as np
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QProgressBar,
    QApplication,
)
import folium
import webbrowser
import pandas as pd
import cplex
import pyomo.environ as pyo
from pyomo.environ import *
import requests
import json
import geopandas as gpd
import warnings
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
import sys
warnings.filterwarnings('ignore')
import time
import random
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import json
from folium.plugins import PolyLineTextPath
from pyomo.util.infeasible import log_infeasible_constraints, log_infeasible_bounds
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from pathlib import Path

# Class Parameters that takes all the functions into account
class Parameters:
    def __init__(self):
        # Initialize default values and value ranges for parameters
        self.seed_val = 42
        self.default_values = {
            'Seed Value': self.seed_val,
            'Transportation Cost ($ per unit battery per mile)': 2,
            'Acquisition Cost ($/unit battery)': 50,
            'Fixed Cost for Recycling ($/year)': 1000,
            'Fixed Cost for Repurposing ($/year)': 2000,
            'Packaging Cost ($/battery)': 0.59,
            'Operating Cost for Recycling ($/unit battery)': 100,
            'Operating Cost for Repurposing ($/unit battery)': 200,
            'Dealership Capacity (unit battery)': 2000,
            'Recycling Capacity (unit battery)': 2000,
            'Repurposing Capacity (unit battery)': 2000
        }
        self.value_ranges = {
            'Seed Value': (1, np.inf),
            'Transportation Cost ($ per unit battery per mile)': (2, 3),
            'Acquisition Cost ($/unit battery)': (45, 55),
            'Fixed Cost for Recycling ($/year)': (900, 1100),
            'Fixed Cost for Repurposing ($/year)': (1800, 2200),
            'Packaging Cost ($/battery)': (0.59 * 0.9, 0.59 * 1.1),
            'Operating Cost for Recycling ($/unit battery)': (90, 110),
            'Operating Cost for Repurposing ($/unit battery)': (180, 220),
            'Dealership Capacity (unit battery)': (100, 2000),
            'Recycling Capacity (unit battery)': (100, 3000),
            'Repurposing Capacity (unit battery)': (100, 3000)
        }

        self.reset_to_defaults()

    def to_dict(self):
        # Convert current values to a dictionary
        return self.values

    def update_from_dict(self, param_dict):  # Updating from the dict
        # Update current values from a dictionary
        for key, value in param_dict.items():
            self.values[key] = value

    def set_values(self, use_random=False):
        """Set values to default or randomized based on the flag."""
        if use_random:
            self.randomize_values()
        else:
            self.reset_to_defaults()

    def reset_to_defaults(self, use_random=False):
        # Reset current values to default values
        if use_random:
            self.values = self.value_ranges.copy()
        else:
            self.values = self.default_values.copy()

    def randomize_values(self):
    # Randomize current values within the specified ranges
        random.seed(self.seed_val)
        self.values = {key: value_range for key, value_range in self.value_ranges.items()}


class SettingsPage(QWidget):
    def __init__(self, parameters, done_callback, parent=None):
        super().__init__(parent)
        self.parameters = Parameters()
        self._done = done_callback
        self.selections = {}
        self.selections_df = None
        self.yearly_df = None
        self.Agg_df=None # Results to store aggregated dataframe
        self.Break_df=None # Results to store breakdown dataframe
        self.Pie_df=None # Results to store piechart results
        self._results_folder_name = None  # set after optimization completes
        self._use_new_db = False          # set by FacilityGenerationPage
        self._build_ui()  # Build the user interface

    def _build_ui(self):
        self.line_edits = {}
        self.range_edits_min = {}
        self.range_edits_max = {}

        # ── Left panel: title + parameter rows + radio + progress ─────────────
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(4)

        title = QLabel("<h1>Parameters</h1>", alignment=Qt.AlignmentFlag.AlignLeft)
        left_layout.addWidget(title)

        # ── Results folder name ───────────────────────────────────────────────
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Results Folder:"))
        self.folder_name_edit = QLineEdit()
        self.folder_name_edit.setPlaceholderText("Auto-derived from selection")
        folder_row.addWidget(self.folder_name_edit)
        left_layout.addLayout(folder_row)

        for param, default_value in self.parameters.to_dict().items():
            h_layout = QHBoxLayout()

            label = QLabel(param)
            line_edit = QLineEdit(str(default_value))
            range_min_edit = QLineEdit(str(self.parameters.value_ranges[param][0]))
            range_max_edit = QLineEdit(str(self.parameters.value_ranges[param][1]))

            if param == 'Seed Value':
                line_edit.setEnabled(False)
                range_min_edit.setEnabled(False)
                range_max_edit.setEnabled(False)
            else:
                range_min_edit.setEnabled(False)
                range_max_edit.setEnabled(False)

            line_edit.setFixedWidth(70)
            range_min_edit.setFixedWidth(50)
            range_max_edit.setFixedWidth(50)

            h_layout.addWidget(label)
            h_layout.addWidget(line_edit)
            h_layout.addWidget(range_min_edit)
            h_layout.addWidget(range_max_edit)

            left_layout.addLayout(h_layout)

            self.line_edits[param] = line_edit
            self.range_edits_min[param] = range_min_edit
            self.range_edits_max[param] = range_max_edit

        # Radio buttons
        self.radio_group = QButtonGroup(self)
        self.radio_default = QRadioButton("Use Default Values")
        self.radio_randomize = QRadioButton("Randomize Values")
        self.radio_randomize.clicked.connect(self.enable_randomization_range)
        self.radio_default.setChecked(True)
        self.radio_group.addButton(self.radio_default)
        self.radio_group.addButton(self.radio_randomize)

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_default)
        radio_layout.addWidget(self.radio_randomize)
        left_layout.addLayout(radio_layout)
        left_layout.addStretch(1)  # push everything above to the top

        # ── Right panel: folium map from the Data page ────────────────────────
        self.map_view = QWebEngineView()
        map_settings = self.map_view.settings()
        map_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        map_settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        map_settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        map_path = Path(BASE_DIR) / "map.html"
        if map_path.exists():
            self.map_view.setUrl(QUrl.fromLocalFile(str(map_path.resolve())))

        # ── Middle row: left params (1) + right map (3) ───────────────────────
        mid_layout = QHBoxLayout()
        mid_layout.addWidget(left_widget, 1)
        mid_layout.addWidget(self.map_view, 4)  # stretch=4 gives map more width

        # ── Status label + full-width progress bar below both panels ─────────
        # Check if any previous result folders exist to decide initial message
        existing_results = []
        try:
            for d in os.listdir("."):
                if not os.path.isdir(d):
                    continue
                try:
                    if any(f.endswith("_Aggregated_Final_Results.xlsx") for f in os.listdir(d)):
                        existing_results.append(d)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if existing_results:
            self.status_label.setText(
                f"Previous results found: {existing_results[0]}. "
                "Adjust parameters, Click submit, and the Run optimization to run the analysis."
            )
        else:
            self.status_label.setText(
                "No results found.  \u2192  "
                "1\ufe0f\u20e3  Choose your parameters   "
                "2\ufe0f\u20e3  Click \u2018Submit\u2019   "
                "3\ufe0f\u20e3  Click \u2018Run Optimization\u2019"
            )
        self.status_label.setStyleSheet("color: #555; font-style: italic; padding: 2px 0;")

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(28)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 4px;
                text-align: center;
                font-size: 13px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 3px;
            }
        """)

        # ── Buttons ───────────────────────────────────────────────────────────
        button_layout = QHBoxLayout()
        submit_button = QPushButton('Submit')
        submit_button.clicked.connect(self.submit_parameters)
        reset_button = QPushButton('Reset to Default')
        reset_button.clicked.connect(self.reset_to_default)
        run_optimization_button = QPushButton('Run Optimization')
        run_optimization_button.clicked.connect(self.run_optimization)
        button_layout.addWidget(submit_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(run_optimization_button)

        # ── Navigation row ────────────────────────────────────────────────────
        self.home_btn = QPushButton("Home")
        self.data_btn = QPushButton("Prev")
        btn_next = QPushButton("Next")
        btn_next.clicked.connect(self._finish)
        nav_row = QHBoxLayout()
        nav_row.addWidget(self.home_btn)
        nav_row.addStretch()
        nav_row.addLayout(button_layout)
        nav_row.addStretch()
        nav_row.addWidget(self.data_btn)
        nav_row.addWidget(btn_next)

        self.location_btn = QPushButton("Go back to city input")
        self.results_btn = QPushButton("Run")

        footer = QLabel("Copyright 2026, Battelle Energy Alliance, LLC. All Rights Reserved")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #555; font-size: 10px; padding: 3px 0;"
            "border-top: 1px solid #ccc; margin-top: 2px;"
        )

        # ── Outer layout ──────────────────────────────────────────────────────
        self.content = QVBoxLayout()
        self.content.addLayout(mid_layout, 1)       # params + map fills height
        self.content.addWidget(self.status_label)   # instruction / status text
        self.content.addWidget(self.progress_bar)   # full-width tall bar
        self.content.addLayout(nav_row)
        self.content.addWidget(footer)
        self.setLayout(self.content)

    def _finish(self):
        folder = self._results_folder_name or self.folder_name_edit.text().strip() or 'REBORN_Results'
        self._done(folder)

    def get_selection_names(self, level: str) -> list[str]:
        # return selected names fro a give level: 'region' | 'state' | 'county' | 'city'
        if getattr(self, "selections_df", None) is None:
            return []
        return (
            self.selections_df.loc[self.selections_df["level"] == level, "name"]
            .astype(str)
            .tolist()
        )
    
    def get_year_range(self):
        # returns(min year, max year) from yearly_df or None if not available
        if getattr(self, "yearly_df", None) is None or self.yearly_df.empty:
            return None
        return int(self.yearly_df["year"].min()), int(self.yearly_df["year"].max())

    def _debug_payload(self, label:str):
        print(f"\n[SettingPage] {label}")
        if getattr(self, "selections_df", None) is not None:
            print(f"selections_df: shape={self.selections_df.shape}")
            print(self.selections_df.to_string(index=False))
        else:
            print("selection_df: None")
        if getattr(self, "yearly_df", None) is not None:
            print(f"yearly_df: shape={self.yearly_df.shape}")
            print(self.yearly_df.head().to_string(index=False))
        else:
            print("yearly_df: None")

    def _make_selection_df(self, selections: dict):
        # Flatten the InputPage selection payload into a table
        rows = []
        for r in selections.get("regions", []):
            rows.append({"level": "region", "name": r})
        for s in selections.get("states", []):
            rows.append({"level": "state", "name": s})
        if selections.get('county'):
            rows.append({"level": "county", "name": selections["county"]})
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["level", "name"])
    
    def set_context(self, *, selections=None, yearly_df_records=None):
        if selections is not None:
            self.selections = selections
            self.selections_df = self._make_selection_df(selections)
            # Auto-populate folder name from the current selection
            selected_places = self.selections_df['name'].unique()
            default_name = '_'.join(str(p) for p in selected_places) if len(selected_places) > 0 else 'REBORN_Results'
            self.folder_name_edit.setText(default_name)

        if yearly_df_records is not None:
            self.yearly_df = pd.DataFrame(yearly_df_records)

        # Reload the map whenever context is updated — map.html is (re)written by DataPage
        map_path = Path(BASE_DIR) / "map.html"
        if map_path.exists():
            self.map_view.setUrl(QUrl.fromLocalFile(str(map_path.resolve())))
            self.map_view.reload()

    def set_use_new_db(self, use_new: bool):
        self._use_new_db = use_new
        facility_map = Path(BASE_DIR) / "new_facility_map.html"
        data_map = Path(BASE_DIR) / "map.html"
        if use_new and facility_map.exists():
            self.map_view.setUrl(QUrl.fromLocalFile(str(facility_map)))
        elif data_map.exists():
            self.map_view.setUrl(QUrl.fromLocalFile(str(data_map.resolve())))

    def submit_parameters(self):
        # Submit and update parameter values from line edits
        param_values = {}
        range_values = {}

        if self.radio_default.isChecked():
            for param in self.parameters.to_dict():
                try:
                    value = float(self.line_edits[param].text())
                    param_values[param] = value
                except ValueError:
                    param_values[param] = self.parameters.default_values[param]
            self.parameters.update_from_dict(param_values)

        elif self.radio_randomize.isChecked():
            for param in self.parameters.value_ranges:
                try:
                # Get the min and max from the range edits
                    min_value = float(self.range_edits_min[param].text())
                    max_value = float(self.range_edits_max[param].text())
            
            # Set the parameter values to the min and max values (you can choose to use one or both)
                    param_values[param] = (min_value, max_value)  # This will store both min and max as a tuple
                except:
                    pass

        # Update the parameters with the min and max values
            self.parameters.update_from_dict(param_values)


        print("Selected Values:")
        if self.radio_default.isChecked():
            print("Using Default Values:")
            print(self.parameters.to_dict())
        # elif self.radio_range.isChecked():
        #     print("Using Range Values:")
        #     print(self.parameters.value_ranges)
        elif self.radio_randomize.isChecked():
            print("Using Randomized Values:")
            print(self.parameters.to_dict())

    def reset_to_default(self):
        # Reset parameter values to defaults
        self.parameters.reset_to_defaults()
        self.line_edits['Seed Value'].setEnabled(False)
        for param in self.parameters.to_dict():
            self.range_edits_min[param].setEnabled(False)
            self.range_edits_max[param].setEnabled(False)
            self.line_edits[param].setEnabled(True)
        self.radio_default.setChecked(True)  # Correctly set the radio button to checked
        self.radio_randomize.setChecked(False)  # Uncheck the randomize radio button
        self.update_ui()

    def enable_randomization_range(self):
        # Enable randomization of parameter values without changing default values
        self.line_edits['Seed Value'].setEnabled(True)
        for param in self.parameters.to_dict():
            self.range_edits_min[param].setEnabled(True)
            self.range_edits_max[param].setEnabled(True)
            self.line_edits[param].setEnabled(False)
        self.update_ui()

    def update_ui(self):
        # Update the UI with current parameter values
        for param, value in self.parameters.to_dict().items():
            self.line_edits[param].setText(str(value))
            self.range_edits_min[param].setText(str(self.parameters.value_ranges[param][0]))
            self.range_edits_max[param].setText(str(self.parameters.value_ranges[param][1]))

    def show_popup(self, checked=False):
        # Show a warning popup
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle('Warning')
        msg.setText("Please click Submit to finalize the values.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)

        retval = msg.exec()
        print("Popup result:", retval)

    def run_optimization(self):
        AR_columns=['Year','Total Batteries Collected','Number of batteries recycled','Number of batteries repurposed', 'Fixed Cost($/Battery)', 'Operating Cost($/Battery)','Collection Cost($/Battery)','Packaging Cost ($/Battery)','Transportation Cost($/Battery)','Total Cost ($/Battery)','Number of recycling centers selected','Number of repurposing centers selected']
        Aggregated_Results_DataFrame=  pd.DataFrame([])

        BR_columns=['Year','Total Batteries Collected','Number of batteries recycled','Number of batteries repurposed', 'Fixed Cost for Repurposing Centers($/Battery)','Fixed Cost for Recycling Centers($/Battery)', 'Operating Cost for Repurposing Centers($/Battery)','Operating Cost for Recycling Centers($/Battery)','Collection Cost($/Battery)','Packaging Cost ($/Battery)','Transportation Cost - Dealership to Repurpose($/Battery)','Transportation Cost - Repurpose to Recycle($/Battery)','Total Cost($/Battery)','Number of recycling centers selected','Number of repurposing centers selected']
        Breakdown_Results_DataFrame=  pd.DataFrame([])
        if self._use_new_db and os.path.exists(os.path.join(BASE_DIR, 'New_Car_DB.xlsx')):
            Car_Dealers = pd.read_excel(os.path.join(BASE_DIR, 'New_Car_DB.xlsx'))
            Car_Dealers.rename(columns={
                'latitude': 'Latitude',
                'longitude': 'Longitude',
            }, inplace=True)
            Car_Dealers['Center Number'] = Car_Dealers.index
        else:
            with open(os.path.join(BASE_DIR, 'Car_USA.json'), 'r') as json_file:
                Car_Dealers = json.load(json_file)
                Car_Dealers = pd.DataFrame(Car_Dealers)
                Car_Dealers['Center Number'] = Car_Dealers.index
        if self._use_new_db and os.path.exists(os.path.join(BASE_DIR, 'New_RR_DB.xlsx')):
            EV_facilities = pd.read_excel(os.path.join(BASE_DIR, 'New_RR_DB.xlsx'))
            EV_facilities.rename(columns={
                'index': 'Facility Name',
                'center_type': 'Facilitiy Type',
                'latitude': 'Latitude',
                'longitude': 'Longitude',
                'capacity': 'Capacity',
                'state': 'Facility State or Province',
                'city': 'Facility City',
            }, inplace=True)
        else:
            with open(os.path.join(BASE_DIR, 'Pyomo_Ex_DB.json'), 'r') as json_file:
                EV_facilities = json.load(json_file)
                EV_facilities = pd.DataFrame(EV_facilities)

        # Limit facility counts to stay within 1000 constraint/variable limit
        MAX_REPURPOSING = 10   # reduced from 19
        MAX_RECYCLING   = 25   # reduced from 44
        EV_facilities = pd.concat([
            EV_facilities[EV_facilities['Facilitiy Type'] == 'P'].head(MAX_REPURPOSING),
            EV_facilities[EV_facilities['Facilitiy Type'] == 'R'].head(MAX_RECYCLING)
        ]).reset_index(drop=True)

        if self.radio_default.isChecked():
            parameter_choice = '1'
        else:
            parameter_choice = '2'
        print(self.yearly_df)
        print(self.selections_df)
        a=list(self.yearly_df['year'])
        recycle_rate=list(self.yearly_df['recycled'])
        repurpose_rate=list(self.yearly_df['repurposed'])
        total_batteries=list(self.yearly_df['total'])
        analysis_level=self.selections_df['level'].unique()
        selected_places=self.selections_df['name'].unique()
        Repurposing_Time_Selection=pd.DataFrame([])
        Recycling_Time_Selection=pd.DataFrame([])
        Dealership_Time_Selection=pd.DataFrame([])
        print(a,recycle_rate,repurpose_rate,total_batteries)
        file_storing_choice=False
        states_analyzed=[]
        # analysis_level is a numpy array — use 'in' not '=='
        if 'region' in analysis_level:
            for j in selected_places:
                if j == "Northeast":
                    state_list = ["Maine", "New Hampshire", "Vermont", "Massachusetts", "Rhode Island", "Connecticut", "New York", "New Jersey", "Pennsylvania"]
                elif j == "Midwest":
                    state_list = ["North Dakota", "South Dakota", "Nebraska", "Kansas", "Minnesota", "Iowa", "Missouri", "Wisconsin", "Illinois", "Indiana", "Ohio", "Michigan"]
                elif j == "South":
                    state_list = ["Delaware", "Maryland", "Virginia", "West Virginia", "North Carolina", "South Carolina", "Georgia", "Florida", "Alabama", "Mississippi", "Tennessee", "Kentucky", "Arkansas", "Louisiana", "Texas", "Oklahoma"]
                elif j == "West":
                    state_list = ["Montana", "Idaho", "Wyoming", "Colorado", "New Mexico", "Arizona", "Utah", "Nevada", "Washington", "Oregon", "California", "Hawaii", "Alaska"]
                else:
                    state_list = []
                states_analyzed.extend(state_list)

        elif 'state' in analysis_level:
            for j in selected_places:
                states_analyzed.append(j)

        elif 'county' in analysis_level:
            states_analyzed = []

        # Derive run name from actual selection, allow user override via folder name field
        auto_name = '_'.join(str(p) for p in selected_places) if len(selected_places) > 0 else 'REBORN_Results'
        user_name = self.folder_name_edit.text().strip()
        state_name = user_name if user_name else auto_name
        print(f"[Settings] Running optimization for: {state_name}")

        # Check if results folder already exists and inform the user
        if os.path.exists(state_name):
            msg = f"Results folder '{state_name}' already exists — results will be overwritten."
        else:
            msg = f"Starting optimization for '{state_name}'..."
        self.status_label.setText(msg)
        print(msg)
        QApplication.processEvents()

        print(states_analyzed)
        Parameters=self.parameters.to_dict()
        print(Parameters)
        total_years = len(a)
        self.progress_bar.setValue(0)
        QApplication.processEvents()
        for i in range(0, total_years):
            pct = int((i / total_years) * 100)
            print(f"[{pct}%] Year {a[i]} ({i+1}/{total_years}) — starting dealership optimisation...")
            self.status_label.setText(f"{pct}%  |  Year {a[i]}  ({i+1} of {total_years})  —  running dealership optimisation...")
            self.progress_bar.setValue(pct)
            QApplication.processEvents()
            start_time = time.time()
            # Function to find the earliest year where a center is open (1) or closed (0)
            def find_earliest_year(df, center_name, status):
                filtered_df = df[df[center_name] == status]
                if not filtered_df.empty:
                    earliest_year = filtered_df['Year'].min()
                else:
                    earliest_year = None
                return earliest_year
            # Initialize the model
            if parameter_choice=='1':
                seed=Parameters['Seed Value']
            else:
                seed=random.uniform(Parameters['Seed Value'][0],Parameters['Seed Value'][1])
            model = pyo.ConcreteModel()
        
        
        # Load the Natural Earth data for US states
            states_gdf =  gpd.read_file(os.path.join(BASE_DIR,'cb_2021_us_state_500k.zip'))

            columns=['state_name','Latitude','Longitude']
            States_Analysed=pd.DataFrame([])
            for state_name_1 in states_analyzed:
                print(state_name_1)
                filtered_option=states_gdf[states_gdf['NAME']==state_name_1]
                print(filtered_option)
                Centroid=filtered_option.geometry.centroid
                print(Centroid)
                # state_boundary = gdf.geometry.iloc[0] # Getting the boundary of the state
                # state_centroid = state_boundary.centroid # Getting the centroid of the data
                state_lat = Centroid.y.iloc[0]
                state_lon = Centroid.x.iloc[0]
                Result_Dict={'State':state_name_1,'Latitude':state_lat,'Longitude':state_lon}
                Result_List=[]
                Result_List.append(Result_Dict)
                States_Analysed=pd.concat([States_Analysed,pd.DataFrame(Result_List)])
            States_Analysed.reset_index(drop=True,inplace=True)
            States_Analysed.columns=columns
            origin_lat=States_Analysed['Latitude'].mean()
            origin_lon=States_Analysed['Longitude'].mean()       
            print(f'The co-ordinates of the NorthEast Region is {origin_lat,origin_lon}')
            
        
            # Converting the Dealership to a set
            model.TC = pyo.Set(initialize=Car_Dealers['Center Number'].tolist())
            
            if os.path.exists(state_name+'_Collection_Center_Distance.xlsx'):
                print('File exists. We do not need to calculate the distance between {} and collection centers'.format(state_name))
                State_Recycling_Distance_Frame=pd.read_excel(state_name+'_Collection_Center_Distance.xlsx')
            else:    
                State_Recycling_Distance_Frame=pd.DataFrame([], columns=['State','collection center','Distance (in miles)'])
                problem_index=[]
                print(f'Calculating the distance between {state_name} and all the collection centers')             
                for index, row in Car_Dealers.iterrows(): # Iterates through the rows
                    dest_lat=row['Latitude']
                    dest_lon=row['Longitude']
                    facility=row['Center Number']
                    r = requests.get("http://router.project-osrm.org/route/v1/truck/{},{};{},{}?overview=false".format(origin_lon,origin_lat, dest_lon,dest_lat))
                    routes = json.loads(r.content) #The json.loads() method can be used to parse a valid JSON string and convert it into a Python Dictionary
                    try:
                        route_1 = routes.get("routes")[0] 
                        Distance = route_1['distance']/(1000*1.60934) # Distance is recorded in meters. So we divide by 1000 and 1.60934 to convert it into miles
                    except:
                        print(routes['message'])
                        Distance=100000000
                        print(f'Driving path is not available between Facility {facility} and Selected State: {state_name}. Assigning the distance as {Distance} miles ')
                        
                    Result_List=[state_name, facility, Distance]
                    Result_df = pd.DataFrame([Result_List], columns=State_Recycling_Distance_Frame.columns)
                    State_Recycling_Distance_Frame=pd.concat([State_Recycling_Distance_Frame,Result_df],ignore_index=True)
                State_Recycling_Distance_Frame.reset_index(inplace=True)
            
            # if  file_storing_choice:
                with pd.ExcelWriter(state_name+'_Collection_Center_Distance.xlsx',engine='openpyxl') as writer:
                    State_Recycling_Distance_Frame.to_excel(writer,index=False)    
            
            State_distance_dict = State_Recycling_Distance_Frame.set_index('collection center')['Distance (in miles)'].to_dict()
            model.state_collection_distance = pyo.Param(model.TC, initialize=State_distance_dict, default=100000000)
            
            # Variables
            model.Y_tc = pyo.Var(model.TC, domain=Binary)  # Binary variable indicating whether Recycling center is open or not
            model.Q_total = pyo.Param(initialize=total_batteries[i])  # Total number of batteries collected from state_name in 2015.
            model.Q_tc = pyo.Var(model.TC, domain=NonNegativeReals)  # Continuous variable
            
            random.seed(seed)
            # Parameter costs obtained from Everbatt
            if parameter_choice == '1':
                model.transportation_cost = pyo.Param(initialize=Parameters['Transportation Cost ($ per unit battery per mile)'])  # Unit is $/mile
            else:
                model.transportation_cost = pyo.Param(initialize=random.uniform(Parameters['Transportation Cost ($ per unit battery per mile)'][0],Parameters['Transportation Cost ($ per unit battery per mile)'][1]))
            model.battery_weight = pyo.Param(initialize=454)  # Unit is kg
            

            # Capacity limits of each facility
            cap_tc_dict={}
            model.CAP_tc = pyo.Param(model.TC,initialize=cap_tc_dict, mutable=True)
            seed_tracker=0
            for c in model.TC:
                seed_tracker+=1
                if parameter_choice=='1':
                    model.CAP_tc[c]=Parameters['Dealership Capacity (unit battery)']
                else:
                    random.seed(seed_tracker)
                    model.CAP_tc[c]=random.randint(Parameters['Dealership Capacity (unit battery)'][0],Parameters['Dealership Capacity (unit battery)'][1])
            
            
            # # Define the Objective function: Sum of costs
            print('Model Running has started. Please be patient...................')
            def objective_rule(model):
                # Transportation costs
                C_tc = sum(model.Y_tc[c] * model.state_collection_distance[c] for c in model.TC)
                return C_tc
            model.obj = Objective(rule=objective_rule, sense=minimize)
            
            # Define Repurposing Center Capacity Limit Constraint
            def Dealer_Capacity_Limit(model, c):
                return model.Q_tc[c] <= model.CAP_tc[c] * model.Y_tc[c]
            model.dcl = pyo.Constraint(model.TC, rule=Dealer_Capacity_Limit)
            
            
            def Dealer_Equality_Balance(model):
                return sum(model.Q_tc[c] for c in model.TC) == model.Q_total  # Corrected the constrain
            model.DEL = pyo.Constraint(rule=Dealer_Equality_Balance)

            # Limit selected collection centers to stay within 1000 constraint/variable limit for Model 2
            MAX_SELECTED_CENTERS = 15
            model.max_centers_constraint = pyo.Constraint(
                expr=sum(model.Y_tc[c] for c in model.TC) <= MAX_SELECTED_CENTERS
            )

            # # Solve the model
            solver = pyo.SolverFactory('cplex')  # Use the appropriate solver
            result = solver.solve(model)
            
            # # Check if the solution is optimal
            if result.solver.status != pyo.SolverStatus.ok or result.solver.termination_condition != pyo.TerminationCondition.optimal:
                raise RuntimeError("Model has failed. Solver did not find an optimal solution")
            else:
                print('Model has been run successfully')

            mid_pct = int((i / total_years + 0.5 / total_years) * 100)
            print(f"[{mid_pct}%] Year {a[i]} — dealership optimisation complete, starting repurposing/recycling...")
            self.status_label.setText(f"{mid_pct}%  |  Year {a[i]}  ({i+1} of {total_years})  —  running repurposing/recycling optimisation...")
            self.progress_bar.setValue(mid_pct)
            QApplication.processEvents()

            C_tc = sum(pyo.value(model.Y_tc[c]) * pyo.value(model.state_collection_distance[c]) for c in model.TC)
            
            collection_map = folium.Map(location=[origin_lat, origin_lon], zoom_start=7)
            
            def custom_round(value):
                if value < 0.1:
                    return 0
                else:
                    return 1
            Collection_Selected_Locations=pd.DataFrame([])
            for c in model.TC:
                    y_ct_value=custom_round(pyo.value(model.Y_tc[c]))
                    if y_ct_value==1:
                        selected_facility=Car_Dealers[Car_Dealers['Center Number']==c]['Center Number'].iloc[0]
                        selected_lat=Car_Dealers[Car_Dealers['Center Number']==c]['Latitude'].iloc[0]
                        selected_long=Car_Dealers[Car_Dealers['Center Number']==c]['Longitude'].iloc[0]
                        selected_quantity=pyo.value(model.Q_tc[c])
                        Collection_1=pd.DataFrame([selected_facility,selected_lat,selected_long,selected_quantity]).T
                        Collection_1.columns=['Center Number','Latitude','Longitude','Capacity Received']
                        Collection_1['Max Capacity']=pyo.value(model.CAP_tc[c])
                        Collection_Selected_Locations=pd.concat([Collection_Selected_Locations,Collection_1])
                        print(f'Selected Facility {selected_facility} has been selected. It is located in {selected_lat,selected_long}\n')
                        print(f' It receives a capacity of {pyo.value(model.Q_tc[c])} batteries. It has a maximum capacity of {pyo.value(model.CAP_tc[c])} batteries/year \n')         
            # Collection_Selected_Locations.columns=['Center Number','Latitude','Longitude','Capacity','Max Capacity']
            Collection_Selected_Locations.reset_index(drop=True, inplace=True)
            Total_Selected_Collection_Centers=Collection_Selected_Locations.shape[0] # Total number of centers selected
            print('The optimized distance for transporting {} batteries in {} is {} miles and {} collection centers have been selected\n'.format(pyo.value(model.Q_total), state_name,C_tc,Total_Selected_Collection_Centers))
            with pd.ExcelWriter(state_name+'_Collection_Center_Selected_Locations_'+str(a[i])+'.xlsx',engine='openpyxl') as writer:
                Collection_Selected_Locations.to_excel(writer,index=False)
                    
            if not Collection_Selected_Locations.empty:
                row={'Year':a[i]}
                center_names=Car_Dealers['Center Number']
                for center in center_names:
                    if center in Collection_Selected_Locations['Center Number'].values:
                        row[center]=1
                    else:
                        row[center]=0
                row_list=[]
                row_list.append(row)
                Dealership_Time_Selection=pd.concat([Dealership_Time_Selection,pd.DataFrame(row_list)])
        # #%%    
            
            ## Creating the state 'NY'
            # Initialize the model
            model = pyo.ConcreteModel()  


            try:
                Selected_Car_Dealers= pd.read_excel(state_name+'_Collection_Center_Selected_Locations_'+str(a[i])+'.xlsx') # Getting the state's selected collection centers
            except:
                Selected_Car_Dealers=Collection_Selected_Locations
            
            folder_name=state_name
            folder_path=os.path.join(BASE_DIR,folder_name)
            if os.path.exists(folder_path):
                print(f'{folder_name} exists')
            else:
                print(f'{folder_name} does not exist. Creating the folder')
                os.makedirs(folder_path)
                
            
            if os.path.exists(os.path.join(folder_path,state_name+'_Collection_Center_P_Distance.xlsx')) and file_storing_choice:
            # Calculating the distance between the state and the various centers
                State_Repurposing_Distance_Frame = pd.read_excel(os.path.join(folder_path,state_name+'_Collection_Center_P_Distance.xlsx'))
            else:
                State_Repurposing_Distance_Frame=pd.DataFrame([], columns=['Center','Repurposing Facility','Distance (in miles)'])
                print(f'Calculating the distance between collection centers in {state_name} and all the Repurposing Facilities')
                P_facilities = EV_facilities[(EV_facilities['Facilitiy Type'] == 'P')]                
                for index, row1 in Selected_Car_Dealers.iterrows(): # Iterates through the rows
                    for index, row2 in P_facilities.iterrows(): # Iterates through the rows
                        origin_lat= row1['Latitude']
                        origin_lon= row1['Longitude']
                        Collection_Center=row1['Center Number']
                        dest_lat=row2['Latitude']
                        dest_lon=row2['Longitude']
                        facility=row2['Facility Name']
                        city=row2['Facility City']
                        state=row2['Facility State or Province']
                        r = requests.get("http://router.project-osrm.org/route/v1/truck/{},{};{},{}?overview=false".format(origin_lon,origin_lat, dest_lon,dest_lat))
                        try:
                            routes = json.loads(r.content) #The json.loads() method can be used to parse a valid JSON string and convert it into a Python Dictionary
                            route_1 = routes.get("routes")[0] 
                            Distance = route_1['distance']/(1000*1.60934) # Distance is recorded in meters. So we divide by 1000 and 1.60934 to convert it into miles
                        except:
                            # print(routes['message'])
                            Distance=100000000
                            print(f'Driving path is not available between Repurposing Center: {facility} located in {city, state} and Selected State: {state_name}. Assigning the distance as {Distance} miles ')
                
                        Result_List=[Collection_Center, facility, Distance]
                        Result_df = pd.DataFrame([Result_List], columns=State_Repurposing_Distance_Frame.columns)
                        State_Repurposing_Distance_Frame=pd.concat([State_Repurposing_Distance_Frame,Result_df],ignore_index=True)
            
            State_Repurposing_Distance_Frame.reset_index(drop=True,inplace=True) 
            if file_storing_choice:
                with pd.ExcelWriter(os.path.join(folder_path,state_name+'_Collection_Center_P_Distance.xlsx'),engine='openpyxl') as writer:
                    State_Repurposing_Distance_Frame.to_excel(writer,index=False) 
                State_Repurposing_Distance_Frame = pd.read_excel(os.path.join(folder_path,state_name+'_Collection_Center_P_Distance.xlsx'))
                
            
            if os.path.exists('PR_Distance.xlsx'):
            # Calculating the distance between the recycling and repurposing centers
                PR_Distance_Frame = pd.read_excel('PR_Distance.xlsx')
            else:    
                print(f'Calculating the distance between each Repurposing Facility and each Recycling Facility')
                PR_Distance_Frame=pd.DataFrame([], columns=['Repurposing_Facility','Recycling_Facility','Distance'])
                R_facilities = EV_facilities[(EV_facilities['Facilitiy Type'] == 'R')] 
                P_facilities = EV_facilities[(EV_facilities['Facilitiy Type'] == 'P')]       
                for index, row1 in P_facilities.iterrows(): # Iterates through the rows
                    for index, row2 in R_facilities.iterrows(): # Iterates through the rows
                        origin_lat=row1['Latitude']
                        origin_lon=row1['Longitude']
                        facility_p=row1['Facility Name']
                        city_p=row1['Facility City']
                        state_p=row1['Facility State or Province']
                        dest_lat=row2['Latitude']
                        dest_lon=row2['Longitude']
                        facility_r=row2['Facility Name']
                        city_r=row2['Facility City']
                        state_r=row2['Facility State or Province']
                        r = requests.get("http://router.project-osrm.org/route/v1/truck/{},{};{},{}?overview=false".format(origin_lon,origin_lat, dest_lon,dest_lat))         
                        try:
                            routes = json.loads(r.content) #The json.loads() method can be used to parse a valid JSON string and convert it into a Python Dictionary
                            route_1 = routes.get("routes")[0] 
                            Distance = route_1['distance']/(1000*1.60934) # Distance is recorded in meters. So we divide by 1000 and 1.60934 to convert it into miles
                        except:
                            # print(routes['message'])
                            Distance=100000000
                            print(f'Driving path is not available between Repurposing Facility: {facility_p} located in {city_p,state_p} and Recycling Facility: {facility_r} located in {city_r, state_r}. Assigning the distance as {Distance} miles ')
                    
                
                        Result_List=[facility_p,facility_r,Distance]
                        Result_df = pd.DataFrame([Result_List], columns=PR_Distance_Frame.columns)
                        PR_Distance_Frame=pd.concat([PR_Distance_Frame,Result_df],ignore_index=True)
            
            PR_Distance_Frame.reset_index(drop=True,inplace=True)
        # if file_storing_choice:
            with pd.ExcelWriter(('PR_Distance.xlsx'),engine='openpyxl') as writer:
                PR_Distance_Frame.to_excel(writer,index=False)
            
            
            # total_batteries=Selected_Car_Dealers['Capacity'].sum()

            model.T= pyo.Set(initialize=[a[i]])
            model.C= pyo.Set(initialize=Selected_Car_Dealers['Center Number'].unique().tolist())
            r_names = EV_facilities[EV_facilities['Facilitiy Type'] == 'R']['Facility Name'].unique().tolist()
            p_names = EV_facilities[EV_facilities['Facilitiy Type'] == 'P']['Facility Name'].unique().tolist()
            model.R = pyo.Set(initialize=r_names)
            model.P = pyo.Set(initialize=p_names)
            # Filter PR_Distance_Frame to only pairs within the capped P and R sets
            # (avoids KeyError when a cached PR_Distance.xlsx contains facilities outside the cap)
            PR_Distance_Filtered = PR_Distance_Frame[
                PR_Distance_Frame['Repurposing_Facility'].isin(p_names) &
                PR_Distance_Frame['Recycling_Facility'].isin(r_names)
            ]
            distance_dict = PR_Distance_Filtered.set_index(['Repurposing_Facility', 'Recycling_Facility'])['Distance'].to_dict()
            model.PR_distance = pyo.Param(model.P, model.R, initialize=distance_dict, default=100000000)
            State_Repurpose_distance_dict = State_Repurposing_Distance_Frame.set_index(['Center','Repurposing Facility'])['Distance (in miles)'].to_dict()
            model.state_repurpose_distance = pyo.Param(model.C, model.P, initialize=State_Repurpose_distance_dict, default=100000000)
            
            
        #     # Variables
            model.Y_cpt = pyo.Var(model.C, model.P, domain=Binary)  # Binary variable indicating whether Recycling center is open or not
            model.Y_prt = pyo.Var(model.P, model.R, domain=Binary)  # Binary variable indicating whether Repurpose center is open or not
            # model.Q_total = pyo.Param(initialize=round(total_batteries[i]))  # Total number of batteries collected from state_name in 2015.
            model.Q_total = pyo.Param(initialize=round(total_batteries[i])) 
            model.Q_Recycle_Total = pyo.Param(initialize=round(recycle_rate[i]))
            model.Q_Repurpose_Total = pyo.Param(initialize=round(repurpose_rate[i]))
            model.Q_cpt = pyo.Var(model.C, model.P, domain=NonNegativeReals)  # Continuous variable
            model.Q_prt= pyo.Var(model.P, model.R, domain=NonNegativeReals) # Continuous variable
            
            
        #     # Parameter costs obtained from Everbatt
        #     # Parameter costs obtained from Everbatt
            if parameter_choice == '1':
                model.transportation_cost = pyo.Param(initialize=Parameters['Transportation Cost ($ per unit battery per mile)'])  # Unit is $/mile
            else:
                random.seed(seed)
                model.transportation_cost = pyo.Param(initialize=random.uniform(Parameters['Transportation Cost ($ per unit battery per mile)'][0],Parameters['Transportation Cost ($ per unit battery per mile)'][1]))
            
            if parameter_choice == '1':
                model.packaging_cost = pyo.Param(initialize=Parameters['Packaging Cost ($/battery)'])  # Unit is $/mile
            else:
                random.seed(seed)
                model.packaging_cost = pyo.Param(initialize=random.uniform(Parameters['Packaging Cost ($/battery)'][0],Parameters['Max_Packaging_Cost']))
                                                    
            model.battery_weight = pyo.Param(initialize=454)  # Unit is kg
            model.R_fc=pyo.Param(model.R,initialize=1, mutable=True)
            seed_tracker=seed
            for r in model.R:
                seed_tracker+=1
                if parameter_choice == '1':
                    model.R_fc[r]=Parameters['Fixed Cost for Recycling ($/year)']
                else:
                    random.seed(seed_tracker)
                    model.R_fc[r]=random.uniform(Parameters['Fixed Cost for Recycling ($/year)'][0],Parameters['Fixed Cost for Recycling ($/year)'][1])
                    
            model.P_fc=pyo.Param(model.P,initialize=1, mutable=True)
            seed_tracker=seed
            for p in model.P:
                seed_tracker+=1
                if parameter_choice == '1':
                    model.P_fc[p]=Parameters['Fixed Cost for Repurposing ($/year)']
                else:
                    random.seed(seed_tracker)
                    model.P_fc[p]=random.uniform(Parameters['Fixed Cost for Repurposing ($/year)'],Parameters['Max_Fixed_Cost_for_Repurposing'])
            
            if parameter_choice == '1':
                model.acquisition_cost = pyo.Param(initialize=Parameters['Acquisition Cost ($/unit battery)'])  # Unit is $/mile
            else:
                model.acquisition_cost = pyo.Param(initialize=random.uniform(Parameters['Acquisition Cost ($/unit battery)'][0],Parameters['Acquisition Cost ($/unit battery)'][1]))


            model.R_oc=pyo.Param(model.R,initialize=1, mutable=True)
            seed_tracker=seed
            for r in model.R:
                seed_tracker+=1
                if parameter_choice=='1':
                    model.R_oc[r]=Parameters['Operating Cost for Recycling ($/unit battery)']
                else:
                    random.seed(seed_tracker)
                    model.R_oc[r]=random.uniform(Parameters['Operating Cost for Recycling ($/unit battery)'][0],Parameters['Operating Cost for Recycling ($/unit battery)'][1])
                    
            model.P_oc=pyo.Param(model.P,initialize=1, mutable=True)
            seed_tracker=seed
            for p in model.P:
                seed_tracker+=1
                if parameter_choice == '1':
                    model.P_oc[p]=Parameters['Operating Cost for Repurposing ($/unit battery)']
                else:
                    random.seed(seed_tracker)
                    model.P_oc[p]=random.uniform(Parameters['Operating Cost for Repurposing ($/unit battery)'][0],Parameters['Operating Cost for Repurposing ($/unit battery)'][1])
            
        #     # Capacity limits of each facility
            cap_r_dict = {row['Facility Name']: row['Capacity'] for _, row in EV_facilities[EV_facilities['Facilitiy Type'] == 'R'].iterrows()}
            model.CAP_r = pyo.Param(model.R, initialize=cap_r_dict, mutable=True)
            seed_tracker=seed
            for r in model.R:
                seed_tracker+=1
                if parameter_choice == '1':
                    try:
                        if np.isnan(pyo.value(model.CAP_r[r])):
                                    model.CAP_r[r] = Parameters['Recycling Capacity (unit battery)']
                    except:
                                    model.CAP_r[r] = Parameters['Recycling Capacity (unit battery)']
                else:
                    random.seed(seed_tracker)
                    try:
                        if np.isnan(pyo.value(model.CAP_r[r])):
                                    model.CAP_r[r] = random.uniform(Parameters['Recycling Capacity (unit battery)'][0],Parameters['Recycling Capacity (unit battery)'][1])
                    except:
                                    model.CAP_r[r] = random.uniform(Parameters['Recycling Capacity (unit battery)'][0],Parameters['Recycling Capacity (unit battery)'][1])
                
            
            cap_p_dict = {row['Facility Name']: row['Capacity'] for _, row in EV_facilities[EV_facilities['Facilitiy Type'] == 'P'].iterrows()}
            model.CAP_p = pyo.Param(model.P, initialize=cap_p_dict, mutable=True)
            seed_tracker=seed
            for p in model.P:
                seed_tracker+=1
                if parameter_choice == '1':
                    try:
                        if np.isnan(pyo.value(model.CAP_p[p])):
                                    model.CAP_p[p] = Parameters['Repurposing Capacity (unit battery)']
                    except:
                                    model.CAP_p[p] = Parameters['Repurposing Capacity (unit battery)']
                else:
                    random.seed(seed_tracker)
                    try:
                        if np.isnan(pyo.value(model.CAP_p[p])):
                                    model.CAP_p[p] = random.uniform(Parameters['Repurposing Capacity (unit battery)'][0],Parameters['Repurposing Capacity (unit battery)'][1])
                    except:
                                    model.CAP_p[p] = random.uniform(Parameters['Repurposing Capacity (unit battery)'][0],Parameters['Repurposing Capacity (unit battery)'][1])
                                    
            cap_c_dict={row['Center Number']: row['Capacity Received'] for _, row in Selected_Car_Dealers.iterrows()}
            model.CAP_c=pyo.Param(model.C,initialize=cap_c_dict,mutable=True)
            
            # # Define the Objective function: Sum of costs
            print('Model Running has started. Please be patient...................')
            def objective_rule(model):
            #     # Fixed costs
                C_FC =  sum(model.P_fc[p] * model.Y_cpt[c,p] for c in model.C for p in model.P) +  \
                        sum(model.R_fc[r] * model.Y_prt[p,r] for p in model.P for r in model.R)
            #     # Operating Costs
                C_oc = sum(model.R_oc[r] * model.Y_prt[p,r] for p in model.P for r in model.R ) + sum(model.P_oc[p] * model.Y_cpt[c,p] for c in model.C for p in model.P) 
            #     # Collection Costs
                C_cc = model.acquisition_cost * model.Q_total
            #     # Packaging Costs
                C_pc = model.battery_weight * model.packaging_cost * model.Q_total
            #     # Transportation costs
                C_tc= sum(model.transportation_cost*model.Q_cpt[c,p]*model.state_repurpose_distance[c,p] for c in model.C for p in model.P) + \
                    sum(model.transportation_cost*model.Q_prt[p,r]*model.PR_distance[p,r] for p in model.P for r in model.R)
            
                return (C_FC + C_oc + C_cc + C_pc+C_tc) / model.Q_total
            
            model.obj = Objective(rule=objective_rule, sense=minimize)
            
            # # # Constraints
            def recycling_capacity_constraint(model,p,r):
                return model.Q_prt[p,r] <= model.CAP_r[r] *model.Y_prt[p,r]
            model.recycling_capacity_constraint = pyo.Constraint(model.P,model.R, rule=recycling_capacity_constraint)
            
            # def recycling_cap_2(model,r):
            #     return sum(model.Q_prt[p,r] for p in model.P)<=model.CAP_r[r]
            # model.recycling_cap_2=pyo.Constraint(model.R, rule=recycling_cap_2)
            
            def dealership_capacity_constraint(model, c):
                return sum(model.Q_cpt[c,p] for p in model.P)<= model.CAP_c[c] 
            model.dealership_capacity_constraint = pyo.Constraint(model.C,rule=dealership_capacity_constraint)
            
            def repurposing_capacity_constraint(model,c,p):
                return model.Q_cpt[c,p]  <= model.CAP_p[p] * model.Y_cpt[c,p]
            model.repurposing_capacity_constraint = pyo.Constraint(model.C,model.P, rule=repurposing_capacity_constraint)
            
            
            # # # Define balance constraints
            def Recycle_Equality_Balance(model):
                return sum(model.Q_prt[p,r] for p in model.P for r in model.R) == model.Q_Recycle_Total
            
            model.prl = pyo.Constraint(rule=Recycle_Equality_Balance)
                
            def Repurpose_Equality_Balance(model):
                return sum(model.Q_cpt[c,p] for c in model.C for p in model.P) == model.Q_total
            
            model.cpl = pyo.Constraint(rule=Repurpose_Equality_Balance)
            
            def Individual_Repurpose_Balance(model,p):
                return sum(model.Q_cpt[c,p] for c in model.C)<=model.CAP_p[p]
            
            model.ipb=pyo.Constraint(model.P, rule=Individual_Repurpose_Balance)
            
            def Individual_Recycle_Balance(model,r):
                return sum(model.Q_prt[p,r] for p in model.P)<=model.CAP_r[r]
            
            model.irb=pyo.Constraint(model.R, rule=Individual_Recycle_Balance)
            
            def Recycle_Repurpose_Balance(model,p):
                return sum(model.Q_cpt[c,p] for c in model.C)>=sum(model.Q_prt[p,r] for r in model.R)
                
            model.cprb=pyo.Constraint(model.P, rule=Recycle_Repurpose_Balance)
            # 
            solver = pyo.SolverFactory('cplex')  # Use the appropriate solver
            result = solver.solve(model)

            # # # Check if the solution is optimal
            if result.solver.status != pyo.SolverStatus.ok or result.solver.termination_condition != pyo.TerminationCondition.optimal:
                log_infeasible_constraints(model)
                log_infeasible_bounds(model)
                raise RuntimeError("Model has failed. Solver did not find an optimal solution")
            else:
                print('Model has been run successfully')

            end_pct = int(((i + 1) / total_years) * 100)
            print(f"[{end_pct}%] Year {a[i]} — complete.")
            self.status_label.setText(f"{end_pct}%  |  Year {a[i]} complete  ({i+1} of {total_years} years done)")
            self.progress_bar.setValue(end_pct)
            QApplication.processEvents()

        # import pickle

        # def save_model(model, filename):
        #     with open(filename, 'wb') as model_file:
        #         pickle.dump(model, model_file)

        # # Usage after your optimization
        # save_model(model, ('model'+str(a)+'.pkl'))


        ### RESULTS SECTION (NEED TO BE TRANSFERRED TO EXECUTION PAGE
            for t in model.T:
            # Calculate and print C_FC, C_oc, and C_cc based on the optimized variables
                C_FC = sum(pyo.value(model.P_fc[p]) * round(pyo.value(model.Y_cpt[c,p])) for c in model.C for p in model.P) + \
                    sum(pyo.value(model.R_fc[r]) * round(pyo.value(model.Y_prt[p,r])) for p in model.P for r in model.R)
                # Operating Costs
                C_oc = sum(pyo.value(model.R_oc[r]) * pyo.value(model.Y_prt[p,r]) for p in model.P for r in model.R) + sum(pyo.value(model.P_oc[p]) * pyo.value(model.Y_cpt[c,p]) for c in model.C for p in model.P)
                # Collection Costs
                C_cc = pyo.value(model.acquisition_cost) * pyo.value(model.Q_total)
                # Packaging Costs
                C_pc = pyo.value(model.battery_weight) * pyo.value(model.packaging_cost) * pyo.value(model.Q_total)
                # Transportation costs
                C_tc= sum(pyo.value(model.transportation_cost)*pyo.value(model.Q_cpt[c,p])*pyo.value(model.state_repurpose_distance[c,p])*pyo.value(model.Y_cpt[c,p]) for c in model.C for p in model.P) +\
                    sum(pyo.value(model.transportation_cost)*pyo.value(model.Q_prt[p,r])*pyo.value(model.PR_distance[p,r])*pyo.value(model.Y_prt[p,r]) for p in model.P for r in model.R)
        
            
                print('.....................................................')
                print('Results for {} in year {} are as follows:'.format(state_name,t))
                print("\nOptimized Cost Components:")
                print(f'Total Costs per unit of battery collected ${(C_FC+C_oc+C_cc+C_pc+C_tc)/pyo.value(model.Q_total)}')
                print(f"Fixed Costs (C_FC): {C_FC/pyo.value(model.Q_total)} ($/battery)")
                print(f"Operating Costs (C_oc): {C_oc/pyo.value(model.Q_total)} ($/battery)")
                print(f"Collection Costs (C_cc): {C_cc/pyo.value(model.Q_total)} ($/battery)")
                print(f"Packaging Costs (C_pc): {C_pc/pyo.value(model.Q_total)} ($/battery)")
                print(f"Transportation Costs (C_tc): {C_tc/pyo.value(model.Q_total)} ($/battery)")
            
            
                def custom_round(value):
                    if value < 0.1:
                        return 0
                    else:
                        return 1
            
                print('Overall {} batteries have been collected from the state of {} \n'.format(pyo.value(model.Q_total), state_name))
                print('Of the {} batteries collected, {} have been recycled and {} have been repurposed\n'.format(pyo.value(model.Q_total),pyo.value(model.Q_Recycle_Total), pyo.value(model.Q_Repurpose_Total)))
                print('The selection of centers for {} are as follows'.format(state_name))
            
                R_facilities = EV_facilities[(EV_facilities['Facilitiy Type'] == 'R')] 
                P_facilities = EV_facilities[(EV_facilities['Facilitiy Type'] == 'P')]       
            
                repurpose_final=0
                Final_Repurposing_Coordinates=pd.DataFrame([])
                for c in model.C:
                    for p in model.P:
                        y_pt_value=custom_round(pyo.value(model.Y_cpt[c,p]))
                        if y_pt_value==1:
                            print(model.Y_cpt[c,p])
                            repurpose_final+=1
                            selected_facility=EV_facilities[EV_facilities['Facility Name']==p]['Facility Name']
                            selected_center=EV_facilities[EV_facilities['Facility Name']==p]['Facility Name']
                            selected_lat=EV_facilities[EV_facilities['Facility Name']==p]['Latitude']
                            selected_long=EV_facilities[EV_facilities['Facility Name']==p]['Longitude']
                            Capacity_Received=pyo.value(model.Q_cpt[c,p])
                            Max_Capacity=pyo.value(model.CAP_p[p])
                            Repurposing_1=pd.DataFrame([selected_facility,selected_lat,selected_long]).T
                            Repurposing_1['Max Capacity']=Max_Capacity
                            Repurposing_1['Capacity_Received']=Capacity_Received
                            Final_Repurposing_Coordinates=pd.concat([Final_Repurposing_Coordinates,Repurposing_1])
                            selected_state=EV_facilities[EV_facilities['Facility Name']==p]['Facility State or Province']
                            if selected_state.shape[0]==1:
                                selected_state=selected_state.item()
                            else:
                                selected_state=EV_facilities[EV_facilities['Facility Name']==p]['Facility State or Province'].unique()[0]
                            selected_city = EV_facilities[EV_facilities['Facility Name']==p]['Facility City']
                            if selected_city.shape[0]==1:
                                selected_city=selected_city.item()
                            else:
                                selected_city=EV_facilities[EV_facilities['Facility Name']==p]['Facility City'].unique()[0]
                            print(f'Collection center {c} transfers to Repurposing Center {p}. The repurposing center is located in {selected_city,selected_state}\n')
                            print(f' It receives a capacity of {pyo.value(model.Q_cpt[c,p])} batteries. It has a maximum capacity of {pyo.value(model.CAP_p[p])} batteries/year \n')         
                Final_Repurposing_Coordinates.drop_duplicates(['Latitude'],inplace=True)
                with pd.ExcelWriter(os.path.join(folder_path,state_name+'_Repurposing_Selection_'+str(t)+'.xlsx'),engine='openpyxl') as writer:
                    Final_Repurposing_Coordinates.to_excel(writer,index=False)
                print(Final_Repurposing_Coordinates)
            
                if not Final_Repurposing_Coordinates.empty:
                    row={'Year':a[i]}
                    center_names=P_facilities['Facility Name']
                    for center in center_names:
                        if center in Final_Repurposing_Coordinates['Facility Name'].values:
                            row[center]=1
                        else:
                            row[center]=0
                    row_list=[]
                    row_list.append(row)
                    Repurposing_Time_Selection=pd.concat([Repurposing_Time_Selection,pd.DataFrame(row_list)])
                
                recycle_final=0
                Final_Recycling_Coordinates=pd.DataFrame([])
                for p in model.P:
                    for r in model.R:
                        y_rt_value=custom_round(pyo.value(model.Y_prt[p,r]))
                        if y_rt_value==1:
                            print(model.Y_prt[p,r])
                            recycle_final+=1
                            selected_center=EV_facilities[EV_facilities['Facility Name']==r]['Facility Name']
                            selected_state=EV_facilities[EV_facilities['Facility Name']==r]['Facility State or Province']
                            selected_facility=EV_facilities[EV_facilities['Facility Name']==r]['Facility Name']
                            selected_lat=EV_facilities[EV_facilities['Facility Name']==r]['Latitude']
                            selected_long=EV_facilities[EV_facilities['Facility Name']==r]['Longitude']
                            Capacity_Received=pyo.value(model.Q_prt[p,r])
                            Max_Capacity=pyo.value(model.CAP_r[r])
                            Recycling_1=pd.DataFrame([selected_facility,selected_lat,selected_long]).T
                            Recycling_1['Max Capacity']=Max_Capacity
                            Recycling_1['Capacity_Received']=Capacity_Received
                            Final_Recycling_Coordinates=pd.concat([Final_Recycling_Coordinates,Recycling_1])
                            if selected_state.shape[0]==1:
                                selected_state=selected_state.item()
                            else:
                                selected_state=EV_facilities[EV_facilities['Facility Name']==r]['Facility State or Province'].unique()[0]
                            selected_city = EV_facilities[EV_facilities['Facility Name']==r]['Facility City']
                            if selected_city.shape[0]==1:
                                selected_city=selected_city.item()
                            else:
                                selected_city=EV_facilities[EV_facilities['Facility Name']==r]['Facility City'].unique()[0]
                            print(f'Repurposing Center {p} transfers to Recycling Center {r} has been selected. The recycling center is located in {selected_city,selected_state}\n')
                            print(f' It receives a capacity of {pyo.value(model.Q_prt[p,r])} batteries. It has a maximum capacity of {pyo.value(model.CAP_r[r])} batteries/year \n')
                Final_Recycling_Coordinates.drop_duplicates(['Latitude'],inplace=True)
                with pd.ExcelWriter(os.path.join(folder_path,state_name+'_Recycling_Selection_'+str(t)+'.xlsx'),engine='openpyxl') as writer:
                    Final_Recycling_Coordinates.to_excel(writer,index=False)
                print(Final_Recycling_Coordinates)   
                if not Final_Recycling_Coordinates.empty:
                    row={'Year':a[i]}
                    center_names=R_facilities['Facility Name']
                    for center in center_names:
                        if center in Final_Recycling_Coordinates['Facility Name'].values:
                            row[center]=1
                        else:
                            row[center]=0
                    row_list=[]
                    row_list.append(row)
                    Recycling_Time_Selection=pd.concat([Recycling_Time_Selection,pd.DataFrame(row_list)])
            
            
            
                # costs= {'Total fixed costs of all recycling & repurposing centers':C_FC,'Total operating costs of all recycling & repurposing centers':C_oc,'Total transportation costs':C_tc,'Total collection costs':C_cc,'Total packaging costs':C_pc}
                # # Extract labels and values
                # labels = list(costs.keys())
                # values = list(costs.values())
                # cmap = cm.get_cmap('tab20c')
                # colors = cmap(range(len(values)))
                # # Plot the pie chart
                # fig, ax = plt.subplots(figsize=(8, 8))
                # ax.pie(values, labels=labels, colors=colors,autopct='%0.1f%%', startangle=140)
                # ax.set_title('Aggregated Cost Distribution for {} in year {}'.format(state_name,t)) 
                # # Save the figure
                # output_filename = 'Aggregated cost_distribution_{}_{}.png'.format(state_name, t)
                # fig.savefig(os.path.join(state_name,output_filename))
            
                P_C_FC = sum(pyo.value(model.P_fc[p]) * round(pyo.value(model.Y_cpt[c,p])) for c in model.C for p in model.P)
                R_C_FC = sum(pyo.value(model.R_fc[r]) * round(pyo.value(model.Y_prt[p,r])) for p in model.P for r in model.R)
                # Operating Costs
                R_C_oc = sum(pyo.value(model.R_oc[r]) * pyo.value(model.Y_prt[p,r]) for p in model.P for r in model.R) 
                P_C_oc = sum(pyo.value(model.P_oc[p]) * pyo.value(model.Y_cpt[c,p]) for c in model.C for p in model.P)
                # Collection Costs
                C_cc = pyo.value(model.acquisition_cost) * pyo.value(model.Q_total)
                # Packaging Costs
                C_pc = pyo.value(model.battery_weight) * pyo.value(model.packaging_cost) * pyo.value(model.Q_total)
                # Transportation costs
                P_C_tc= sum(pyo.value(model.transportation_cost)*pyo.value(model.Q_cpt[c,p])*pyo.value(model.state_repurpose_distance[c,p])*pyo.value(model.Y_cpt[c,p]) for c in model.C for p in model.P) 
                R_C_tc=sum(pyo.value(model.transportation_cost)*pyo.value(model.Q_prt[p,r])*pyo.value(model.PR_distance[p,r])*pyo.value(model.Y_prt[p,r]) for p in model.P for r in model.R)
            
                costs= {'Fixed cost for all repurposing centers':P_C_FC,'Fixed cost for all recycling centers':R_C_FC,'Operating cost for all repurposing centers':P_C_oc,'Operating cost for all recycling centers':R_C_oc,'Transportation cost from dealership to repurposing centers':P_C_tc,'Transportation cost from repurposing to recycling centers':R_C_tc,'Total collection costs':C_cc,'Total packaging costs':C_pc}
                # Extract labels and values
                labels = list(costs.keys())
                values = list(costs.values())
                cmap = cm.get_cmap('tab20c')
                colors = cmap(range(len(values)))
                # Plot the pie chart
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(values, labels=labels, colors=colors,autopct='%0.1f%%', startangle=140)
                ax.set_title('Cost Distribution for {} in year {}'.format(state_name,t))
                output_filename = 'Breakdown cost_distribution_{}_{}.png'.format(state_name, t)
                fig.savefig(os.path.join(folder_path,output_filename))
                plt.close(fig)
            
            
                # List of states in the Northeast region
                states_gdf =  gpd.read_file(os.path.join(BASE_DIR, 'cb_2021_us_state_500k.zip'))

                # Filter the GeoDataFrame for the states in the Northeast region
                filtered_states_gdf = states_gdf[states_gdf['NAME'].isin(states_analyzed)]

            
                columns=['state_name','Latitude','Longitude']
                States_Analysed=pd.DataFrame([])
                for state_name_1 in states_analyzed:
                    filtered_option=states_gdf[states_gdf['NAME']==state_name_1]
                    Centroid=filtered_option.geometry.centroid
                    # state_boundary = gdf.geometry.iloc[0] # Getting the boundary of the state
                    # state_centroid = state_boundary.centroid # Getting the centroid of the data
                    state_lat = Centroid.y.iloc[0]
                    state_lon = Centroid.x.iloc[0]
                    Result_Dict={'State':state_name_1,'Latitude':state_lat,'Longitude':state_lon}
                    Result_List=[]
                    Result_List.append(Result_Dict)
                    States_Analysed=pd.concat([States_Analysed,pd.DataFrame(Result_List)])
                States_Analysed.reset_index(drop=True,inplace=True)
                States_Analysed.columns=columns
                origin_lat=States_Analysed['Latitude'].mean()
                origin_lon=States_Analysed['Longitude'].mean()      
                print(f'The co-ordinates of the Selected Region is {origin_lat,origin_lon}')


            
                # Create a Folium map centered at an approximate central location of the Northeast region
                map_center = [origin_lat,origin_lon]  # Approximate center of the Northeast region
                ny_map = folium.Map(location=map_center, zoom_start=6)
                ny_map_WL=folium.Map(location=map_center, zoom_start=6)
            
                # Add the GeoJson data to the map, coloring the states blue and the boundaries yellow
                folium.GeoJson(
                    filtered_states_gdf,
                    style_function=lambda feature: {
                        'fillColor': 'blue',
                        'color': 'yellow',
                        'weight': 2,
                        'fillOpacity': 0.5,
                    }
                ).add_to(ny_map)
            
                folium.GeoJson(
                    filtered_states_gdf,
                    style_function=lambda feature: {
                        'fillColor': 'blue',
                        'color': 'yellow',
                        'weight': 2,
                        'fillOpacity': 0.5,
                    }
                ).add_to(ny_map_WL)
            
            
                popup_message = f"Region Centroid<br>Total batteries repurposed: {pyo.value(model.Q_Repurpose_Total)}<br> Total batteries recycled: {pyo.value(model.Q_Recycle_Total)}"
                #     # Add a marker for the centroid
                folium.Marker(
                    location=[origin_lat, origin_lon],
                    # popup='Region Centroid',
                    popup=folium.Popup(popup_message,max_width=300),
                    icon=folium.Icon(color='orange',icon='gear',prefix='fa')
                ).add_to(ny_map)

                popup_message = f"Region Centroid<br>Total batteries repurposed: {pyo.value(model.Q_Repurpose_Total)}<br> Total batteries recycled: {pyo.value(model.Q_Recycle_Total)}"
                #     # Add a marker for the centroid
                folium.Marker(
                    location=[origin_lat, origin_lon],
                    # popup='Region Centroid',
                    popup=folium.Popup(popup_message,max_width=300),
                    icon=folium.Icon(color='orange',icon='gear',prefix='fa')
                ).add_to(ny_map_WL)
            

                # Only selected collection centers are shown (added below as darkblue markers)
                    # folium.Marker(
                    #         location=[row['Latitude'], row['Longitude']],
                    #         icon=folium.DivIcon(
                    #             html='<div style="font-size: 16px; color: lightblue;"> X</div>'  # Customize the 'X' appearance
                    #         ),
                    #         popup=row['Center Number']
                    #     ).add_to(ny_map)
            
                try:
                    Car_Dealership=pd.read_excel(state_name+'_Collection_Center_Selected_Locations_'+str(t)+'.xlsx')
                except:
                    Car_Dealership=Collection_Selected_Locations
                
                for index,row in Car_Dealership.iterrows():
                    # print(row)
                    # earliest_open_years = find_earliest_year(df, center_names, 1)
                    try:
                        earliest_open_years = find_earliest_year(Dealership_Time_Selection, row['Center Number'], 1)
                    except:
                        earliest_open_years=a[i]
                    popup_message = f"Center Number: {row['Center Number']}<br>Max Capacity: {row['Max Capacity']}<br>Capacity Received: {row['Capacity Received']}<br> Opening Period: {earliest_open_years}"
                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        # popup=row['Center Number'],
                        popup=folium.Popup(popup_message,max_width=300),
                        icon=folium.Icon(color='darkblue', icon='car', prefix='fa')
                        ).add_to(ny_map)
                
                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        # popup=row['Center Number'],
                        popup=folium.Popup(popup_message,max_width=300),
                        icon=folium.Icon(color='darkblue', icon='car', prefix='fa')
                        ).add_to(ny_map_WL)
            
                for index,row in P_facilities.iterrows():
                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        popup=row['Facility Name'],
                        icon=folium.Icon(color='lightgreen', icon='tools', prefix='fa')
                        # icon=folium.Icon(color='white', icon='tools', icon_color='lightgreen', prefix='fa')
                    ).add_to(ny_map_WL)

                     
                Repurposing_Center=pd.read_excel(os.path.join(folder_path, state_name+'_Repurposing_Selection_'+str(t)+'.xlsx'))
                for index,row in Repurposing_Center.iterrows():
                    # print(row)
                    try:
                        earliest_open_years = find_earliest_year(Repurposing_Time_Selection, row['Facility Name'], 1)
                    except:
                        earliest_open_years=a[i]
                    popup_message = f"Facility Name: {row['Facility Name']}<br>Max Capacity: {row['Max Capacity']}<br>Capacity Received: {row['Capacity_Received']}<br> Opening Period: {earliest_open_years}"
                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        popup=folium.Popup(popup_message, max_width=300),
                        # popup=row['Facility Name'],
                        icon=folium.Icon(color='darkgreen', icon='tools', prefix='fa')
                    ).add_to(ny_map)

                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        popup=folium.Popup(popup_message, max_width=300),
                        # popup=row['Facility Name'],
                        icon=folium.Icon(color='darkgreen', icon='tools', prefix='fa')
                    ).add_to(ny_map_WL)
            
                for index,row in R_facilities.iterrows():
                        folium.Marker(
                            location=[row['Latitude'],row['Longitude']],
                            popup=row['Facility Name'],
                            icon=folium.Icon(color='lightred', icon='recycle', prefix='fa')
                            # icon=folium.Icon(color='white', icon='recycle', icon_color='lightred', prefix='fa')
                        ).add_to(ny_map_WL)

            
                Recycling_Center=pd.read_excel(os.path.join(folder_path,state_name+'_Recycling_Selection_'+str(t)+'.xlsx'))
                for index,row in Recycling_Center.iterrows():
                    # print(row)
                    try:
                        earliest_open_years = find_earliest_year(Recycling_Time_Selection, row['Facility Name'], 1)
                    except:
                        earliest_open_years=a[i]
                    popup_message = f"Facility Name: {row['Facility Name']}<br>Max Capacity: {row['Max Capacity']}<br>Capacity Received: {row['Capacity_Received']}<br> Opening Period: {earliest_open_years}"
                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        popup=folium.Popup(popup_message, max_width=300),
                        # popup=row['Facility Name'],
                        icon=folium.Icon(color='darkred', icon='recycle', prefix='fa')
                    ).add_to(ny_map) 

                    folium.Marker(
                        location=[row['Latitude'],row['Longitude']],
                        popup=folium.Popup(popup_message, max_width=300),
                        # popup=row['Facility Name'],
                        icon=folium.Icon(color='darkred', icon='recycle', prefix='fa')
                    ).add_to(ny_map_WL)    
            
                for c in model.C:
                    origin_lat=States_Analysed['Latitude'].mean()
                    origin_lon=States_Analysed['Longitude'].mean()    
                    dest_lat=Selected_Car_Dealers[Selected_Car_Dealers['Center Number']==c]['Latitude'].iloc[0]
                    dest_lon=Selected_Car_Dealers[Selected_Car_Dealers['Center Number']==c]['Longitude'].iloc[0]
                    origin=[origin_lat,origin_lon]
                    destination=[dest_lat,dest_lon]
                    # folium.PolyLine(locations=[origin, destination], color='green').add_to(ny_map)
                    # Save the map to an HTML file
                    # Add the glowing effect using a PolyLineTextPath
                    folium.PolyLine(
                    [origin, destination],
                    color="orange",
                    weight=10,
                    opacity=0.5
                    ).add_to(ny_map)

                    folium.PolyLine(
                    [origin, destination],
                    color="orange",
                    weight=10,
                    opacity=0.5
                    ).add_to(ny_map_WL)

            
            
                for c in model.C:
                    for p in model.P:
                        if custom_round(pyo.value(model.Y_cpt[c,p]))==1:
                            origin_lat=Selected_Car_Dealers[Selected_Car_Dealers['Center Number']==c]['Latitude'].iloc[0]
                            origin_lon=Selected_Car_Dealers[Selected_Car_Dealers['Center Number']==c]['Longitude'].iloc[0]
                            dest_lat=EV_facilities[EV_facilities['Facility Name']==p]['Latitude'].iloc[0]
                            dest_lon=EV_facilities[EV_facilities['Facility Name']==p]['Longitude'].iloc[0]
                            origin=[origin_lat,origin_lon]
                            destination=[dest_lat,dest_lon]
                            # folium.PolyLine(locations=[origin, destination], color='green').add_to(ny_map)
                            # Save the map to an HTML file
                            # Add the glowing effect using a PolyLineTextPath
                            folium.PolyLine(
                            [origin, destination],
                            color="blue",
                            weight=10,
                            opacity=0.5
                            ).add_to(ny_map)

                            folium.PolyLine(
                            [origin, destination],
                            color="blue",
                            weight=10,
                            opacity=0.5
                            ).add_to(ny_map_WL)
                        
                        
                for p in model.P:
                    for r in model.R:
                        if custom_round(pyo.value(model.Y_prt[p,r]))==1:
                            origin_lat=EV_facilities[EV_facilities['Facility Name']==p]['Latitude'].iloc[0]
                            origin_lon=EV_facilities[EV_facilities['Facility Name']==p]['Longitude'].iloc[0]
                            dest_lat=EV_facilities[EV_facilities['Facility Name']==r]['Latitude'].iloc[0]
                            dest_lon=EV_facilities[EV_facilities['Facility Name']==r]['Longitude'].iloc[0]
                            origin=[origin_lat,origin_lon]
                            destination=[dest_lat,dest_lon]
                            # folium.PolyLine(locations=[origin, destination], color='green').add_to(ny_map)
                            # Save the map to an HTML file
                            # Add the glowing effect using a PolyLineTextPath
                            folium.PolyLine(
                            [origin, destination],
                            color="green",
                            weight=10,
                            opacity=0.5
                            ).add_to(ny_map)

                            folium.PolyLine(
                            [origin, destination],
                            color="green",
                            weight=10,
                            opacity=0.5
                            ).add_to(ny_map_WL)
            

                legend_html = '''
                    <div style="
                    position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 250px; 
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    ">
                    &nbsp; <b>Legend</b> <br>
                    &nbsp; <i style="background:blue; width: 10px; height: 10px; display: inline-block;"></i>&nbsp; NorthEast_Region <br>
                    &nbsp; <i class="fa fa-gear" style="color:orange; width: 10px; height: 10px;"></i>&nbsp; Centroid <br>
                    &nbsp; <i class="fa fa-car" style="color:lightblue; width: 10px; height: 10px;"></i>&nbsp; Existing Car Dealerships <br>
                    &nbsp; <i class="fa fa-car" style="color:darkblue; width: 10px; height: 10px;"></i>&nbsp; Chosen Car Dealerships <br>
                    &nbsp; <i class="fa fa-recycle" style="color:lightred; width: 10px; height: 10px;"></i>&nbsp; Existing Recycling Center <br>
                    &nbsp; <i class="fa fa-recycle" style="color:darkred; width: 10px; height: 10px;"></i>&nbsp; Chosen Recycling Center <br>
                    &nbsp; <i class="fa fa-tools" style="color:lightgreen; width: 10px; height: 10px;"></i>&nbsp; Existing Repurposing Center <br>
                    &nbsp; <i class="fa fa-tools" style="color:darkgreen; width: 10px; height: 10px;"></i>&nbsp; Chosen Repurposing Center <br>    
                    </div>
            #          '''
                ny_map_WL.get_root().html.add_child(folium.Element(legend_html)) 
                map_file=state_name+'_map_WL_'+str(t)+'.html'
                map_path=os.path.join(folder_path,map_file)
                ny_map_WL.save(map_path)

                legend_html = '''
                    <div style="
                    position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 150px; 
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white;
                    ">
                    &nbsp; <b>Legend</b> <br>
                    &nbsp; <i style="background:blue; width: 10px; height: 10px; display: inline-block;"></i>&nbsp; NorthEast_Region <br>
                    &nbsp; <i class="fa fa-gear" style="color:orange; width: 10px; height: 10px;"></i>&nbsp; Centroid <br>
                    &nbsp; <i class="fa fa-car" style="color:darkblue; width: 10px; height: 10px;"></i>&nbsp; Chosen Car Dealerships <br>
                    &nbsp; <i class="fa fa-recycle" style="color:darkred; width: 10px; height: 10px;"></i>&nbsp; Chosen Recycling Center <br>
                    &nbsp; <i class="fa fa-tools" style="color:darkgreen; width: 10px; height: 10px;"></i>&nbsp; Chosen Repurposing Center <br>    
                    </div>
            #          '''
                ny_map.get_root().html.add_child(folium.Element(legend_html)) 
                map_file=state_name+'_map_'+str(t)+'.html'
                map_path=os.path.join(folder_path,map_file)
                ny_map.save(map_path)
                # webbrowser.open(map_path)
                # Display the map  
                # ny_map
                Aggregated_Results_List=[]
                Breakdown_Results_List=[]
                C_total=(C_FC+C_oc+C_cc+C_pc+C_tc)/pyo.value(model.Q_total)
                Aggregated_Results_List.append([a[i],total_batteries[i],round(pyo.value(model.Q_Recycle_Total)),round(pyo.value(model.Q_Repurpose_Total)),round(C_FC/pyo.value(model.Q_total)),C_oc/pyo.value(model.Q_total),C_cc/pyo.value(model.Q_total), C_pc/pyo.value(model.Q_total), C_tc/pyo.value(model.Q_total),C_total ,repurpose_final,recycle_final])
                # Results_List.append([a[i],total_batteries,round(pyo.value(model.Q_Recycle_Total)),round(pyo.value(model.Q_Repurpose_Total)),round(C_FC/pyo.value(model.Q_total)),C_oc/pyo.value(model.Q_total),C_cc/pyo.value(model.Q_total), C_pc/pyo.value(model.Q_total), C_tc/pyo.value(model.Q_total), C_ec/pyo.value(model.Q_total),C_total ,repurpose_final,recycle_final])
                Aggregated_Results_DataFrame=pd.concat([Aggregated_Results_DataFrame,pd.DataFrame(Aggregated_Results_List)])
            
                Breakdown_Results_List.append([a[i],total_batteries[i],round(pyo.value(model.Q_Recycle_Total)),round(pyo.value(model.Q_Repurpose_Total)),round(P_C_FC/pyo.value(model.Q_total)),round(R_C_FC/pyo.value(model.Q_total)),round(P_C_oc/pyo.value(model.Q_total)),round(R_C_oc/pyo.value(model.Q_total)),C_cc/pyo.value(model.Q_total), C_pc/pyo.value(model.Q_total), round(P_C_tc/pyo.value(model.Q_total)),round(R_C_tc/pyo.value(model.Q_total)),C_total,repurpose_final,recycle_final])
                Breakdown_Results_DataFrame= pd.concat([Breakdown_Results_DataFrame,pd.DataFrame(Breakdown_Results_List)])
            
                end_time=time.time()
                Time_Elapsed=end_time-start_time
                print('Model Reading and Execution Time (in seconds): {}'.format(Time_Elapsed))

        AR_columns=['Year','Total Batteries Collected','Number of batteries recycled','Number of batteries repurposed', 'Fixed Cost($/Battery)', 'Operating Cost($/Battery)','Collection Cost($/Battery)','Packaging Cost ($/Battery)','Transportation Cost($/Battery)','Total Cost ($/Battery)','Number of recycling centers selected','Number of repurposing centers selected']
        BR_columns=['Year','Total Batteries Collected','Number of batteries recycled','Number of batteries repurposed', 'Fixed Cost for Repurposing Centers($/Battery)','Fixed Cost for Recycling Centers($/Battery)', 'Operating Cost for Repurposing Centers($/Battery)','Operating Cost for Recycling Centers($/Battery)','Collection Cost($/Battery)','Packaging Cost ($/Battery)','Transportation Cost - Dealership to Repurpose($/Battery)','Transportation Cost - Repurpose to Recycle($/Battery)','Total Cost($/Battery)','Number of recycling centers selected','Number of repurposing centers selected']
        
        Aggregated_Results_DataFrame.columns=AR_columns
        with pd.ExcelWriter(os.path.join(BASE_DIR,state_name,state_name+'_Aggregated_Final_Results.xlsx')) as writer:
                Aggregated_Results_DataFrame.to_excel(writer,index=False)

        Breakdown_Results_DataFrame.columns=BR_columns
        with pd.ExcelWriter(os.path.join(BASE_DIR,state_name,state_name+'_Breakdown_Final_Results.xlsx')) as writer:
                Breakdown_Results_DataFrame.to_excel(writer,index=False)

        self._results_folder_name = state_name
        self.progress_bar.setValue(100)
        self.status_label.setText(f"100%  |  Optimisation complete — results saved to '{state_name}/'")
        self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 2px 0;")
        QApplication.processEvents()
        print("[100%] Optimisation complete — all results published.")