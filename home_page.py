# Copyright 2026, Battelle Energy Alliance, LLC, ALL RIGHTS RESERVED
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMainWindow,
    QStackedWidget, QPushButton, QTextBrowser, QTabWidget, QScrollArea, QTextEdit,
    QSizePolicy
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import os

BASE_DIR = os.path.dirname(__file__)

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        logo_path = os.path.join(BASE_DIR, "logo.png")

        # ── Tab 1: Home ───────────────────────────────────────────
        home_tab = QWidget()
        home_layout = QVBoxLayout(home_tab)
        home_layout.setContentsMargins(20, 20, 20, 20)
        home_layout.setSpacing(10)

        title = QLabel("<h1>REBORN</h1>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_layout.addWidget(title)

        description = QTextBrowser()
        description.setReadOnly(True)
        description.setFixedHeight(75)
        description.document().setDocumentMargin(4)
        description.setHtml("""
            <p>REBORN is an optimization model that identifies cost-effective reverse logistics networks for battery recycling and repurposing.
            By integrating geographic, economic, and facility location data, it will support informed regional decision-making to determine optimal sites for battery reverse logistics operations.
            Unlike existing approaches, which are often limited to specific states or regions and lack detailed modeling of battery-specific logistics, this tool offers scalable analysis at national, regional, state, and county levels. It also includes the capability to identify ideal locations for new facilities in areas where infrastructure is currently lacking.
            </p>
        """)
        home_layout.addWidget(description)

        pathway_path = os.path.join(BASE_DIR, "REBORN_Pathway.png")
        if os.path.exists(pathway_path):
            self._pathway_label = QLabel()
            self._pathway_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pathway_label.setMinimumSize(1, 1)
            self._pathway_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            # Store the raw pixmap so we can rescale on window resize
            self._pathway_raw = QPixmap(pathway_path)
            self._pathway_label.setPixmap(
                self._pathway_raw.scaledToWidth(1050, Qt.TransformationMode.SmoothTransformation)
            )
            home_layout.addWidget(self._pathway_label, 1)  # stretch=1 fills the bottom half

        if os.path.exists(logo_path):
            logo = QLabel()
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(logo_path).scaledToWidth(120, mode=Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
            home_layout.addWidget(logo)

        version = QLabel("Version 0.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author = QLabel("Srikar V Srinivas, Yuan-Yuan, Andrew Bremond, Miles Palmer, Rajiv Paudel, Ange-Lionel Toba, Ruby T. Nguyen")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        home_layout.addWidget(version)
        home_layout.addWidget(author)

        self.location_btn = QPushButton("Start")
        home_layout.addWidget(self.location_btn)

        # ── Tab 2: About the Team ─────────────────────────────────
        about_tab = QWidget()
        about_outer_layout = QVBoxLayout(about_tab)
        about_outer_layout.setContentsMargins(20, 20, 20, 20)
        about_outer_layout.setSpacing(10)

        if os.path.exists(logo_path):
            logo2 = QLabel()
            logo2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap2 = QPixmap(logo_path).scaledToWidth(120, mode=Qt.TransformationMode.SmoothTransformation)
            logo2.setPixmap(pixmap2)
            about_outer_layout.addWidget(logo2)

        about_title = QLabel("<h1>About the team</h1>")
        about_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_outer_layout.addWidget(about_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_contents = QWidget()
        scroll_layout = QVBoxLayout(scroll_contents)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(20)

        people = [
            ("Srikar",  "Photos/Srikar.jpg"),
            ("Yuan",    "Photos/Yuan.jpg"),
            ("Andrew",  "Photos/Andrew.jpg"),
            ("Miles",   "Photos/Miles.jpg"),
            ("Rajiv",   "Photos/Rajiv.jpg"),
            ("Lionel",  "Photos/Lionel.jpg"),
            ("Ruby",    "Photos/Ruby.jpg"),
        ]

        self.about_image_labels = []
        self.about_text_edits = []

        for name, rel_path in people:
            row = QHBoxLayout()
            row.setSpacing(15)

            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setFixedSize(300, 200)
            img_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
            photo_path = os.path.join(BASE_DIR, rel_path)
            if os.path.exists(photo_path):
                photo_pixmap = QPixmap(photo_path).scaled(
                    300, 200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                img_label.setPixmap(photo_pixmap)
            else:
                img_label.setText(name)
            self.about_image_labels.append(img_label)
            row.addWidget(img_label)

            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            desc_path = os.path.join(BASE_DIR, "Descriptions", f"{name}.txt")
            if os.path.exists(desc_path):
                with open(desc_path, "r", encoding="utf-8") as f:
                    text_edit.setPlainText(f.read().strip())
            else:
                text_edit.setPlaceholderText(f"No description found for {name}.")
            text_edit.setMinimumHeight(200)
            self.about_text_edits.append(text_edit)
            row.addWidget(text_edit, stretch=1)

            scroll_layout.addLayout(row)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_contents)
        about_outer_layout.addWidget(scroll_area)

        # ── Tab 3: ReCell ─────────────────────────────────────────
        recell_tab = QWidget()
        recell_layout = QVBoxLayout(recell_tab)
        recell_layout.setContentsMargins(20, 20, 20, 20)
        recell_layout.setSpacing(10)

        if os.path.exists(logo_path):
            logo3 = QLabel()
            logo3.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap3 = QPixmap(logo_path).scaledToWidth(120, mode=Qt.TransformationMode.SmoothTransformation)
            logo3.setPixmap(pixmap3)
            recell_layout.addWidget(logo3)

        recell_title = QLabel("<h1>About ReCell</h1>")
        recell_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recell_layout.addWidget(recell_title)

        recell_scroll = QScrollArea()
        recell_scroll.setWidgetResizable(True)
        recell_scroll_contents = QWidget()
        recell_scroll_layout = QVBoxLayout(recell_scroll_contents)
        recell_scroll_layout.setContentsMargins(10, 10, 10, 10)
        recell_scroll_layout.setSpacing(15)

        recell_img_label = QLabel()
        recell_img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recell_image_path = os.path.join(BASE_DIR, "Recell_Image.jpg")
        if os.path.exists(recell_image_path):
            recell_pixmap = QPixmap(recell_image_path).scaledToWidth(
                950, Qt.TransformationMode.SmoothTransformation
            )
            recell_img_label.setPixmap(recell_pixmap)
        else:
            recell_img_label.setFixedHeight(250)
            recell_img_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
            recell_img_label.setText("[ ReCell Image ]")
        recell_scroll_layout.addWidget(recell_img_label)

        self.recell_text = QTextEdit()
        self.recell_text.setReadOnly(True)
        self.recell_text.setHtml("""
            <p>The ReCell Center is a national collaboration of industry, academia, and national
            laboratories working together to advance recycling technologies along the entire battery
            life-cycle for current and future battery chemistries.</p>

            <h3>Mission</h3>
            <p>The ReCell Center aims to grow a sustainable advanced battery recycling industry by
            developing economic and environmentally sound recycling processes that can be adopted by
            industry for lithium-ion and future battery chemistries.</p>

            <h3>Vision</h3>
            <p>Using science-based strategies to remove the high-risk barriers to economical
            lithium-ion battery recycling could reduce waste, create jobs, encourage increased
            adoption of electric vehicles, and reduce the US reliance on foreign supplies of critical
            materials and mined metals used in battery materials.</p>

            <p>For more information, please visit:
            <a href="https://recellcenter.org/about/">https://recellcenter.org/about/</a></p>
        """)
        self.recell_text.setMinimumHeight(300)
        recell_scroll_layout.addWidget(self.recell_text)
        recell_scroll_layout.addStretch()

        recell_scroll.setWidget(recell_scroll_contents)
        recell_layout.addWidget(recell_scroll)


        # ── Tab 4: User Manual ────────────────────────────────────
        manual_tab = QWidget()
        manual_layout = QVBoxLayout(manual_tab)
        manual_layout.setContentsMargins(20, 20, 20, 20)
        manual_layout.setSpacing(10)

        manual_title = QLabel("<h1>User Manual</h1>")
        manual_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        manual_layout.addWidget(manual_title)

        manual_text = QTextBrowser()
        manual_text.setReadOnly(True)
        manual_text.setOpenExternalLinks(True)
        manual_text.setHtml("""
            <h3>Getting Started</h3>
            <p>From the <b>Home</b> tab, click <b>Start</b>. The sidebar on the left shows the five sequential steps:
            <b>Location &rarr; Data &rarr; Facility &rarr; Settings &rarr; Results</b>.
            Each step unlocks only after the previous one is completed.</p>

            <h3>Step 1 &mdash; Location</h3>
            <p>Choose a selection mode, then pick your geographic scope:</p>
            <ul>
                <li><b>Regions:</b> Select one or more of Northeast, Midwest, South, West.</li>
                <li><b>States:</b> Multi-select individual states.</li>
                <li><b>County/City:</b> Drill down to a single county and city.</li>
            </ul>
            <p>A reference map on the right reflects US regions. Click <b>Next</b> when done.</p>

            <h3>Step 2 &mdash; Data</h3>
            <p>Set the simulation year range, then load demand data:</p>
            <ul>
                <li><b>Multi years:</b> Enter start and end years, then click <b>Load default data</b> to pull ABM-based recycling/repurposing projections for your selected area.</li>
                <li><b>Single year:</b> Enter one year and load defaults.</li>
                <li><b>Custom Data tab:</b> Manually enter year-by-year Recycled and Repurposed battery quantities, then save as CSV or Excel.</li>
            </ul>
            <p>The map panel updates to highlight selected states and show existing facility markers. Click <b>Next</b> when done.</p>

            <h3>Step 3 &mdash; Facility Database</h3>
            <p>Choose the facility database for the optimization:</p>
            <ul>
                <li><b>Use Default Database:</b> Uses the pre-loaded <i>Pyomo_Ex_DB.xlsx</i> with existing recycling and repurposing centers.</li>
                <li><b>Generate New Facility Locations:</b> Randomly generate candidate facilities within the selected geography. Set total facility count, recycling/repurposing/dealership ratios, and capacities (batteries/year). Click <b>Generate Facilities</b>. Results can replace or append to existing databases.</li>
            </ul>
            <p>Click <b>Next</b> when done.</p>

            <h3>Step 4 &mdash; Settings (Run Optimization)</h3>
            <p>Review and adjust model parameters, then run the solver:</p>
            <ul>
                <li>Parameters include transportation cost, acquisition cost, fixed and operating costs for recycling and repurposing centers, packaging cost, and facility capacities.</li>
                <li>Select <b>Use Default Values</b> or <b>Randomize Values</b> within the defined ranges.</li>
                <li>Optionally set a custom <b>Results Folder</b> name (auto-derived if left blank).</li>
                <li>Click <b>Run</b> to execute the CPLEX optimization. A progress bar tracks solver status.</li>
                <li>Wait for the completion message before navigating to Results.</li>
            </ul>
            <p><b>Note:</b> CPLEX must be installed and licensed on your machine. The solver is called via Pyomo.</p>

            <h3>Step 5 &mdash; Results</h3>
            <p>After the optimization completes:</p>
            <ul>
                <li>Use the <b>Year</b> dropdown to select a result year.</li>
                <li><b>Show with Locations:</b> Interactive map with facility and flow overlays.</li>
                <li><b>Show without Locations:</b> Map showing flows only.</li>
                <li><b>Show Generated Facility Map:</b> Visible only if new facilities were generated in Step 3.</li>
                <li><b>Trend Evolution:</b> Table summarizing key metrics across all years.</li>
                <li><b>Cost Breakdown:</b> Pie charts showing cost distribution per year.</li>
            </ul>

            <h3>Notes</h3>
            <ul>
                <li>Steps must be completed in order; sidebar buttons for later steps remain disabled until unlocked.</li>
                <li>Re-running the optimization in Settings overwrites the previous results folder.</li>
                <li>Do not modify column headers in any input Excel files.</li>
                <li>Large geographic scopes (multi-region or national) may take several minutes to solve.</li>
            </ul>

            <h3>Contact</h3>
            <p>For questions or issues, contact <b>Srikar Srinivas</b> at
            <a href="mailto:srikar.srinivas@inl.gov">srikar.srinivas@inl.gov</a>.</p>
        """)
        manual_layout.addWidget(manual_text)

        # ── Tab 5: Copyright Information ──────────────────────────
        copyright_tab = QWidget()
        copyright_layout = QVBoxLayout(copyright_tab)
        copyright_layout.setContentsMargins(20, 20, 20, 20)
        copyright_layout.setSpacing(10)

        copyright_title = QLabel("<h1>Terms and Conditions</h1>")
        copyright_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_layout.addWidget(copyright_title)

        copyright_text = QTextBrowser()
        copyright_text.setReadOnly(True)
        copyright_text.setOpenExternalLinks(True)
        copyright_text.setHtml("""
            <p><b>Notice:</b> These data were produced by BATTELLE ENERGY ALLIANCE, LLC under
            Contract No. DE-AC07-05ID14517 with the Department of Energy. For ten (10) years
            from June 5, 2023, the Government is granted for itself and others acting on its
            behalf a nonexclusive, paid-up, irrevocable worldwide license in this data to
            reproduce, prepare derivative works, and perform publicly and display publicly,
            by or on behalf of the Government. There is provision for the possible extension
            of the term of this license. Subsequent to that period or any extension granted,
            the Government is granted for itself and others acting on its behalf a
            nonexclusive, paid-up, irrevocable worldwide license in this data to reproduce,
            prepare derivative works, distribute copies to the public, perform publicly and
            display publicly, and to permit others to do so. The specific term of the license
            can be identified by inquiry made to Contractor or DOE.</p>

            <p>NEITHER THE UNITED STATES NOR THE UNITED STATES DEPARTMENT OF ENERGY, NOR ANY
            OF THEIR EMPLOYEES, MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR ASSUMES ANY LEGAL
            LIABILITY OR RESPONSIBILITY FOR THE ACCURACY, COMPLETENESS, OR USEFULNESS OF ANY
            DATA, APPARATUS, PRODUCT, OR PROCESS DISCLOSED, OR REPRESENTS THAT ITS USE WOULD
            NOT INFRINGE PRIVATELY OWNED RIGHTS.</p>
        """)
        copyright_layout.addWidget(copyright_text)

        # ── QTabWidget ────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.addTab(home_tab,       "Home")
        tabs.addTab(manual_tab,     "User Manual")
        tabs.addTab(recell_tab,     "About ReCell")
        tabs.addTab(about_tab,      "About the Team")
        tabs.addTab(copyright_tab,  "Copyright Information")

        footer = QLabel("Copyright 2026, Battelle Energy Alliance, LLC. All Rights Reserved")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            "color: #555; font-size: 10px; padding: 3px 0;"
            "border-top: 1px solid #ccc; margin-top: 2px;"
        )

        main_layout = QVBoxLayout()
        main_layout.addWidget(tabs, 1)
        main_layout.addWidget(footer)
        self.setLayout(main_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_pathway_label') and hasattr(self, '_pathway_raw'):
            w = self._pathway_label.width()
            if w > 0:
                self._pathway_label.setPixmap(
                    self._pathway_raw.scaledToWidth(w, Qt.TransformationMode.SmoothTransformation)
                )
