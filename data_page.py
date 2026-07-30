# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
from sidebar import SideBar
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QFormLayout,
      QDoubleSpinBox, QMessageBox, QFileDialog, QRadioButton, QTabWidget, QLineEdit, QGridLayout,
      QTableWidget, QSpinBox
)
from PyQt6.QtCore import Qt, QSignalBlocker, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import pandas as pd
from pathlib import Path
from typing import Dict, List
import folium
from geopy.geocoders import Nominatim
import json
import html
import numpy as np
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from folium import Marker, Popup
from branca.element import Element
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Full state name → 2-letter abbreviation
_STATE_TO_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}

class YearDemandTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tbl = QTableWidget(0, 3, self)
        self.tbl.setHorizontalHeaderLabels(["Year", "Recycled", "Repurposed"])
        self.tbl.horizontalHeader().setStretchLastSection(True)

        btn_add = QPushButton("Add year")
        btn_save = QPushButton("Save CSV/Excel")

        btn_add.clicked.connect(self._add_row)
        btn_save.clicked.connect(self._export)

        ctl = QHBoxLayout()
        ctl.addWidget(btn_add)
        ctl.addStretch()
        ctl.addWidget(btn_save)

        lay = QVBoxLayout(self)
        lay.addLayout(ctl)
        lay.addWidget(self.tbl)
    
    # adds a new row to the table with year, recycled and repurposed values 
    # (Used in: Connected to the "Add year" button's clicked signal)
    def _add_row(self):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)

        spin_year = QSpinBox()
        spin_year.setRange(2000, 2100)
        self.tbl.setCellWidget(r, 0, spin_year)

        for col in (1, 2):
            spin = QDoubleSpinBox()
            spin.setRange(0, 1e9)
            spin.setDecimals(2)
            self.tbl.setCellWidget(r, col, spin)
        
    # Collects data from each row and returns it as a list of dictionaries containing year, recycled, and repurposed values 
    # (Used in: The _export method to gather data before exporting)
    def _rows_as_dicts(self):
        rows = []
        for r in range(self.tbl.rowCount()):
            year = self.tbl.cellWidget(r, 0).value()
            recyc = self.tbl.cellWidget(r, 1).value()
            repurp = self.tbl.cellWidget(r, 2).value()
            if year:
                rows.append({"year": year,
                             "recycled": recyc,
                             "repurposed": repurp,
                })
        return rows
    
    # Collects row data, opens a file dialog for selecting save location and format (CSV or Excel), and saves the data to the selected file
    # (Used in: Connected to the "Save CSV/Excel" button's clicked signal)
    def _export(self):
        rows = self._rows_as_dicts()
        if not rows:
            return
        
        df = pd.DataFrame(rows).sort_values("year")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save file", "", "Excel (*.xlsx);; CSV(*.csv)"
        )
        if not path:
            return
        if path.endswith(".csv"):
            df.to_csv(path, index=False)
        else:
            df.to_excel(path, index=False)
            


class DataPage(QWidget):
    def __init__(
            self, 
            selections: Dict,
            region_map: Dict[str, List[str]],
            done_callback, 
            paths:Dict[str, Path] | None = None,
            parent=None
        ):
        super().__init__(parent) 
        with open(os.path.join(BASE_DIR, "location_data.json")) as f:
            self.location_data = json.load(f)
        self.selections = selections
        self.region_map = region_map
        self._done = done_callback
        self.period_mode: str = "multiple"
        self.period_year: int | None = None
        self.paths = paths or {
            "regions": Path(BASE_DIR) / "default_data_regions.xlsx",
            "states": Path(BASE_DIR) / "default_data_states.xlsx",
            "counties": Path(BASE_DIR) / "default_data_counties.xlsx",
            "cities": Path(BASE_DIR) / "default_data_cities.xlsx",
        }
        self.default_df: pd.DataFrame | None = None
        self.effective = self._deduplicate()
        self.map_view = QWebEngineView()
        settings = self.map_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self._build_ui()

    # builds the entire UI
    def _build_ui(self):
        # default tab
        default_tab = QWidget()
        left_default_content = QVBoxLayout(default_tab)

        # year selection
        header1 = QLabel("<h4>Select year</h4>")
        left_default_content.addWidget(header1)
        left_default_content.setAlignment(Qt.AlignmentFlag.AlignTop)

        # period selection
        self.radio_all = QRadioButton("Multi years")
        self.radio_single = QRadioButton("Single year")
        self.radio_all.setChecked(True)
        grid = QGridLayout()
        grid.addWidget(self.radio_all, 0, 0)
        grid.addWidget(self.radio_single, 0, 1)

        # multi year container
        self.multi_container = QWidget()
        multi_layout = QHBoxLayout(self.multi_container)
        multi_layout.addWidget(QLabel("Start:"))
        self.start_year_input = QLineEdit()
        multi_layout.addWidget(self.start_year_input)
        self.start_year_input.setPlaceholderText("e.g. 2020")
        multi_layout.addWidget(QLabel("End:"))
        self.end_year_input = QLineEdit()
        multi_layout.addWidget(self.end_year_input)
        self.end_year_input.setPlaceholderText("e.g. 2025")
        
        # single year container
        self.single_container = QWidget()
        single_layout = QHBoxLayout(self.single_container)
        self.single_year_input = QLineEdit()
        single_layout.addWidget(self.single_year_input)
        self.single_year_input.setPlaceholderText("e.g. 2025")

        grid.addWidget(self.multi_container, 1, 0)
        grid.addWidget(self.single_container, 1, 1)
        left_default_content.addLayout(grid)

        self.radio_all.toggled.connect(self._on_period_toggle)
        self.radio_single.toggled.connect(self._on_period_toggle)
        self._on_period_toggle()


        # selected location confirmations
        left_default_content.addWidget(QLabel(self._pretty_selection_html(), alignment=Qt.AlignmentFlag.AlignLeft))

        # load default buttons + status
        btn_defaults = QPushButton("Load default data")
        btn_defaults.clicked.connect(self._load_defaults)
        left_default_content.addWidget(btn_defaults)
        self.defaults_status = QLabel("")
        left_default_content.addWidget(self.defaults_status)

        # custom tab
        self.abm_table = YearDemandTable()


        # connect tabs
        tabs = QTabWidget()
        tabs.addTab(default_tab, "Default Data")
        tabs.addTab(self.abm_table, "Custom Data")

        title = QLabel("<h2>Data<\h2>", alignment=Qt.AlignmentFlag.AlignCenter)

        left_content = QWidget() 
        c_vbox = QVBoxLayout(left_content)
        c_vbox.addWidget(title)
        c_vbox.addWidget(tabs, 1) # add tabs

        merge_content = QHBoxLayout()
        merge_content.addWidget(left_content, 1) # add left content
        self._update_map()
        merge_content.addWidget(self.map_view, 3) # add right content (map)


        # nav buttons
        self.home_btn = QPushButton("Home") 
        self.location_btn = QPushButton("Prev")
        btn_next = QPushButton("Next")
        self.map_btn = QPushButton("")
        btn_next.clicked.connect(self._finish)
        nav_row = QHBoxLayout()
        nav_row.addWidget(self.home_btn)
        nav_row.addStretch()
        nav_row.addWidget(self.location_btn)
        nav_row.addWidget(btn_next)

        footer = QLabel("Copyright 2026, Battelle Energy Alliance, LLC. All Rights Reserved")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #555; font-size: 10px; padding: 3px 0;"
            "border-top: 1px solid #ccc; margin-top: 2px;"
        )

        # connecting everything together
        main_layout = QVBoxLayout()
        main_layout.addLayout(merge_content, 1)  # stretch=1 so map+content fills all available height
        main_layout.addLayout(nav_row)
        main_layout.addWidget(footer)
        self.setLayout(main_layout)

    # switches the visible input widgets between multi and single years
    # (Used in: Connected to the toggled signal of the radio_all and radio_single radio buttons.)
    def _on_period_toggle(self):
        if self.radio_single.isChecked():
            self.single_container.setEnabled(True)
            self.multi_container.setEnabled(False)
        else:
            self.single_container.setEnabled(False)
            self.multi_container.setEnabled(True)

    # removes duplicate region/state/county/city names for the user selection 
    # (called in the init method for use in pretty_selection)
    def _deduplicate(self) -> Dict[str, List[str | None]]:
        regions = set(self.selections["regions"])
        states = set(self.selections["states"])
        for r in regions:
            states -= {s for s in states if s.lower() in {t.lower() for t in self.region_map[r]}}
        return {
            "regions": list(regions),
            "states": list(states),
            "county": [self.selections["county"]] if self.selections["county"] else [],
            "city": [self.selections["city"]] if self.selections["city"] else [],
        }
    
    # returns an HTML snippet listing what regions the user has picked (used for error message when loading data)
    # (Used in: Called within the _build_ui method to display the selected locations.)
    def _pretty_selection_html(self) -> str:
        return "<br>".join(
            f"<b>{lvl.capitalize()}:</b>{','.join(items)}"
            for lvl, items in self.effective.items() if items
        ) or "<i> No locations selected </i>"
    
    # loads default (ABM) data for the selected areas and year range, cleans and aggregates it
    # (Used in: Connected to the clicked signal of the btn_defaults button)
    def _load_defaults(self):
        try:
            if self.radio_single.isChecked():
                year_txt = self.single_year_input.text().strip()
                if not year_txt:
                    QMessageBox.information(self, "Location needed", "Please enter a year.")
                    return
                try:
                    start = end = int(year_txt)
                except ValueError:
                    QMessageBox.critical(self, "Invalid year", f"'{year_txt}' isn't a number.")
                    return
            else:
                start_txt = self.start_year_input.text().strip()
                end_txt = self.end_year_input.text().strip()
                if not start_txt or not end_txt:
                    QMessageBox.information(self, "Location needed", "Please enter both start and end years.")
                    return
                try:
                    start, end = int(start_txt), int(end_txt)
                except ValueError:
                    QMessageBox.critical(self, "Invalid range", "Start and end must be integers.")
                    return
                if start > end:
                    QMessageBox.warning(self, "Invalid range", "Start year must be less than end year.")
                    return
                
            frames = []
            for r in self.effective["regions"]:
                frames.append(pd.read_excel(self.paths["regions"], sheet_name=r))
            for s in self.effective["states"]:
                frames.append(pd.read_excel(self.paths["states"], sheet_name=s))
            if self.effective["county"]:
                frames.append(pd.read_excel(self.paths["counties"], sheet_name=self.effective["county"][0]))
            if self.effective["city"]:
                frames.append(pd.read_excel(self.paths["cities"], sheet_name=self.effective["city"][0]))
            if not frames:
                QMessageBox.information(self, "Nothing to load", "No applicable default data")
                return
            
            df = pd.concat(frames, ignore_index=True)
            df = df[df["Year"].between(start, end)]
            df = df[[
                "Year",
                "Reused in other applications",
                "Reused in other EV",
                "Recycle Rate"
            ]].rename(columns={
                "Reused in other applications": "_a",
                "Reused in other EV": "_b",
                "Recycle Rate": "recycled"
            })

            df["repurposed"] = df["_a"].fillna(0) + df["_b"].fillna(0)
            df = df.drop(columns=["_a", "_b"])
            df["total"] = df["recycled"] + df["repurposed"]
            df = (df.groupby("Year", as_index=False).agg({
                "recycled": "sum",
                "repurposed": "sum",
                "total": "sum",
            }).sort_values("Year").reset_index(drop=True))

            self.default_df = df
            self.defaults_status.setText(
                f"<span style='color:green'> Loaded {len(df)} rows of default data </span>"
            )

        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))

    # colors the selected states on a Folium map and saves the map to disk
    # (Used in: Called within the _build_ui method to update the map view.)
    def _update_map(self):
        geo_path = Path(BASE_DIR) / "us-states.json"
        states_geo = json.loads(geo_path.read_text())
        selected_states = set(self.selections.get("states", []))
        for region in self.selections.get("regions", []):
            selected_states.update(self.region_map.get(region, []))

        # Build shapely geometries for selected states and compute map centre
        selected_shapes = []
        all_lats, all_lons = [], []
        for feature in states_geo["features"]:
            if feature["properties"]["name"] in selected_states:
                geom = shape(feature["geometry"])
                selected_shapes.append(geom)
                b = geom.bounds  # (minx, miny, maxx, maxy)
                all_lats += [b[1], b[3]]
                all_lons += [b[0], b[2]]

        if all_lats:
            center_lat = float(np.mean(all_lats))
            center_lon = float(np.mean(all_lons))
            zoom = 5 if len(selected_states) <= 3 else 4
        else:
            center_lat, center_lon, zoom = 37.0902, -95.7129, 4

        folium_map = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

        def style_fn(feature):
            name = feature["properties"]["name"]
            if name in selected_states:
                return {"fillColor": "blue", "color": "yellow", "weight": 2, "fillOpacity": 0.5}
            else:
                return {"fillColor": "white", "color": "gray", "weight": 1, "fillOpacity": 0.1}

        folium.GeoJson(
            states_geo,
            name="US States",
            style_function=style_fn
        ).add_to(folium_map)
        self.add_external_markers(folium_map, selected_states, selected_shapes)

        legend_html = '''
            <div style="
            position: fixed; 
            bottom: 20px; left: 20px; width: 200px; 
            border:2px solid grey; z-index:9999; font-size:14px;
            background-color:white;
            ">
            &nbsp; <b>Legend</b> <br>
            &nbsp; <i style="background:blue; width: 10px; height: 10px; display: inline-block;"></i>&nbsp; Selected Area <br>
            &nbsp; <i class="fa fa-car" style="color:lightblue; width: 10px; height: 10px;"></i>&nbsp; Car Dealerships <br>
            &nbsp; <i class="fa fa-recycle" style="color:red; width: 10px; height: 10px;"></i>&nbsp; Recycling Center <br>
            &nbsp; <i class="fa fa-tools" style="color:lightgreen; width: 10px; height: 10px;"></i>&nbsp; Repurposing Center <br> 
            </div>
        #          '''
        folium_map.get_root().html.add_child(Element(legend_html)) 

        out = Path(BASE_DIR) / "map.html"
        folium_map.save(str(out))
        self.map_view.setUrl(QUrl.fromLocalFile(str(out.resolve())))
        self.map_view.reload()

    # adds the markers from pyomo and collection-center Excel files to the folium map,
    # filtered to only the selected states/region
    # (Used in: Called within the _update_map method.)
    def add_external_markers(self, folium_map, selected_states=None, selected_shapes=None):
        # Build a combined polygon for point-in-polygon checks
        combined_shape = unary_union(selected_shapes) if selected_shapes else None

        # extracting centers from pyomo — filter to selected states
        path_fac = Path(BASE_DIR) / "Pyomo_Ex_DB.xlsx"
        if path_fac.exists():
            fac_df = pd.read_excel(path_fac, sheet_name="Final_Sheet")
            fac_df = fac_df[fac_df["Facility Type"].isin(["R", "P"])]
            # Strip whitespace from state column (e.g. 'OH ' → 'OH')
            fac_df["Facility State or Province"] = (
                fac_df["Facility State or Province"].astype(str).str.strip()
            )

            # Apply same caps used in the optimisation
            fac_df = pd.concat([
                fac_df[fac_df["Facility Type"] == "P"].head(10),
                fac_df[fac_df["Facility Type"] == "R"].head(25),
            ])

            for _, row in fac_df.iterrows():
                lat, lon = row["Latitude"], row["Longitude"]
                if pd.isna(lat) or pd.isna(lon):
                    continue

                ftype = row["Facility Type"]
                icon_color = "lightred" if ftype == "R" else "lightgreen"
                icon_name = "recycle" if ftype == "R" else "tools"

                popup_html = "<b>{}</b><br>".format(html.escape(str(row["Facility Name"])))
                for col in ["Facility Type", "Facility City", "Facility State or Province",
                            "Facility Country", "Capacity", "Capacity Units"]:
                    if col in row and pd.notna(row[col]):
                        popup_html += f"{html.escape(col)}: {html.escape(str(row[col]))}<br>"

                Marker(
                    location=[lat, lon],
                    popup=Popup(popup_html, max_width=300),
                    icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
                ).add_to(folium_map)

        # extracting collection centers — filter by point-in-polygon (no state column in file)
        path_car = Path(BASE_DIR) / "Car_USA.xlsx"
        if path_car.exists():
            tsla_df = pd.read_excel(path_car, sheet_name="Sheet1")
            for idx, row in tsla_df.iterrows():
                lat, lon = row["Latitude"], row["Longitude"]
                if pd.isna(lat) or pd.isna(lon):
                    continue
                if combined_shape is not None and not combined_shape.contains(Point(lon, lat)):
                    continue
                Marker(
                    location=[lat, lon],
                    popup=f"Dealer_{idx+1}",
                    icon=folium.Icon(color="lightblue", icon="car", prefix="fa"),
                ).add_to(folium_map)

    # helper for finish() to merge default data and custom data into a standardised DataFrame
    # (Used in: Called within the _finish method to prepare the data before proceeding)
    def _make_yearly_df(self) -> pd.DataFrame | None:
        frames = []

        # default tab
        if self.default_df is not None and not self.default_df.empty: 
            df_def = (self.default_df.rename(columns={"Year": "year"})[["year", "recycled", "repurposed"]])
            frames.append(df_def)
        
        # custom tab
        rows = self.abm_table._rows_as_dicts()
        if rows:
            frames.append(pd.DataFrame(rows))

        if not frames:
            return None
        df = (pd.concat(frames, ignore_index=True).fillna(0.0))

        # safety net
        for col in ("recycled", "repurposed"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        df["total"] = df["recycled"] + df["repurposed"] # adds the total to the df
        return (df.sort_values("year").reset_index(drop=True)[["year", "recycled", "repurposed", "total"]])
        
    # collects the user inputs, bundles into a payload and fires the done-callback
    # (Used in: Connected to the clicked signal of the btn_next button)
    def _finish(self):
        yearly_df = self._make_yearly_df()
        if yearly_df is None:
            QMessageBox.warning(self, "No data", "Please input data before proceeding")
            return
        print("\n[DataPage] yearly_df.head():\n", yearly_df.head(),"\n")
        payload = {
            "yearly_data": yearly_df.to_dict(orient="records")
        }
        self._done(payload)

        # how to use the df on the next page
        # df = pd.DataFrame(records) --> this returns the 4 cols

