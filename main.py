# Importing all the relevant libraries
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMainWindow, QStackedWidget, QPushButton, QHBoxLayout
from home_page import HomePage
from input_page import LocationPage
# from about_page import AboutPage
from data_page import DataPage
from map_page import MapPage
from settings_page import SettingsPage, Parameters
from execution_page import ResultsPage
from facility_page import FacilityGenerationPage
from sidebar import SideBar # Separate class to set the sidebar
import matplotlib.pyplot as plt

# Defining a class that uses the QMainWindow as its parent
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() # Calling the parent class QMainWindow
        self.setWindowTitle("ReCell Interface") # Setting the Window Title to be Recell Interface

        # sidebar
        root = QWidget(self) 
        layout = QHBoxLayout(root) # Horizontal Box layout
        layout.setSpacing(15) # Sets the spacing between widgets

        self.sidebar = SideBar(self._on_sidebar_clicked) # Function to set active the current page
        layout.addWidget(self.sidebar) # Adding the sidebar to the layout

        # create QStackedWidget container
        self.stack = QStackedWidget() # QStackedWidget: This is a container widget in the Qt framework that can hold multiple widgets but displays only one at a time. It is useful for implementing interfaces where you need to switch between different views or pages, such as in a tabbed interface or a wizard.
        layout.addWidget(self.stack, 1) # Stretch Factor: The stretch factor determines how much space the widget should take relative to other widgets in the same layout. A higher stretch factor means the widget will take up more space.
        self.setCentralWidget(root) #  In a QMainWindow, the central widget is the primary area where the main content of the application is displayed.

        # add pages here
        self.home = HomePage()
        # self.about = AboutPage()
        self.location = LocationPage(done_callback=self.done_location) 
        # self.data = DataPage(self.done_data)
        # self.map = MapPage(self.done_map)
        self.Parameters=Parameters
        self.settings = SettingsPage(self.Parameters,self.done_settings)
        # print(f"[MainWindow.__init__] settings id = {id(self.settings)}")
        self.facility = FacilityGenerationPage(done_callback=self.done_facility)
        self.results = ResultsPage()

        # add cross-page scratchpad used to pass data into SettingsPage
        self.ctx = {}

        self.pages = {
            "Home": self.home,
            # "About": self.about,
            "Location": self.location,
            # "Data": self.data,
            # "Map": self.map,
            "Facility": self.facility,
            "Settings": self.settings,
            "Results": self.results
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.sidebar.set_active("Location")
        self.stack.setCurrentWidget(self.home)

        def _go_in(page_name: str):
            if page_name not in self.pages:
                return
            self.sidebar.set_active(page_name)
            self.stack.setCurrentWidget(self.pages[page_name])


        # Home Page buttons
        # self.home.about_btn.clicked.connect(lambda: _go_in("About"))
        self.home.location_btn.clicked.connect(lambda: _go_in("Location"))

        # About Page buttons
        # self.about.home_btn.clicked.connect(lambda: _go_in("Home"))

        # Location Page buttons
        self.location.home_btn.clicked.connect(lambda: _go_in("Home"))

        # Data Page buttons
        # self.data.home_btn.clicked.connect(lambda: __go_ino("Home"))
        # self.data.Location_btn.clicked.connect(lambda: _go_in("Location"))
        # self.data.map_btn.clicked.connect(lambda: _go_in("Map"))

        # Map Page buttons
        # self.map.home_btn.clicked.connect(lambda: _go_in("Home"))
        # self.map.Location_btn.clicked.connect(lambda: _go_in("Location"))
        # self.map.data_btn.clicked.connect(lambda: _go_in("Data"))
        # self.map.settings_btn.clicked.connect(lambda: _go_in("Settings"))

        # Facility Page buttons
        self.facility.home_btn.clicked.connect(lambda: _go_in("Home"))
        self.facility.back_btn.clicked.connect(lambda: _go_in("Data"))

        # Settings Page buttons
        self.settings.home_btn.clicked.connect(lambda: _go_in("Home"))
        self.settings.location_btn.clicked.connect(lambda: _go_in("Location"))
        self.settings.data_btn.clicked.connect(lambda: _go_in("Facility"))
        # self.settings.map_btn.clicked.connect(lambda: _go_in("Map"))
        def _go_to_results_from_settings():
            folder = (self.settings._results_folder_name
                      or self.settings.folder_name_edit.text().strip()
                      or 'REBORN_Results')
            self.results.set_results_dir(folder)
            _go_in("Results")
        self.settings.results_btn.clicked.connect(_go_to_results_from_settings)

        # Results Page buttons
        self.results.home_btn.clicked.connect(lambda: _go_in("Home"))
        self.results.location_btn.clicked.connect(lambda: _go_in("Location"))
        self.results.data_btn.clicked.connect(lambda: _go_in("Settings"))
        # self.Results.map_btn.clicked.connect(lambda: _go_in("Map"))
        # self.Results.settings_btn.clicked.connect(lambda: _go_in("Settings"))

        
    def _go_to(self, page_name: str) -> None:
        if page_name not in self.pages:
            return
        self.sidebar.set_active(page_name)
        self.stack.setCurrentWidget(self.pages[page_name])

    # Function to set the current widget
    def _on_sidebar_clicked(self, step:str):
        self.sidebar.set_active(step)
        self.stack.setCurrentWidget(self.pages[step])

    # def done_Location(self):
    #     self.sidebar.unlock_next("Location")
    #     self._on_sidebar_clicked("Data")
    
    # def done_data(self):
    #     self.sidebar.unlock_next("Data")
    #     self._on_sidebar_clicked("Map")

    # def done_map(self):
    #     self.sidebar.unlock_next("Map")
    #     self._on_sidebar_clicked("Settings")

    def done_settings(self, folder_name='REBORN_Results'):
        self.sidebar.unlock_next("Settings")
        self.results.set_results_dir(folder_name)
        self._on_sidebar_clicked("Results")

    def done_location(self, info:dict):
        print(f"[MainWindow.done_inpu] settings id={id(self.settings)}, payload keys={list(info.keys())}")
        self.ctx["selections"] = info
        self.settings.set_context(selections=info)
        self.facility.set_context(selections=info)
        self.settings._debug_payload("after set_context")
        self.data = DataPage(
            selections = {
                "regions": info["regions"],
                "states": info["states"],
                "county": info["county"],
                "city": info["city"],
            },
            region_map = info["region_map"],
            done_callback =  self.done_data,
        )
        self.pages["Data"] = self.data
        self.stack.addWidget(self.data)
        self.stack.setCurrentWidget(self.data)
        self.sidebar.unlock_next("Location")
        self.sidebar.set_active("Data")
        self._on_sidebar_clicked("Data")
        
        self.data.home_btn.clicked.connect(lambda: self._go_to("Home"))
        self.data.location_btn.clicked.connect(lambda: self._go_to("Location"))
    
    def done_data(self, results:dict):
        # print(f"[MainWindow.done_data] settings id={id(self.settings)}, yearly_df_records? {results.get('yearly_data') is not None}")
        self.ctx["yearly_data"] = results.get("yearly_data", [])
        self.settings.set_context(yearly_df_records=self.ctx["yearly_data"])
        self.settings._debug_payload("after set_context")
        self.sidebar.unlock_next("Data")
        self._on_sidebar_clicked("Facility")

    def done_facility(self, result: dict):
        use_new_db = result.get("use_new_db", False)
        self.settings.set_use_new_db(use_new_db)
        self.results.set_use_new_db(use_new_db)
        self.sidebar.unlock_next("Facility")
        self._on_sidebar_clicked("Settings")



if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QPushButton[checkable="true"]{
            padding: 6px 12px;
            text-align: left;
            border: none;
        }
        QPushButton[checkable="true"]:checked{
            background: #0078d7;         /* accent blue */
            color: white;
        }
        QPushButton:disabled{
            color:gray;
        }
    """)

    w = MainWindow()
    w.resize(1100,600) 
    w.show()
    sys.exit(app.exec())