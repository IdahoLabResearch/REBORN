# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
import os
import random
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QRadioButton, QButtonGroup, QGroupBox, QSpinBox, QDoubleSpinBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

BASE_DIR = os.path.dirname(__file__)


def _generate_random_points(polygon, num_points, seed=42):
    rng = random.Random(seed)
    min_x, min_y, max_x, max_y = polygon.bounds
    points = []
    while len(points) < num_points:
        p = Point(rng.uniform(min_x, max_x), rng.uniform(min_y, max_y))
        if polygon.contains(p):
            points.append(p)
    return points


class FacilityGenerationPage(QWidget):
    def __init__(self, done_callback, parent=None):
        super().__init__(parent)
        self._done = done_callback
        self._selections = {}
        self._use_new_db = False
        self._build_ui()

    def set_context(self, selections: dict):
        self._selections = selections
        self._refresh_map_view()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        title = QLabel("<h2>Facility Database</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(title)

        # Mode selection
        mode_box = QGroupBox("Database Selection")
        mode_layout = QHBoxLayout(mode_box)
        self.rb_default = QRadioButton("Use Default Database")
        self.rb_generate = QRadioButton("Generate New Facility Locations")
        self.rb_default.setChecked(True)
        mode_grp = QButtonGroup(self)
        mode_grp.addButton(self.rb_default)
        mode_grp.addButton(self.rb_generate)
        mode_layout.addWidget(self.rb_default)
        mode_layout.addWidget(self.rb_generate)
        outer.addWidget(mode_box)
        self.rb_default.toggled.connect(self._on_mode_changed)
        self.rb_generate.toggled.connect(self._on_mode_changed)

        # Generation controls (hidden by default)
        self.gen_widget = QWidget()
        gen_layout = QVBoxLayout(self.gen_widget)
        gen_layout.setContentsMargins(0, 0, 0, 0)
        gen_layout.setSpacing(8)

        # Total facilities
        num_row = QHBoxLayout()
        num_row.addWidget(QLabel("Total facilities to generate:"))
        self.num_centers_spin = QSpinBox()
        self.num_centers_spin.setRange(1, 10000)
        self.num_centers_spin.setValue(50)
        self.num_centers_spin.setFixedWidth(90)
        num_row.addWidget(self.num_centers_spin)
        num_row.addStretch()
        gen_layout.addLayout(num_row)

        # Ratios
        ratio_box = QGroupBox("Center Type Ratios")
        ratio_layout = QVBoxLayout(ratio_box)

        rec_row = QHBoxLayout()
        rec_row.addWidget(QLabel("Recycling ratio (0–1):"))
        self.recycling_ratio_spin = QDoubleSpinBox()
        self.recycling_ratio_spin.setRange(0.0, 1.0)
        self.recycling_ratio_spin.setSingleStep(0.05)
        self.recycling_ratio_spin.setValue(0.35)
        self.recycling_ratio_spin.setFixedWidth(80)
        rec_row.addWidget(self.recycling_ratio_spin)
        rec_row.addStretch()
        ratio_layout.addLayout(rec_row)

        rep_row = QHBoxLayout()
        rep_row.addWidget(QLabel("Repurposing ratio (0–1):"))
        self.repurposing_ratio_spin = QDoubleSpinBox()
        self.repurposing_ratio_spin.setRange(0.0, 1.0)
        self.repurposing_ratio_spin.setSingleStep(0.05)
        self.repurposing_ratio_spin.setValue(0.35)
        self.repurposing_ratio_spin.setFixedWidth(80)
        rep_row.addWidget(self.repurposing_ratio_spin)
        rep_row.addStretch()
        ratio_layout.addLayout(rep_row)

        self.dealership_label = QLabel("Dealership ratio: 0.30 (auto)")
        ratio_layout.addWidget(self.dealership_label)

        self.recycling_ratio_spin.valueChanged.connect(self._update_dealership_label)
        self.repurposing_ratio_spin.valueChanged.connect(self._update_dealership_label)
        gen_layout.addWidget(ratio_box)

        # Capacities
        cap_box = QGroupBox("Capacity (batteries/year)")
        cap_layout = QVBoxLayout(cap_box)

        for label_text, attr in [
            ("Recycling capacity:", "recycling_cap_spin"),
            ("Repurposing capacity:", "repurposing_cap_spin"),
            ("Dealership capacity:", "dealership_cap_spin"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            spin = QSpinBox()
            spin.setRange(0, 10_000_000)
            spin.setValue(50000)
            spin.setFixedWidth(110)
            setattr(self, attr, spin)
            row.addWidget(spin)
            row.addStretch()
            cap_layout.addLayout(row)

        self.dealership_cap_spin.setValue(100000)
        gen_layout.addWidget(cap_box)

        # Save options
        save_box = QGroupBox("Save Options")
        save_layout = QVBoxLayout(save_box)

        for label_text, rb_replace_attr, rb_append_attr in [
            ("RR Database:", "rb_rr_replace", "rb_rr_append"),
            ("Car/Dealership Database:", "rb_car_replace", "rb_car_append"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            rb_r = QRadioButton("Replace")
            rb_a = QRadioButton("Append")
            rb_r.setChecked(True)
            grp = QButtonGroup(self)
            grp.addButton(rb_r)
            grp.addButton(rb_a)
            setattr(self, rb_replace_attr, rb_r)
            setattr(self, rb_append_attr, rb_a)
            row.addWidget(rb_r)
            row.addWidget(rb_a)
            row.addStretch()
            save_layout.addLayout(row)

        gen_layout.addWidget(save_box)

        # Generate button + status
        gen_btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("Generate Facilities")
        self.generate_btn.setMinimumHeight(34)
        self.generate_btn.clicked.connect(self._run_generation)
        gen_btn_row.addWidget(self.generate_btn)
        gen_btn_row.addStretch()
        gen_layout.addLayout(gen_btn_row)

        self.status_label = QLabel("")
        gen_layout.addWidget(self.status_label)

        outer.addWidget(self.gen_widget)

        # Map preview
        self.map_view = QWebEngineView(self)
        self.map_view.setMinimumHeight(300)
        s = self.map_view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        outer.addWidget(self.map_view, 1)

        # Nav buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(12)
        self.home_btn = QPushButton("Home")
        self.home_btn.setMinimumHeight(34)
        self.back_btn = QPushButton("Back to Data")
        self.back_btn.setMinimumHeight(34)
        self.next_btn = QPushButton("Next")
        self.next_btn.setMinimumHeight(34)
        self.next_btn.clicked.connect(self._finish)
        nav_row.addWidget(self.home_btn)
        nav_row.addWidget(self.back_btn)
        nav_row.addStretch()
        nav_row.addWidget(self.next_btn)
        outer.addLayout(nav_row)

        footer = QLabel("Copyright 2026, Battelle Energy Alliance, LLC. All Rights Reserved")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #555; font-size: 10px; padding: 3px 0;"
            "border-top: 1px solid #ccc; margin-top: 2px;"
        )
        outer.addWidget(footer)

        self._on_mode_changed()

    # --------------------------------------------------------- slots ---------
    def _on_mode_changed(self):
        self.gen_widget.setVisible(self.rb_generate.isChecked())
        self._refresh_map_view()

    def _refresh_map_view(self):
        """Show facility map if generated, otherwise fall back to the data-page map."""
        facility_map = os.path.join(BASE_DIR, "new_facility_map.html")
        data_map = os.path.join(BASE_DIR, "map.html")
        if self.rb_generate.isChecked() and self._use_new_db and os.path.exists(facility_map):
            self.map_view.setUrl(QUrl.fromLocalFile(facility_map))
        elif os.path.exists(data_map):
            self.map_view.setUrl(QUrl.fromLocalFile(data_map))

    def _update_dealership_label(self):
        d = 1.0 - self.recycling_ratio_spin.value() - self.repurposing_ratio_spin.value()
        self.dealership_label.setText(f"Dealership ratio: {d:.2f} (auto)")

    def _run_generation(self):
        rr = self.recycling_ratio_spin.value()
        rp = self.repurposing_ratio_spin.value()
        d = 1.0 - rr - rp
        if d < -1e-9:
            QMessageBox.warning(self, "Invalid Ratios",
                "Recycling + Repurposing ratios cannot exceed 1.0.")
            return

        selections = self._selections
        regions = selections.get("regions", [])
        states = selections.get("states", [])
        region_map = selections.get("region_map", {})

        self.status_label.setText("Loading geographic data…")
        self.generate_btn.setEnabled(False)

        try:
            shp_path = os.path.join(BASE_DIR, "cb_2021_us_state_500k.shp")
            states_gdf = self._load_states_gdf(shp_path)
            if states_gdf is None:
                return

            # Detect the state-name column (varies across shapefile versions)
            name_col = None
            for candidate in ['NAME', 'Name', 'name', 'STATE_NAME', 'NAMELSAD', 'STUSPS']:
                if candidate in states_gdf.columns:
                    name_col = candidate
                    break
            if name_col is None:
                QMessageBox.critical(self, "Shapefile Error",
                    f"Could not find a state-name column.\n"
                    f"Available columns: {list(states_gdf.columns)}")
                return

            # Collect state names from selections
            state_names = []
            for region in regions:
                state_names.extend(region_map.get(region, []))
            state_names.extend(states)
            state_names = list(dict.fromkeys(state_names))  # deduplicate

            if not state_names:
                QMessageBox.warning(self, "No Selection",
                    "No geographic area found. Please go back and select "
                    "a region or state on the Location page.")
                return

            selected_gdf = states_gdf[states_gdf[name_col].isin(state_names)]
            if selected_gdf.empty:
                QMessageBox.warning(self, "No Data",
                    f"Could not find states {state_names} in the shapefile.\n"
                    f"Name column used: '{name_col}'")
                return

            combined_boundary = selected_gdf.unary_union
            total = self.num_centers_spin.value()
            self.status_label.setText(f"Generating {total} random locations…")

            random_points = _generate_random_points(combined_boundary, total)
            points_gdf = gpd.GeoDataFrame(geometry=random_points, crs=states_gdf.crs)
            points_gdf = gpd.sjoin(points_gdf, states_gdf[['geometry', name_col]], how='left')
            points_gdf.rename(columns={name_col: 'state'}, inplace=True)
            if 'index_right' in points_gdf.columns:
                points_gdf.drop(columns=['index_right'], inplace=True)
            points_gdf.reset_index(drop=True, inplace=True)
            points_gdf['latitude'] = points_gdf.geometry.y
            points_gdf['longitude'] = points_gdf.geometry.x
            points_gdf['city'] = points_gdf['state']
            points_gdf.reset_index(inplace=True)

            # Assign center types
            num_recycling = int(total * rr)
            num_repurposing = int(total * rp)
            num_dealership = total - num_recycling - num_repurposing
            center_types = ['R'] * num_repurposing + ['P'] * num_recycling + ['C'] * num_dealership
            random.shuffle(center_types)
            points_gdf['center_type'] = center_types

            rec_cap = self.recycling_cap_spin.value()
            rep_cap = self.repurposing_cap_spin.value()
            deal_cap = self.dealership_cap_spin.value()
            points_gdf['capacity'] = points_gdf['center_type'].apply(
                lambda x: rep_cap if x == 'R' else (rec_cap if x == 'P' else deal_cap)
            )

            # Capture existing data BEFORE saving (needed for append visualisation)
            rr_path = os.path.join(BASE_DIR, "New_RR_DB.xlsx")
            car_path = os.path.join(BASE_DIR, "New_Car_DB.xlsx")
            existing_rr_df = None
            existing_car_df = None
            if self.rb_rr_append.isChecked() and os.path.exists(rr_path):
                try:
                    existing_rr_df = pd.read_excel(rr_path)
                except Exception as load_err:
                    print(f"[Facility] Could not load existing RR DB: {load_err}")
            if self.rb_car_append.isChecked() and os.path.exists(car_path):
                try:
                    existing_car_df = pd.read_excel(car_path)
                except Exception as load_err:
                    print(f"[Facility] Could not load existing Car DB: {load_err}")

            self._save_databases(points_gdf)

            # Build folium map
            self.status_label.setText("Building map…")
            map_center = [combined_boundary.centroid.y, combined_boundary.centroid.x]
            m = folium.Map(location=map_center, zoom_start=6)
            folium.GeoJson(
                selected_gdf.__geo_interface__,
                style_function=lambda _f: {
                    'fillColor': 'blue', 'color': 'yellow',
                    'weight': 2, 'fillOpacity': 0.1,
                }
            ).add_to(m)

            # Colours: new = bright, existing = muted
            new_colors  = {'R': 'green',     'P': 'red',      'C': 'purple'}
            old_colors  = {'R': 'lightgreen', 'P': 'lightred', 'C': 'lightgray'}

            show_existing = (existing_rr_df is not None) or (existing_car_df is not None)

            # --- Existing RR locations (repurposing / recycling) ---
            if existing_rr_df is not None and 'latitude' in existing_rr_df.columns:
                for _, row in existing_rr_df.iterrows():
                    ct = str(row.get('center_type', 'R'))
                    folium.Marker(
                        location=[row['latitude'], row['longitude']],
                        popup=f"[Existing] Type: {ct}, Capacity: {row.get('capacity', 'N/A')}",
                        icon=folium.Icon(color=old_colors.get(ct, 'lightgray'), icon='minus'),
                    ).add_to(m)

            # --- Existing Car/Dealership locations ---
            if existing_car_df is not None and 'latitude' in existing_car_df.columns:
                for _, row in existing_car_df.iterrows():
                    folium.Marker(
                        location=[row['latitude'], row['longitude']],
                        popup=f"[Existing] Dealership, Capacity: {row.get('capacity', 'N/A')}",
                        icon=folium.Icon(color='gray', icon='minus'),
                    ).add_to(m)

            # --- New locations ---
            for _, row in points_gdf.iterrows():
                ct = row.get('center_type', 'C')
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=f"[New] Type: {ct}, Capacity: {row['capacity']}",
                    icon=folium.Icon(color=new_colors.get(ct, 'blue'), icon='arrow-up'),
                ).add_to(m)

            # Build legend — add existing rows only when appending
            existing_legend = ""
            if show_existing:
                existing_legend = """
                <hr style="margin:4px 0;">
                <b>Existing Facilities</b><br>
                <span style="color:gray;font-size:16px;">&#9679;</span>&nbsp;Existing Dealerships<br>
                <span style="color:#e06060;font-size:16px;">&#9679;</span>&nbsp;Existing Recycling Centers<br>
                <span style="color:#60c060;font-size:16px;">&#9679;</span>&nbsp;Existing Repurposing Centers<br>"""

            legend_html = f"""
            <div style="position:fixed;bottom:50px;left:50px;width:310px;
                        border:2px solid grey;z-index:9999;font-size:13px;
                        background-color:white;padding:10px;">
            <span style="background:blue;display:inline-block;width:12px;height:12px;"></span>
            &nbsp;Selected Region<br>
            <hr style="margin:4px 0;">
            <b>New Facilities</b><br>
            <span style="color:purple;font-size:16px;">&#9679;</span>&nbsp;New Dealerships<br>
            <span style="color:red;font-size:16px;">&#9679;</span>&nbsp;New Recycling Centers<br>
            <span style="color:green;font-size:16px;">&#9679;</span>&nbsp;New Repurposing Centers
            {existing_legend}
            </div>"""
            m.get_root().html.add_child(folium.Element(legend_html))

            map_path = os.path.join(BASE_DIR, "new_facility_map.html")
            m.save(map_path)
            self.map_view.setUrl(QUrl.fromLocalFile(map_path))

            self._use_new_db = True
            self._refresh_map_view()
            self.status_label.setText(
                f"Done. {total} facilities generated and databases saved."
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Generation failed:\n{e}")
            self.status_label.setText("Error during generation.")
        finally:
            self.generate_btn.setEnabled(True)

    def _load_states_gdf(self, shp_path: str):
        """Load US state boundaries. Tries local files first, then Census Bureau URL."""
        CENSUS_URL = (
            "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_us_state_500k.zip"
        )
        zip_path = shp_path.replace(".shp", ".zip")
        cached_zip = os.path.join(BASE_DIR, "cb_2021_us_state_500k_cached.zip")

        # 1. Try local .zip (full shapefile bundle, most reliable)
        for zp in (zip_path, cached_zip):
            if os.path.exists(zp):
                try:
                    gdf = gpd.read_file(zp)
                    if len(gdf.columns) > 1:   # has attributes
                        return gdf
                except Exception:
                    pass

        # 2. Try local .shp (only useful if .dbf is also present)
        if os.path.exists(shp_path):
            try:
                os.environ['SHAPE_RESTORE_SHX'] = 'YES'
                gdf = gpd.read_file(shp_path)
                if len(gdf.columns) > 1:
                    return gdf
            except Exception:
                pass

        # 3. Download from Census Bureau and cache locally
        self.status_label.setText("Downloading state boundaries from Census Bureau…")
        try:
            gdf = gpd.read_file(CENSUS_URL)
            try:
                gdf.to_file(cached_zip)
            except Exception:
                pass  # caching is best-effort; don't fail if write fails
            return gdf
        except Exception as e:
            QMessageBox.critical(
                self, "Data Load Failed",
                f"Could not load state boundary data.\n\n"
                f"Please place cb_2018_us_state_500k.zip in:\n{BASE_DIR}\n\n"
                f"Download from:\n{CENSUS_URL}\n\nError: {e}"
            )
            return None

    def _save_databases(self, points_gdf):
        # Drop geometry column — Shapely objects cannot be serialised to Excel
        rr_gdf = (pd.DataFrame(points_gdf[points_gdf['center_type'] != 'C'])
                  .drop(columns=['geometry'], errors='ignore'))
        car_gdf = (pd.DataFrame(points_gdf[points_gdf['center_type'] == 'C'])
                   .drop(columns=['geometry'], errors='ignore'))

        rr_path = os.path.join(BASE_DIR, "New_RR_DB.xlsx")
        car_path = os.path.join(BASE_DIR, "New_Car_DB.xlsx")

        # RR database
        if self.rb_rr_replace.isChecked() or not os.path.exists(rr_path):
            with pd.ExcelWriter(rr_path, engine='openpyxl') as writer:
                rr_gdf.to_excel(writer, index=False)
        else:
            existing = pd.read_excel(rr_path)
            combined = pd.concat([existing, rr_gdf], ignore_index=True)
            with pd.ExcelWriter(rr_path, engine='openpyxl') as writer:
                combined.to_excel(writer, index=False)

        # Car/Dealership database
        if self.rb_car_replace.isChecked() or not os.path.exists(car_path):
            with pd.ExcelWriter(car_path, engine='openpyxl') as writer:
                car_gdf.to_excel(writer, index=False)
        else:
            existing = pd.read_excel(car_path)
            combined = pd.concat([existing, car_gdf], ignore_index=True)
            with pd.ExcelWriter(car_path, engine='openpyxl') as writer:
                combined.to_excel(writer, index=False)

    def _finish(self):
        use_new = self.rb_generate.isChecked() and self._use_new_db
        self._done({"use_new_db": use_new})
