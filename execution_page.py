import sys
import os
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QMessageBox,
    QComboBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtCore import QUrl, QSignalBlocker
import pandas as pd
import matplotlib.pyplot as plt
from PyQt6.QtGui import QPixmap
from pathlib import Path

class TrendEvolutionWindow(QWidget):
    def __init__(self, df):
        super().__init__()
        self.setWindowTitle("Trend Evolution — Results Summary")
        self.resize(1300, 420)
        self._build_ui(df)

    def _build_ui(self, df):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Trend Evolution — Results by Year")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold; padding: 4px 0;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setRowCount(df.shape[0])
        table.setColumnCount(df.shape[1])

        # Wrap header text so long column names split across two lines
        wrapped = [c.replace(" (", "\n(").replace(" -", "\n-") for c in df.columns]
        table.setHorizontalHeaderLabels(wrapped)
        table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setMinimumSectionSize(80)
        table.verticalHeader().setVisible(False)
        table.setWordWrap(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2c5f8a;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 2px;
                border: 1px solid #1a3d5c;
            }
            QTableWidget::item:alternate {
                background-color: #f0f6fc;
            }
        """)

        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                raw = df.iat[i, j]
                # Format floats to 4 decimal places, leave ints as-is
                try:
                    val = float(raw)
                    text = f"{val:.4f}" if val != int(val) else str(int(val))
                except (ValueError, TypeError):
                    text = str(raw)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(i, j, item)

        table.resizeRowsToContents()
        layout.addWidget(table)
        self.setLayout(layout)

class Cost_Breakdown_Window(QWidget):
    def __init__(self, df):
        super().__init__()
        self.setWindowTitle("Cost Breakdown by Year")
        self.resize(950, 620)
        self._build_ui(df)

    def _build_ui(self, df):
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Cost Breakdown by Year")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold; padding: 4px 0;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        years = df['Year'].unique()

        # Short display labels for the pie slices (keep them brief)
        label_map = {
            "Fixed Cost for Repurposing Centers($/Battery)": "Fixed\nRepurposing",
            "Fixed Cost for Recycling Centers($/Battery)":   "Fixed\nRecycling",
            "Operating Cost for Repurposing Centers($/Battery)": "Operating\nRepurposing",
            "Operating Cost for Recycling Centers($/Battery)":   "Operating\nRecycling",
            "Collection Cost($/Battery)":   "Collection",
            "Packaging Cost ($/Battery)":   "Packaging",
            "Transportation Cost - Dealership to Repurpose($/Battery)": "Transport\nDealer→Repurpose",
            "Transportation Cost - Repurpose to Recycle($/Battery)":    "Transport\nRepurpose→Recycle",
        }

        colors = cm.tab10.colors

        for year in years:
            year_data = df[df['Year'] == year].iloc[:, 1:]
            year_values = year_data.sum(axis=0)
            full_labels = list(year_values.index)
            short_labels = [label_map.get(l, l) for l in full_labels]
            values = year_values.values

            fig, ax = plt.subplots(figsize=(9, 5.5))
            fig.patch.set_facecolor('#f8f8f8')
            ax.set_facecolor('#f8f8f8')

            wedges, _, autotexts = ax.pie(
                values,
                labels=None,          # no inline labels — legend handles them
                autopct='%1.1f%%',
                pctdistance=0.75,
                startangle=90,
                colors=colors[:len(values)],
                wedgeprops=dict(linewidth=0.8, edgecolor='white'),
            )
            for at in autotexts:
                at.set_fontsize(9)
                at.set_color('white')
                at.set_fontweight('bold')

            ax.legend(
                wedges, full_labels,
                title="Cost Component",
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                fontsize=8,
                title_fontsize=9,
                frameon=True,
                framealpha=0.9,
            )
            ax.set_title(f"Cost Distribution — Year {year}", fontsize=13, fontweight='bold', pad=12)
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setPixmap(pixmap)

            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.addWidget(img_label)
            self.tabs.addTab(tab, str(year))

        layout.addWidget(self.tabs)
        self.setLayout(layout)

class ResultsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.trend_window = None  # Keep a reference to the window
        self._file_prefix = "REBORN_Initial_Results"
        self.map_dir = (Path(__file__).resolve().parent / self._file_prefix).resolve()
        self._current_map_type = None  # 'with' or 'without'
        self._use_new_db = False

        self._build_ui()

    def set_use_new_db(self, use_new: bool):
        self._use_new_db = use_new
        facility_map = Path(__file__).resolve().parent / "new_facility_map.html"
        data_map = (Path(__file__).resolve().parent / "map.html")
        if use_new and facility_map.exists():
            self.web_view.setUrl(QUrl.fromLocalFile(str(facility_map)))
        elif data_map.exists():
            self.web_view.setUrl(QUrl.fromLocalFile(str(data_map)))
        # Update visibility of facility map button
        self.facility_map_btn.setVisible(use_new and facility_map.exists())

    def set_results_dir(self, folder_name: str):
        """Called by MainWindow after optimization to point at the correct results folder."""
        self._file_prefix = folder_name
        self.map_dir = (Path(__file__).resolve().parent / folder_name).resolve()
        print(f"[ResultsPage] Results dir set to: {self.map_dir}")
        # Pre-populate year combo from the new results folder
        self._populate_year_combo()

    def _build_ui(self):
        # Main content
        content = QVBoxLayout()

        # Title
        # title = QLabel("<h2>Final Results</h2>", alignment=Qt.AlignmentFlag.AlignCenter)
        # title = QLabel("<h1>Results</h1>", alignment=Qt.AlignmentFlag.AlignLeft)
        # content.addWidget(title)

        # Year selector
        year_row = QHBoxLayout()
        year_row.addWidget(QLabel("Select Year:"))
        self.year_combo = QComboBox(self)
        self.year_combo.setFixedHeight(28)
        self.year_combo.setMinimumWidth(100)
        self.year_combo.setMaximumWidth(140)
        self.year_combo.currentTextChanged.connect(self._on_year_combo_changed)
        year_row.addWidget(self.year_combo)
        year_row.addStretch()
        content.addLayout(year_row)

        # Web engine to display HTML files
        self.web_view = QWebEngineView(self)
        self.web_view.setMinimumSize(800, 600)
        s = self.web_view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.web_view.loadFinished.connect(lambda ok: print("load Finished:", ok))
        content.addWidget(self.web_view)  # Add the web view to the layout

        # Button to download the image
        download_button_layout = QHBoxLayout()
        download_button_layout.setSpacing(16)

        self.download_with_locations_button = QPushButton("Show with Locations")
        self.download_with_locations_button.setMinimumHeight(36)
        self.download_with_locations_button.clicked.connect(self.show_with_locations)
        download_button_layout.addWidget(self.download_with_locations_button)

        self.download_without_locations_button = QPushButton("Show without Locations")
        self.download_without_locations_button.setMinimumHeight(36)
        self.download_without_locations_button.clicked.connect(self.show_without_locations)
        download_button_layout.addWidget(self.download_without_locations_button)

        self.facility_map_btn = QPushButton("Show Generated Facility Map")
        self.facility_map_btn.setMinimumHeight(36)
        self.facility_map_btn.clicked.connect(self._show_facility_map)
        self.facility_map_btn.setVisible(False)  # hidden until new DB is used
        download_button_layout.addWidget(self.facility_map_btn)

        content.addLayout(download_button_layout)

        # Buttons for different options
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)

        # Trend Evolution Table
        trend_button = QPushButton("Trend Evolution")
        trend_button.setMinimumHeight(36)
        trend_button.clicked.connect(self.show_trend_evolution)
        button_layout.addWidget(trend_button)

        # Cost Breakdown button
        cost_button = QPushButton("Cost Breakdown")
        cost_button.setMinimumHeight(36)
        cost_button.clicked.connect(self.show_cost_breakdown)
        button_layout.addWidget(cost_button)

        content.addLayout(button_layout)

        # Navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(16)
        self.home_btn = QPushButton("Home")
        self.home_btn.setMinimumHeight(36)
        self.location_btn = QPushButton("Go back to city input")
        self.location_btn.setMinimumHeight(36)
        self.data_btn = QPushButton("Prev")
        self.data_btn.setMinimumHeight(36)

        nav_row.addWidget(self.home_btn)
        nav_row.addWidget(self.location_btn)
        nav_row.addWidget(self.data_btn)

        content.addLayout(nav_row)

        footer = QLabel("Copyright 2026, Battelle Energy Alliance, LLC. All Rights Reserved")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #555; font-size: 10px; padding: 3px 0;"
            "border-top: 1px solid #ccc; margin-top: 2px;"
        )
        content.addWidget(footer)

        self.setLayout(content)

    def _populate_year_combo(self):
        import re
        with QSignalBlocker(self.year_combo):
            self.year_combo.clear()
        years = []
        if self.map_dir.exists():
            prefix = re.escape(self._file_prefix)
            years = sorted({
                m.group(1)
                for f in self.map_dir.iterdir()
                if (m := re.search(rf'{prefix}_map_(\d{{4}})\.html$', f.name))
            })
        if not years:
            years = ["2015"]
        self.year_combo.addItems(years)

    def _on_year_combo_changed(self, year_str):
        if self._current_map_type == 'with':
            self.show_with_locations()
        elif self._current_map_type == 'without':
            self.show_without_locations()

    def _breakdown_excel_path(self) -> str:
        return str(self.map_dir / f"{self._file_prefix}_Breakdown_Final_Results.xlsx")

    def show_cost_breakdown(self):
        print("Cost Breakdown button clicked.")
        excel_file_path = self._breakdown_excel_path()
        if not Path(excel_file_path).exists():
            QMessageBox.warning(self, "File not found",
                f"Results file not found:\n{excel_file_path}\n\nRun the optimisation first.")
            return
        df = pd.read_excel(excel_file_path)
        self.cost_breakdown_window = Cost_Breakdown_Window(df)
        self.cost_breakdown_window.show()

    def show_trend_evolution(self):
        print("Trend Evolution button clicked.")
        excel_file_path = self._breakdown_excel_path()
        if not Path(excel_file_path).exists():
            QMessageBox.warning(self, "File not found",
                f"Results file not found:\n{excel_file_path}\n\nRun the optimisation first.")
            return
        df = pd.read_excel(excel_file_path)
        self.trend_window = TrendEvolutionWindow(df)
        self.trend_window.show()

    def download_with_locations(self):
        print("Download with Locations button clicked.")
        # Logic for downloading the image with locations goes here

    def download_without_locations(self):
        print("Download without Locations button clicked.")
        # Logic for downloading the image without locations goes here

    def _load_map(self, file_name:str):
        html_path = (self.map_dir / file_name).resolve()
        print(f"[Map] Trying to load: {html_path}")
        if not html_path.exists():
            QMessageBox.warning(
                self, "Map not found",
                f"Couldn't find the map HTML: {html_path}\nCWD: {Path.cwd()}"
            )
            return
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

    def _year(self) -> int:
        try:
            return int(self.year_combo.currentText())
        except (ValueError, AttributeError):
            return 2015

    def _show_facility_map(self):
        self._current_map_type = None  # deselect year-based map type
        facility_map = Path(__file__).resolve().parent / "new_facility_map.html"
        if facility_map.exists():
            self.web_view.setUrl(QUrl.fromLocalFile(str(facility_map)))
        else:
            QMessageBox.warning(self, "Not Found",
                "Generated facility map not found. Run facility generation first.")

    def show_with_locations(self):
        self._current_map_type = 'with'
        year = self._year()
        self._load_map(f"{self._file_prefix}_map_WL_{year}.html")

    def show_without_locations(self):
        self._current_map_type = 'without'
        year = self._year()
        self._load_map(f"{self._file_prefix}_map_{year}.html")

    def show_plots(self):
        print('Plot Button is Clicked')
        pass