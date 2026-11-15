# ==================================================================================================
# CLEFTMETER, VERSION 2.0
# Authors: Libor Borak, Petr Marcian, Olga Koskova
# @ 2025, 2026
# ==================================================================================================
# Records of revision:
# 
# CleftMeter v1.0:
# - Initial issue
#
# CleftMeter v2.0:
# - Added user-defined custom landmark points (X1, X2, ...).
# - Added automatic landmark side-consistency checking with a color-coded reference landmark diagram.
# - Improved point editing and deletion, including direct point selection on the 3D model.
# - Introduced the .cleftp project format with separate clinical TXT report output and legacy TXT import support.
# - Added protection against accidental loss of unsaved changes.
# - Added model transparency control and customizable 3D workspace background color.
# - Improved project loading, saving, data handling, and overall user interface.
# ==================================================================================================

import sys
import os
import traceback 
from PySide6 import QtWidgets, QtCore, QtGui
# Import only the VTK modules used by CleftMeter (avoid loading the entire VTK package).
from types import SimpleNamespace
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkLine, vtkPolyData
from vtkmodules.vtkFiltersSources import vtkLineSource, vtkRegularPolygonSource, vtkSphereSource
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkIOImage import vtkPNGReader
from vtkmodules.vtkRenderingAnnotation import vtkCornerAnnotation
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkCellPicker, vtkFollower, vtkImageActor, vtkPolyDataMapper,
    vtkRenderer, VTK_SURFACE, VTK_WIREFRAME,
)
from vtkmodules.vtkRenderingFreeType import vtkVectorText

# Register the VTK implementations needed for OpenGL rendering and interactivity.
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkRenderingUI

# Keep existing vtk.vtkClass(...) and vtk.VTK_... calls unchanged.
vtk = SimpleNamespace(
    vtkActor=vtkActor,
    vtkCellArray=vtkCellArray,
    vtkCellPicker=vtkCellPicker,
    vtkCornerAnnotation=vtkCornerAnnotation,
    vtkFollower=vtkFollower,
    vtkImageActor=vtkImageActor,
    vtkLine=vtkLine,
    vtkLineSource=vtkLineSource,
    vtkPNGReader=vtkPNGReader,
    vtkPoints=vtkPoints,
    vtkPolyData=vtkPolyData,
    vtkPolyDataMapper=vtkPolyDataMapper,
    vtkRegularPolygonSource=vtkRegularPolygonSource,
    vtkRenderer=vtkRenderer,
    vtkSphereSource=vtkSphereSource,
    vtkSTLReader=vtkSTLReader,
    vtkVectorText=vtkVectorText,
    VTK_SURFACE=VTK_SURFACE,
    VTK_WIREFRAME=VTK_WIREFRAME,
)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor 
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera 
from vtkmodules.vtkCommonCore import vtkCommand 
import math
import numpy as np



## ------------------------------------------------------------------------
## Unified About dialog helper used by all CleftMeter About windows.
## ------------------------------------------------------------------------
def show_cleftmeter_about_dialog(parent, window_title, heading, subtitle, body_html, min_size=(820, 720)):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(window_title)
    dialog.setMinimumSize(*min_size)
    dialog.resize(*min_size)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    text_browser = QtWidgets.QTextBrowser(dialog)
    text_browser.setOpenExternalLinks(False)
    text_browser.setStyleSheet("""
        QTextBrowser {
            background: #fbfbfd;
            border: 1px solid #cfd8dc;
            border-radius: 6px;
            padding: 8px;
        }
    """)

    html = """
    <html>
    <head>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.55;
            color: #263238;
            background-color: #fbfbfd;
        }
        .header {
            background-color: #eaf4fb;
            border: 1px solid #b8d7ea;
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 14px;
        }
        h1 {
            color: #1f4e79;
            font-size: 20pt;
            margin: 0 0 4px 0;
        }
        .subtitle {
            color: #455a64;
            margin: 0;
            font-size: 10pt;
        }
        h2 {
            color: #1f4e79;
            font-size: 13pt;
            margin-top: 18px;
            margin-bottom: 8px;
            border-bottom: 2px solid #90caf9;
            padding-bottom: 4px;
        }
        h3 {
            color: #2e6f9e;
            font-size: 11pt;
            margin-top: 12px;
            margin-bottom: 5px;
        }
        p {
            margin-top: 5px;
            margin-bottom: 8px;
        }
        ul, ol {
            margin-top: 4px;
            margin-bottom: 10px;
        }
        li {
            margin-bottom: 4px;
        }
        .section {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 12px;
        }
        .note {
            background-color: #fff8e1;
            border: 1px solid #ffe082;
            border-radius: 5px;
            padding: 8px 10px;
            margin: 8px 0;
        }
        .warning {
            background-color: #ffebee;
            border: 1px solid #ef9a9a;
            border-radius: 5px;
            padding: 8px 10px;
            margin: 8px 0;
        }
        .formula {
            background-color: #f5f7fa;
            border: 1px solid #d6dde5;
            border-radius: 5px;
            padding: 8px 10px;
            margin: 8px 0;
            text-align: center;
            font-size: 11pt;
        }
        .kbd {
            font-family: Consolas, monospace;
            background-color: #eceff1;
            border: 1px solid #b0bec5;
            border-radius: 3px;
            padding: 1px 5px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 8px 0;
        }
        th {
            background-color: #e3f2fd;
            color: #1f4e79;
            border: 1px solid #cfd8dc;
            padding: 5px;
            text-align: left;
        }
        td {
            border: 1px solid #cfd8dc;
            padding: 5px;
            vertical-align: top;
        }
        .footer {
            color: #607d8b;
            font-size: 9pt;
            border-top: 1px solid #cfd8dc;
            margin-top: 14px;
            padding-top: 8px;
        }
    </style>
    </head>
    <body>
        <div class="header">
            <h1>""" + heading + """</h1>
            <p class="subtitle">""" + subtitle + """</p>
        </div>
    """ + body_html + """
    </body>
    </html>
    """

    text_browser.setHtml(html)
    layout.addWidget(text_browser)

    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, dialog)
    ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
    if ok_button:
        ok_button.setText("Close")
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.exec()



## ------------------------------------------------------------------------
## Custom VTK interactor style handling mouse events for defining, editing, and deleting points in the 3D space.
## ------------------------------------------------------------------------
class CustomInteractorStyle(vtkInteractorStyleTrackballCamera):
    ## Initializes the custom interactor style and registers event listeners for mouse interactions.
    def __init__(self, renderer, stl_viewer):
        super().__init__()
        self.stl_viewer = stl_viewer
        self.Renderer = renderer
        self.AddObserver(vtkCommand.LeftButtonPressEvent, self.left_button_press_event)
        self.AddObserver(vtkCommand.RightButtonPressEvent, self.right_button_press_event)

        self.d_pressed = False
        self.e_pressed = False
        self.delete_mode = False
        self.last_picked_point = None
        
    ## Handles right mouse button clicks, primarily used to spawn the background color selection menu.
    def right_button_press_event(self, obj, event):
        self.stl_viewer.show_background_color_menu()

    ## Processes left mouse button clicks to either pick existing actors for editing/deleting or define new points.
    def left_button_press_event(self, obj, event):
        if not (
            self.d_pressed or
            self.e_pressed or
            self.delete_mode
        ):
            self.OnLeftButtonDown()
            return

        click_pos = self.GetInteractor().GetEventPosition()
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005)

        if not self.stl_viewer.actor:
            return

        picker.AddPickList(self.stl_viewer.actor)
        picker.PickFromListOn()
        picker.Pick(
            click_pos[0],
            click_pos[1],
            0,
            self.Renderer
        )

        if picker.GetActor() != self.stl_viewer.actor:
            return

        world_pos = picker.GetPickPosition()

        if self.d_pressed:
            if self.last_picked_point is None or \
               (world_pos[0] - self.last_picked_point[0])**2 + \
               (world_pos[1] - self.last_picked_point[1])**2 + \
               (world_pos[2] - self.last_picked_point[2])**2 > 1e-6:

                self.stl_viewer.add_point(world_pos)
                self.last_picked_point = world_pos

            return

        if self.e_pressed:
            self.stl_viewer.vtkWidget.setFocus()

            if self.stl_viewer.selected_point_index is None:
                min_dist_sq = float('inf')
                closest_point_index = -1

                search_radius_sq = (
                    self.Renderer.GetActiveCamera().GetDistance() * 0.05
                )**2

                for i, (pos_data, _, _) in enumerate(
                        self.stl_viewer.points):

                    if isinstance(pos_data, tuple):
                        point_pos = np.array(pos_data)

                        dist_sq = np.sum(
                            (np.array(world_pos) - point_pos)**2
                        )

                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            closest_point_index = i

                if closest_point_index != -1 and \
                   min_dist_sq < search_radius_sq:

                    self.stl_viewer.highlight_selected_point(
                        closest_point_index
                    )

                    self.stl_viewer.update_prompt()
                    self.stl_viewer.update_info_panel()

                else:
                    QtWidgets.QToolTip.showText(
                        QtGui.QCursor.pos(),
                        "No defined point found close enough to edit.",
                        self.stl_viewer.vtkWidget
                    )

            else:
                self.stl_viewer.redefine_point(world_pos)

            return

        if self.delete_mode:
            min_dist_sq = float('inf')
            closest_point_index = -1

            search_radius_sq = (
                self.Renderer.GetActiveCamera().GetDistance() * 0.05
            )**2

            for i, (pos_data, _, _) in enumerate(
                    self.stl_viewer.points):

                if isinstance(pos_data, tuple):
                    point_pos = np.array(pos_data)

                    dist_sq = np.sum(
                        (np.array(world_pos) - point_pos)**2
                    )

                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        closest_point_index = i

            if closest_point_index != -1 and \
               min_dist_sq < search_radius_sq:

                self.stl_viewer.delete_point(
                    closest_point_index
                )

            else:
                QtWidgets.QToolTip.showText(
                    QtGui.QCursor.pos(),
                    "No defined point found close enough to delete.",
                    self.stl_viewer.vtkWidget
                )

            return
        
## ------------------------------------------------------------------------
## Dialog window for selecting defined points to create new distance or angle measurements.
## ------------------------------------------------------------------------
class SelectPointsDialog(QtWidgets.QDialog):
    ## Sets up the point selection dialog UI with dropdown combo boxes.
    def __init__(self, available_points, num_points=2, title="Select Points", labels=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.combos = []

        if labels is None or len(labels) != num_points:
            if num_points == 3 and "Angle" in title:
                 labels = ["Point 1", "Vertex Point", "Point 2"]
            else:
                 labels = [f"Point {i+1}" for i in range(num_points)]

        for i in range(num_points):
            label_text = labels[i]
            label = QtWidgets.QLabel(label_text)
            combo = QtWidgets.QComboBox()
            
            if "Distance" in title and i == 2:
                combo.addItems(["NONE"] + [str(p) for p in available_points])
            else:
                combo.addItems([str(p) for p in available_points])

            self.layout.addWidget(label)
            self.layout.addWidget(combo)
            self.combos.append(combo)

        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    ## Returns a list containing the currently selected text values from the dialog's comboboxes.
    def getSelectedLabels(self):
        return [combo.currentText() for combo in self.combos]



## ------------------------------------------------------------------------
## Core application container holding top-level UI, main 3D visualization scene, and file handling logic.
## ------------------------------------------------------------------------
class STLViewer(QtWidgets.QMainWindow):
    ## Main execution entry point initializing frame layouts embedding VTK viewer handling baseline parameter configurations setting base application state.
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("CleftMeter 2.0") 
        self.frame = QtWidgets.QFrame()
        self.main_layout = QtWidgets.QHBoxLayout(self.frame)

        self.FIXED_LABELS_CLEFT = ['I', 'P', 'P\'', 'L', 'L\'', 'C', 'C\'', 'Q', 'Q\'', 'T', 'T\'']
        self.DEFAULT_CLEFT_DIST_DEFS = [
            ("I", "P"), ("I", "P'"), ("I", "L"), ("I", "L'"), ("I", "C"), ("I", "C'"),
            ("I", "Q"), ("I", "Q'"), ("I", "T"), ("I", "T'"), ("P", "L"), ("P'", "L'"),
            ("P", "C"), ("P'", "C'"), ("P", "Q"), ("P'", "Q'"), ("P", "T"), ("P'", "T'"),
            ("P", "P'"), ("L", "L'"), ("C", "C'"), ("Q", "Q'"), ("T", "T'"),
            ("I", "C", "C'"), ("I", "Q", "Q'"), ("I", "T", "T'")
        ]
        self.DEFAULT_CLEFT_ANGLE_DEFS = [
            ("I", "L", "L'"), ("I", "L'", "L"), ("I", "C", "C'"), ("I", "C'", "C"),
            ("I", "Q", "Q'"), ("I", "Q'", "Q"), ("I", "T", "T'"), ("I", "T'", "T"),
            ("C", "L", "P"), ("T", "C", "L")
        ]
        
      
        
        self.left_panel = QtWidgets.QWidget()
        self.left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        self.left_panel.setFixedWidth(350) 

        self.left_layout.addWidget(QtWidgets.QLabel("<b>Points:</b>"))
        self.info_panel = QtWidgets.QListWidget()
        self.left_layout.addWidget(self.info_panel)
        self.info_panel.itemClicked.connect(self.on_point_selected)
        
        self.point_buttons_layout = QtWidgets.QHBoxLayout()
        self.add_custom_point_button = QtWidgets.QPushButton("Add")
        self.add_custom_point_button.clicked.connect(self.add_custom_point)
        self.remove_custom_point_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_custom_point_button.clicked.connect(self.remove_selected_custom_point)
        self.remove_custom_point_button.setEnabled(False)
        self.point_buttons_layout.addWidget(self.add_custom_point_button)
        self.point_buttons_layout.addWidget(self.remove_custom_point_button)
        self.left_layout.addLayout(self.point_buttons_layout)
        
        font = self.info_panel.font()
        font.setPointSize(font.pointSize() * 1.5) 
        self.info_panel.setFont(font)

        self.left_layout.addWidget(QtWidgets.QLabel("<b>Distances:</b>"))
        self.distances_panel = QtWidgets.QListWidget()
        self.left_layout.addWidget(self.distances_panel)
        self.distances_panel.setFont(font)
        self.distances_panel.itemClicked.connect(self.on_distance_selected)

        self.distance_buttons_layout = QtWidgets.QHBoxLayout()
        self.add_distance_button = QtWidgets.QPushButton("Add")
        self.add_distance_button.clicked.connect(self.add_distance_definition)
        self.remove_distance_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_distance_button.clicked.connect(self.remove_selected_distance)
        self.remove_distance_button.setEnabled(False)
        self.distance_buttons_layout.addWidget(self.add_distance_button)
        self.distance_buttons_layout.addWidget(self.remove_distance_button)
        self.left_layout.addLayout(self.distance_buttons_layout)

        self.left_layout.addWidget(QtWidgets.QLabel("<b>Angles:</b>"))
        self.angles_panel = QtWidgets.QListWidget()
        self.left_layout.addWidget(self.angles_panel)
        self.angles_panel.setFont(font)
        self.angles_panel.itemClicked.connect(self.on_angle_selected)

        self.angle_buttons_layout = QtWidgets.QHBoxLayout()
        self.add_angle_button = QtWidgets.QPushButton("Add")
        self.add_angle_button.clicked.connect(self.add_angle_definition)
        self.remove_angle_button = QtWidgets.QPushButton("Remove Selected")
        self.remove_angle_button.clicked.connect(self.remove_selected_angle)
        self.remove_angle_button.setEnabled(False)
        self.angle_buttons_layout.addWidget(self.add_angle_button)
        self.angle_buttons_layout.addWidget(self.remove_angle_button)
        self.left_layout.addLayout(self.angle_buttons_layout)

        
        self.point_size_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.point_size_slider.setMinimum(1)
        self.point_size_slider.setMaximum(100)
        self.point_size_slider.setValue(50)
        self.point_size_slider.valueChanged.connect(self.update_point_size)
        self.left_layout.addWidget(QtWidgets.QLabel("Point Size:"))
        self.left_layout.addWidget(self.point_size_slider)

        
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(0) 
        self.opacity_slider.valueChanged.connect(self.update_model_opacity)
        self.left_layout.addWidget(QtWidgets.QLabel("Model Transparency:"))
        self.left_layout.addWidget(self.opacity_slider)
        

        self.logo_label = QtWidgets.QLabel("CleftMeter 2.0") 
        self.logo_label.setAlignment(QtCore.Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-family: 'Arial Black'; font-size: 24px; border: 1px solid black; padding: 5px;") 
        self.left_layout.addWidget(self.logo_label)

        self.left_layout.setStretchFactor(self.info_panel, 4)
        self.left_layout.setStretchFactor(self.distances_panel, 3)
        self.left_layout.setStretchFactor(self.angles_panel, 3)

        self.vtk_panel = QtWidgets.QWidget()
        self.vtk_layout = QtWidgets.QVBoxLayout(self.vtk_panel)
        self.vtkWidget = QVTKRenderWindowInteractor(self.vtk_panel)
        self.vtkWidget.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.vtk_layout.addWidget(self.vtkWidget)
        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.interactor_style = CustomInteractorStyle(renderer=self.ren, stl_viewer=self)
        self.iren.SetInteractorStyle(self.interactor_style)
        self.vtkWidget.installEventFilter(self)
        self.ren.GetActiveCamera().SetPosition(0, -1, 0)
        self.ren.GetActiveCamera().SetFocalPoint(0, 0, 0)
        self.ren.GetActiveCamera().SetViewUp(0, 0, 1)
        self.ren.ResetCamera()
        self.ren.SetBackground(0.2, 0.3, 0.4) 

        self.key_hints_annotation = vtk.vtkCornerAnnotation()
        self.key_hints_annotation.SetLinearFontScaleFactor(2)
        self.key_hints_annotation.SetNonlinearFontScaleFactor(1)
        self.key_hints_annotation.SetMaximumFontSize(15) 
        self.key_hints_annotation.SetText(vtk.vtkCornerAnnotation.UpperLeft,
                                          " Instructions:\n\n Key D: Define point\n\n Key E: Edit point\n\n Key N: Skip/Defer point\n\n Key Del: Delete point")
        self.key_hints_annotation.GetTextProperty().SetColor(1.0, 1.0, 1.0) 
        self.key_hints_annotation.GetTextProperty().SetFontSize(10) 
        self.ren.AddViewProp(self.key_hints_annotation)

        self.filename_annotation = vtk.vtkCornerAnnotation()
        self.filename_annotation.SetLinearFontScaleFactor(2)
        self.filename_annotation.SetNonlinearFontScaleFactor(1)
        self.filename_annotation.SetMaximumFontSize(28) 
        self.filename_annotation.GetTextProperty().SetColor(0.96, 0.96, 0.86) 
        self.filename_annotation.SetText(vtk.vtkCornerAnnotation.UpperRight, "")
        self.ren.AddViewProp(self.filename_annotation)
     
        self.button_layout = QtWidgets.QHBoxLayout()
        self.open_button = QtWidgets.QPushButton("Open STL")
        self.open_button.clicked.connect(self.open_stl) 
        self.button_layout.addWidget(self.open_button)
        self.open_points_button = QtWidgets.QPushButton("Open Points") 
        self.open_points_button.clicked.connect(self.open_points) 
        self.button_layout.addWidget(self.open_points_button)
        self.save_button = QtWidgets.QPushButton("Save") 
        self.save_button.clicked.connect(self.save_points) 
        self.save_button.setEnabled(False)
        self.button_layout.addWidget(self.save_button)

        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_active_data) 
        self.button_layout.addWidget(self.clear_button)
        
        self.zoom_to_fit_button = QtWidgets.QPushButton("Zoom To Fit")
        self.zoom_to_fit_button.clicked.connect(self.zoom_to_fit) 
        self.button_layout.addWidget(self.zoom_to_fit_button)

        self.about_button = QtWidgets.QPushButton("About")
        self.about_button.clicked.connect(self.show_about_dialog) 
        self.button_layout.addWidget(self.about_button)
        
        self.prompt_label = QtWidgets.QLabel("")
        self.prompt_label.setAlignment(QtCore.Qt.AlignCenter)
        self.prompt_label.setStyleSheet("font-weight: bold; font-size: 16px;") 
        self.vtk_layout.addWidget(self.prompt_label)
        self.vtk_layout.addLayout(self.button_layout)

        self.main_layout.addWidget(self.left_panel)
        self.main_layout.addWidget(self.vtk_panel)
        self.main_layout.setStretchFactor(self.left_panel, 1)
        self.main_layout.setStretchFactor(self.vtk_panel, 3)
        self.setCentralWidget(self.frame)
        QtCore.QTimer.singleShot(100, self.showMaximized)
        self.iren.Initialize()
        
        self.actor = None
        self.current_stl_path = None
        
        self.selected_point_index = None
        self.currently_highlighted_point_index = None
        self.selected_distance_index = None
        self.selected_angle_index = None

        self.highlight_color = (0, 1, 0) 
        self.default_color = (1, 0, 0) 
        self.blue_highlight_color = (0, 0, 1) 
        self.angle_highlight_color = (0.1, 0.9, 0.9) 
        self.status_colors = { 
            "defined": QtGui.QColor(0, 128, 0),
            "skipped": QtGui.QColor(128, 128, 128),
            "define_now": QtGui.QColor(255, 0, 0),
            "to_be_defined": QtCore.Qt.black,
        }
        self.status_text = {
            "defined": "",
            "skipped": "skipped",
            "define_now": "define now",
            "to_be_defined": "to be defined",
        }
        self.base_point_radius = 0.5 
        self.unsaved_changes = False

        self.distance_line_actors = []
        self.angle_line_actors = []

        self._init_data_structures()
        self._load_visuals_and_ui() 

        self.main_consistency_warning_labels = []
        self.main_consistency_check_state = "not_run"

        

    ## Passes transparency values interpreting slider position translating directly toward material opacity modifications executing viewer redraws dynamically.
    def update_model_opacity(self):
        if self.actor:
            opacity = 1.0 - (self.opacity_slider.value() / 100.0)
            self.actor.GetProperty().SetOpacity(opacity)
            self.iren.Render()

    ## Integrates external mesh assets via VTK file readers checking format validity flushing internal state rendering resulting shape directly updating session strings.
    def load_stl(self, filename):
        try:
            reader = vtk.vtkSTLReader()
            reader.SetFileName(filename)
            reader.Update()
            polydata = reader.GetOutput()
            if not polydata or polydata.GetNumberOfPoints() == 0:
                 QtWidgets.QMessageBox.critical(self, "Error", f"Invalid STL: {filename}")
                 return False

            self._remove_all_point_actors()

            if self.actor:
                self.ren.RemoveActor(self.actor)

            self.actor = vtk.vtkActor()
            self.actor.SetMapper(vtk.vtkPolyDataMapper())
            self.actor.GetMapper().SetInputConnection(reader.GetOutputPort())
            self.ren.AddActor(self.actor)
            
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(0)
            self.opacity_slider.blockSignals(False)
            self.actor.GetProperty().SetOpacity(1.0)
            
            self.current_stl_path = filename
            base_stl_name = os.path.basename(filename)
            self.filename_annotation.SetText(vtk.vtkCornerAnnotation.UpperRight, base_stl_name)

            self._init_data_structures() 
            
            self._load_visuals_and_ui()
            self._update_reference_points_status_overlay()

            self.ren.ResetCamera()
            self.iren.Render() 

            self.save_button.setEnabled(False) 
            self.unsaved_changes = False
            
            self.vtkWidget.setFocus()
            
            return True

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load STL: {e}\n{traceback.format_exc()}")
            self.current_stl_path = None
            self.actor = None
            if hasattr(self, 'filename_annotation'):
                self.filename_annotation.SetText(vtk.vtkCornerAnnotation.UpperRight, "")

            
            self._init_data_structures()

            self._load_visuals_and_ui()
            self._update_reference_points_status_overlay() 

            return False

    ## Activates floating right click menus delivering UI interaction nodes accessing background color alteration logic paths directly.
    def show_background_color_menu(self):
        menu = QtWidgets.QMenu(self)
        change_color_action = menu.addAction("Change background color…")
        change_color_action.triggered.connect(self.open_background_color_dialog)
        menu.exec(QtGui.QCursor.pos())

    ## Initiates standard operating system palette UI polling output color arrays pushing values directly overriding active VTK renderer background layers.
    def open_background_color_dialog(self):
        current_color_vtk = self.ren.GetBackground()
        initial_color = QtGui.QColor.fromRgbF(current_color_vtk[0], current_color_vtk[1], current_color_vtk[2])
        
        color = QtWidgets.QColorDialog.getColor(initial_color, self, "Select background color")

        if color.isValid():
            self.ren.SetBackground(color.redF(), color.greenF(), color.blueF())
            self.iren.Render()

    ## Initializes landmark, measurement, selection, and consistency data structures.
    def _init_data_structures(self):
        self.main_consistency_warning_labels = []
        self.main_consistency_check_state = "not_run"

        self.points = [
            ("to_be_defined", None, None)
            for _ in self.FIXED_LABELS_CLEFT
        ]

        self.all_labels_in_order = list(
            self.FIXED_LABELS_CLEFT
        )

        self.point_count = 0
        self.custom_point_counter = 0

        self.distance_definitions = list(
            self.DEFAULT_CLEFT_DIST_DEFS
        )
        self.distances = {}

        self.angle_definitions = list(
            self.DEFAULT_CLEFT_ANGLE_DEFS
        )
        self.angles = {}

        self.selected_point_index = None
        self.currently_highlighted_point_index = None
        self.selected_distance_index = None
        self.selected_angle_index = None
        
        
    ## Rebuilds landmark actors and refreshes the user interface from the current data.
    def _load_visuals_and_ui(self):
        point_states = []

        for i, label in enumerate(
                self.all_labels_in_order):

            if i < len(self.points):
                pos_or_status = self.points[i][0]
            else:
                pos_or_status = "to_be_defined"

            point_states.append(
                (pos_or_status, label)
            )

        if hasattr(self, "points"):
            for _, sphere_actor, text_follower in self.points:
                if sphere_actor:
                    self.ren.RemoveActor(
                        sphere_actor
                    )

                if text_follower:
                    self.ren.RemoveActor(
                        text_follower
                    )

        self.remove_distance_lines()
        self.remove_angle_lines()

        self.points = []

        scale_factor = (
            self.point_size_slider.value() / 50.0
        )

        for pos_or_status, label in point_states:

            if isinstance(pos_or_status, tuple):
                sphere_actor, text_follower = \
                    self._create_point_actors(
                        pos_or_status,
                        label,
                        self.default_color,
                        scale_factor
                    )

                self.points.append(
                    (
                        pos_or_status,
                        sphere_actor,
                        text_follower
                    )
                )

            else:
                self.points.append(
                    (
                        pos_or_status,
                        None,
                        None
                    )
                )

        self.update_info_panel()
        self.update_distances_panel()
        self.update_angles_panel()
        self.update_prompt()
        self._update_button_texts()

        self.reapply_measurement_highlight()

        self.iren.Render()
        
    ## Handles creation routing attaching basic spherical geometry marking coordinates alongside dynamic orienting text labels following primary rendering cameras natively.
    def _create_point_actors(self, world_pos, label, color, scale_factor):
        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(world_pos)
        sphere.SetRadius(self.base_point_radius * scale_factor)
        sphere.SetPhiResolution(15)
        sphere.SetThetaResolution(15) 
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())
        sphere_actor = vtk.vtkActor()
        sphere_actor.SetMapper(mapper)
        sphere_actor.GetProperty().SetColor(color)
        self.ren.AddActor(sphere_actor)

        text_source = vtk.vtkVectorText()
        text_source.SetText(str(label))
        text_mapper = vtk.vtkPolyDataMapper()
        text_mapper.SetInputConnection(text_source.GetOutputPort())
        text_follower = vtk.vtkFollower()
        text_follower.SetMapper(text_mapper)
        text_follower.SetCamera(self.ren.GetActiveCamera())
        text_offset = self.base_point_radius * scale_factor * 1.5 
        text_follower.SetPosition(world_pos[0], world_pos[1] + text_offset, world_pos[2])
        text_follower.GetProperty().SetColor(color)
        text_follower.SetScale(1.5, 1.5, 1.5) 
        self.ren.AddActor(text_follower)
        return sphere_actor, text_follower

    ## Syncs the displayed distance UI panel iterating list widgets writing specific strings applying backgrounds resolving highlights properly returning view anchors.
    def update_distances_panel(self):
        top_item_index = self.distances_panel.indexAt(QtCore.QPoint(5, 5)).row()

        self.distances_panel.clear()
        for index, definition in enumerate(self.distance_definitions):
            distance_val = self.distances.get(definition, "n/a")
            item_text = ""
            if len(definition) == 2:
                item_text = f"{str(definition[0])}-{str(definition[1])}: {distance_val}"
            elif len(definition) == 3: 
                item_text = f"{str(definition[0])}-{str(definition[1])}{str(definition[2])}: {distance_val}"

            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, index)
            self.distances_panel.addItem(item)

            if index == self.selected_distance_index:
                item.setBackground(QtGui.QColor(173, 216, 230))
            else:
                item.setBackground(QtGui.QColor(255, 255, 255))
        
        if top_item_index != -1 and top_item_index < self.distances_panel.count():
            item_to_scroll_to = self.distances_panel.item(top_item_index)
            self.distances_panel.scrollToItem(item_to_scroll_to, QtWidgets.QAbstractItemView.ScrollHint.PositionAtTop)

        self.remove_distance_button.setEnabled(self.selected_distance_index is not None)

    ## Syncs the displayed angle UI panel iterating sequence strings assigning corresponding index pointers tracking highlights restoring former visual boundaries correctly.
    def update_angles_panel(self):
        top_item_index = self.angles_panel.indexAt(QtCore.QPoint(5, 5)).row()

        self.angles_panel.clear()
        for index, triplet in enumerate(self.angle_definitions):
            angle_val = self.angles.get(triplet, "n/a")
            item_text = f"{str(triplet[0])}-{str(triplet[1])}-{str(triplet[2])}: {angle_val}"
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, index)
            self.angles_panel.addItem(item)

            if index == self.selected_angle_index:
                item.setBackground(QtGui.QColor(173, 216, 230))
            else:
                item.setBackground(QtGui.QColor(255, 255, 255))
        
        if top_item_index != -1 and top_item_index < self.angles_panel.count():
            item_to_scroll_to = self.angles_panel.item(top_item_index)
            self.angles_panel.scrollToItem(item_to_scroll_to, QtWidgets.QAbstractItemView.ScrollHint.PositionAtTop)

        self.remove_angle_button.setEnabled(self.selected_angle_index is not None)
        
    ## Loops active internal coordinate tracking assigning structural string outputs displaying color coded properties identifying defined undefined skipped status items cleanly.
    def update_info_panel(self):
        self.info_panel.clear()
        for i, (pos_or_status, _, _) in enumerate(self.points):
            label = self.all_labels_in_order[i] if i < len(self.all_labels_in_order) else f"Point {i+1}?" 

            if pos_or_status == "to_be_defined":
                if i == self.point_count: 
                    item_text = f"Point {label}: {self.status_text['define_now']}"
                    color = self.status_colors["define_now"]
                else:
                    item_text = f"Point {label}: {self.status_text['to_be_defined']}"
                    color = self.status_colors["to_be_defined"]
            elif pos_or_status == "skipped":
                item_text = f"Point {label}: {self.status_text['skipped']}"
                color = self.status_colors["skipped"]
            else: 
                item_text = f"Point {label}: ({pos_or_status[0]:.2f}, {pos_or_status[1]:.2f}, {pos_or_status[2]:.2f})"
                color = self.status_colors["defined"]

            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, i)
            item.setForeground(color)

            item.setBackground(QtGui.QColor(255, 255, 255)) 
            if i == self.selected_point_index: 
                item.setBackground(QtGui.QColor.fromRgbF(*self.highlight_color))
            elif i == self.currently_highlighted_point_index and isinstance(pos_or_status, tuple): 
                 item.setBackground(QtGui.QColor.fromRgbF(*self.blue_highlight_color))
            self.info_panel.addItem(item)

    ## Flushes rendering targets severing visual tracking nodes destroying associated markers resetting subset variables preventing graphical carryovers entirely.
    def _remove_all_point_actors(self):
        if hasattr(self, 'points'):
             for _, sphere_actor, text_follower in self.points:
                 if sphere_actor:
                     self.ren.RemoveActor(sphere_actor)
                 if text_follower:
                     self.ren.RemoveActor(text_follower)
        self.remove_distance_lines()
        self.remove_angle_lines()
        
        self.selected_point_index = None
        self.currently_highlighted_point_index = None
        self.selected_distance_index = None
        self.selected_angle_index = None

    ## Displays the CleftMeter user manual and application information.
    def show_about_dialog(self):
        body_html = """
        <div class="section">
            <p>
                <b>Authors:</b> Libor Borák, Petr Marcián, Olga Košková<br>
                <b>Version:</b> CleftMeter 2.0<br>
                <b>Copyright:</b> © 2025, 2026
            </p>
        </div>

        <div class="section">
            <h2>Purpose</h2>
            <p>
                <b>CleftMeter</b> is a tool for landmark-based measurement of 3D STL models
                of the cleft maxilla. It allows the user to define anatomical landmarks on
                a 3D surface and calculate distances and angles.
            </p>
            <p>
                The software is intended for structured geometric documentation of cleft
                morphology, project archiving, and clinical report generation.
            </p>
        </div>

        <div class="section">
            <h2>Main GUI Overview</h2>

            <h3>3D Workspace</h3>
            <p>
                The central 3D window displays the loaded STL model. Points, labels,
                highlighted measurements, and helper annotations are rendered directly
                on the model.
            </p>

            <h3>Points Panel</h3>
            <p>
                The <b>Points</b> panel lists predefined landmarks in the recommended
                marking order:
                I, P, P&prime;, L, L&prime;, C, C&prime;, Q, Q&prime;, T, and T&prime;.
                Each point can be <b>defined by 3D coordinates</b> using the
                <span class="kbd">D</span> key or <b>skipped</b> using the
                <span class="kbd">N</span> key.
                A defined point can subsequently be removed using the
                <span class="kbd">Delete</span> key; its status then changes to
                <b>skipped</b>.
                Both defined and skipped points can be redefined at any time using the
                <span class="kbd">E</span> key.
            </p>
            <p>
                The <b>Add</b> button creates additional custom points named
                X1, X2, X3, and so on.
                The <b>Remove Selected</b> button removes only selected custom points.
                Predefined anatomical points cannot be removed.
            </p>

            <h3>Landmark Placement Guide</h3>
            <p>
                A schematic guide showing the <b>typical arrangement of the predefined
                landmarks</b> is displayed in the lower-left corner of the 3D workspace.
                It is intended as a quick visual reference when assigning the points
                I, P, P&prime;, L, L&prime;, C, C&prime;, Q, Q&prime;, T, and T&prime;.
            </p>
            <p>
                The diagram is schematic and does not define an exact anatomical position
                for an individual model. Landmark placement must always be based on the
                anatomy of the evaluated maxilla.
            </p>
            <div class="note">
                <b>Side convention:</b> P/P&prime;, L/L&prime;, C/C&prime;,
                Q/Q&prime;, and T/T&prime; form paired landmarks. Keep the primed and
                unprimed labels consistently assigned to opposite sides throughout
                the model.
            </div>

            <h3>Distances Panel</h3>
            <p>
                The <b>Distances</b> panel displays predefined and user-defined
                measurements. CleftMeter supports both point-to-point distances and
                point-to-line distances. Selecting a distance highlights the
                corresponding geometry in the 3D view.
            </p>

            <h3>Angles Panel</h3>
            <p>
                The <b>Angles</b> panel displays predefined and user-defined angular
                measurements. An angle is defined by three points, where the middle
                point is the vertex. Selecting an angle highlights both arms of the
                angle in the 3D view.
            </p>

            <h3>Sliders</h3>
            <ul>
                <li>
                    <b>Point Size</b> changes the rendered size of point markers.
                </li>
                <li>
                    <b>Model Transparency</b> adjusts STL opacity to improve
                    landmark visibility.
                </li>
            </ul>

            <h3>Main Buttons</h3>
            <table>
                <tr>
                    <th>Button</th>
                    <th>Function</th>
                </tr>
                <tr>
                    <td><b>Open STL</b></td>
                    <td>Loads a 3D STL model.</td>
                </tr>
                <tr>
                    <td><b>Open Points</b></td>
                    <td>
                        Loads an existing CleftMeter project or legacy point file.
                    </td>
                </tr>
                <tr>
                    <td><b>Save</b></td>
                    <td>
                        Saves the project file and generates the clinical report.
                    </td>
                </tr>
                <tr>
                    <td><b>Clear</b></td>
                    <td>
                        Clears all points and measurements while keeping the STL
                        model loaded.
                    </td>
                </tr>
                <tr>
                    <td><b>Zoom To Fit</b></td>
                    <td>Resets the camera to show the whole model.</td>
                </tr>
                <tr>
                    <td><b>About</b></td>
                    <td>Displays this manual.</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>User Instructions</h2>

            <h3>Recommended Workflow</h3>
            <ol>
                <li>
                    Click <b>Open STL</b> and load the target 3D model.
                </li>

                <li>
                    Hold <span class="kbd">D</span> and click the STL surface
                    to define the currently requested landmark.
                </li>

                <li>
                    Continue defining the landmarks in the sequence shown in the
                    <b>Points</b> panel. Use the schematic landmark guide in the
                    lower-left corner of the 3D workspace as a visual reference
                    for their typical arrangement. Colored circles indicate
                    landmark status: <b>green</b> = defined/consistent,
                    <b>grey</b> = consistency not established, and
                    <b>red</b> = possible inconsistency.
                </li>

                <li>
                    Press <span class="kbd">N</span> to skip the currently
                    requested landmark if it cannot be identified.
                </li>

                <li>
                    Click a defined point in the <b>Points</b> list to highlight
                    it in blue. Click it again to remove the blue highlight.
                </li>

                <li>
                    To edit a point, hold <span class="kbd">E</span> and either
                    click the corresponding point in the <b>Points</b> list or
                    click directly on the existing point on the 3D model.
                    The selected point becomes the active editing target.
                </li>

                <li>
                    After selecting an editing target, you may release
                    <span class="kbd">E</span> and rotate or inspect the model.
                    To redefine the point, hold <span class="kbd">E</span>
                    again and click its new position on the STL surface.
                </li>

                <li>
                    Press <span class="kbd">Escape</span> to cancel a pending
                    point edit without changing its position.
                </li>

                <li>
                    To delete a defined point, hold
                    <span class="kbd">Delete</span> and either select it in the
                    <b>Points</b> list or click the point directly on the model.
                </li>

                <li>
                    After all predefined landmarks have been marked or skipped,
                    review the automatic landmark side-consistency check and
                    visually verify all landmark positions.
                </li>

                <li>
                    Review the calculated distances and angles in the left panel.
                </li>

                <li>
                    Click <b>Save</b> to store the project and generate the
                    clinical report.
                </li>
            </ol>

            <h3>Keyboard Shortcuts</h3>
            <table>
                <tr>
                    <th>Shortcut</th>
                    <th>Action</th>
                </tr>

                <tr>
                    <td><span class="kbd">D</span></td>
                    <td>
                        Hold D and click the STL surface to define the currently
                        requested point.
                    </td>
                </tr>

                <tr>
                    <td><span class="kbd">E</span></td>
                    <td>
                        Edit mode. Hold E and select an existing point either in
                        the Points list or directly on the model. The selected
                        point remains the editing target after E is released.
                        Hold E again and click a new surface position to redefine it.
                    </td>
                </tr>

                <tr>
                    <td><span class="kbd">Escape</span></td>
                    <td>
                        Cancels the currently selected editing target without
                        changing the point.
                    </td>
                </tr>

                <tr>
                    <td><span class="kbd">N</span></td>
                    <td>
                        Skips the currently requested point. N is ignored while
                        a point is selected for editing.
                    </td>
                </tr>

                <tr>
                    <td><span class="kbd">Delete</span></td>
                    <td>
                        Hold Delete and select a defined point either in the
                        Points list or directly on the model to delete it.
                    </td>
                </tr>

                <tr>
                    <td><span class="kbd">W</span></td>
                    <td>Switches the STL display to wireframe.</td>
                </tr>

                <tr>
                    <td><span class="kbd">S</span></td>
                    <td>Switches the STL display back to surface mode.</td>
                </tr>
            </table>

            <h3>Landmark Side-Consistency Check</h3>
            <p>
                When all predefined landmarks have been marked or skipped,
                CleftMeter automatically checks the side consistency of the paired
                landmarks <b>P/P&prime;, L/L&prime;, C/C&prime;, Q/Q&prime;,
                and T/T&prime;</b>. The check is designed to detect possible
                interchange of primed and unprimed landmarks or other obvious
                side inconsistencies.
            </p>

            <p>
                When the landmark set is completed for the first time, the result
                of the check is displayed to the user. If a landmark is subsequently
                edited while the dataset remains complete, the check is repeated
                automatically. In that case, no message is displayed if the side
                assignment remains consistent; a warning is shown only if a
                potential inconsistency is detected or if the available landmarks
                do not allow a reliable automatic check.
            </p>

            <div class="warning">
                <b>Important:</b> The consistency check evaluates the relative
                side assignment of paired landmarks only. It does <b>not</b>
                verify their anatomical correctness. Point I and user-defined
                X points are not included in the side-consistency test.
                Always visually verify all landmark positions before interpreting
                the measurements.
            </div>

            <div class="note">
                <b>Tip:</b> Right-click inside the 3D workspace to change the
                background color. This can improve landmark visibility during
                inspection or screenshots.
            </div>
        </div>

        <div class="section">
            <h2>Files, Working Directory, and Saving</h2>

            <h3>Working Directory Logic</h3>
            <p>
                CleftMeter does not use a separate internal workspace folder.
                The currently loaded STL file defines the active working location.
                Project and report files are saved next to the loaded STL file
                and use the same base filename.
            </p>

            <h3>Opening Files</h3>
            <ul>
                <li>
                    <b>Open STL</b> allows the user to select an STL model from
                    any accessible folder. After loading, the selected STL path
                    becomes the active file path for the session.
                </li>

                <li>
                    <b>Open Points</b> first looks in the same folder as the loaded
                    STL file for a matching <b>.cleftp</b> project file. If no
                    matching project file is found, it looks for a matching
                    legacy <b>.txt</b> file.
                </li>

                <li>
                    If neither matching file is found automatically, CleftMeter
                    opens a file dialog where the user can manually select a
                    <b>.cleftp</b> or <b>.txt</b> file.
                </li>
            </ul>

            <h3>Saved Output Files</h3>
            <p>
                Saving creates two complementary files in the folder of the
                loaded STL model:
            </p>

            <ul>
                <li>
                    <b>&lt;STL_base_name&gt;.cleftp</b> &ndash; CleftMeter project
                    file in JSON format. It stores landmark coordinates and status,
                    custom points, and distance and angle definitions.
                </li>

                <li>
                    <b>&lt;STL_base_name&gt;.txt</b> &ndash; clinical report with
                    tab-separated values for easier spreadsheet import.
                </li>
            </ul>

            <div class="note">
                <b>Practical example:</b> If the loaded model is
                <b>C:/Data/patient_01.stl</b>, then CleftMeter saves the project
                as <b>C:/Data/patient_01.cleftp</b> and the clinical report as
                <b>C:/Data/patient_01.txt</b> in the same
                <b>C:/Data/</b> folder.
            </div>

            <div class="warning">
                <b>Important:</b> Keep the STL file, project file, and report file
                together when archiving or transferring a case. The
                <b>.cleftp</b> file stores the landmark and measurement
                definitions, while the STL file provides the actual 3D geometry.
            </div>
        </div>

        <div class="section">
            <h2>Theoretical Background</h2>

            <h3>Landmark-Based 3D Measurement</h3>
            <p>
                All measurements are calculated from 3D landmark coordinates
                placed on the STL surface. Point-to-point distances are Euclidean
                distances between two landmarks. Point-to-line distances are
                perpendicular distances from a landmark to a line defined by two
                other landmarks.
            </p>

            <h3>Angles</h3>
            <p>
                Angular measurements are calculated from two vectors sharing a
                common vertex. The reported value is the angle between the vectors
                in degrees.
            </p>
        </div>

        <div class="section">
            <h2>References</h2>
            <ol>
                <li>
                    Seckel NG, van der Tweel I, Elema GA, Specken TF.
                    Landmark positioning on maxilla of cleft lip and palate infant--a reality?
                    <i>The Cleft Palate-Craniofacial Journal</i>. 1995;32(5):434-441.
                    doi:10.1597/1545-1569_1995_032_0434_lpomoc_2.3.co_2.
                    PMID:7578209.
                </li>

                <li>
                    Shaw WC.
                    Early orthopaedic treatment of unilateral cleft lip and palate.
                    <i>British Journal of Orthodontics</i>. 1978;5(3):119-132.
                    PMID:290384.
                </li>

                <li>
                    Košková O, Borák L, Urbanová W, Bryšová A, Nováková M,
                    Richtrová M, Streit L, Štourač P, Marcián P.
                    Comparison of silicone impressions with intraoral 3D scans in
                    newborns with cleft lip and palate.
                    <i>Journal of Prosthetic Dentistry</i>. 2025;134(1):275-282.
                    doi:10.1016/j.prosdent.2025.02.054.
                    PMID:40148199.
                </li>
            </ol>
        </div>
        """

        show_cleftmeter_about_dialog(
            self,
            "About CleftMeter v2.0",
            "CleftMeter v2.0",
            "User manual for 3D landmark definition, measurements, and saving.",
            body_html
        )
        
    ## Adjusts primary instruction element assigning relevant guiding messages based surrounding active tracking variables isolating completed contexts appropriately.
    def update_prompt(self):
        if self.selected_point_index is not None and \
           0 <= self.selected_point_index < len(self.points):
            point_status = self.points[self.selected_point_index][0]

            if point_status != "to_be_defined":
                point_label = self.all_labels_in_order[self.selected_point_index]

                if point_status == "skipped":
                    self.prompt_label.setText(
                        f"Editing skipped Point {point_label}: Hold E and click new position on model"
                    )
                else:
                    self.prompt_label.setText(
                        f"Editing Point {point_label}: Hold E and click new position on model"
                    )
                return

        if self.interactor_style.delete_mode:
            self.prompt_label.setText("Delete (select point in list)")
            return

        if self.interactor_style.e_pressed:
            self.prompt_label.setText("Edit (select point in list)")
            return

        if self.point_count < len(self.all_labels_in_order):
            next_label = self.all_labels_in_order[self.point_count]
            self.prompt_label.setText(f"Define point {next_label}")
        else:
            self.prompt_label.setText("All points marked.")

    ## Math engine translating definition pairs calculating pure euclidean metric outputs processing cross products deriving line variants mapping string outputs cleanly.
    def calculate_distances(self):
        self.distances = {}
        for definition in self.distance_definitions:
            if len(definition) == 2:  
                p1_label, p2_label = definition
                point1_index = self.get_index_by_label(p1_label)
                point2_index = self.get_index_by_label(p2_label)

                if point1_index is not None and point2_index is not None and \
                   point1_index < len(self.points) and point2_index < len(self.points):
                    pos1_data = self.points[point1_index][0]
                    pos2_data = self.points[point2_index][0]

                    if isinstance(pos1_data, tuple) and isinstance(pos2_data, tuple):
                        pos1 = np.array(pos1_data)
                        pos2 = np.array(pos2_data)
                        distance = np.linalg.norm(pos1 - pos2)
                        self.distances[definition] = f"{distance:.3f}"
                    else:
                        self.distances[definition] = "n/a"
                else:
                    self.distances[definition] = "n/a"

            elif len(definition) == 3:  
                p0_label, p1_label, p2_label = definition
                p0_idx = self.get_index_by_label(p0_label)
                p1_idx = self.get_index_by_label(p1_label)
                p2_idx = self.get_index_by_label(p2_label)
                
                if all(idx is not None and idx < len(self.points) for idx in [p0_idx, p1_idx, p2_idx]):
                    p0_data = self.points[p0_idx][0]
                    p1_data = self.points[p1_idx][0]
                    p2_data = self.points[p2_idx][0]
                    
                    if isinstance(p0_data, tuple) and isinstance(p1_data, tuple) and isinstance(p2_data, tuple):
                        p0 = np.array(p0_data)
                        p1 = np.array(p1_data)
                        p2 = np.array(p2_data)
                        line_vec = p2 - p1
                        line_norm = np.linalg.norm(line_vec)
                        if line_norm > 1e-9:
                            dist = np.linalg.norm(np.cross(line_vec, p1 - p0)) / line_norm
                            self.distances[definition] = f"{dist:.3f}"
                        else:
                            self.distances[definition] = "invalid" 
                    else:
                        self.distances[definition] = "n/a"
                else:
                    self.distances[definition] = "n/a"
        self.update_distances_panel()

    ## Vector algebra function deducing relative orientations forming dot products translating resulting angles strictly capturing standard degrees reliably handling anomalies seamlessly.
    def calculate_angles(self):
        self.angles = {} 
        for triplet in self.angle_definitions:
            idx1 = self.get_index_by_label(triplet[0])
            idx_v = self.get_index_by_label(triplet[1])
            idx2 = self.get_index_by_label(triplet[2])

            if idx1 is not None and idx_v is not None and idx2 is not None:
                if idx1 < len(self.points) and idx_v < len(self.points) and idx2 < len(self.points):
                    pos1_data = self.points[idx1][0]
                    posV_data = self.points[idx_v][0]
                    pos2_data = self.points[idx2][0]

                    if isinstance(pos1_data, tuple) and isinstance(posV_data, tuple) and isinstance(pos2_data, tuple):
                        p1 = np.array(pos1_data)
                        pV = np.array(posV_data)
                        p2 = np.array(pos2_data)
                        vec1 = p1 - pV
                        vec2 = p2 - pV
                        norm1 = np.linalg.norm(vec1)
                        norm2 = np.linalg.norm(vec2)
                        if norm1 > 1e-9 and norm2 > 1e-9: 
                            dot_product = np.dot(vec1, vec2)
                            cos_theta = np.clip(dot_product / (norm1 * norm2), -1.0, 1.0)
                            angle_rad = math.acos(cos_theta)
                            self.angles[triplet] = f"{math.degrees(angle_rad):.2f}"
                        else:
                            self.angles[triplet] = "invalid"
                    else:
                        self.angles[triplet] = "n/a"
                else:
                    self.angles[triplet] = "n/a"
            else:
                self.angles[triplet] = "n/a"
        self.update_angles_panel()

    ## Synchronized pipeline executing dependent calculation operations cascading updates systematically triggering complete metric evaluations concurrently.
    def calculate_all_measurements(self):
        self.calculate_distances()
        self.calculate_angles()

    ## Resolves array index matching internal lists passing specific character identifying components successfully masking runtime extraction errors natively.
    def get_index_by_label(self, label_to_find):
        try:
            return self.all_labels_in_order.index(str(label_to_find)) 
        except ValueError:
            return None

    ## Polling routine interpreting UI trackbar feeding spatial scaling properties scaling marker entities explicitly altering view proportions fluidly without coordinate modifications.
    def update_point_size(self):
        scale_factor = self.point_size_slider.value() / 50.0
        for i in range(len(self.points)):
             if i < len(self.points): 
                pos_data, sphere_actor, text_follower = self.points[i]
                if sphere_actor: 
                    sphere_source = sphere_actor.GetMapper().GetInputAlgorithm()
                    if isinstance(sphere_source, vtk.vtkSphereSource):
                        sphere_source.SetRadius(self.base_point_radius * scale_factor)
                        sphere_source.Modified()
                    if text_follower and isinstance(pos_data, tuple):
                        text_offset = self.base_point_radius * scale_factor * 1.5 
                        text_follower.SetPosition(pos_data[0], pos_data[1] + text_offset, pos_data[2])
        self.iren.Render() 

    ## Simple VTK instruction executing automated bounds tracking orienting camera positions maximizing model context immediately inside active window dimensions.
    def zoom_to_fit(self):
        self.ren.ResetCamera()
        self.iren.Render() 

    ## Defines the next pending landmark at the selected 3D position and updates measurements, UI state, and landmark consistency.
    def add_point(self, world_pos):
        scale_factor = self.point_size_slider.value() / 50.0
        target_index_for_new_point = -1
        label_for_new_point = ""


        next_idx = self.find_next_undefined_index()

        if next_idx is None:
            self.prompt_label.setText(
                "All points marked."
            )
            return

        target_index_for_new_point = next_idx
        label_for_new_point = (
            self.all_labels_in_order[
                target_index_for_new_point
            ]
        )


        if target_index_for_new_point == -1:
            return

        if not (
            0 <= target_index_for_new_point <
            len(self.points)
        ):
            print(
                f"Error: Calculated target index "
                f"{target_index_for_new_point} "
                f"out of bounds for points list "
                f"(len {len(self.points)})"
            )
            return

        _, old_sphere_actor, old_text_follower = \
            self.points[target_index_for_new_point]

        if old_sphere_actor:
            self.ren.RemoveActor(
                old_sphere_actor
            )

        if old_text_follower:
            self.ren.RemoveActor(
                old_text_follower
            )

        sphere_actor, text_follower = \
            self._create_point_actors(
                world_pos,
                label_for_new_point,
                self.default_color,
                scale_factor
            )

        self.points[
            target_index_for_new_point
        ] = (
            world_pos,
            sphere_actor,
            text_follower
        )

        self.find_next_undefined()
        self.update_info_panel()
        self.iren.Render()

        self._handle_geometry_modification()

        self.calculate_all_measurements()
        self.update_prompt()

        self.reapply_measurement_highlight()

        self._schedule_landmark_side_consistency_check(
            show_dialog=(
                label_for_new_point == "T'"
            )
        )
        
    ## Repositions the selected landmark and updates its visualization, measurements, and landmark consistency state.
    def redefine_point(self, world_pos):
        if self.selected_point_index is None:
            return

        index = self.selected_point_index

        if not (0 <= index < len(self.points)):
            return


        old_pos_data, old_sphere_actor, \
            old_text_follower = self.points[index]

        label = self.all_labels_in_order[index]
        scale_factor = (
            self.point_size_slider.value() / 50.0
        )

        if old_sphere_actor:
            self.ren.RemoveActor(
                old_sphere_actor
            )

        if old_text_follower:
            self.ren.RemoveActor(
                old_text_follower
            )

        sphere_actor, text_follower = \
            self._create_point_actors(
                world_pos,
                label,
                self.default_color,
                scale_factor
            )

        self.points[index] = (
            world_pos,
            sphere_actor,
            text_follower
        )

        self.interactor_style.e_pressed = False
        self.unhighlight_selected_point()
        self.find_next_undefined()
        self.update_info_panel()
        self.update_prompt()
        self.iren.Render()

        self._handle_geometry_modification()

        self.calculate_all_measurements()

        self.reapply_measurement_highlight()

        self.vtkWidget.setFocus()

        self._schedule_landmark_side_consistency_check(
            show_dialog=False
        )
        
    ## Assigns skipped placeholder identifiers passing indexing targets advancing workflow contexts correctly mapping logic.
    def defer_point(self):
        next_index_to_define = \
            self.find_next_undefined_index()

        if next_index_to_define is None:
            return

        target_index_for_skip = -1


        if next_index_to_define is not None:
            target_index_for_skip = \
                next_index_to_define


        if target_index_for_skip != -1 and \
           target_index_for_skip < len(self.points):

            pos_data, sphere_actor, \
                text_follower = \
                self.points[target_index_for_skip]

            if sphere_actor:
                self.ren.RemoveActor(
                    sphere_actor
                )

            if text_follower:
                self.ren.RemoveActor(
                    text_follower
                )

            self.points[
                target_index_for_skip
            ] = (
                "skipped",
                None,
                None
            )

            self.find_next_undefined()
            self.update_info_panel()
            self.update_prompt()

            self._handle_geometry_modification()

            self.calculate_all_measurements()

            self.reapply_measurement_highlight()
            self.iren.Render()

            self._schedule_landmark_side_consistency_check(
                show_dialog=False
            )
            
            
        
    ## Handles explicit deletion operations validating targeted index structures clearing rendering memory reverting properties cleanly executing system state refreshes correctly.
    def delete_point(self, index_to_delete): 
        if index_to_delete is None or not (0 <= index_to_delete < len(self.points)):
             return


        
        if self.selected_point_index == index_to_delete:
            self.unhighlight_selected_point() 
        if self.currently_highlighted_point_index == index_to_delete:
            self.unhighlight_blue_point()

        _, sphere_actor, text_follower = self.points[index_to_delete]
        if sphere_actor:
            self.ren.RemoveActor(sphere_actor)
        if text_follower:
            self.ren.RemoveActor(text_follower)

        self.points[index_to_delete] = ("skipped", None, None) 

        self.update_info_panel()
        
        self._handle_geometry_modification()
        
        self.calculate_all_measurements()

        self.find_next_undefined() 
        self.update_prompt()
        self.reapply_measurement_highlight()
        self.iren.Render()

        self._schedule_landmark_side_consistency_check(
            show_dialog=False
        )


    ## Performs an automatic side-consistency check of paired cleft landmarks, detecting possible primed/unprimed side assignment errors while accounting for skipped points.
    def _run_landmark_side_consistency_check(self,show_dialog=False):      
        self.main_consistency_warning_labels = []


        for label in self.FIXED_LABELS_CLEFT:
            idx = self.get_index_by_label(label)

            if idx is None or \
               not (0 <= idx < len(self.points)) or \
               self.points[idx][0] == "to_be_defined":

                self.main_consistency_check_state = "not_run"
                self._update_reference_points_status_overlay()
                return

        paired_labels = [
            ("P", "P'"),
            ("L", "L'"),
            ("C", "C'"),
            ("Q", "Q'"),
            ("T", "T'")
        ]

        def get_defined_position(label):
            idx = self.get_index_by_label(label)
            if idx is None or not (0 <= idx < len(self.points)):
                return None

            pos_data = self.points[idx][0]
            if isinstance(pos_data, tuple) and len(pos_data) == 3:
                return np.asarray(pos_data, dtype=float)

            return None

        positions = {}

        for unprimed, primed in paired_labels:
            for label in (unprimed, primed):
                pos = get_defined_position(label)
                if pos is not None:
                    positions[label] = pos

        defined_unprimed = [
            positions[unprimed]
            for unprimed, _ in paired_labels
            if unprimed in positions
        ]

        defined_primed = [
            positions[primed]
            for _, primed in paired_labels
            if primed in positions
        ]

        available_count = len(positions)

        if available_count < 3 or not defined_unprimed or not defined_primed:
            self.main_consistency_check_state = "indeterminate"
            self._update_reference_points_status_overlay()

            if show_dialog:

                QtWidgets.QMessageBox.warning(
                    self,
                    "Landmark Consistency Check",
                    "The automatic side-consistency check could not be performed reliably.\n\n"
                )
            return

        valid_pair_vectors = []
        valid_pair_midpoints = []
        valid_pair_widths = []
        degenerate_pairs = []

        for unprimed, primed in paired_labels:
            if unprimed in positions and primed in positions:
                p_unprimed = positions[unprimed]
                p_primed = positions[primed]

                pair_vector = p_primed - p_unprimed
                pair_width = float(np.linalg.norm(pair_vector))

                if pair_width > 1e-9:
                    valid_pair_vectors.append(pair_vector)
                    valid_pair_midpoints.append(
                        (p_unprimed + p_primed) / 2.0
                    )
                    valid_pair_widths.append(pair_width)
                else:
                    degenerate_pairs.append((unprimed, primed))

        limited_reference = False

        if valid_pair_vectors:
            unit_vectors = np.array([
                vector / np.linalg.norm(vector)
                for vector in valid_pair_vectors
            ])

            orientation_matrix = np.zeros((3, 3), dtype=float)

            for vector in unit_vectors:
                orientation_matrix += np.outer(vector, vector)

            eigenvalues, eigenvectors = np.linalg.eigh(
                orientation_matrix
            )

            lateral_axis = eigenvectors[
                :, int(np.argmax(eigenvalues))
            ]

            lateral_axis = (
                lateral_axis / np.linalg.norm(lateral_axis)
            )

            orientation_votes = [
                float(np.dot(vector, lateral_axis))
                for vector in valid_pair_vectors
            ]

            positive_votes = sum(
                value > 1e-9
                for value in orientation_votes
            )

            negative_votes = sum(
                value < -1e-9
                for value in orientation_votes
            )

            if negative_votes > positive_votes:
                lateral_axis = -lateral_axis

            elif positive_votes == negative_votes:
                unprimed_centroid = np.mean(
                    np.array(defined_unprimed),
                    axis=0
                )

                primed_centroid = np.mean(
                    np.array(defined_primed),
                    axis=0
                )

                centroid_direction = float(
                    np.dot(
                        primed_centroid - unprimed_centroid,
                        lateral_axis
                    )
                )

                if centroid_direction < -1e-9:
                    lateral_axis = -lateral_axis

                elif abs(centroid_direction) <= 1e-9:
                    self.main_consistency_check_state = "indeterminate"
                    self._update_reference_points_status_overlay()

                    if show_dialog:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "Landmark Consistency Check",
                            "The automatic side-consistency check could not determine reliably which "
                            "side corresponds to primed and unprimed landmarks.\n\n"
                        )

                    return

            plane_offset = float(
                np.median([
                    np.dot(midpoint, lateral_axis)
                    for midpoint in valid_pair_midpoints
                ])
            )

            reference_scale = float(
                np.median(valid_pair_widths)
            )

            limited_reference = (
                len(valid_pair_vectors) == 1
            )

        else:
            unprimed_centroid = np.mean(
                np.array(defined_unprimed),
                axis=0
            )

            primed_centroid = np.mean(
                np.array(defined_primed),
                axis=0
            )

            centroid_vector = (
                primed_centroid - unprimed_centroid
            )

            reference_scale = float(
                np.linalg.norm(centroid_vector)
            )

            if reference_scale <= 1e-9:
                self.main_consistency_check_state = "indeterminate"
                self._update_reference_points_status_overlay()

                if show_dialog:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Landmark Consistency Check",
                        "The automatic side-consistency check could not establish a reliable separation "
                        "between the primed and unprimed landmark groups.\n\n"
                    )

                return

            lateral_axis = (
                centroid_vector / reference_scale
            )

            plane_center = (
                unprimed_centroid + primed_centroid
            ) / 2.0

            plane_offset = float(
                np.dot(plane_center, lateral_axis)
            )

            limited_reference = True

        tolerance = max(
            reference_scale * 0.05,
            1e-6
        )

        def signed_distance(label):
            return float(
                np.dot(
                    positions[label],
                    lateral_axis
                ) - plane_offset
            )

        def side_of_plane(distance):
            if distance > tolerance:
                return 1

            if distance < -tolerance:
                return -1

            return 0

        issues = []
        affected_labels = set()

        for unprimed, primed in degenerate_pairs:
            issues.append(
                f"{unprimed}/{primed}: the two points are at the same or nearly the same position."
            )
            affected_labels.update([unprimed, primed])

        for unprimed, primed in paired_labels:
            unprimed_defined = unprimed in positions
            primed_defined = primed in positions

            if unprimed_defined and primed_defined:
                if (unprimed, primed) in degenerate_pairs:
                    continue

                d_unprimed = signed_distance(unprimed)
                d_primed = signed_distance(primed)

                side_unprimed = side_of_plane(
                    d_unprimed
                )

                side_primed = side_of_plane(
                    d_primed
                )

                near_midline = []

                if side_unprimed == 0:
                    near_midline.append(unprimed)

                if side_primed == 0:
                    near_midline.append(primed)

                if near_midline:
                    issues.append(
                        f"{'/'.join(near_midline)}: unusually close to the estimated midline."
                    )
                    affected_labels.update(near_midline)

                elif side_unprimed == 1 and \
                     side_primed == -1:

                    issues.append(
                        f"{unprimed}/{primed}: the pair appears to be reversed."
                    )
                    affected_labels.update([unprimed, primed])

                elif side_unprimed == side_primed:
                    issues.append(
                        f"{unprimed}/{primed}: both points lie on the same side of the estimated midline."
                    )
                    affected_labels.update([unprimed, primed])

            elif unprimed_defined:
                d_unprimed = signed_distance(
                    unprimed
                )

                side_unprimed = side_of_plane(
                    d_unprimed
                )

                if side_unprimed == 0:
                    issues.append(
                        f"{unprimed}: unusually close to the estimated midline; {primed} is skipped."
                    )
                    affected_labels.add(unprimed)

                elif side_unprimed == 1:
                    issues.append(
                        f"{unprimed}: lies on the side associated with primed landmarks; {primed} is skipped."
                    )
                    affected_labels.add(unprimed)

            elif primed_defined:
                d_primed = signed_distance(
                    primed
                )

                side_primed = side_of_plane(
                    d_primed
                )

                if side_primed == 0:
                    issues.append(
                        f"{primed}: unusually close to the estimated midline; {unprimed} is skipped."
                    )
                    affected_labels.add(primed)

                elif side_primed == -1:
                    issues.append(
                        f"{primed}: lies on the side associated with unprimed landmarks; {unprimed} is skipped."
                    )
                    affected_labels.add(primed)

        self.main_consistency_warning_labels = [
            label
            for label in self.FIXED_LABELS_CLEFT
            if label in affected_labels
        ]

        self.main_consistency_check_state = "completed"
        self._update_reference_points_status_overlay()

        if issues and show_dialog:
            issue_text = "\n".join(
                f"• {issue}"
                for issue in issues
            )

            reference_note = ""

            if limited_reference:
                reference_note = (
                    "\n\nThe geometric reference is based on limited available data, "
                    "so the result should be interpreted with additional caution."
                )

            QtWidgets.QMessageBox.warning(
                self,
                "Landmark Consistency Check",
                "Potential landmark-side inconsistency was detected:\n\n"
                f"{issue_text}{reference_note}\n\n"
            )
            

    ## Schedules the landmark side-consistency check after mouse interaction has fully finished and restores normal VTK interaction state before showing the dialog.
    def _schedule_landmark_side_consistency_check(
            self,
            show_dialog=False):

        def run_when_mouse_released():
            if QtWidgets.QApplication.mouseButtons() != \
                    QtCore.Qt.NoButton:

                QtCore.QTimer.singleShot(
                    25,
                    run_when_mouse_released
                )
                return

            # Reset temporary point-definition/edit/delete modes.
            # A modal consistency dialog may otherwise intercept
            # the corresponding key-release event.
            self.interactor_style.d_pressed = False
            self.interactor_style.e_pressed = False
            self.interactor_style.delete_mode = False
            self.interactor_style.last_picked_point = None

            # Ensure that VTK is not left in an unfinished
            # rotate/pan/zoom interaction state.
            if self.interactor_style.GetState() != 0:
                self.interactor_style.StopState()

            self.update_prompt()
            self.update_info_panel()

            self._run_landmark_side_consistency_check(
                show_dialog=show_dialog
            )

            # Return keyboard/mouse focus to the 3D workspace
            # after the modal QMessageBox is closed.
            self.vtkWidget.setFocus()
            self.iren.Render()

        QtCore.QTimer.singleShot(
            0,
            run_when_mouse_released
        )

        
    ## Scans internal definitions returning numeric identifiers representing exact array slots missing numerical associations actively.
    def find_next_undefined_index(self):
        for i, (status, _, _) in enumerate(self.points):
            if status == "to_be_defined":
                return i
        return None

    ## Overrides current target cursor executing index scanning resolving prompt markers ensuring UI accurately displays next expected user action.
    def find_next_undefined(self):
        next_idx = self.find_next_undefined_index()
        if next_idx is not None:
            self.point_count = next_idx
        else:
            self.point_count = len(self.points) 

    ## Clears all landmarks and measurements and restores the default project state.
    def clear_points(self):
        for _, sphere_actor, text_follower in self.points:
            if sphere_actor:
                self.ren.RemoveActor(
                    sphere_actor
                )

            if text_follower:
                self.ren.RemoveActor(
                    text_follower
                )

        self.unhighlight_all()

        self.main_consistency_warning_labels = []
        self.main_consistency_check_state = "not_run"

        self.points = [
            ("to_be_defined", None, None)
            for _ in self.FIXED_LABELS_CLEFT
        ]

        self.all_labels_in_order = list(
            self.FIXED_LABELS_CLEFT
        )

        self.point_count = 0
        self.custom_point_counter = 0

        self.distance_definitions = list(
            self.DEFAULT_CLEFT_DIST_DEFS
        )
        self.distances = {}

        self.angle_definitions = list(
            self.DEFAULT_CLEFT_ANGLE_DEFS
        )
        self.angles = {}

        self.selected_point_index = None
        self.currently_highlighted_point_index = None
        self.selected_distance_index = None
        self.selected_angle_index = None

        self._load_visuals_and_ui()
        self._update_reference_points_status_overlay()

        self.save_button.setEnabled(False)
        self.unsaved_changes = False

        self.iren.Render()

        if not self.current_stl_path:
            self.filename_annotation.SetText(
                vtk.vtkCornerAnnotation.UpperRight,
                ""
            )

    ## Recovers active tracking properties executing color updates explicitly rendering measurement lines maintaining visual persistence correctly across global layout transitions.
    def reapply_measurement_highlight(self):
        dist_idx = self.selected_distance_index 
        angle_idx = self.selected_angle_index 
        
        temp_dist_idx = dist_idx
        temp_angle_idx = angle_idx

        if dist_idx is not None:
            self.unhighlight_distance()
        if angle_idx is not None:
            self.unhighlight_angle()   

        if temp_dist_idx is not None:
            if 0 <= temp_dist_idx < len(self.distance_definitions):
                 self.highlight_distance(temp_dist_idx)
        elif temp_angle_idx is not None:
             if 0 <= temp_angle_idx < len(self.angle_definitions):
                 self.highlight_angle(temp_angle_idx)

    ## Polling mechanism translating UI list click signals navigating internal states distinguishing edit sequences deletion commands generic highlighting triggering downstream visibility procedures systematically.
    def on_point_selected(self, item):
        index = item.data(QtCore.Qt.UserRole)
        if index is None or not (0 <= index < len(self.points)):
            return

        self.unhighlight_distance()
        self.unhighlight_angle()

        if self.selected_point_index is not None:
            self.update_prompt()
            self.update_info_panel()
            self.vtkWidget.setFocus()
            return


        if self.interactor_style.e_pressed:
            current_point_status = self.points[index][0]

            if current_point_status != "to_be_defined":
                self.highlight_selected_point(index)
            else:
                self.unhighlight_selected_point()

            self.update_prompt()


        elif self.interactor_style.delete_mode:
            if isinstance(self.points[index][0], tuple):
                self.delete_point(index)
                self.interactor_style.delete_mode = False
                self.update_prompt()
            else:
                QtWidgets.QToolTip.showText(
                    QtGui.QCursor.pos(),
                    "Cannot delete - point not defined.",
                    self.vtkWidget
                )
                self.update_prompt()


        else:
            if isinstance(self.points[index][0], tuple):
                self.toggle_blue_highlight(index)
            else:
                self.unhighlight_blue_point()

            is_custom_selected = False
            if self.currently_highlighted_point_index is not None:
                label = self.all_labels_in_order[self.currently_highlighted_point_index]
                if label.upper().startswith('X'):
                    is_custom_selected = True

            self.remove_custom_point_button.setEnabled(is_custom_selected)

        self.update_info_panel()
        self.vtkWidget.setFocus()
        
    ## Basic branching logic tracking current highlighting determining exact off or on toggle sequences targeting specific active nodes cleanly.
    def toggle_blue_highlight(self, index):
        if self.currently_highlighted_point_index == index:
            self.unhighlight_blue_point()
        else:
            self.highlight_blue_point(index)

    ## Wipes surrounding tracking colors selecting single array item applying alternate blue properties redrawing scene capturing user focus directly.
    def highlight_blue_point(self, index):
        if index is None or not (0 <= index < len(self.points)) or \
           not isinstance(self.points[index][0], tuple): 
            self.unhighlight_blue_point()
            return

        self.unhighlight_all() 
        self.currently_highlighted_point_index = index
        _, sphere_actor, text_follower = self.points[index]
        if sphere_actor:
            sphere_actor.GetProperty().SetColor(self.blue_highlight_color)
        if text_follower:
            text_follower.GetProperty().SetColor(self.blue_highlight_color)
        self.iren.Render() 
        self.update_info_panel()


    ## Disables explicit tracking removing modified blue rendering variables reverting elements default colors returning visual states normalized properly.
    def unhighlight_blue_point(self):
        if self.currently_highlighted_point_index is not None:
            idx = self.currently_highlighted_point_index
            self.currently_highlighted_point_index = None
            if 0 <= idx < len(self.points) and isinstance(self.points[idx][0], tuple): 
                 _, sphere_actor, text_follower = self.points[idx]
                 if sphere_actor:
                     sphere_actor.GetProperty().SetColor(self.default_color)
                 if text_follower:
                     text_follower.GetProperty().SetColor(self.default_color)
                 self.iren.Render() 
            self.update_info_panel()


    ## Isolates specific object targets extracting rendering layers assigning unique green edit colorizations stripping competing attributes signaling strict editing readiness implicitly.
    def highlight_selected_point(self, index): 
        if index is None or not (0 <= index < len(self.points)) or \
           self.points[index][0] == "to_be_defined": 
            self.unhighlight_selected_point()
            return

        self.unhighlight_all()
        self.selected_point_index = index
        
        point_status, sphere_actor, text_follower = self.points[index]
        if point_status != "skipped": 
            if sphere_actor:
                sphere_actor.GetProperty().SetColor(self.highlight_color)
            if text_follower:
                text_follower.GetProperty().SetColor(self.highlight_color)
            self.iren.Render() 
        self.update_info_panel()


    ## Dismantles editing color attributes targeting selected memory indices reverting VTK appearances standardizations clearing operational focus explicitly.
    def unhighlight_selected_point(self): 
        if self.selected_point_index is not None:
            idx = self.selected_point_index
            self.selected_point_index = None
            if 0 <= idx < len(self.points):
                point_status, sphere_actor, text_follower = self.points[idx]
                if isinstance(point_status, tuple): 
                    if sphere_actor:
                        sphere_actor.GetProperty().SetColor(self.default_color)
                    if text_follower:
                        text_follower.GetProperty().SetColor(self.default_color)
                    self.iren.Render() 
            self.update_info_panel()


    ## Routes user list interactions executing underlying line coloring toggles driving corresponding spatial graphics representations seamlessly.
    def on_distance_selected(self, item):
        index = item.data(QtCore.Qt.UserRole)
        if index is None: return
        self.toggle_distance_highlight(index)

    ## Wraps execution tracking determining current matching items executing background shading toggles identifying measurement relationships visually across interfaces.
    def toggle_distance_highlight(self, index):
        if self.selected_distance_index is not None and 0 <= self.selected_distance_index < self.distances_panel.count():
            old_item = self.distances_panel.item(self.selected_distance_index)
            if old_item:
                old_item.setBackground(QtGui.QColor(255, 255, 255))

        if self.selected_distance_index == index:
            self.unhighlight_distance() 
        else:
            self.highlight_distance(index)
            if self.selected_distance_index is not None and 0 <= self.selected_distance_index < self.distances_panel.count():
                new_item = self.distances_panel.item(self.selected_distance_index)
                if new_item:
                    new_item.setBackground(QtGui.QColor(173, 216, 230))


    ## Dissects definitions matching coordinates building explicit 3D visual segments marking linear relationships highlighting associated endpoint actors accurately natively.
    def highlight_distance(self, index):
        if index is None or not (0 <= index < len(self.distance_definitions)):
            self.unhighlight_distance()
            return
        
        self.unhighlight_all()
        self.selected_distance_index = index
        
        definition = self.distance_definitions[index]
        
        if len(definition) == 2: 
            idx1 = self.get_index_by_label(definition[0])
            idx2 = self.get_index_by_label(definition[1])
            pos1, pos2 = self.get_pos_by_index(idx1), self.get_pos_by_index(idx2)
            if pos1 and pos2:
                self.highlight_points([idx1, idx2])
                self.draw_distance_lines(solid_lines=[(pos1, pos2)])
        
        elif len(definition) == 3: 
            p0_idx, p1_idx, p2_idx = [self.get_index_by_label(lbl) for lbl in definition]
            p0, p1, p2 = self.get_pos_by_index(p0_idx), self.get_pos_by_index(p1_idx), self.get_pos_by_index(p2_idx)
            
            if p0 and p1 and p2:
                self.highlight_points([p0_idx, p1_idx, p2_idx])
                p0, p1, p2 = np.array(p0), np.array(p1), np.array(p2)
                line_vec = p2 - p1
                line_norm_sq = np.dot(line_vec, line_vec)
                
                if line_norm_sq > 1e-9:
                    t = np.dot(p0 - p1, line_vec) / line_norm_sq
                    closest_point = p1 + t * line_vec
                    
                    points_on_line = [p1, p2, closest_point]
                    t_vals = [np.dot(pt - p1, line_vec) / line_norm_sq for pt in points_on_line]
                    
                    min_idx = np.argmin(t_vals)
                    max_idx = np.argmax(t_vals)
                    
                    axis_start = points_on_line[min_idx]
                    axis_end = points_on_line[max_idx]

                    self.draw_distance_lines(solid_lines=[(p0, closest_point)], dashed_lines=[(axis_start, axis_end)])
        
        self.remove_distance_button.setEnabled(True)
        if self.distance_line_actors:
            self.iren.Render()

    ## Scans target tuples determining legitimate values returning absolute dimensional locations preventing invalid assignment calls explicitly.
    def get_pos_by_index(self, index):
        if index is not None and 0 <= index < len(self.points) and isinstance(self.points[index][0], tuple):
            return self.points[index][0]
        return None

    ## Mutates VTK mapping applying unified identifying colors resolving grouping mechanisms tracking active geometry visually.
    def highlight_points(self, indices):
        for idx in indices:
            if idx is not None and 0 <= idx < len(self.points) and isinstance(self.points[idx][0], tuple):
                _, sphere_actor, text_follower = self.points[idx]
                if sphere_actor:
                    sphere_actor.GetProperty().SetColor(self.blue_highlight_color)
                if text_follower:
                    text_follower.GetProperty().SetColor(self.blue_highlight_color)

    ## Discards tracked lines stripping element coloration restoring standardized layouts avoiding cross tracking pollution consistently.
    def unhighlight_distance(self):
        if self.selected_distance_index is not None:
             sdi = self.selected_distance_index 
             self.selected_distance_index = None 
             self.remove_distance_button.setEnabled(False)
             self.remove_distance_lines() 
             
             colors_reset = False
             try:
                 if 0 <= sdi < len(self.distance_definitions):
                     definition = self.distance_definitions[sdi]
                     indices_to_reset = [self.get_index_by_label(lbl) for lbl in definition]
                     for current_idx in indices_to_reset:
                         if current_idx is not None and 0 <= current_idx < len(self.points) and \
                            isinstance(self.points[current_idx][0], tuple) and \
                            current_idx != self.selected_point_index and \
                            current_idx != self.currently_highlighted_point_index: 
                              _, sphere_actor, text_follower = self.points[current_idx]
                              if sphere_actor and sphere_actor.GetProperty().GetColor() != self.default_color: 
                                  sphere_actor.GetProperty().SetColor(self.default_color)
                                  colors_reset = True
                              if text_follower and text_follower.GetProperty().GetColor() != self.default_color: 
                                  text_follower.GetProperty().SetColor(self.default_color)
                                  colors_reset = True
             except IndexError: pass
             
             if colors_reset: 
                 self.iren.Render() 

    ## Constructs visual VTK source paths generating discrete segmented polydata creating complex multi variant visual line groupings representing mathematical geometries internally.
    def draw_distance_lines(self, solid_lines=[], dashed_lines=[]):
        self.remove_distance_lines()
        
        for p1, p2 in solid_lines:
            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(p1)
            line_source.SetPoint2(p2)
            line_source.Update()
            
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(line_source.GetOutputPort())
            
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(self.blue_highlight_color)
            prop.SetLineWidth(3)
            
            self.ren.AddActor(actor)
            self.distance_line_actors.append(actor)

        for p1_coords, p2_coords in dashed_lines:
            p1 = np.array(p1_coords)
            p2 = np.array(p2_coords)
            
            points = vtk.vtkPoints()
            lines = vtk.vtkCellArray()
            
            length = np.linalg.norm(p2 - p1)
            if length < 1e-6:
                continue 
                
            direction = (p2 - p1) / length
            
            num_segments = 10 
            dash_ratio = 0.6  
            
            segment_length = length / num_segments
            dash_length = segment_length * dash_ratio
            
            point_id_counter = 0
            current_pos = np.copy(p1)
            
            for _ in range(num_segments):
                start_point = current_pos
                end_point = start_point + direction * dash_length
                
                if np.linalg.norm(end_point - p1) > length:
                    end_point = p2

                points.InsertNextPoint(start_point)
                points.InsertNextPoint(end_point)
                
                line = vtk.vtkLine()
                line.GetPointIds().SetId(0, point_id_counter)
                line.GetPointIds().SetId(1, point_id_counter + 1)
                lines.InsertNextCell(line)
                
                point_id_counter += 2
                current_pos = start_point + direction * segment_length
                
                if np.linalg.norm(current_pos - p1) >= length:
                    break

            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            polydata.SetLines(lines)
            
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(polydata)
            
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(self.blue_highlight_color)
            prop.SetLineWidth(2)
            
            self.ren.AddActor(actor)
            self.distance_line_actors.append(actor)

    ## Scrubs spatial rendering environments deleting active measurement mapping lines preserving rendering performance preventing graphical duplicates explicitly.
    def remove_distance_lines(self):
        if self.distance_line_actors:
            for actor in self.distance_line_actors:
                self.ren.RemoveActor(actor)
            self.distance_line_actors = []

    ## Directs user interaction events triggering line highlighting toggles corresponding to active angular selection metrics inside UI boundaries.
    def on_angle_selected(self, item):
        index = item.data(QtCore.Qt.UserRole)
        if index is None: return
        self.toggle_angle_highlight(index)

    ## Modulates panel background hues processing toggles driving active object references identifying angle properties dynamically distinguishing selected elements actively.
    def toggle_angle_highlight(self, index):
        if self.selected_angle_index is not None and 0 <= self.selected_angle_index < self.angles_panel.count():
            old_item = self.angles_panel.item(self.selected_angle_index)
            if old_item:
                old_item.setBackground(QtGui.QColor(255, 255, 255))

        if self.selected_angle_index == index:
            self.unhighlight_angle()
        else:
            self.highlight_angle(index)
            if self.selected_angle_index is not None and 0 <= self.selected_angle_index < self.angles_panel.count():
                new_item = self.angles_panel.item(self.selected_angle_index)
                if new_item:
                    new_item.setBackground(QtGui.QColor(173, 216, 230))


    ## Processes string definitions gathering underlying coordinates generating explicit line meshes bridging components highlighting relative spatial orientations physically within viewing context.
    def highlight_angle(self, index):
        if index is None or not (0 <= index < len(self.angle_definitions)):
             self.unhighlight_angle()
             return

        self.unhighlight_all()
        self.selected_angle_index = index
        
        triplet = self.angle_definitions[index]
        idx1 = self.get_index_by_label(triplet[0])
        idxV = self.get_index_by_label(triplet[1])
        idx2 = self.get_index_by_label(triplet[2])
        pos1, posV, pos2 = None, None, None
        
        points_colored = False
        for current_idx in [idx1, idxV, idx2]:
            if current_idx is not None and 0 <= current_idx < len(self.points) and \
               isinstance(self.points[current_idx][0], tuple): 
                _, sphere_actor, text_follower = self.points[current_idx]
                if sphere_actor: 
                    sphere_actor.GetProperty().SetColor(self.blue_highlight_color)
                    points_colored = True
                if text_follower:
                    text_follower.GetProperty().SetColor(self.blue_highlight_color)
                
                if current_idx == idx1: pos1 = self.points[current_idx][0]
                if current_idx == idxV: posV = self.points[current_idx][0]
                if current_idx == idx2: pos2 = self.points[current_idx][0]
        
        if pos1 and posV and pos2:
            self.draw_angle_lines(posV, pos1, pos2)
        self.remove_angle_button.setEnabled(True)
        if points_colored or self.angle_line_actors: 
            self.iren.Render() 


    ## Wipes internal angular memory stripping coloration overrides applying standard visual norms breaking rendering dependencies clearing active pointers structurally.
    def unhighlight_angle(self):
        if self.selected_angle_index is not None:
            sai = self.selected_angle_index
            self.selected_angle_index = None
            self.remove_angle_button.setEnabled(False)
            self.remove_angle_lines() 

            colors_reset = False
            try:
                if 0 <= sai < len(self.angle_definitions):
                    triplet = self.angle_definitions[sai]
                    idx1 = self.get_index_by_label(triplet[0])
                    idxV = self.get_index_by_label(triplet[1])
                    idx2 = self.get_index_by_label(triplet[2])
                    for current_idx in [idx1, idxV, idx2]:
                        if current_idx is not None and 0 <= current_idx < len(self.points) and \
                           isinstance(self.points[current_idx][0], tuple) and \
                           current_idx != self.selected_point_index and \
                           current_idx != self.currently_highlighted_point_index:
                             _, sphere_actor, text_follower = self.points[current_idx]
                             if sphere_actor and sphere_actor.GetProperty().GetColor() != self.default_color: 
                                  sphere_actor.GetProperty().SetColor(self.default_color)
                                  colors_reset = True
                             if text_follower and text_follower.GetProperty().GetColor() != self.default_color: 
                                  text_follower.GetProperty().SetColor(self.default_color)
                                  colors_reset = True
            except IndexError: pass
            
            if colors_reset: 
                 self.iren.Render() 


    ## Injects VTK geometries spawning simple lines bridging vertices formulating angular representation visually guiding user interpretation intuitively natively.
    def draw_angle_lines(self, vertex_pos, point1_pos, point2_pos):
        self.remove_angle_lines() 
        colors = [self.angle_highlight_color, self.angle_highlight_color] 
        for i, p_end in enumerate([point1_pos, point2_pos]):
            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(vertex_pos)
            line_source.SetPoint2(p_end)
            line_source.Update()
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(line_source.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(colors[i])
            prop.SetLineWidth(2) 
            self.ren.AddActor(actor)
            self.angle_line_actors.append(actor)

    ## Flushes scene properties identifying matching items deleting corresponding entities managing memory maintaining efficient display states seamlessly.
    def remove_angle_lines(self):
        if self.angle_line_actors:
            for actor in self.angle_line_actors:
                self.ren.RemoveActor(actor)
            self.angle_line_actors = []
            

    ## Blanket execution resetting multiple tracking parameters nullifying concurrent highlights returning viewer completely back baseline neutral properties enforcing isolated view contexts.
    def unhighlight_all(self):
        dist_idx = self.selected_distance_index 
        angle_idx = self.selected_angle_index
        sel_pt_idx = self.selected_point_index
        hl_pt_idx = self.currently_highlighted_point_index

        if dist_idx is not None:
            self.unhighlight_distance()
        if angle_idx is not None:
            self.unhighlight_angle()   
        if sel_pt_idx is not None:
            self.unhighlight_selected_point() 
        if hl_pt_idx is not None:
            self.unhighlight_blue_point()     
        
        
    ## Returns labels of all currently defined points available for custom measurements.
    def get_defined_point_labels(self): 
        defined_labels = []
        for i, (pos_data, _, _) in enumerate(self.points):
            if isinstance(pos_data, tuple): 
                 if i < len(self.all_labels_in_order):
                     defined_labels.append(self.all_labels_in_order[i])
        return defined_labels

    ## Constructs filtering logic calling selection windows binding valid elements tracking duplications generating fresh metric nodes calculating new outputs updating UI states securely.
    def add_distance_definition(self):
        defined_labels = self.get_defined_point_labels()
        if len(defined_labels) < 2:
            QtWidgets.QMessageBox.warning(self, "Not Enough Points", "Need at least two defined points to create a distance.")
            return

        dialog_labels = ["Point 1", "Point 2 (or Line Point 1)", "Line Point 2 (optional, select NONE for point-to-point)"]
        dialog = SelectPointsDialog(defined_labels, num_points=3, title="Add Distance", labels=dialog_labels, parent=self)
        
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            labels = dialog.getSelectedLabels()
            p1_label, p2_label, p3_label = labels[0], labels[1], labels[2]

            if p3_label == "NONE":
                if p1_label == p2_label:
                    QtWidgets.QMessageBox.warning(self, "Invalid Selection", "Please select two different points for a point-to-point distance.")
                    return

                new_def = (p1_label, p2_label)
                rev_def = (p2_label, p1_label)
                
                if any(d == new_def or d == rev_def for d in self.distance_definitions if len(d) == 2):
                    QtWidgets.QMessageBox.warning(self, "Duplicate", f"Distance {p1_label}-{p2_label} is already defined.")
                    return
                
                self.distance_definitions.append(new_def)

            else:
                if len(set(labels)) < 3: 
                    QtWidgets.QMessageBox.warning(self, "Invalid Selection", "Please select three different points for a point-to-line distance.")
                    return
                
                new_def = (p1_label, p2_label, p3_label)
                rev_def = (p1_label, p3_label, p2_label) 

                if new_def in self.distance_definitions or rev_def in self.distance_definitions:
                    QtWidgets.QMessageBox.warning(self, "Duplicate", f"Distance {p1_label}-{p2_label}{p3_label} is already defined.")
                    return

                self.distance_definitions.append(new_def)

            self.calculate_distances()
            self.unsaved_changes = True
            self.save_button.setEnabled(True)
            self.distances_panel.scrollToBottom()

    ## Safely removes mathematical dependencies verifying user choices executing corresponding array manipulation erasing references propagating metric calculations cleanly formatting output panels natively.
    def remove_selected_distance(self):
        if self.selected_distance_index is None:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Select distance to remove.")
            return
        
        idx_to_remove = self.selected_distance_index
        if not (0 <= idx_to_remove < len(self.distance_definitions)):
             QtWidgets.QMessageBox.critical(self, "Error", "Invalid distance index.")
             return

        pair_to_remove = self.distance_definitions[idx_to_remove]

        if len(pair_to_remove) == 3:
            confirmation_text = f"Remove distance {pair_to_remove[0]}-{pair_to_remove[1]}{pair_to_remove[2]}?"
        else:
            confirmation_text = f"Remove distance {pair_to_remove[0]}-{pair_to_remove[1]}?"

        reply = QtWidgets.QMessageBox.question(self, "Confirm Removal", confirmation_text,
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.unhighlight_distance() 
            del self.distance_definitions[idx_to_remove]
            self.distances.pop(pair_to_remove, None) 
            self.distances.pop((pair_to_remove[1],pair_to_remove[0]), None) 
            self.update_distances_panel()
            self.unsaved_changes = True
            self.save_button.setEnabled(True)


    ## Validates node availability projecting interactive prompts receiving string references catching duplicates updating internal structures recalculating math results automatically correctly assigning visual flags dynamically.
    def add_angle_definition(self):
        defined_labels = self.get_defined_point_labels() 
        if len(defined_labels) < 3:
            QtWidgets.QMessageBox.warning(self, "Not Enough Points", "Need at least three defined points for an angle.")
            return

        dialog = SelectPointsDialog(defined_labels, num_points=3, title="Add Angle", parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            labels = dialog.getSelectedLabels()
            l1, v, l2 = labels[0], labels[1], labels[2]

            if l1==v or l2==v or l1==l2:
                QtWidgets.QMessageBox.warning(self, "Invalid Selection", "Please select three different points.")
                return

            new_triplet = (l1, v, l2)
            rev_triplet = (l2, v, l1)
            if any(t == new_triplet or t == rev_triplet for t in self.angle_definitions):
                QtWidgets.QMessageBox.warning(self, "Duplicate", f"Angle {l1}-{v}-{l2} already defined.")
                return
            
            self.angle_definitions.append(new_triplet)
            self.calculate_angles() 
            self.unsaved_changes = True
            self.save_button.setEnabled(True)
            self.angles_panel.scrollToBottom()

    ## Strips identified angular hierarchies deleting internal string references clearing tracked numerical outputs flushing specific highlights propagating user interface synchronizations properly.
    def remove_selected_angle(self):
        if self.selected_angle_index is None:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Select angle to remove.")
            return

        idx_to_remove = self.selected_angle_index
        if not (0 <= idx_to_remove < len(self.angle_definitions)):
             QtWidgets.QMessageBox.critical(self, "Error", "Invalid angle index.")
             return

        triplet_to_remove = self.angle_definitions[idx_to_remove]
        reply = QtWidgets.QMessageBox.question(self, "Confirm", f"Remove angle {triplet_to_remove[0]}-{triplet_to_remove[1]}-{triplet_to_remove[2]}?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.unhighlight_angle()
            del self.angle_definitions[idx_to_remove]
            self.angles.pop(triplet_to_remove, None)
            self.angles.pop((triplet_to_remove[2],triplet_to_remove[1],triplet_to_remove[0]), None)
            self.update_angles_panel()
            self.unsaved_changes = True
            self.save_button.setEnabled(True)

    ## Interrupts procedural transitions executing conditional branching analyzing state variables spawning critical dialogue nodes processing save operations returning binary continuances preserving core data explicitly.
    def check_for_unsaved_changes(self, action_context="proceeding"):
        
        if not self.unsaved_changes:
            return True

        reply = QtWidgets.QMessageBox.question(
            self, "Unsaved Changes",
            f"You have unsaved changes. Do you want to save data before {action_context}?",
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
            QtWidgets.QMessageBox.Save
        )

        if reply == QtWidgets.QMessageBox.Save:
            self.save_points()
            return not self.unsaved_changes 
        elif reply == QtWidgets.QMessageBox.Discard:
            return True
        else: 
            return False


    ## Activates OS standard file picking mechanisms tracking output paths channeling specific STL loading calls translating inputs executing visual reinitializations successfully updating logic boundaries natively.
    def open_stl(self): 
        if not self.check_for_unsaved_changes("loading a new model"):
            return
            
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open STL File", "", "STL Files (*.stl)")
        if filename:
            if self.load_stl(filename):
                self._update_button_texts()

       

    ## Coordinates file format routing parsing JSON schemas populating application dictionaries allocating rendering models checking prerequisite validations driving metrics logic systematically handling mixed legacy conditions transparently.
    def open_points(self):
        import json
        import os

        if not self.actor:
            QtWidgets.QMessageBox.warning(self, "Warning", "Load STL model first.")
            return

        if not self.check_for_unsaved_changes("loading different points"):
            return

        
        base_name = os.path.splitext(self.current_stl_path)[0]
        cleftp_file = base_name + ".cleftp"
        txt_file = base_name + ".txt"
        
        file_to_load = None
        is_json = False

        if os.path.exists(cleftp_file):
            file_to_load = cleftp_file
            is_json = True
        elif os.path.exists(txt_file):
            file_to_load = txt_file
            is_json = False
        else:
            
            file_to_load, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open Project/Points", "", "CleftMeter Project (*.cleftp);;Text Files (*.txt)"
            )
            if not file_to_load: return
            if file_to_load.endswith(".cleftp"): is_json = True

        if is_json:
            try:
                with open(file_to_load, 'r') as f:
                    data = json.load(f)
                
                t1_data = data.get("T1_geometry", {})
                points_list_in_file = t1_data.get("points", [])
                
                self.clear_points()
                self.all_labels_in_order = []
                self.points = []
                
                scale_factor = self.point_size_slider.value() / 50.0
                
                for p_entry in points_list_in_file:
                    lbl = p_entry["label"]
                    self.all_labels_in_order.append(lbl)
                    if "pos" in p_entry:
                        pos = tuple(p_entry["pos"])
                        sphere, label_actor = self._create_point_actors(pos, lbl, self.default_color, scale_factor)
                        self.points.append((pos, sphere, label_actor))
                    elif "status" in p_entry:
                        self.points.append((p_entry["status"], None, None))
                
                self.custom_point_counter = t1_data.get("custom_point_count", 0)
                defs = data.get("definitions", {})
                self.distance_definitions = [tuple(x) for x in defs.get("distances", [])]
                self.angle_definitions = [tuple(x) for x in defs.get("angles", [])]
                
                
                self.find_next_undefined()
                self.calculate_all_measurements()
                self.update_info_panel()
                self.update_distances_panel()
                self.update_angles_panel()
                self.update_prompt()

                self._run_landmark_side_consistency_check(
                    show_dialog=False
                )

                self.iren.Render()

                QtWidgets.QMessageBox.information(
                    self,
                    "Loaded",
                    f"Project loaded from {os.path.basename(file_to_load)}"
                )
                    
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Load Error", f"Failed to load .cleftp file:\n{e}")
        else:
            self.load_points_from_txt(file_to_load)

            

    ## Clears all active landmark and measurement data.
    def clear_active_data(self):
        if not self.check_for_unsaved_changes("clearing data"):
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Confirm Clear",
            f"Are you sure you want to clear all points and measurements "
            f"? "
            "(The STL model will remain)",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        self.clear_points()
            

    ## Loads landmark and measurement data from a legacy TXT file.
    def load_points_from_txt(self, txt_filename):
        if not self.actor:
            QtWidgets.QMessageBox.warning(
                self,
                "Warning",
                "Load STL model before loading points."
            )
            return

        if not os.path.exists(txt_filename):
            self.clear_points()
            return

        temp_points_config = []
        temp_all_labels = []
        temp_dist_defs = []
        temp_angle_defs = []

        is_new_format = False
        detected_format = False
        current_section = None

        try:
            with open(txt_filename, "r") as f_detect:
                for _ in range(20):
                    line_detect = f_detect.readline()

                    if not line_detect:
                        break

                    line_detect_strip = \
                        line_detect.strip()

                    if line_detect_strip.upper() in (
                            "[POINTS]",
                            "[DISTANCES]",
                            "[ANGLES]"):

                        is_new_format = True
                        detected_format = True
                        break

                    if line_detect_strip.startswith(
                            "Point "):

                        is_new_format = False
                        detected_format = True
                        break

            if not detected_format:
                print(
                    f"Warning: Could not reliably "
                    f"detect format for "
                    f"{txt_filename}. "
                    f"Assuming old format."
                )

                is_new_format = False

            with open(txt_filename, "r") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()

                    if not line:
                        continue

                    if is_new_format:
                        if line.startswith("#"):
                            continue

                        if line.upper() == "[POINTS]":
                            current_section = "[POINTS]"
                            continue

                        elif line.upper() == "[DISTANCES]":
                            current_section = "[DISTANCES]"
                            continue

                        elif line.upper() == "[ANGLES]":
                            current_section = "[ANGLES]"
                            continue


                        # Import tab-separated reports saved by CleftMeter 1.0.
                        if "\t" in line and ":" not in line:
                            fields = [field.strip() for field in line.split("\t")]

                            if current_section == "[POINTS]" and len(fields) >= 2 and fields[0] != "Label":
                                label, status = fields[0], fields[1].lower()
                                if status == "defined" and len(fields) >= 5:
                                    try:
                                        point_data = tuple(float(value) for value in fields[2:5])
                                    except ValueError:
                                        point_data = "to_be_defined"
                                else:
                                    point_data = status if status in ("skipped", "to_be_defined") else "to_be_defined"
                                temp_all_labels.append(label)
                                temp_points_config.append((point_data, label))

                            elif current_section == "[DISTANCES]" and fields[0] in ("Point-Point", "Point-Line"):
                                count = 2 if fields[0] == "Point-Point" else 3
                                if len(fields) > count:
                                    temp_dist_defs.append(tuple(fields[1:count + 1]))

                            elif current_section == "[ANGLES]" and fields[0] == "Angle" and len(fields) >= 4:
                                temp_angle_defs.append(tuple(fields[1:4]))

                            continue



                        if current_section == "[POINTS]" or \
                           (
                               current_section is None and
                               line.startswith("Point ")
                           ):

                            parts = line.split(":", 1)

                            if len(parts) == 2 and \
                               parts[0].startswith("Point"):

                                label_str = \
                                    parts[0][
                                        len("Point"):
                                    ].strip()

                                temp_all_labels.append(
                                    label_str
                                )

                                value_str = \
                                    parts[1].strip().lower()

                                if value_str == "skipped":
                                    temp_points_config.append(
                                        (
                                            "skipped",
                                            label_str
                                        )
                                    )

                                elif value_str == \
                                        "to_be_defined":

                                    temp_points_config.append(
                                        (
                                            "to_be_defined",
                                            label_str
                                        )
                                    )

                                else:
                                    coords_str_list = \
                                        value_str.split()

                                    if len(
                                            coords_str_list
                                    ) >= 3:

                                        try:
                                            coords_tuple = (
                                                float(
                                                    coords_str_list[0]
                                                ),
                                                float(
                                                    coords_str_list[1]
                                                ),
                                                float(
                                                    coords_str_list[2]
                                                )
                                            )

                                            temp_points_config.append(
                                                (
                                                    coords_tuple,
                                                    label_str
                                                )
                                            )

                                        except ValueError:
                                            temp_points_config.append(
                                                (
                                                    "to_be_defined",
                                                    label_str
                                                )
                                            )

                                            print(
                                                f"Warning: Could not parse "
                                                f"coordinates for point "
                                                f"{label_str} at line "
                                                f"{line_num + 1}. "
                                                f"Marked as to_be_defined."
                                            )

                                    else:
                                        temp_points_config.append(
                                            (
                                                "to_be_defined",
                                                label_str
                                            )
                                        )

                                        print(
                                            f"Warning: Invalid coordinate "
                                            f"format for point "
                                            f"{label_str} at line "
                                            f"{line_num + 1}. "
                                            f"Marked as to_be_defined."
                                        )

                        elif current_section == \
                                "[DISTANCES]":

                            try:
                                def_part, _ = \
                                    line.split(":", 1)

                                p0_str, line_part_str = \
                                    def_part.strip().split(
                                        "-",
                                        1
                                    )

                                p0 = p0_str.strip()
                                line_part = \
                                    line_part_str.strip()

                                known_labels = sorted(
                                    [
                                        cfg[1]
                                        for cfg
                                        in temp_points_config
                                    ],
                                    key=len,
                                    reverse=True
                                )

                                p1 = None
                                p2 = None
                                is_point_to_line = False

                                for label_candidate \
                                        in known_labels:

                                    if line_part.startswith(
                                            label_candidate):

                                        p1 = label_candidate
                                        remaining_str = \
                                            line_part[
                                                len(p1):
                                            ]

                                        if remaining_str \
                                                in known_labels:

                                            p2 = \
                                                remaining_str

                                            is_point_to_line = \
                                                True
                                            break

                                if is_point_to_line:
                                    temp_dist_defs.append(
                                        (
                                            p0,
                                            p1,
                                            p2
                                        )
                                    )

                                else:
                                    temp_dist_defs.append(
                                        (
                                            p0,
                                            line_part
                                        )
                                    )

                            except Exception as e:
                                QtWidgets.QMessageBox.warning(
                                    self,
                                    "Warning",
                                    f"Skipping format error "
                                    f"line {line_num + 1} "
                                    f"in [DISTANCES]: "
                                    f"{line} ({e})"
                                )

                        elif current_section == \
                                "[ANGLES]":

                            try:
                                def_part, _ = \
                                    line.split(":", 1)

                                points = \
                                    def_part.strip().split(
                                        "-"
                                    )

                                if len(points) == 3:
                                    temp_angle_defs.append(
                                        tuple(
                                            p.strip()
                                            for p in points
                                        )
                                    )

                            except Exception as e:
                                QtWidgets.QMessageBox.warning(
                                    self,
                                    "Warning",
                                    f"Skipping format error "
                                    f"line {line_num + 1} "
                                    f"in [ANGLES]: "
                                    f"{line} ({e})"
                                )

                    else:
                        if line.startswith("Point "):
                            parts = line.split(":", 1)

                            if len(parts) == 2:
                                label_str = \
                                    parts[0][
                                        len("Point"):
                                    ].strip()

                                temp_all_labels.append(
                                    label_str
                                )

                                value_str = \
                                    parts[1].strip().lower()

                                if value_str == "skipped":
                                    temp_points_config.append(
                                        (
                                            "skipped",
                                            label_str
                                        )
                                    )

                                else:
                                    coords_str_list = \
                                        value_str.split()

                                    if len(
                                            coords_str_list
                                    ) >= 3:

                                        try:
                                            coords_tuple = (
                                                float(
                                                    coords_str_list[0]
                                                ),
                                                float(
                                                    coords_str_list[1]
                                                ),
                                                float(
                                                    coords_str_list[2]
                                                )
                                            )

                                            temp_points_config.append(
                                                (
                                                    coords_tuple,
                                                    label_str
                                                )
                                            )

                                        except ValueError:
                                            temp_points_config.append(
                                                (
                                                    "to_be_defined",
                                                    label_str
                                                )
                                            )

                                            print(
                                                f"Warning: Could not parse "
                                                f"coordinates for point "
                                                f"{label_str} "
                                                f"(old format) at line "
                                                f"{line_num + 1}. "
                                                f"Marked as to_be_defined."
                                            )

                                    else:
                                        temp_points_config.append(
                                            (
                                                "to_be_defined",
                                                label_str
                                            )
                                        )

                                        print(
                                            f"Warning: Invalid coordinate "
                                            f"format for point "
                                            f"{label_str} "
                                            f"(old format) at line "
                                            f"{line_num + 1}. "
                                            f"Marked as to_be_defined."
                                        )

                            else:
                                print(
                                    f"Warning: Skipping malformed "
                                    f"line (old format) at "
                                    f"{line_num + 1}: {line}"
                                )

            self._remove_all_point_actors()

            if temp_points_config:
                self.all_labels_in_order = \
                    list(temp_all_labels)

                self.points = [
                    (
                        pos_or_status,
                        None,
                        None
                    )
                    for pos_or_status, _
                    in temp_points_config
                ]

            else:
                self.all_labels_in_order = list(
                    self.FIXED_LABELS_CLEFT
                )

                self.points = [
                    (
                        "to_be_defined",
                        None,
                        None
                    )
                    for _ in self.FIXED_LABELS_CLEFT
                ]

            max_x_num = 0

            for label in self.all_labels_in_order:
                if label.upper().startswith("X"):
                    try:
                        num = int(label[1:])

                        if num > max_x_num:
                            max_x_num = num

                    except (
                            ValueError,
                            IndexError):
                        continue

            self.custom_point_counter = max_x_num
            self.point_count = 0

            self.distance_definitions = (
                temp_dist_defs
                if temp_dist_defs
                else list(
                    self.DEFAULT_CLEFT_DIST_DEFS
                )
            )

            self.angle_definitions = (
                temp_angle_defs
                if temp_angle_defs
                else list(
                    self.DEFAULT_CLEFT_ANGLE_DEFS
                )
            )

            self.distances = {}
            self.angles = {}

            self.selected_point_index = None
            self.currently_highlighted_point_index = None
            self.selected_distance_index = None
            self.selected_angle_index = None

            self._load_visuals_and_ui()
            self.find_next_undefined()

            self.unsaved_changes = False
            self.save_button.setEnabled(True)

            self._run_landmark_side_consistency_check(
                show_dialog=False
            )

            self.iren.Render()

            QtWidgets.QMessageBox.information(
                self,
                "Load Complete",
                f"Points data loaded from "
                f"{os.path.basename(txt_filename)}."
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to load points file: "
                f"{e}\n{traceback.format_exc()}"
            )

            self.clear_points()

        finally:
            self.update_prompt()
            self.calculate_all_measurements()
            self.unhighlight_all()
            self.iren.Render()

    ## Appends dynamically assigned naming structures expanding standard measurement sets allowing custom point instantiation extending application analytical flexibility actively.
    def add_custom_point(self):
        self.custom_point_counter += 1
        new_label = f"X{self.custom_point_counter}"
        
        while new_label in self.all_labels_in_order:
            self.custom_point_counter += 1
            new_label = f"X{self.custom_point_counter}"

        self.all_labels_in_order.append(new_label)
        self.points.append(("to_be_defined", None, None))
        
        self.find_next_undefined()
        self.update_info_panel()
        self.update_prompt()
        self.unsaved_changes = True
        self.save_button.setEnabled(True)

        self.vtkWidget.setFocus()

    ## Removes the selected custom point and refreshes point and measurement states.
    def remove_selected_custom_point(self):
        if self.currently_highlighted_point_index is None:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Please select a custom point (X1, X2...) from the list to remove.")
            return

        index_to_remove = self.currently_highlighted_point_index
        if not (0 <= index_to_remove < len(self.all_labels_in_order)):
            return

        label_to_remove = self.all_labels_in_order[index_to_remove]

        if not label_to_remove.upper().startswith('X'):
            QtWidgets.QMessageBox.warning(self, "Cannot Remove", "Only custom points (X1, X2...) can be removed. Predefined points cannot be removed.")
            return

        reply = QtWidgets.QMessageBox.question(self, "Confirm Removal",
                                               f"Are you sure you want to permanently remove point {label_to_remove}?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.unhighlight_all()

            _, sphere_actor, text_follower = self.points[index_to_remove]
            if sphere_actor:
                self.ren.RemoveActor(sphere_actor)
            if text_follower:
                self.ren.RemoveActor(text_follower)

            del self.points[index_to_remove]
            del self.all_labels_in_order[index_to_remove]
            
            self.selected_point_index = None
            self.currently_highlighted_point_index = None

            self.find_next_undefined()
            
            self.update_info_panel()
            self.update_prompt()
            self.calculate_all_measurements()
            self.iren.Render()
            
            self._handle_geometry_modification()
            
            self.remove_custom_point_button.setEnabled(False)
            
    ## Saves the current project state and clinical report.
    def save_points(self):
        import json
        import os
        import getpass
        import socket
        from datetime import datetime

        if not self.current_stl_path:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                "No STL file loaded."
            )
            return

        base_name = os.path.splitext(
            self.current_stl_path
        )[0]

        project_filename = base_name + (
            ".cleftp"
        )

        report_filename = base_name + (
            ".txt"
        )

        username = getpass.getuser()
        domain = os.environ.get("USERDOMAIN", "")

        user_identity = (
            f"{domain}\\{username}"
            if domain
            else username
        )

        computer_name = socket.gethostname()

        


        self.calculate_all_measurements()


        points_export = []

        for i, (pos_data, _, _) in enumerate(
                self.points):

            label = self.all_labels_in_order[i]

            if isinstance(pos_data, tuple):
                points_export.append({
                    "label": label,
                    "pos": pos_data
                })

            else:
                points_export.append({
                    "label": label,
                    "status": pos_data
                })

        technical_data = {
            "metadata": {
                "version": "1.3",
                "stl_file":
                    os.path.basename(
                        self.current_stl_path
                    ),
                "save_date":
                    str(datetime.now()),
                "user": user_identity,
                "computer": computer_name
            },

            "T1_geometry": {
                "points": points_export,
                "custom_point_count":
                    self.custom_point_counter
            },

            


            "definitions": {
                "distances":
                    self.distance_definitions,
                "angles":
                    self.angle_definitions
            }
        }

        try:
            with open(
                    project_filename,
                    "w"
            ) as f:

                json.dump(
                    technical_data,
                    f,
                    indent=4
                )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save .cleftp: {e}"
            )
            return

        try:
            with open(
                    report_filename,
                    "w"
            ) as f:

                f.write(
                    "==================================================\n"
                )

                f.write(
                    " CLINICAL REPORT\n"
                )

                f.write(
                    f" Patient/File:\t"
                    f"{os.path.basename(self.current_stl_path)}\n"
                )

                f.write(
                    f" Date:\t"
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                )

                f.write(
                    f" User:\t{user_identity}\n"
                )

                f.write(
                    f" Computer:\t{computer_name}\n"
                )

                f.write(
                    "==================================================\n\n"
                )

                warning_labels = []

                warning_labels.extend(
                    getattr(
                        self,
                        "main_consistency_warning_labels",
                        []
                    )
                )



                warning_labels = list(
                    dict.fromkeys(
                        warning_labels
                    )
                )

                if warning_labels:
                    f.write(
                        "WARNING: Side inconsistency: "
                        + ", ".join(warning_labels)
                        + "\n\n"
                    )

                f.write(
                    "=== MAIN MEASUREMENTS ===\n\n"
                )

                f.write(
                    "--- Distances ---\n"
                )

                for definition in \
                        self.distance_definitions:

                    val = self.distances.get(
                        definition,
                        "n/a"
                    )

                    lbl = (
                        f"{definition[0]}-{definition[1]}"
                        if len(definition) == 2
                        else
                        f"{definition[0]}-"
                        f"{definition[1]}"
                        f"{definition[2]}"
                    )

                    f.write(
                        f"{lbl}:\t{val}\n"
                    )

                f.write(
                    "\n--- Angles ---\n"
                )

                for triplet in \
                        self.angle_definitions:

                    val = self.angles.get(
                        triplet,
                        "n/a"
                    )

                    f.write(
                        f"{triplet[0]}-"
                        f"{triplet[1]}-"
                        f"{triplet[2]}:\t"
                        f"{val}\n"
                    )



                self.unsaved_changes = False
                self.save_button.setEnabled(False)



        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Report Error",
                f"Failed to save clinical report: {e}"
            )

            
    ## intercepts raw GUI input sequences redirecting custom configured shortcuts triggering appropriate layout executing command streams transparently.
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.text().lower()
            key_sym = event.key()

            if event.isAutoRepeat():
                return True

            if key_sym == QtCore.Qt.Key_Escape:
                if self.selected_point_index is not None:
                    self.interactor_style.e_pressed = False
                    self.unhighlight_selected_point()
                    self.update_prompt()
                    self.update_info_panel()
                    self.vtkWidget.setFocus()
                return True

            if key == 'd':
                if self.selected_point_index is not None:
                    return True

                can_define = (
                    self.find_next_undefined_index() is not None
                )

                if can_define:
                    self.unhighlight_all()
                    self.interactor_style.e_pressed = False
                    self.interactor_style.delete_mode = False
                    self.interactor_style.d_pressed = True
                    self.update_prompt()
                    self.update_info_panel()

                return True

            elif key == 'e':
                self.interactor_style.d_pressed = False
                self.interactor_style.delete_mode = False

                if self.selected_point_index is None:
                    self.unhighlight_all()

                self.interactor_style.e_pressed = True
                self.update_prompt()
                self.update_info_panel()
                return True

            elif key == 'n':
                if self.selected_point_index is not None:
                    return True

                if not self.interactor_style.e_pressed and \
                   not self.interactor_style.d_pressed and \
                   not self.interactor_style.delete_mode:
                    self.defer_point()

                return True

            elif key_sym == QtCore.Qt.Key_Delete:
                if self.selected_point_index is not None:
                    return True

                self.unhighlight_all()
                self.interactor_style.d_pressed = False
                self.interactor_style.e_pressed = False
                self.interactor_style.delete_mode = True
                self.update_prompt()
                self.update_info_panel()
                return True

            elif key == 'w':
                if self.actor:
                    prop = self.actor.GetProperty()
                    if prop.GetRepresentation() == vtk.VTK_SURFACE:
                        prop.SetRepresentationToWireframe()
                    self.iren.ReInitialize()
                return True

            elif key == 's':
                if self.actor:
                    prop = self.actor.GetProperty()
                    if prop.GetRepresentation() == vtk.VTK_WIREFRAME:
                        prop.SetRepresentationToSurface()
                    self.iren.ReInitialize()
                return True

        elif event.type() == QtCore.QEvent.KeyRelease:
            key = event.text().lower()
            key_sym = event.key()

            if event.isAutoRepeat():
                return True

            if key == 'd':
                if self.interactor_style.d_pressed:
                    self.interactor_style.d_pressed = False
                    self.interactor_style.last_picked_point = None
                    self.update_prompt()
                    self.update_info_panel()
                return True

            elif key == 'e':
                if self.interactor_style.e_pressed:
                    self.interactor_style.e_pressed = False
                    self.update_prompt()
                    self.update_info_panel()
                return True

            elif key == 'n':
                return True

            elif key_sym == QtCore.Qt.Key_Delete:
                if self.interactor_style.delete_mode:
                    self.interactor_style.delete_mode = False
                    self.update_prompt()
                return True

        return super().eventFilter(obj, event)



    ## Creates a non-interactive transparent VTK overlay renderer displaying the illustrative reference-landmark PNG and landmark-status indicators.
    def _setup_reference_points_overlay(self):
        if hasattr(self, 'reference_points_image_actor') and \
           self.reference_points_image_actor is not None:
            self._position_reference_points_overlay()
            return

        if not hasattr(self, 'vtkWidget') or self.vtkWidget is None:
            return

        image_name = "reference_points.png"
        candidate_paths = []

        try:
            candidate_paths.append(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    image_name
                )
            )
        except NameError:
            pass

        if hasattr(sys, '_MEIPASS'):
            candidate_paths.append(
                os.path.join(sys._MEIPASS, image_name)
            )

        candidate_paths.append(
            os.path.join(os.getcwd(), image_name)
        )

        candidate_paths.append(
            os.path.join(
                os.path.dirname(os.path.abspath(sys.executable)),
                image_name
            )
        )

        image_path = None

        for candidate in candidate_paths:
            if os.path.isfile(candidate):
                image_path = candidate
                break

        if image_path is None:
            print(
                "Reference-points overlay image not found: "
                "reference_points.png"
            )
            return

        self.reference_points_png_reader = vtk.vtkPNGReader()
        self.reference_points_png_reader.SetFileName(image_path)
        self.reference_points_png_reader.Update()

        image_data = self.reference_points_png_reader.GetOutput()

        if image_data is None or image_data.GetNumberOfPoints() == 0:
            print(
                "Reference-points overlay image could not be loaded."
            )
            return

        render_window = self.vtkWidget.GetRenderWindow()

        render_window.SetNumberOfLayers(
            max(2, render_window.GetNumberOfLayers())
        )

        self.ren.SetLayer(0)

        self.reference_points_overlay_renderer = vtk.vtkRenderer()
        self.reference_points_overlay_renderer.SetLayer(1)
        self.reference_points_overlay_renderer.SetViewport(
            0.0, 0.0, 1.0, 1.0
        )
        self.reference_points_overlay_renderer.InteractiveOff()

        self.reference_points_overlay_renderer.SetBackground(
            0.0, 0.0, 0.0
        )
        self.reference_points_overlay_renderer.SetBackgroundAlpha(
            0.0
        )

        self.reference_points_overlay_renderer.PreserveColorBufferOn()
        self.reference_points_overlay_renderer.PreserveDepthBufferOff()

        render_window.AddRenderer(
            self.reference_points_overlay_renderer
        )

        self.reference_points_image_actor = vtk.vtkImageActor()
        self.reference_points_image_actor.SetInputData(
            image_data
        )

        self.reference_points_image_actor.GetProperty().SetOpacity(
            1.0
        )
        self.reference_points_image_actor.InterpolateOn()

        self.reference_points_overlay_renderer.AddActor(
            self.reference_points_image_actor
        )

        # Normalized positions of landmark labels within reference_points.png.
        # x = 0..1 from left to right, y = 0..1 from bottom to top.
        self.reference_points_status_positions = {
            "I":  (0.500, 0.955),
            "P":  (0.296, 0.823),
            "P'": (0.710, 0.820),
            "L":  (0.325, 0.720),
            "L'": (0.680, 0.717),
            "C":  (0.183, 0.645),
            "C'": (0.817, 0.640),
            "Q":  (0.305, 0.455),
            "Q'": (0.690, 0.456),
            "T":  (0.134, 0.106),
            "T'": (0.858, 0.097),
        }

        self.reference_points_status_sources = {}
        self.reference_points_status_actors = {}

        for label in self.reference_points_status_positions:
            source = vtk.vtkRegularPolygonSource()
            source.SetNumberOfSides(64)
            source.GeneratePolygonOn()
            source.SetCenter(0.0, 0.0, 0.05)
            source.SetRadius(1.0)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(
                source.GetOutputPort()
            )

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().LightingOff()
            actor.GetProperty().SetOpacity(0.38)
            actor.SetVisibility(False)
            actor.PickableOff()

            self.reference_points_overlay_renderer.AddActor(
                actor
            )

            self.reference_points_status_sources[label] = source
            self.reference_points_status_actors[label] = actor

        self._position_reference_points_overlay()

        self.iren.Render()


    ## Updates landmark-status circles in the reference diagram according to point definition and consistency-check results.
    def _update_reference_points_status_overlay(self):
        if not hasattr(
                self,
                "reference_points_status_actors"
        ):
            return

        green = (0.10, 0.85, 0.10)
        red = (1.00, 0.10, 0.10)
        grey = (0.62, 0.62, 0.62)

        main_warning_labels = set(
            getattr(
                self,
                "main_consistency_warning_labels",
                []
            )
        )

        main_check_state = getattr(
            self,
            "main_consistency_check_state",
            "not_run"
        )

        for label, actor in \
                self.reference_points_status_actors.items():

            idx = self.get_index_by_label(label)

            defined = (
                idx is not None and
                0 <= idx < len(self.points) and
                isinstance(self.points[idx][0], tuple)
            )

            if not defined:
                actor.SetVisibility(False)
                continue

            actor.SetVisibility(True)

            if label == "I":
                color = green

            elif main_check_state == "completed":
                if label in main_warning_labels:
                    color = red
                else:
                    color = green

            else:
                color = grey

            actor.GetProperty().SetColor(*color)
            actor.GetProperty().SetOpacity(0.38)

        if hasattr(self, "iren") and self.iren:
            self.iren.Render()


    ## Positions and proportionally scales the transparent reference-landmark image in the lower-left corner of the main VTK workspace.
    def _position_reference_points_overlay(self):
        if not hasattr(self, 'reference_points_image_actor') or \
           self.reference_points_image_actor is None:
            return

        if not hasattr(
            self,
            'reference_points_overlay_renderer'
        ):
            return

        if not hasattr(
            self,
            'reference_points_png_reader'
        ):
            return

        image_data = self.reference_points_png_reader.GetOutput()

        if image_data is None:
            return

        dimensions = image_data.GetDimensions()

        image_width = dimensions[0]
        image_height = dimensions[1]

        if image_width <= 0 or image_height <= 0:
            return

        render_window = self.vtkWidget.GetRenderWindow()
        window_size = render_window.GetSize()

        workspace_width = max(1, window_size[0])
        workspace_height = max(1, window_size[1])

        try:
            dpr = float(self.vtkWidget.devicePixelRatioF())
        except Exception:
            dpr = 1.0

        target_width = min(
            int(360 * dpr),
            int(workspace_width * 0.28)
        )

        target_height = (
            target_width *
            image_height /
            image_width
        )

        max_height = min(
            int(260 * dpr),
            int(workspace_height * 0.32)
        )

        if target_height > max_height:
            target_height = max_height

            target_width = (
                target_height *
                image_width /
                image_height
            )

        scale_factor = (
            target_width /
            image_width
        )

        margin = 12.0 * dpr

        self.reference_points_image_actor.SetScale(
            scale_factor,
            scale_factor,
            1.0
        )

        self.reference_points_image_actor.SetPosition(
            margin,
            margin,
            0.0
        )

        if hasattr(
                self,
                "reference_points_status_sources"
        ):

            circle_radius = target_height * 0.036

            for label, normalized_pos in \
                    self.reference_points_status_positions.items():

                source = \
                    self.reference_points_status_sources.get(
                        label
                    )

                if source is None:
                    continue

                nx, ny = normalized_pos

                center_x = (
                    margin +
                    nx * target_width
                )

                center_y = (
                    margin +
                    ny * target_height
                )

                source.SetCenter(
                    center_x,
                    center_y,
                    0.05
                )

                source.SetRadius(
                    circle_radius
                )

                source.Modified()

        camera = \
            self.reference_points_overlay_renderer.GetActiveCamera()

        camera.ParallelProjectionOn()

        camera.SetFocalPoint(
            workspace_width / 2.0,
            workspace_height / 2.0,
            0.0
        )

        camera.SetPosition(
            workspace_width / 2.0,
            workspace_height / 2.0,
            1.0
        )

        camera.SetViewUp(
            0.0,
            1.0,
            0.0
        )

        camera.SetParallelScale(
            workspace_height / 2.0
        )

        camera.SetClippingRange(
            0.1,
            10.0
        )

        self._update_reference_points_status_overlay()

        if hasattr(self, 'iren') and self.iren:
            self.iren.Render()


    ## Repositions the illustrative reference-landmark overlay whenever the main application window is resized.
    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, 'reference_points_image_actor'):
            QtCore.QTimer.singleShot(
                0,
                self._position_reference_points_overlay
            )


    ## Handles window activation and show events by restoring VTK focus and initializing the reference-landmark overlay.
    def event(self, event):
        if event.type() == QtCore.QEvent.WindowActivate:
            if hasattr(self, 'vtkWidget') and self.vtkWidget:
                self.vtkWidget.setFocus()

        if event.type() == QtCore.QEvent.Show:
            QtCore.QTimer.singleShot(
                0,
                self._setup_reference_points_overlay
            )

        return super().event(event)

    ## Polling protocol resolving termination states issuing confirmation dialogs verifying user intent preserving local progress eliminating accidental tracking wipes upon standard shutdown loops.
    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Close",
                f"You have unsaved changes. Do you want to save data before closing?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Save
            )

            if reply == QtWidgets.QMessageBox.Save:
                self.save_points()
                if not self.unsaved_changes: 
                    event.accept()
                else: 
                    event.ignore()
            elif reply == QtWidgets.QMessageBox.Discard:
                event.accept()
            else: 
                event.ignore()
        else:
            event.accept()



    ## Restores the standard text of the main file-operation buttons.
    def _update_button_texts(self):
        self.open_points_button.setText("Open Points")
        self.save_button.setText("Save")


                
    ## Resets landmark-consistency status and marks the project as modified and ready to save.
    def _handle_geometry_modification(self):
        self.main_consistency_warning_labels = []
        self.main_consistency_check_state = "not_run"
        self._update_reference_points_status_overlay()

        self.unsaved_changes = True
        self.save_button.setEnabled(True)
              



if __name__ == "__main__":
    import traceback
    import os
    
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    
    app = QtWidgets.QApplication(sys.argv)
    
    app.setStyle("Fusion") 
    
    f = app.font()
    f.setPointSize(9)
    app.setFont(f)
    
    window = STLViewer()
    window.show()
    sys.exit(app.exec())

