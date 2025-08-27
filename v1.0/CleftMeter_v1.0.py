# =======================================================================
# CLEFTMETER, VERSION 1.0
# Authors: Libor Borak, Petr Marcian, Olga Koskova
# @ 2025
# =======================================================================
# Records of revision:
# 
# - v1.0: Initial issue
# =======================================================================

import sys
import os
import traceback
from PySide6 import QtWidgets, QtCore, QtGui
import vtkmodules.all as vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkCommonCore import vtkCommand
import math
import numpy as np


class CustomInteractorStyle(vtkInteractorStyleTrackballCamera):
    """
    Defines a custom VTK interactor style by inheriting from vtkInteractorStyleTrackballCamera,
    used for mouse interactions in the main 3D viewing window.
    """
    def __init__(self, renderer, stl_viewer):
        """
        Initializes the custom interactor style.
        It links to the STLViewer instance and the VTK renderer,
        and sets up an observer for left mouse button press events and keyboard state.
        """
        super().__init__()
        self.stl_viewer = stl_viewer
        self.Renderer = renderer
        self.AddObserver(vtkCommand.LeftButtonPressEvent, self.left_button_press_event)

        self.d_pressed = False
        self.e_pressed = False
        self.delete_mode = False
        self.last_picked_point = None

    def left_button_press_event(self, obj, event):
        """
        Handles actions when the left mouse button is pressed.
        This method checks if the interaction is intended for defining, editing, or deleting a point
        based on keyboard flags (d_pressed, e_pressed, delete_mode).
        It uses a vtkCellPicker to get the 3D coordinates of the click on the STL model.
        """
        if self.d_pressed or (self.e_pressed and self.stl_viewer.selected_point_index is not None) or self.delete_mode:
            click_pos = self.GetInteractor().GetEventPosition()
            picker = vtk.vtkCellPicker()
            picker.SetTolerance(0.005)

            if self.stl_viewer.actor:
                picker.AddPickList(self.stl_viewer.actor)
                picker.PickFromListOn()
                picker.Pick(click_pos[0], click_pos[1], 0, self.Renderer)

                if picker.GetActor() == self.stl_viewer.actor:
                    world_pos = picker.GetPickPosition()

                    if self.d_pressed:
                        if self.last_picked_point is None or \
                           (world_pos[0] - self.last_picked_point[0])**2 + \
                           (world_pos[1] - self.last_picked_point[1])**2 + \
                           (world_pos[2] - self.last_picked_point[2])**2 > 1e-6:
                                self.stl_viewer.add_point(world_pos)
                                self.last_picked_point = world_pos
                    elif self.e_pressed:
                        self.stl_viewer.vtkWidget.setFocus()
                        self.stl_viewer.redefine_point(world_pos)
                    elif self.delete_mode:
                        pass
        self.OnLeftButtonDown()


class SelectPointsDialog(QtWidgets.QDialog):
    """
    Creates a dialog for users to select a specified number of points
    from a list of available points, typically for defining distances or angles.
    """
    def __init__(self, available_points, num_points=2, title="Select Points", labels=None, parent=None):
        """
        Initializes the dialog for selecting points.
        It sets up the UI with combo boxes for point selection and standard OK/Cancel buttons.
        """
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

    def getSelectedLabels(self):
        """Returns the labels of the points selected by the user in the combo boxes."""
        return [combo.currentText() for combo in self.combos]


class STLViewer(QtWidgets.QMainWindow):
    """
    Main application window class, inheriting from QMainWindow.
    This class manages the overall UI, VTK rendering for point placement,
    point data, distance and angle calculations, and file operations.
    """
    def __init__(self, parent=None):
        """
        Initializes the main window UI, VTK setup, and application state.
        Sets up panels for points, distances, angles, and VTK rendering.
        """
        super().__init__(parent)

        self.setWindowTitle("CleftMeter 1.0")
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

        self.all_labels_in_order = list(self.FIXED_LABELS_CLEFT)
        self.points = [("to_be_defined", None, None) for _ in self.all_labels_in_order]
        self.point_count = 0
        self.distance_definitions = list(self.DEFAULT_CLEFT_DIST_DEFS)
        self.distances = {}
        self.angle_definitions = list(self.DEFAULT_CLEFT_ANGLE_DEFS)
        self.angles = {}
        
        self.left_panel = QtWidgets.QWidget()
        self.left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        self.left_panel.setFixedWidth(350)

        self.left_layout.addWidget(QtWidgets.QLabel("<b>Points:</b>"))
        self.info_panel = QtWidgets.QListWidget()
        self.left_layout.addWidget(self.info_panel)
        self.info_panel.itemClicked.connect(self.on_point_selected)
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

        self.logo_label = QtWidgets.QLabel("CleftMeter 1.0")
        self.logo_label.setAlignment(QtCore.Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-family: 'Arial Black'; font-size: 24px; border: 1px solid black; padding: 5px;")
        self.left_layout.addWidget(self.logo_label)

        self.left_layout.setStretchFactor(self.info_panel, 4)
        self.left_layout.setStretchFactor(self.distances_panel, 3)
        self.left_layout.setStretchFactor(self.angles_panel, 3)

        self.vtk_panel = QtWidgets.QWidget()
        self.vtk_layout = QtWidgets.QVBoxLayout(self.vtk_panel)
        self.vtkWidget = QVTKRenderWindowInteractor(self.vtk_panel)
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

        self.clear_button = QtWidgets.QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all_data)
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
        self.showMaximized()
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

        self.update_info_panel()
        self.update_distances_panel()
        self.update_angles_panel()
        self.update_prompt()

    def _reset_state_without_confirmation(self):
        """Internal method for resetting the application state without confirmation."""
        for _, sphere_actor, text_follower in self.points:
            if sphere_actor: self.ren.RemoveActor(sphere_actor)
            if text_follower: self.ren.RemoveActor(text_follower)
        self.remove_distance_lines()
        self.remove_angle_lines()
        self.selected_point_index = None
        self.currently_highlighted_point_index = None
        self.selected_distance_index = None
        self.selected_angle_index = None
        
        self.all_labels_in_order = list(self.FIXED_LABELS_CLEFT)
        self.points = [("to_be_defined", None, None) for _ in self.all_labels_in_order]
        self.point_count = 0
        self.distance_definitions = list(self.DEFAULT_CLEFT_DIST_DEFS)
        self.distances = {}
        self.angle_definitions = list(self.DEFAULT_CLEFT_ANGLE_DEFS)
        self.angles = {}

        self.update_info_panel()
        self.update_distances_panel()
        self.update_angles_panel()
        self.update_prompt()
        
        self.unsaved_changes = False
        self.save_button.setEnabled(False)
        self.iren.Render()

    def _create_point_actors(self, world_pos, label, color, scale_factor):
        """Helper method to create and add sphere and text label actors for a point in the 3D scene."""
        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(world_pos)
        sphere.SetRadius(self.base_point_radius * scale_factor)
        sphere.SetPhiResolution(15); sphere.SetThetaResolution(15)
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(sphere.GetOutputPort())
        sphere_actor = vtk.vtkActor(); sphere_actor.SetMapper(mapper)
        sphere_actor.GetProperty().SetColor(color)
        self.ren.AddActor(sphere_actor)

        text_source = vtk.vtkVectorText(); text_source.SetText(str(label))
        text_mapper = vtk.vtkPolyDataMapper(); text_mapper.SetInputConnection(text_source.GetOutputPort())
        text_follower = vtk.vtkFollower(); text_follower.SetMapper(text_mapper)
        text_follower.SetCamera(self.ren.GetActiveCamera())
        text_offset = self.base_point_radius * scale_factor * 1.5
        text_follower.SetPosition(world_pos[0], world_pos[1] + text_offset, world_pos[2])
        text_follower.GetProperty().SetColor(color)
        text_follower.SetScale(1.5, 1.5, 1.5)
        self.ren.AddActor(text_follower)
        return sphere_actor, text_follower

    def initialize_distances_panel(self):
        """Initializes the distances panel by calling `update_distances_panel`."""
        self.update_distances_panel()

    def update_distances_panel(self):
        """Updates the list of distances displayed in the UI panel."""
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
        self.remove_distance_button.setEnabled(self.selected_distance_index is not None)

    def initialize_angles_panel(self):
        """Initializes the angles panel by calling `update_angles_panel`."""
        self.update_angles_panel()

    def update_angles_panel(self):
        """Updates the list of angles displayed in the UI panel."""
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
        self.remove_angle_button.setEnabled(self.selected_angle_index is not None)

    def initialize_info_panel(self):
        """Initializes the points information panel by calling `update_info_panel`."""
        self.update_info_panel()
        
    def update_info_panel(self):
        """Updates the list of points displayed in the UI panel."""
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
            elif i == self.currently_highlighted_point_index and \
                 isinstance(pos_or_status, tuple): 
                 item.setBackground(QtGui.QColor.fromRgbF(*self.blue_highlight_color))
            self.info_panel.addItem(item)

    def clear_all_data(self):
        """
        Clears all data (points, measurements) for the application.
        Prompts the user for confirmation before clearing.
        """
        reply = QtWidgets.QMessageBox.question(self, "Confirm Clear",
                                               "Are you sure you want to clear all points and measurements? (The STL model will remain)",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self._reset_state_without_confirmation()

    def show_about_dialog(self):
        """
        Displays the 'About' dialog with information about the CleftMeter application.
        """
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("About CleftMeter v.1.0")
        dialog.setMinimumWidth(650)
        dialog.setMinimumHeight(720)

        layout = QtWidgets.QVBoxLayout(dialog)
        
        text_browser = QtWidgets.QTextBrowser(dialog)
        text_browser.setOpenExternalLinks(True)

        about_text = """
        <style>
            h2 {{ margin-bottom: 10px; }}
            h3 {{ margin-top: 15px; margin-bottom: 5px; }}
            ul {{ margin-top: 0px; padding-left: 20px; }}
            li {{ margin-bottom: 4px; }}
            p {{ margin-bottom: 8px; }}
        </style>
        
        <h2>CleftMeter v.1.0</h2>
        <p>Authors: Libor Borák, Petr Marcián, Olga Košková</p>
        <p>© 2025</p>
        <hr>

        <h3>Application Description:</h3>
        <p><b>CleftMeter</b> is a specialized tool for anthropometric measurements on 3D models, primarily focused on the analysis of cleft palate defects. It allows the user to load a 3D model in STL format, define a set of predefined anatomical points on it, and subsequently measure distances and angles between these points.</p>
        
        <h3>Keyboard Functions:</h3>
        <ul>
            <li><b>D</b>: Hold to enter Define Point mode (click on model).</li>
            <li><b>E</b>: Hold to enter Edit Point mode (select point in list, then click new position).</li>
            <li><b>N</b>: Skips the definition of the current point and moves to the next.</li>
            <li><b>Delete</b>: Hold to enter Delete Point mode (select point in list to delete/skip it).</li>
            <li><b>W</b>: Toggle Wireframe view of the STL model.</li>
            <li><b>S</b>: Toggle Surface view of the STL model.</li>
        </ul>
        <hr>

        <h3>Mouse Controls:</h3>
        <ul>
            <li><b>Left Mouse Button</b>: Rotate model.</li>
            <li><b>Middle Mouse Button / Shift + Left Click</b>: Pan model.</li>
            <li><b>Right Mouse Button / Ctrl + Left Click</b>: Zoom model.</li>
            <li><b>Scroll Wheel</b>: Zoom model.</li>
            <li><b>Left Click in Lists</b>: Select point/distance/angle for inspection or removal.</li>
            <li><b>Left Click on Model</b>: Define or Edit point position (when corresponding key 'D' or 'E' is held).</li>
        </ul>
        <hr>

        <h3>Panel Functions:</h3>
        <ul>
            <li><b>Distances / Angles Panels:</b> Use the 'Add' and 'Remove Selected' buttons within these panels to manage custom measurements based on the defined points.</li>
        </ul>
        <hr>

        <h3>Button Functions:</h3>
        <ul>
            <li><b>Open STL:</b> Opens a file dialog to load a 3D model in STL format.</li>
            <li><b>Open Points:</b> Loads point data from a .txt file. If no model is loaded, it attempts to load the associated STL file.</li>
            <li><b>Save:</b> Saves the current state (point coordinates, distances, and angles) to a .txt file named after the loaded STL model.</li>
            <li><b>Clear All:</b> Clears all defined points and measurements from the session after confirmation.</li>
            <li><b>Zoom To Fit:</b> Adjusts the camera to fit the entire 3D model within the view.</li>
            <li><b>About:</b> Displays this information window.</li>
        </ul>
        """
        text_browser.setHtml(about_text)
        text_browser.setReadOnly(True)

        layout.addWidget(text_browser)
        
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, dialog)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec()

    def update_prompt(self):
        """Updates the prompt label to guide the user to the next point to define."""
        if self.point_count < len(self.all_labels_in_order):
            next_label = self.all_labels_in_order[self.point_count]
            self.prompt_label.setText(f"Define point {next_label}")
        else:
            self.prompt_label.setText("All points marked.")

    def calculate_distances(self):
        """Calculates all defined distances between pairs of points."""
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
                        p0, p1, p2 = np.array(p0_data), np.array(p1_data), np.array(p2_data)
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

    def calculate_angles(self):
        """Calculates all defined angles between triplets of points."""
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
                        p1 = np.array(pos1_data); pV = np.array(posV_data); p2 = np.array(pos2_data)
                        vec1 = p1 - pV; vec2 = p2 - pV
                        norm1 = np.linalg.norm(vec1); norm2 = np.linalg.norm(vec2)
                        if norm1 > 1e-9 and norm2 > 1e-9:
                            dot_product = np.dot(vec1, vec2)
                            cos_theta = np.clip(dot_product / (norm1 * norm2), -1.0, 1.0)
                            angle_rad = math.acos(cos_theta)
                            self.angles[triplet] = f"{math.degrees(angle_rad):.2f}°"
                        else: self.angles[triplet] = "invalid"
                    else: self.angles[triplet] = "n/a"
                else: self.angles[triplet] = "n/a"
            else: self.angles[triplet] = "n/a"
        self.update_angles_panel()

    def calculate_all_measurements(self):
        """Calculates all defined distances and angles."""
        self.calculate_distances()
        self.calculate_angles()

    def get_index_by_label(self, label_to_find):
        """Gets the index of a point in the `self.all_labels_in_order` list by its label."""
        try:
            return self.all_labels_in_order.index(str(label_to_find))
        except ValueError:
            return None

    def update_point_size(self):
        """Updates the size of all point actors (spheres and labels) based on the point size slider value."""
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

    def zoom_to_fit(self):
        """Resets the camera of the VTK renderer to fit all actors in the scene."""
        self.ren.ResetCamera(); self.iren.Render()

    def add_point(self, world_pos):
        """Adds a new point at the given 3D world coordinates."""
        scale_factor = self.point_size_slider.value() / 50.0
        next_idx = self.find_next_undefined_index()
        if next_idx is None:
            self.prompt_label.setText("All points marked.")
            return
        
        target_index_for_new_point = next_idx
        label_for_new_point = self.all_labels_in_order[target_index_for_new_point]

        _, old_sphere_actor, old_text_follower = self.points[target_index_for_new_point]
        if old_sphere_actor: self.ren.RemoveActor(old_sphere_actor)
        if old_text_follower: self.ren.RemoveActor(old_text_follower)

        sphere_actor, text_follower = self._create_point_actors(world_pos, label_for_new_point, self.default_color, scale_factor)
        self.points[target_index_for_new_point] = (world_pos, sphere_actor, text_follower)
        
        self.find_next_undefined()
        self.update_info_panel()
        self.iren.Render()
        self.save_button.setEnabled(True)
        self.unsaved_changes = True
        self.calculate_all_measurements()
        self.update_prompt()
        self.reapply_measurement_highlight()

    def redefine_point(self, world_pos):
        """Redefines the position of the currently selected point to the new 3D world coordinates."""
        if self.selected_point_index is None: return

        index = self.selected_point_index
        if not (0 <= index < len(self.points)): return

        _, old_sphere_actor, old_text_follower = self.points[index]
        label = self.all_labels_in_order[index]
        scale_factor = self.point_size_slider.value() / 50.0

        if old_sphere_actor: self.ren.RemoveActor(old_sphere_actor)
        if old_text_follower: self.ren.RemoveActor(old_text_follower)
            
        sphere_actor, text_follower = self._create_point_actors(world_pos, label, self.default_color, scale_factor)
        self.points[index] = (world_pos, sphere_actor, text_follower)

        self.unsaved_changes = True
        self.interactor_style.e_pressed = False
        self.unhighlight_selected_point()
        self.find_next_undefined()
        self.update_info_panel()
        self.update_prompt()
        self.iren.Render()
        self.calculate_all_measurements()
        self.reapply_measurement_highlight()

    def defer_point(self):
        """Marks the next point to be defined as 'skipped'."""
        next_index_to_define = self.find_next_undefined_index()
        if next_index_to_define is None: return

        _, sphere_actor, text_follower = self.points[next_index_to_define]
        if sphere_actor: self.ren.RemoveActor(sphere_actor)
        if text_follower: self.ren.RemoveActor(text_follower)
        
        self.points[next_index_to_define] = ("skipped", None, None)

        self.find_next_undefined()
        self.update_info_panel()
        self.update_prompt()
        self.unsaved_changes = True
        self.calculate_all_measurements()
        self.reapply_measurement_highlight()
        self.iren.Render()

    def skip_selected_point(self):
        """Marks the currently selected point (in edit mode) as 'skipped'."""
        if self.selected_point_index is None: return
        
        index_to_skip = self.selected_point_index
        if not (0 <= index_to_skip < len(self.points)):
            self.unhighlight_selected_point(); return

        self.unhighlight_selected_point()

        _, sphere_actor, text_follower = self.points[index_to_skip]
        if sphere_actor: self.ren.RemoveActor(sphere_actor)
        if text_follower: self.ren.RemoveActor(text_follower)

        self.points[index_to_skip] = ("skipped", None, None)
        
        self.unsaved_changes = True
        self.interactor_style.e_pressed = False
        self.find_next_undefined()
        self.update_info_panel()
        self.update_prompt()
        self.calculate_all_measurements()
        self.reapply_measurement_highlight()
        self.iren.Render()

    def delete_point(self, index_to_delete):
        """Marks a point at the specified index as 'skipped' (effectively deleting its coordinates)."""
        if index_to_delete is None or not (0 <= index_to_delete < len(self.points)):
             return

        if self.selected_point_index == index_to_delete: self.unhighlight_selected_point()
        if self.currently_highlighted_point_index == index_to_delete: self.unhighlight_blue_point()

        _, sphere_actor, text_follower = self.points[index_to_delete]
        if sphere_actor: self.ren.RemoveActor(sphere_actor)
        if text_follower: self.ren.RemoveActor(text_follower)

        self.points[index_to_delete] = ("skipped", None, None)

        self.update_info_panel()
        self.unsaved_changes = True
        self.calculate_all_measurements()
        self.find_next_undefined()
        self.update_prompt()
        self.reapply_measurement_highlight()
        self.iren.Render()

    def find_next_undefined_index(self):
        """Finds the index of the next point in the list that has a status of 'to_be_defined'."""
        for i, (status, _, _) in enumerate(self.points):
            if status == "to_be_defined":
                return i
        return None

    def find_next_undefined(self):
        """Updates `self.point_count` to the index of the next 'to_be_defined' point."""
        next_idx = self.find_next_undefined_index()
        if next_idx is not None:
            self.point_count = next_idx
        else:
            self.point_count = len(self.points)

    def reapply_measurement_highlight(self):
        """Reapplies visual highlighting for the currently selected distance or angle, if any."""
        dist_idx = self.selected_distance_index
        angle_idx = self.selected_angle_index
        
        temp_dist_idx = dist_idx
        temp_angle_idx = angle_idx

        if dist_idx is not None: self.unhighlight_distance()
        if angle_idx is not None: self.unhighlight_angle()   
        
        if temp_dist_idx is not None:
            if 0 <= temp_dist_idx < len(self.distance_definitions):
                 self.highlight_distance(temp_dist_idx)
        elif temp_angle_idx is not None:
             if 0 <= temp_angle_idx < len(self.angle_definitions):
                 self.highlight_angle(temp_angle_idx)

    def on_point_selected(self, item):
        """Handles user clicks on an item in the points list (info_panel)."""
        index = item.data(QtCore.Qt.UserRole)
        if index is None or not (0 <= index < len(self.points)): return

        self.unhighlight_distance(); self.unhighlight_angle()

        if self.interactor_style.e_pressed:
            current_point_status = self.points[index][0]
            if current_point_status != "to_be_defined":
                self.highlight_selected_point(index)
                point_label = self.all_labels_in_order[index]
                prompt_msg = f"Editing Point {point_label}: Click new position or press N to skip"
                if current_point_status == "skipped":
                    prompt_msg = f"Editing skipped Point {point_label}: Click new position on model"
                self.prompt_label.setText(prompt_msg)
            else:
                 self.unhighlight_selected_point()
                 self.prompt_label.setText("Edit (select a defined or skipped point to edit)")
        
        elif self.interactor_style.delete_mode:
            if isinstance(self.points[index][0], tuple): 
                self.delete_point(index)
                self.interactor_style.delete_mode = False
                self.update_prompt()
            else:
                QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), "Cannot delete - point not defined.", self.vtkWidget)
        
        else: 
             if isinstance(self.points[index][0], tuple): 
                 self.toggle_blue_highlight(index)
             else:
                 self.unhighlight_blue_point()
        self.update_info_panel()

    def toggle_blue_highlight(self, index):
        """Toggles the blue highlight state for a point at the given index."""
        if self.currently_highlighted_point_index == index:
            self.unhighlight_blue_point()
        else:
            self.highlight_blue_point(index)

    def highlight_blue_point(self, index):
        """Highlights a point at the given index with a blue color."""
        if index is None or not (0 <= index < len(self.points)) or \
           not isinstance(self.points[index][0], tuple): 
            self.unhighlight_blue_point(); return

        self.unhighlight_all()
        self.currently_highlighted_point_index = index
        _, sphere_actor, text_follower = self.points[index]
        if sphere_actor: sphere_actor.GetProperty().SetColor(self.blue_highlight_color)
        if text_follower: text_follower.GetProperty().SetColor(self.blue_highlight_color)
        self.iren.Render()
        self.update_info_panel()

    def unhighlight_blue_point(self):
        """Removes the blue highlight from the currently blue-highlighted point."""
        if self.currently_highlighted_point_index is not None:
            idx = self.currently_highlighted_point_index
            self.currently_highlighted_point_index = None
            if 0 <= idx < len(self.points) and isinstance(self.points[idx][0], tuple): 
                 _, sphere_actor, text_follower = self.points[idx]
                 if sphere_actor: sphere_actor.GetProperty().SetColor(self.default_color)
                 if text_follower: text_follower.GetProperty().SetColor(self.default_color)
                 self.iren.Render()
            self.update_info_panel()

    def highlight_selected_point(self, index):
        """Highlights a point at the given index with a green color (typically for editing)."""
        if index is None or not (0 <= index < len(self.points)) or \
           self.points[index][0] == "to_be_defined": 
            self.unhighlight_selected_point(); return

        self.unhighlight_all()
        self.selected_point_index = index
        
        point_status, sphere_actor, text_follower = self.points[index]
        if point_status != "skipped":
            if sphere_actor: sphere_actor.GetProperty().SetColor(self.highlight_color)
            if text_follower: text_follower.GetProperty().SetColor(self.highlight_color)
            self.iren.Render()
        self.update_info_panel()

    def unhighlight_selected_point(self):
        """Removes the green highlight from the currently selected point."""
        if self.selected_point_index is not None:
            idx = self.selected_point_index
            self.selected_point_index = None
            if 0 <= idx < len(self.points):
                point_status, sphere_actor, text_follower = self.points[idx]
                if isinstance(point_status, tuple):
                    if sphere_actor: sphere_actor.GetProperty().SetColor(self.default_color)
                    if text_follower: text_follower.GetProperty().SetColor(self.default_color)
                    self.iren.Render()
            self.update_info_panel()

    def on_distance_selected(self, item):
        """Handles user clicks on an item in the distances list."""
        index = item.data(QtCore.Qt.UserRole)
        if index is None: return
        self.toggle_distance_highlight(index)

    def toggle_distance_highlight(self, index):
        """Toggles the highlight state for a distance, updating UI items directly without rebuilding the list."""
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

    def highlight_distance(self, index):
        """Highlights a distance at the given index."""
        if index is None or not (0 <= index < len(self.distance_definitions)):
            self.unhighlight_distance(); return
        
        self.unhighlight_all()
        self.selected_distance_index = index
        
        definition = self.distance_definitions[index]
        
        if len(definition) == 2:
            idx1 = self.get_index_by_label(definition[0]); idx2 = self.get_index_by_label(definition[1])
            pos1, pos2 = self.get_pos_by_index(idx1), self.get_pos_by_index(idx2)
            if pos1 and pos2:
                self.highlight_points([idx1, idx2])
                self.draw_distance_lines(solid_lines=[(pos1, pos2)])
        
        elif len(definition) == 3:
            p0_idx, p1_idx, p2_idx = [self.get_index_by_label(lbl) for lbl in definition]
            p0, p1, p2 = self.get_pos_by_index(p0_idx), self.get_pos_by_index(p1_idx), self.get_pos_by_index(p2_idx)
            
            if p0 and p1 and p2:
                self.highlight_points([p0_idx, p1_idx, p2_idx])
                p0_np, p1_np, p2_np = np.array(p0), np.array(p1), np.array(p2)
                line_vec = p2_np - p1_np
                line_norm_sq = np.dot(line_vec, line_vec)
                
                if line_norm_sq > 1e-9:
                    t = np.dot(p0_np - p1_np, line_vec) / line_norm_sq
                    t = np.clip(t, 0, 1)
                    closest_point = p1_np + t * line_vec
                    self.draw_distance_lines(solid_lines=[(p0_np, closest_point)], dashed_lines=[(p1_np,p2_np)])
        
        self.remove_distance_button.setEnabled(True)
        if self.distance_line_actors:
            self.iren.Render()

    def get_pos_by_index(self, index):
        """Gets the coordinates of a point by index, if it is defined."""
        if index is not None and 0 <= index < len(self.points) and isinstance(self.points[index][0], tuple):
            return self.points[index][0]
        return None

    def highlight_points(self, indices):
        """Highlights the points at the given indices."""
        for idx in indices:
            if idx is not None and 0 <= idx < len(self.points) and isinstance(self.points[idx][0], tuple):
                _, sphere_actor, text_follower = self.points[idx]
                if sphere_actor: sphere_actor.GetProperty().SetColor(self.blue_highlight_color)
                if text_follower: text_follower.GetProperty().SetColor(self.blue_highlight_color)

    def unhighlight_distance(self):
        """Removes the highlight from the currently selected distance."""
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

    def draw_distance_lines(self, solid_lines=[], dashed_lines=[]):
        """Draws a set of solid and/or dashed line actors in the 3D scene for distance visualization."""
        self.remove_distance_lines()
        
        for p1, p2 in solid_lines:
            line_source = vtk.vtkLineSource()
            line_source.SetPoint1(p1)
            line_source.SetPoint2(p2)
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
            p1 = np.array(p1_coords); p2 = np.array(p2_coords)
            length = np.linalg.norm(p2 - p1)
            if length < 1e-6: continue
            
            direction = (p2 - p1) / length
            num_segments = 10; dash_ratio = 0.6
            segment_length = length / num_segments; dash_length = segment_length * dash_ratio
            
            points = vtk.vtkPoints(); lines = vtk.vtkCellArray()
            point_id_counter = 0; current_pos = np.copy(p1)
            
            for _ in range(num_segments):
                start_point = current_pos
                end_point = start_point + direction * dash_length
                if np.linalg.norm(end_point - p1) > length: end_point = p2
                points.InsertNextPoint(start_point); points.InsertNextPoint(end_point)
                line = vtk.vtkLine(); line.GetPointIds().SetId(0, point_id_counter); line.GetPointIds().SetId(1, point_id_counter + 1)
                lines.InsertNextCell(line)
                point_id_counter += 2
                current_pos = start_point + direction * segment_length
                if np.linalg.norm(current_pos - p1) >= length: break

            polydata = vtk.vtkPolyData(); polydata.SetPoints(points); polydata.SetLines(lines)
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(polydata)
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            prop = actor.GetProperty(); prop.SetColor(self.blue_highlight_color); prop.SetLineWidth(2)
            self.ren.AddActor(actor)
            self.distance_line_actors.append(actor)

    def remove_distance_lines(self):
        """Removes all currently displayed distance line actors from the 3D scene."""
        if self.distance_line_actors:
            for actor in self.distance_line_actors:
                self.ren.RemoveActor(actor)
            self.distance_line_actors = []

    def on_angle_selected(self, item):
        """Handles user clicks on an item in the angles list."""
        index = item.data(QtCore.Qt.UserRole)
        if index is None: return
        self.toggle_angle_highlight(index)

    def toggle_angle_highlight(self, index):
        """Toggles the highlight state for an angle, updating UI items directly without rebuilding the list."""
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

    def highlight_angle(self, index):
        """Highlights an angle at the given index."""
        if index is None or not (0 <= index < len(self.angle_definitions)):
             self.unhighlight_angle(); return

        self.unhighlight_all()
        self.selected_angle_index = index
        
        triplet = self.angle_definitions[index]
        idx1=self.get_index_by_label(triplet[0]); idxV=self.get_index_by_label(triplet[1]); idx2=self.get_index_by_label(triplet[2])
        pos1, posV, pos2 = None, None, None
        
        points_colored = False
        for current_idx in [idx1, idxV, idx2]:
            if current_idx is not None and 0 <= current_idx < len(self.points) and \
               isinstance(self.points[current_idx][0], tuple): 
                _, sphere_actor, text_follower = self.points[current_idx]
                if sphere_actor: 
                    sphere_actor.GetProperty().SetColor(self.blue_highlight_color)
                    points_colored = True
                if text_follower: text_follower.GetProperty().SetColor(self.blue_highlight_color)
                
                if current_idx == idx1: pos1 = self.points[current_idx][0]
                if current_idx == idxV: posV = self.points[current_idx][0]
                if current_idx == idx2: pos2 = self.points[current_idx][0]
        
        if pos1 and posV and pos2: self.draw_angle_lines(posV, pos1, pos2)
        self.remove_angle_button.setEnabled(True)
        if points_colored or self.angle_line_actors: 
            self.iren.Render()

    def unhighlight_angle(self):
        """Removes the highlight from the currently selected angle."""
        if self.selected_angle_index is not None:
            sai = self.selected_angle_index
            self.selected_angle_index = None
            self.remove_angle_button.setEnabled(False)
            self.remove_angle_lines() 

            colors_reset = False
            try:
                if 0 <= sai < len(self.angle_definitions):
                    triplet = self.angle_definitions[sai]
                    idx1=self.get_index_by_label(triplet[0]); idxV=self.get_index_by_label(triplet[1]); idx2=self.get_index_by_label(triplet[2])
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

    def draw_angle_lines(self, vertex_pos, point1_pos, point2_pos):
        """Draws line actors in the 3D scene from a vertex point to two other points for angle visualization."""
        self.remove_angle_lines()
        colors = [self.angle_highlight_color, self.angle_highlight_color]
        for i, p_end in enumerate([point1_pos, point2_pos]):
            line_source = vtk.vtkLineSource(); line_source.SetPoint1(vertex_pos); line_source.SetPoint2(p_end); line_source.Update()
            mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(line_source.GetOutputPort())
            actor = vtk.vtkActor(); actor.SetMapper(mapper)
            prop = actor.GetProperty(); prop.SetColor(colors[i]); prop.SetLineWidth(2)
            self.ren.AddActor(actor); self.angle_line_actors.append(actor)

    def remove_angle_lines(self):
        """Removes any currently displayed angle line actors from the 3D scene."""
        if self.angle_line_actors:
            for actor in self.angle_line_actors: self.ren.RemoveActor(actor)
            self.angle_line_actors = []

    def unhighlight_all(self):
        """Unhighlights all currently highlighted items (points, distances, angles)."""
        dist_idx = self.selected_distance_index; angle_idx = self.selected_angle_index
        sel_pt_idx = self.selected_point_index; hl_pt_idx = self.currently_highlighted_point_index
        if dist_idx is not None: self.unhighlight_distance()
        if angle_idx is not None: self.unhighlight_angle()   
        if sel_pt_idx is not None: self.unhighlight_selected_point()
        if hl_pt_idx is not None: self.unhighlight_blue_point()

    def get_defined_point_labels(self):
        """Returns a list of labels of all points that are currently defined (have coordinates)."""
        defined_labels = []
        for i, (pos_data, _, _) in enumerate(self.points):
            if isinstance(pos_data, tuple):
                 if i < len(self.all_labels_in_order):
                     defined_labels.append(self.all_labels_in_order[i])
        return defined_labels

    def add_distance_definition(self):
        """Opens a dialog for the user to define a new distance by selecting points."""
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

    def remove_selected_distance(self):
        """Removes the currently selected distance definition after user confirmation."""
        if self.selected_distance_index is None:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Select distance to remove."); return
        
        idx_to_remove = self.selected_distance_index
        if not (0 <= idx_to_remove < len(self.distance_definitions)): return

        pair_to_remove = self.distance_definitions[idx_to_remove]
        confirmation_text = f"Remove distance {pair_to_remove[0]}-{pair_to_remove[1]}{pair_to_remove[2]}?" if len(pair_to_remove) == 3 else f"Remove distance {pair_to_remove[0]}-{pair_to_remove[1]}?"

        reply = QtWidgets.QMessageBox.question(self, "Confirm Removal", confirmation_text, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.unhighlight_distance()
            del self.distance_definitions[idx_to_remove]
            self.distances.pop(pair_to_remove, None)
            self.distances.pop((pair_to_remove[1],pair_to_remove[0]), None)
            self.update_distances_panel()
            self.unsaved_changes = True

    def add_angle_definition(self):
        """Opens a dialog for the user to define a new angle by selecting three points."""
        defined_labels = self.get_defined_point_labels()
        if len(defined_labels) < 3:
            QtWidgets.QMessageBox.warning(self, "Not Enough Points", "Need at least three defined points for an angle.")
            return

        dialog = SelectPointsDialog(defined_labels, num_points=3, title="Add Angle", parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            labels = dialog.getSelectedLabels()
            l1, v, l2 = labels[0], labels[1], labels[2]

            if l1==v or l2==v or l1==l2:
                QtWidgets.QMessageBox.warning(self, "Invalid Selection", "Please select three different points."); return

            new_triplet = (l1, v, l2); rev_triplet = (l2, v, l1)
            if any(t == new_triplet or t == rev_triplet for t in self.angle_definitions):
                QtWidgets.QMessageBox.warning(self, "Duplicate", f"Angle {l1}-{v}-{l2} already defined."); return
            
            self.angle_definitions.append(new_triplet)
            self.calculate_angles()
            self.unsaved_changes = True

    def remove_selected_angle(self):
        """Removes the currently selected angle definition after user confirmation."""
        if self.selected_angle_index is None:
            QtWidgets.QMessageBox.warning(self, "No Selection", "Select angle to remove."); return

        idx_to_remove = self.selected_angle_index
        if not (0 <= idx_to_remove < len(self.angle_definitions)): return

        triplet_to_remove = self.angle_definitions[idx_to_remove]
        reply = QtWidgets.QMessageBox.question(self, "Confirm", f"Remove angle {triplet_to_remove[0]}-{triplet_to_remove[1]}-{triplet_to_remove[2]}?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.unhighlight_angle()
            del self.angle_definitions[idx_to_remove]
            self.angles.pop(triplet_to_remove, None)
            self.angles.pop((triplet_to_remove[2],triplet_to_remove[1],triplet_to_remove[0]), None)
            self.update_angles_panel()
            self.unsaved_changes = True

    def open_stl(self):
        """Opens a file dialog for the user to select an STL file and loads the model."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open STL File", "", "STL Files (*.stl)")
        if filename:
            self.load_stl(filename)

    def load_stl(self, filename):
        """Loads an STL model from the given filename and resets the measurement state."""
        try:
            reader = vtk.vtkSTLReader(); reader.SetFileName(filename); reader.Update()
            polydata = reader.GetOutput()
            if not polydata or polydata.GetNumberOfPoints() == 0:
                 QtWidgets.QMessageBox.critical(self, "Error", f"Invalid STL: {filename}"); return

            if self.actor: self.ren.RemoveActor(self.actor)
            self.actor = vtk.vtkActor(); self.actor.SetMapper(vtk.vtkPolyDataMapper())
            self.actor.GetMapper().SetInputConnection(reader.GetOutputPort())
            self.ren.AddActor(self.actor)
            
            self.current_stl_path = filename
            self.filename_annotation.SetText(vtk.vtkCornerAnnotation.UpperRight, os.path.basename(filename))

            self._reset_state_without_confirmation()

            self.ren.ResetCamera()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load STL: {e}\n{traceback.format_exc()}")
            self.current_stl_path = None; self.actor = None
            self.filename_annotation.SetText(vtk.vtkCornerAnnotation.UpperRight, "")
            self._reset_state_without_confirmation()

    def open_points(self):
        """Opens a points data file (TXT)."""
        txt_filename_to_load = ""

        if self.current_stl_path and self.actor:
            base_name = os.path.splitext(self.current_stl_path)[0]
            txt_filename_to_load = base_name + ".txt"
            self.load_points(txt_filename_to_load)
        else:
            dialog_title = "Open Points File - Associated STL will be loaded"
            selected_filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, dialog_title, "", "Text Files (*.txt)")
            
            if not selected_filename: return

            txt_filename_to_load = selected_filename
            base_txt_name_no_ext = os.path.splitext(txt_filename_to_load)[0]
            stl_filename_associated_with_txt = base_txt_name_no_ext + ".stl"
            
            if not os.path.exists(stl_filename_associated_with_txt):
                QtWidgets.QMessageBox.critical(self, "Error", f"Cannot load points: Associated STL file '{os.path.basename(stl_filename_associated_with_txt)}' not found.")
                return
                
            self.load_stl(stl_filename_associated_with_txt)
            self.load_points(txt_filename_to_load)

    def load_points(self, txt_filename):
        if not self.actor:
            QtWidgets.QMessageBox.warning(self, "Warning", "Load STL model before loading points.")
            return
        
        if not os.path.exists(txt_filename):
            self._reset_state_without_confirmation()
            return

        temp_points_config = []
        temp_all_labels = []
        temp_dist_defs = []
        temp_angle_defs = []
        current_section = None 
        
        file_content = ""
        try:
            # Read the file in binary mode first to avoid immediate decoding errors
            with open(txt_filename, 'rb') as f:
                raw_data = f.read()
            
            # Try to decode as UTF-8 (for new files)
            try:
                file_content = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                # If UTF-8 fails, fall back to a common Windows encoding (for old files)
                file_content = raw_data.decode('cp1250')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not read file {os.path.basename(txt_filename)}: {e}")
            return

        try:
            lines = file_content.splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.upper() == "[POINTS]":
                    current_section = "POINTS"
                    continue
                elif line.upper() == "[DISTANCES]":
                    current_section = "DISTANCES"
                    continue
                elif line.upper() == "[ANGLES]":
                    current_section = "ANGLES"
                    continue

                if '\t' in line: # New tab-separated format parsing
                    if line.lower().startswith("label\t") or line.lower().startswith("type\t"):
                        continue
                    
                    parts = line.split('\t')
                    if current_section == "POINTS":
                        if len(parts) >= 2:
                            label, status = parts[0], parts[1].lower()
                            temp_all_labels.append(label)
                            if status == "defined" and len(parts) >= 5:
                                try:
                                    coords = (float(parts[2]), float(parts[3]), float(parts[4]))
                                    temp_points_config.append((coords, label))
                                except (ValueError, IndexError):
                                    temp_points_config.append(("to_be_defined", label))
                            elif status == "skipped":
                                temp_points_config.append(("skipped", label))
                            else:
                                temp_points_config.append(("to_be_defined", label))

                    elif current_section == "DISTANCES":
                        if len(parts) >= 3:
                            p1, p2 = parts[1], parts[2]
                            p3 = parts[3] if len(parts) > 3 and parts[3].strip() else None
                            if p3:
                                temp_dist_defs.append((p1, p2, p3))
                            else:
                                temp_dist_defs.append((p1, p2))
                    
                    elif current_section == "ANGLES":
                        if len(parts) >= 4:
                            p1, v, p2 = parts[1], parts[2], parts[3]
                            temp_angle_defs.append((p1, v, p2))

                elif ':' in line: # Old colon-separated and simple formats parsing
                    # Case 1: Simple format (no sections, e.g., "Point I: ...")
                    if current_section is None and line.lower().startswith("point "):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            label_str = parts[0][len("Point"):].strip()
                            temp_all_labels.append(label_str)
                            value_str = parts[1].strip().lower()
                            if value_str == "skipped":
                                temp_points_config.append(("skipped", label_str))
                            else:
                                coords_str_list = value_str.split()
                                if len(coords_str_list) >= 3:
                                    coords_tuple = (float(coords_str_list[0]), float(coords_str_list[1]), float(coords_str_list[2]))
                                    temp_points_config.append((coords_tuple, label_str))
                                else:
                                    temp_points_config.append(("to_be_defined", label_str))
                    
                    # Case 2: Old format with sections
                    elif current_section == "POINTS":
                        parts = line.split(":", 1)
                        if len(parts) == 2 and parts[0].lower().startswith("point"):
                            label_str = parts[0][len("Point"):].strip()
                            temp_all_labels.append(label_str)
                            value_str = parts[1].strip().lower()
                            if value_str == "skipped":
                                temp_points_config.append(("skipped", label_str))
                            elif value_str == "to_be_defined":
                                temp_points_config.append(("to_be_defined", label_str))
                            else:
                                coords_str_list = value_str.split()
                                if len(coords_str_list) >= 3:
                                    coords_tuple = (float(coords_str_list[0]), float(coords_str_list[1]), float(coords_str_list[2]))
                                    temp_points_config.append((coords_tuple, label_str))
                                else:
                                    temp_points_config.append(("to_be_defined", label_str))
                    elif current_section == "DISTANCES":
                        try:
                            def_part, _ = line.split(':', 1)
                            def_part = def_part.strip()
                            if "-" in def_part:
                                parts = def_part.split('-', 1)
                                p0 = parts[0].strip()
                                line_str = parts[1].strip()
                                line_str_no_apostrophe = line_str.replace("'", "")
                                if len(line_str) >= 2 and len(line_str_no_apostrophe) >= 2 and line_str[0] == line_str_no_apostrophe[1]:
                                    temp_dist_defs.append((p0, line_str[0], line_str[1:]))
                                else:
                                    temp_dist_defs.append((p0, line_str))
                        except Exception:
                            pass
                    elif current_section == "ANGLES":
                        try:
                            def_part, _ = line.split(':', 1)
                            temp_angle_defs.append(tuple(def_part.strip().split('-')))
                        except Exception:
                            pass

            self._reset_state_without_confirmation()

            if temp_points_config:
                self.points = []
                self.all_labels_in_order = temp_all_labels
                scale_factor = self.point_size_slider.value() / 50.0
                for pos_or_status, label in temp_points_config:
                    if isinstance(pos_or_status, tuple):
                        sphere_actor, text_follower = self._create_point_actors(pos_or_status, label, self.default_color, scale_factor)
                        self.points.append((pos_or_status, sphere_actor, text_follower))
                    else:
                        self.points.append((pos_or_status, None, None))
            
            if temp_dist_defs:
                self.distance_definitions = temp_dist_defs
            if temp_angle_defs:
                self.angle_definitions = temp_angle_defs

            self.find_next_undefined()
            self.unsaved_changes = False
            self.save_button.setEnabled(True)
            QtWidgets.QMessageBox.information(self, "Load Complete", f"Points data loaded from {os.path.basename(txt_filename)}.")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to parse points file: {e}\n{traceback.format_exc()}")
            self._reset_state_without_confirmation()
        finally:
            self.update_prompt()
            self.update_info_panel()
            self.calculate_all_measurements()
            self.unhighlight_all()
            self.iren.Render()

    def save_points(self):
        if not self.current_stl_path:
            QtWidgets.QMessageBox.critical(self, "Error", "No STL file loaded. Cannot determine save filename."); return
        
        save_filename = os.path.splitext(self.current_stl_path)[0] + ".txt"

        if os.path.exists(save_filename):
            reply = QtWidgets.QMessageBox.question(self, "Confirm Overwrite", f"File {os.path.basename(save_filename)} exists. Overwrite?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No: return

        try:
            self.calculate_all_measurements()
            with open(save_filename, "w", encoding='utf-8') as f:
                f.write("# CleftMeter Data\n")
                f.write(f"# STL File: {os.path.basename(self.current_stl_path)}\n")
                f.write("# To import into Excel: open this file, press Ctrl+A (select all), Ctrl+C (copy), and paste into a blank Excel sheet.\n\n")

                f.write("[POINTS]\n")
                f.write("Label\tStatus\tX\tY\tZ\n")
                for i, (pos_data, _, _) in enumerate(self.points):
                    label = self.all_labels_in_order[i]
                    if pos_data == "to_be_defined":
                        f.write(f"{label}\tto_be_defined\t\t\t\n")
                    elif pos_data == "skipped":
                        f.write(f"{label}\tskipped\t\t\t\n")
                    else:
                        f.write(f"{label}\tdefined\t{pos_data[0]:.6f}\t{pos_data[1]:.6f}\t{pos_data[2]:.6f}\n")

                f.write("\n[DISTANCES]\n")
                f.write("Type\tPoint 1\tPoint 2\tPoint 3\tValue\tUnit\n")
                for definition in self.distance_definitions:
                    val = self.distances.get(definition, "n/a")
                    if len(definition) == 2:
                        p1, p2 = definition
                        f.write(f"Point-Point\t{p1}\t{p2}\t\t{val}\tmm\n")
                    elif len(definition) == 3:
                        p0, p1, p2 = definition
                        f.write(f"Point-Line\t{p0}\t{p1}\t{p2}\t{val}\tmm\n")

                f.write("\n[ANGLES]\n")
                f.write("Type\tPoint 1\tVertex\tPoint 2\tValue\tUnit\n")
                for triplet in self.angle_definitions:
                    val_str = self.angles.get(triplet, "n/a")
                    val_num = val_str.replace('°', '') if isinstance(val_str, str) else val_str
                    p1, v, p2 = triplet
                    f.write(f"Angle\t{p1}\t{v}\t{p2}\t{val_num}\tdegrees\n")
            
            QtWidgets.QMessageBox.information(self, "Success", f"Data saved to {os.path.basename(save_filename)}.")
            self.unsaved_changes = False
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save file: {e}\n{traceback.format_exc()}")

    def eventFilter(self, obj, event):
        """Filters and processes keyboard events for the main window."""
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.text().lower(); key_sym = event.key()
            if key == 'd':
                if self.find_next_undefined_index() is not None:
                    self.unhighlight_all(); self.interactor_style.d_pressed = True
                    self.update_prompt(); self.update_info_panel()
                return True
            elif key == 'e':
                self.unhighlight_all(); self.interactor_style.e_pressed = True
                self.prompt_label.setText("Edit (select point in list)"); self.update_info_panel()
                return True
            elif key == 'n':
                if self.interactor_style.e_pressed and self.selected_point_index is not None:
                    self.skip_selected_point(); self.prompt_label.setText("Edit (select point in list)")
                elif not self.interactor_style.e_pressed and not self.interactor_style.d_pressed and not self.interactor_style.delete_mode:
                     self.defer_point()
                return True
            elif key_sym == QtCore.Qt.Key_Delete:
                 self.unhighlight_all(); self.interactor_style.delete_mode = True
                 self.prompt_label.setText("Delete (select point in list)"); self.update_info_panel()
                 return True
            elif key == 'w':
                if self.actor: self.actor.GetProperty().SetRepresentationToWireframe(); self.iren.ReInitialize()
                return True
            elif key == 's':
                if self.actor: self.actor.GetProperty().SetRepresentationToSurface(); self.iren.ReInitialize()
                return True
        elif event.type() == QtCore.QEvent.KeyRelease:
            key = event.text().lower(); key_sym = event.key()
            if key == 'd':
                if self.interactor_style.d_pressed:
                    self.interactor_style.d_pressed = False; self.interactor_style.last_picked_point = None
                    self.update_prompt(); self.update_info_panel()
                return True
            elif key == 'e':
                if self.interactor_style.e_pressed:
                    self.interactor_style.e_pressed = False
                    if self.selected_point_index is not None: self.unhighlight_selected_point()
                    self.update_prompt()
                return True
            elif key_sym == QtCore.Qt.Key_Delete:
                if self.interactor_style.delete_mode:
                    self.interactor_style.delete_mode = False; self.update_prompt()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """Handles the close event of the main application window."""
        if self.unsaved_changes:
            reply = QtWidgets.QMessageBox.question(self, "Confirm Close", "You have unsaved changes. Do you want to save before closing?", QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Save)
            if reply == QtWidgets.QMessageBox.Save:
                self.save_points()
                if not self.unsaved_changes: event.accept()
                else: event.ignore()
            elif reply == QtWidgets.QMessageBox.Discard: event.accept()
            else: event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = STLViewer()
    window.show()
    sys.exit(app.exec())
