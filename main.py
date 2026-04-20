import sys
import os
import wave
import threading
import queue
import numpy as np
import re
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QComboBox, QFileDialog, QStackedWidget, QMessageBox,
                           QListWidget, QSlider, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush
try:
    import sounddevice as sd
    import soundfile as sf
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("Audio libraries not available - recording will be simulated")


class VUMeter(QWidget):
    def __init__(self):
        super().__init__()
        self.left_level = 0
        self.right_level = 0
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)
        
    def update_levels(self, left, right):
        self.left_level = left
        self.right_level = right
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        # Meter dimensions
        width = self.width()
        height = self.height()
        meter_width = width // 2 - 10
        meter_height = height - 20
        
        # Left meter
        left_x = 5
        left_y = 10
        self.draw_meter(painter, left_x, left_y, meter_width, meter_height, self.left_level, "L")
        
        # Right meter
        right_x = width // 2 + 5
        right_y = 10
        self.draw_meter(painter, right_x, right_y, meter_width, meter_height, self.right_level, "R")
        
    def draw_meter(self, painter, x, y, width, height, level, label):
        # Draw meter background
        painter.fillRect(x, y, width, height, QColor(40, 40, 40))
        
        # Draw level bars with color coding
        bar_width = int(width * level)
        
        # Green zone (0-70%)
        green_width = min(bar_width, int(width * 0.7))
        painter.fillRect(x, y, green_width, height, QColor(0, 255, 0))
        
        # Yellow zone (70-90%)
        if bar_width > int(width * 0.7):
            yellow_start = int(width * 0.7)
            yellow_width = min(bar_width - yellow_start, int(width * 0.2))
            painter.fillRect(x + yellow_start, y, yellow_width, height, QColor(255, 255, 0))
        
        # Red zone (90-100%)
        if bar_width > int(width * 0.9):
            red_start = int(width * 0.9)
            red_width = bar_width - red_start
            painter.fillRect(x + red_start, y, red_width, height, QColor(255, 0, 0))
        
        # Draw border
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(x, y, width, height)
        
        # Draw label
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(x + 5, y - 2, label)


class WaveformWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.waveform_data = []
        self.position = 0
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)
        self.setStyleSheet("background-color: #1a1a1a; border: 1px solid #404040;")
        
    def update_waveform(self, audio_data):
        # Convert audio data to RMS levels for visualization
        if len(audio_data) > 0:
            # Handle both single values and arrays
            if isinstance(audio_data, (list, tuple)) and len(audio_data) == 1:
                rms = audio_data[0]  # Single value from buffer
            else:
                rms = np.sqrt(np.mean(audio_data**2))  # Calculate from array
                
            self.waveform_data.append(rms)
            
            # Keep only last 1000 points for performance
            if len(self.waveform_data) > 1000:
                self.waveform_data = self.waveform_data[-1000:]
                
            self.position = len(self.waveform_data)
            self.update()
            
    def clear_waveform(self):
        self.waveform_data = []
        self.position = 0
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clear background
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        if len(self.waveform_data) < 2:
            return
            
        # Draw waveform
        width = self.width()
        height = self.height()
        center_y = height // 2
        
        # Scale data to fit widget
        if len(self.waveform_data) > 1:
            x_step = width / len(self.waveform_data)
            
            painter.setPen(QPen(QColor(74, 158, 255), 2))
            
            for i in range(1, len(self.waveform_data)):
                x1 = (i - 1) * x_step
                x2 = i * x_step
                
                # Scale RMS values to pixel height
                y1 = center_y - int(self.waveform_data[i-1] * height * 0.8)
                y2 = center_y - int(self.waveform_data[i] * height * 0.8)
                
                painter.drawLine(int(x1), y1, int(x2), y2)
                
        # Draw center line
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawLine(0, center_y, width, center_y)


class TrackNamingDialog(QDialog):
    def __init__(self, track_number, parent=None):
        super().__init__(parent)
        self.track_number = track_number
        self.setWindowTitle(f"Name Track {track_number}")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Instructions
        label = QLabel(f"Enter name for Track {self.track_number}:")
        layout.addWidget(label)
        
        # Track name input
        self.track_name_input = QLineEdit()
        self.track_name_input.setPlaceholderText(f"Track {self.track_number}")
        layout.addWidget(self.track_name_input)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def get_track_name(self):
        return self.track_name_input.text().strip() or f"Track {self.track_number}"


class GrooveRipApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Thread safety
        self.frames_mutex = QMutex()
        self.ui_mutex = QMutex()
        
        # Resource management
        self.audio_stream = None
        self.monitoring_stream = None
        self.recording_thread = None
        self.monitoring_thread = None
        self.progress_timer = None
        self.ui_update_timer = None
        
        self.recording_data = {
            'artist_name': '',
            'album_name': '',
            'lp_type': 'LP',
            'side': '',
            'sample_rate': '',
            'format': 'WAV',
            'monitoring': False,
            'directory': '',
            'device_index': None,
            'device_name': ''
        }
        self.is_recording = False
        self.frames = []
        self.audio_queue = None
        
        # Track detection
        self.detected_tracks = []
        self.track_boundaries = []
        self.silence_threshold = 0.01
        self.current_track_start = 0
        
        # UI components
        self.vu_meter = None
        self.waveform_widget = None
        
        # UI update timer for VU meter and waveform
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self.update_ui_components)
        self.ui_update_timer.start(50)  # Update every 50ms (20 FPS)
        
        # Buffer for UI updates (thread-safe)
        self.vu_buffer = {'left': 0, 'right': 0}
        self.waveform_buffer = []
        
        # Configuration persistence
        self.config_file = "grooverip_config.json"
        self.load_config()
        
        self.init_ui()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Apply saved settings to defaults
                    if 'directory' in config:
                        self.recording_data['directory'] = config['directory']
                    if 'sample_rate' in config:
                        self.recording_data['sample_rate'] = config['sample_rate']
                    if 'format' in config:
                        self.recording_data['format'] = config['format']
                    if 'lp_type' in config:
                        self.recording_data['lp_type'] = config['lp_type']
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            config = {
                'directory': self.recording_data['directory'],
                'sample_rate': self.recording_data['sample_rate'],
                'format': self.recording_data['format'],
                'lp_type': self.recording_data['lp_type']
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def sanitize_filename(self, filename):
        """Sanitize filename for cross-platform compatibility"""
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        # Limit length
        sanitized = sanitized[:100]
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        return sanitized or 'unnamed'
    
    def validate_device(self, device_index):
        """Validate that the selected device can record audio"""
        if not SOUND_AVAILABLE or device_index is None:
            return False
        
        try:
            device_info = sd.query_devices(device_index)
            return device_info['max_input_channels'] > 0
        except Exception:
            return False
    
    def parse_sample_rate(self, rate_text):
        """Robust sample rate parsing"""
        # Extract numbers from text like "44100 Hz (CD Quality)"
        match = re.search(r'\d+', rate_text)
        if match:
            return int(match.group())
        return 44100  # Default fallback
    
    def init_ui(self):
        self.setWindowTitle("GrooveRip - Vinyl Recording Tool")
        self.setGeometry(100, 100, 600, 500)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 16px;
                color: #e0e0e0;
                margin: 10px;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
            QPushButton {
                background-color: #4a9eff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #2968a8;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #808080;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 10px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Title
        title_label = QLabel("GrooveRip")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #4a9eff;
            margin: 20px;
        """)
        layout.addWidget(title_label)
        
        # Create single page form
        self.create_single_page_form()
        layout.addWidget(self.form_widget)
        
        # Project creation button at bottom
        self.create_project_controls()
        layout.addWidget(self.project_widget)
        
    def create_single_page_form(self):
        self.form_widget = QWidget()
        layout = QVBoxLayout()
        self.form_widget.setLayout(layout)
        
        # Artist and Album row
        artist_album_layout = QHBoxLayout()
        
        # Artist section
        artist_layout = QVBoxLayout()
        artist_label = QLabel("Artist:")
        artist_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        artist_layout.addWidget(artist_label)
        
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("e.g., Pink Floyd")
        self.artist_input.textChanged.connect(self.validate_form)
        artist_layout.addWidget(self.artist_input)
        artist_album_layout.addLayout(artist_layout)
        
        # Album section
        album_layout = QVBoxLayout()
        album_label = QLabel("Album:")
        album_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        album_layout.addWidget(album_label)
        
        self.album_input = QLineEdit()
        self.album_input.setPlaceholderText("e.g., The Dark Side of the Moon")
        self.album_input.textChanged.connect(self.validate_form)
        album_layout.addWidget(self.album_input)
        artist_album_layout.addLayout(album_layout)
        
        layout.addLayout(artist_album_layout)
        
        # LP Type and Side row
        lp_type_side_layout = QHBoxLayout()
        
        # LP Type section
        lp_type_layout = QVBoxLayout()
        lp_type_label = QLabel("LP Type:")
        lp_type_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        lp_type_layout.addWidget(lp_type_label)
        
        self.lp_type_combo = QComboBox()
        self.lp_type_combo.addItems(["LP", "2LP"])
        self.lp_type_combo.currentTextChanged.connect(self.update_sides)
        lp_type_layout.addWidget(self.lp_type_combo)
        lp_type_side_layout.addLayout(lp_type_layout)
        
        # Side section
        side_layout = QVBoxLayout()
        side_label = QLabel("Side:")
        side_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        side_layout.addWidget(side_label)
        
        self.side_combo = QComboBox()
        self.side_combo.addItems(["Side A", "Side B"])
        self.side_combo.currentTextChanged.connect(self.validate_form)
        side_layout.addWidget(self.side_combo)
        lp_type_side_layout.addLayout(side_layout)
        
        layout.addLayout(lp_type_side_layout)
        
        # Sample Rate row
        rate_layout = QHBoxLayout()
        rate_label = QLabel("Sample Rate:")
        rate_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        rate_layout.addWidget(rate_label)
        
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100 Hz (CD Quality)", "48000 Hz (DVD Quality)", 
                                        "96000 Hz (High Resolution)", "192000 Hz (Studio Quality)"])
        self.sample_rate_combo.currentTextChanged.connect(self.validate_form)
        rate_layout.addWidget(self.sample_rate_combo)
        layout.addLayout(rate_layout)
        
        # Format and Device row
        format_device_layout = QHBoxLayout()
        
        # Format section
        format_layout = QVBoxLayout()
        format_label = QLabel("Format:")
        format_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        format_layout.addWidget(format_label)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["WAV", "MP3", "FLAC"])
        self.format_combo.currentTextChanged.connect(self.validate_form)
        format_layout.addWidget(self.format_combo)
        format_device_layout.addLayout(format_layout)
        
        # Device section
        device_layout = QVBoxLayout()
        device_label = QLabel("Recording Device:")
        device_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        device_layout.addWidget(device_label)
        
        self.device_combo = QComboBox()
        self.populate_devices()
        self.device_combo.currentTextChanged.connect(self.validate_form)
        device_layout.addWidget(self.device_combo)
        format_device_layout.addLayout(device_layout)
        
        layout.addLayout(format_device_layout)
        
        # Monitoring section
        monitoring_layout = QHBoxLayout()
        monitoring_label = QLabel("Real-time Monitoring:")
        monitoring_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        monitoring_layout.addWidget(monitoring_label)
        
        self.monitoring_checkbox = QPushButton("Enable Monitoring")
        self.monitoring_checkbox.setCheckable(True)
        self.monitoring_checkbox.clicked.connect(self.toggle_monitoring)
        self.monitoring_checkbox.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #4a9eff;
                border-color: #4a9eff;
            }
            QPushButton:hover {
                border-color: #4a9eff;
            }
        """)
        monitoring_layout.addWidget(self.monitoring_checkbox)
        monitoring_layout.addStretch()
        layout.addLayout(monitoring_layout)
        
                
        # Directory section
        dir_label = QLabel("Output Directory:")
        dir_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        layout.addWidget(dir_label)
        
        dir_layout = QHBoxLayout()
        self.directory_input = QLineEdit()
        self.directory_input.setReadOnly(True)
        self.directory_input.setPlaceholderText("No directory selected")
        dir_layout.addWidget(self.directory_input)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_directory)
        browse_btn.setFixedWidth(100)
        dir_layout.addWidget(browse_btn)
        layout.addLayout(dir_layout)
        
    def populate_devices(self):
        if SOUND_AVAILABLE:
            try:
                devices = sd.query_devices()
                self.device_combo.clear()
                print("\n=== Audio Devices ===")
                for i, device in enumerate(devices):
                    print(f"Device {i}: {device['name']}")
                    print(f"  Input channels: {device['max_input_channels']}")
                    print(f"  Output channels: {device['max_output_channels']}")
                    print(f"  Sample rate: {device['default_samplerate']}")
                    if device['max_input_channels'] > 0:
                        self.device_combo.addItem(f"{device['name']} (In: {device['max_input_channels']})", i)
                print(f"Default input device: {sd.default.device[0]}")
                print(f"Default output device: {sd.default.device[1]}")
                print("===================\n")
            except Exception as e:
                self.device_combo.addItem("Error loading devices", -1)
                print(f"Error populating devices: {e}")
        else:
            self.device_combo.addItem("Audio libraries not installed - simulation mode", -1)
            
    def create_project_controls(self):
        self.project_widget = QWidget()
        layout = QVBoxLayout()
        self.project_widget.setLayout(layout)
        
        # Summary
        summary_label = QLabel("Project Summary:")
        summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4a9eff;")
        layout.addWidget(summary_label)
        
        self.summary_text = QLabel("Fill in all fields above to create project")
        self.summary_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_text.setWordWrap(True)
        layout.addWidget(self.summary_text)
        
        # Create project button
        self.create_project_btn = QPushButton("Create Project & Start Recording")
        self.create_project_btn.clicked.connect(self.create_project)
        self.create_project_btn.setEnabled(False)
        self.create_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                font-size: 16px;
                padding: 16px 32px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #808080;
            }
        """)
        layout.addWidget(self.create_project_btn)
        
    def update_sides(self):
        lp_type = self.lp_type_combo.currentText()
        self.recording_data['lp_type'] = lp_type
        
        # Store current selection
        current_side = self.side_combo.currentText()
        
        # Update side options based on LP type
        self.side_combo.clear()
        if lp_type == "LP":
            self.side_combo.addItems(["Side A", "Side B"])
        else:  # 2LP
            self.side_combo.addItems(["Side A", "Side B", "Side C", "Side D"])
        
        # Try to restore previous selection if it's still valid
        index = self.side_combo.findText(current_side)
        if index >= 0:
            self.side_combo.setCurrentIndex(index)
        
        self.validate_form()
        
    def toggle_monitoring(self):
        self.recording_data['monitoring'] = self.monitoring_checkbox.isChecked()
        
    def validate_form(self):
        # Update recording data
        self.recording_data['artist_name'] = self.artist_input.text().strip()
        self.recording_data['album_name'] = self.album_input.text().strip()
        self.recording_data['side'] = self.side_combo.currentText()
        self.recording_data['format'] = self.format_combo.currentText()
        
        # Use robust sample rate parsing
        sample_rate_text = self.sample_rate_combo.currentText()
        self.recording_data['sample_rate'] = str(self.parse_sample_rate(sample_rate_text))
        
        device_data = self.device_combo.currentData()
        if device_data is not None and device_data >= 0:
            # Validate device capabilities
            if self.validate_device(device_data):
                self.recording_data['device_index'] = device_data
                self.recording_data['device_name'] = self.device_combo.currentText()
            else:
                self.recording_data['device_index'] = None
                self.recording_data['device_name'] = ''
        else:
            self.recording_data['device_index'] = None
            self.recording_data['device_name'] = ''
        
        # Check if form is complete
        is_complete = (
            bool(self.recording_data['artist_name']) and
            bool(self.recording_data['album_name']) and
            bool(self.recording_data['directory']) and
            self.recording_data['device_index'] is not None
        )
        
        self.create_project_btn.setEnabled(is_complete)
        self.update_summary()
        
        # Save config when form changes
        self.save_config()
        
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.directory_input.setText(directory)
            self.recording_data['directory'] = directory
            self.validate_form()
            
    def update_summary(self):
        if self.create_project_btn.isEnabled():
            monitoring_status = "Enabled" if self.recording_data['monitoring'] else "Disabled"
            summary = f"""
Artist: {self.recording_data['artist_name']}
Album: {self.recording_data['album_name']}
LP Type: {self.recording_data['lp_type']}
Side: {self.recording_data['side']}
Sample Rate: {self.recording_data['sample_rate']} Hz
Format: {self.recording_data['format']}
Monitoring: {monitoring_status}
Device: {self.recording_data['device_name']}
Output Directory: {self.recording_data['directory']}
            """.strip()
            self.summary_text.setText(summary)
        else:
            self.summary_text.setText("Fill in all fields above to create project")
        
    def create_project(self):
        """Create project and open main recording interface"""
        # Store project settings
        self.project_settings = self.recording_data.copy()
        
        # Hide settings screen and show main recording interface
        self.form_widget.hide()
        self.project_widget.hide()
        
        # Create main recording interface
        self.create_main_recording_interface()
        
    def create_main_recording_interface(self):
        """Create the main recording and editing interface"""
        self.main_widget = QWidget()
        layout = QVBoxLayout()
        self.main_widget.setLayout(layout)
        
        # Title with project info
        title_layout = QHBoxLayout()
        title_label = QLabel(f"GrooveRip - {self.project_settings['artist_name']} - {self.project_settings['album_name']}")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4a9eff;")
        title_layout.addWidget(title_label)
        
        back_btn = QPushButton("Back to Settings")
        back_btn.clicked.connect(self.back_to_settings)
        back_btn.setFixedWidth(150)
        title_layout.addWidget(back_btn)
        layout.addLayout(title_layout)
        
        # Main recording area with track detection
        self.create_recording_area(layout)
        
        # Add main widget to window
        self.centralWidget().layout().addWidget(self.main_widget)
        
    def create_recording_area(self, parent_layout):
        """Create the main recording area with track detection"""
        recording_widget = QWidget()
        layout = QVBoxLayout()
        recording_widget.setLayout(layout)
        
        # Track detection controls
        track_controls = QHBoxLayout()
        detect_btn = QPushButton("Auto-Detect Tracks")
        detect_btn.clicked.connect(self.detect_tracks)
        detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                padding: 8px 16px;
            }
        """)
        track_controls.addWidget(detect_btn)
        
        self.track_threshold_label = QLabel("Silence Threshold:")
        track_controls.addWidget(self.track_threshold_label)
        
        self.track_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.track_threshold_slider.setRange(1, 100)
        self.track_threshold_slider.setValue(10)  # Lower default threshold
        self.track_threshold_slider.setMaximumWidth(200)
        self.track_threshold_slider.valueChanged.connect(self.update_threshold_label)
        track_controls.addWidget(self.track_threshold_slider)
        
        self.threshold_value_label = QLabel("0.010")
        track_controls.addWidget(self.threshold_value_label)
        
        track_controls.addStretch()
        layout.addLayout(track_controls)
        
        # Track list
        self.track_list_widget = QWidget()
        track_list_layout = QVBoxLayout()
        self.track_list_widget.setLayout(track_list_layout)
        
        track_list_label = QLabel("Detected Tracks:")
        track_list_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        track_list_layout.addWidget(track_list_label)
        
        self.track_list = QListWidget()
        self.track_list.setMaximumHeight(200)
        track_list_layout.addWidget(self.track_list)
        
        layout.addWidget(self.track_list_widget)
        
        # VU Meter and Waveform
        self.vu_meter = VUMeter()
        layout.addWidget(self.vu_meter)
        
        self.waveform_widget = WaveformWidget()
        layout.addWidget(self.waveform_widget)
        
        # Recording controls
        self.create_recording_controls_advanced(layout)
        
        parent_layout.addWidget(recording_widget)
        
    def create_recording_controls_advanced(self, parent_layout):
        """Create advanced recording controls"""
        controls_widget = QWidget()
        layout = QVBoxLayout()
        controls_widget.setLayout(layout)
        
        # Recording controls
        record_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4a4a;
                font-size: 16px;
                padding: 16px 32px;
            }
            QPushButton:hover {
                background-color: #cc3535;
            }
        """)
        record_layout.addWidget(self.record_btn)
        
        # Progress indicator
        self.progress_label = QLabel("Ready to record")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 14px; color: #4a9eff;")
        layout.addWidget(self.progress_label)
        
        layout.addLayout(record_layout)
        parent_layout.addWidget(controls_widget)
        
    def update_threshold_label(self):
        """Update the threshold value label"""
        value = self.track_threshold_slider.value()
        threshold = value / 1000.0
        self.threshold_value_label.setText(f"{threshold:.3f}")
        
    def detect_tracks(self):
        """Manual track detection for existing recording"""
        if not self.frames:
            QMessageBox.warning(self, "No Recording", "Please record some audio first.")
            return
            
        # Clear existing tracks
        self.track_boundaries = []
        self.current_track_start = 0
        self.silence_duration = 0
        
        # Process existing frames
        print("Running manual track detection on existing recording...")
        
        # Simple approach: split into equal parts for now
        total_frames = len(self.frames)
        sample_rate = int(float(self.project_settings['sample_rate']))
        
        # Create 4 equal tracks (typical for vinyl)
        frames_per_track = total_frames // 4
        for i in range(4):
            start = i * frames_per_track
            end = (i + 1) * frames_per_track if i < 3 else total_frames
            self.track_boundaries.append((start, end))
            
        QMessageBox.information(self, "Track Detection", 
                              f"Created 4 equal tracks from the recording.\nYou can adjust the silence threshold slider for better automatic detection.")
        
    def back_to_settings(self):
        """Return to project settings with proper cleanup"""
        # Stop recording if active
        if self.is_recording:
            reply = QMessageBox.question(self, 'Stop Recording', 
                                       'You are currently recording. Stop and return to settings?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_recording()
            else:
                return  # Don't go back if user chooses to continue recording
        
        # Hide main recording interface
        if hasattr(self, 'main_widget'):
            self.main_widget.hide()
        
        # Show settings screens
        self.form_widget.show()
        self.project_widget.show()
        
    def update_ui_components(self):
        """Update VU meter and waveform on main thread (thread-safe)"""
        if self.is_recording:
            with QMutexLocker(self.ui_mutex):
                # Update VU meter
                if self.vu_meter and hasattr(self, 'vu_buffer'):
                    self.vu_meter.update_levels(self.vu_buffer['left'], self.vu_buffer['right'])
                
                # Update waveform
                if self.waveform_widget and hasattr(self, 'waveform_buffer') and self.waveform_buffer:
                    # Use the most recent waveform data
                    self.waveform_widget.update_waveform([self.waveform_buffer[-1]])
                
    def toggle_recording(self):
        if not hasattr(self, 'is_recording') or not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        """Start recording with proper resource management"""
        try:
            # Validate device before starting
            if not self.validate_device(self.recording_data['device_index']):
                QMessageBox.critical(self, "Device Error", 
                                   "Selected recording device is not available or cannot record audio.")
                return
            
            self.is_recording = True
            
            # Thread-safe initialization
            with QMutexLocker(self.frames_mutex):
                self.frames = []
            
            # Initialize queue with proper size to prevent overflow
            self.audio_queue = queue.Queue(maxsize=10)  # Limit queue size
            
            # Reset track detection
            self.detected_tracks = []
            self.track_boundaries = []
            self.current_track_start = 0
            self.silence_duration = 0
            self.consecutive_silence = 0
            
            # Clear buffers (thread-safe)
            with QMutexLocker(self.ui_mutex):
                self.vu_buffer = {'left': 0, 'right': 0}
                self.waveform_buffer = []
            
            # Clear VU meter and waveform
            if self.vu_meter:
                self.vu_meter.update_levels(0, 0)
            if self.waveform_widget:
                self.waveform_widget.clear_waveform()
            
            # Update silence threshold from slider
            threshold_value = self.track_threshold_slider.value()
            # Better threshold calculation - slider 1-100 maps to 0.001-0.1
            self.silence_threshold = threshold_value / 1000.0
            print(f"Silence threshold set to: {self.silence_threshold}")
            
            # Update UI
            self.record_btn.setText("Stop Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4a4a;
                    font-size: 16px;
                    padding: 16px 32px;
                }
                QPushButton:hover {
                    background-color: #cc3535;
                }
            """)
            
            # Start progress indicator
            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self.update_progress)
            self.start_time = datetime.now()
            self.progress_timer.start(1000)  # Update every second
            
            # Start recording thread
            if SOUND_AVAILABLE and self.recording_data['device_index'] is not None:
                self.recording_thread = threading.Thread(target=self.record_audio, daemon=True)
                self.recording_thread.start()
                
                # Start monitoring if enabled
                if self.recording_data['monitoring']:
                    # Try system-level monitoring first (less glitchy)
                    try:
                        self.monitoring_thread = threading.Thread(target=self.monitor_audio_simple, daemon=True)
                        self.monitoring_thread.start()
                        print("Using simple monitoring mode")
                    except Exception as e:
                        print(f"Simple monitoring failed, trying advanced: {e}")
                        self.monitoring_thread = threading.Thread(target=self.monitor_audio, daemon=True)
                        self.monitoring_thread.start()
                        
                    # Test tone to verify monitoring works
                    print("Testing monitoring with test tone...")
                    self.test_monitoring()
            else:
                # Simulation mode
                self.recording_thread = threading.Thread(target=self.simulate_recording, daemon=True)
                self.recording_thread.start()
                
                # Test monitoring in simulation mode
                if self.recording_data['monitoring']:
                    self.test_monitoring()
                    
        except Exception as e:
            self.is_recording = False
            QMessageBox.critical(self, "Recording Error", f"Failed to start recording: {e}")
            self.cleanup_resources()
            
    def cleanup_resources(self):
        """Clean up all resources safely"""
        try:
            # Stop progress timer
            if self.progress_timer:
                self.progress_timer.stop()
            
            # Stop recording
            self.is_recording = False
            
            # Wait for threads with timeout
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
            
            if hasattr(self, 'monitoring_thread') and self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)
            
            # Clear audio queue
            if self.audio_queue:
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        break
            
            # Reset UI
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4aff4a;
                    font-size: 16px;
                    padding: 16px 32px;
                }
                QPushButton:hover {
                    background-color: #35cc35;
                }
            """)
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def record_audio(self):
        try:
            sample_rate = int(self.recording_data['sample_rate'])
            blocksize = 1024
            
            def callback(indata, frames, time, status):
                if status:
                    print(f"Callback status: {status}")
                if self.is_recording:
                    # Thread-safe frame storage
                    with QMutexLocker(self.frames_mutex):
                        self.frames.append(indata.copy())
                    
                    # Optimized VU meter calculation (minimal processing)
                    left_rms = np.sqrt(np.mean(indata[:, 0]**2))
                    right_rms = np.sqrt(np.mean(indata[:, 1]**2))
                    
                    # Thread-safe buffer update
                    with QMutexLocker(self.ui_mutex):
                        self.vu_buffer['left'] = min(1.0, left_rms * 5)  # Reduced scaling
                        self.vu_buffer['right'] = min(1.0, right_rms * 5)  # Reduced scaling
                        
                        # Optimized waveform data (minimal processing)
                        mono_rms = np.sqrt(np.mean(np.mean(indata, axis=1)**2))
                        self.waveform_buffer.append(mono_rms)
                        if len(self.waveform_buffer) > 100:
                            self.waveform_buffer = self.waveform_buffer[-100:]
                    
                    # Lightweight track detection
                    if self.waveform_buffer:
                        self.detect_track_boundaries_lightweight(indata)
                    
                    # Put audio data in queue for monitoring (non-blocking)
                    if self.recording_data['monitoring'] and self.audio_queue:
                        try:
                            self.audio_queue.put_nowait(indata.copy())
                        except queue.Full:
                            # Drop oldest frame and add new one
                            try:
                                self.audio_queue.get_nowait()
                                self.audio_queue.put_nowait(indata.copy())
                            except (queue.Empty, queue.Full):
                                pass
                            
            with sd.InputStream(samplerate=sample_rate, 
                              channels=2, 
                              dtype='float32',
                              device=self.recording_data['device_index'],
                              callback=callback,
                              blocksize=blocksize) as stream:
                self.audio_stream = stream
                while self.is_recording:
                    sd.sleep(10)  # Reduced sleep for better responsiveness
                    
        except Exception as e:
            print(f"Recording error: {e}")
            QMessageBox.critical(self, "Recording Error", f"Audio recording failed: {e}")
        finally:
            self.audio_stream = None
    
    def detect_track_boundaries_lightweight(self, audio_data):
        """Lightweight track detection for use in audio callback"""
        try:
            # Use pre-calculated RMS from waveform buffer if available
            rms_level = self.waveform_buffer[-1] if self.waveform_buffer else 0
            
            # Check if we're in silence (below threshold)
            is_silence = rms_level < self.silence_threshold
            
            # Initialize tracking variables if needed
            if not hasattr(self, 'silence_duration'):
                self.silence_duration = 0
            if not hasattr(self, 'consecutive_silence'):
                self.consecutive_silence = 0
                
            if is_silence:
                self.silence_duration += len(audio_data)
                self.consecutive_silence += 1
            else:
                # Only process silence if we had enough consecutive silence
                if self.consecutive_silence > 10:  # At least 10 consecutive silent chunks
                    with QMutexLocker(self.frames_mutex):
                        current_frame_count = len(self.frames)
                    
                    silence_samples = int(self.silence_duration)
                    sample_rate = int(float(self.project_settings['sample_rate']))
                    min_silence = int(sample_rate * 2.0)  # 2 seconds minimum silence
                    min_track_length = int(sample_rate * 30)  # 30 seconds minimum track length
                    
                    if silence_samples > min_silence:
                        # Found a track boundary
                        track_end = current_frame_count - int(self.silence_duration / 2)
                        if track_end > self.current_track_start + min_track_length:
                            self.track_boundaries.append((self.current_track_start, track_end))
                            print(f"Track boundary detected at frame {track_end} (silence: {silence_samples/sample_rate:.1f}s)")
                            self.current_track_start = track_end
                            
                self.silence_duration = 0
                self.consecutive_silence = 0
        except Exception as e:
            print(f"Track detection error: {e}")
            
    def monitor_audio(self):
        try:
            sample_rate = int(self.recording_data['sample_rate'])
            
            # Find the first available output device
            output_device = None
            devices = sd.query_devices()
            print(f"Available devices:")
            for i, device in enumerate(devices):
                print(f"  {i}: {device['name']} - Input: {device['max_input_channels']}, Output: {device['max_output_channels']}")
                if device['max_output_channels'] > 0 and output_device is None:
                    output_device = i
            
            if output_device is None:
                print("No output device available for monitoring")
                return
            
            print(f"Using output device {output_device}: {devices[output_device]['name']}")
                
            def callback(outdata, frames, time, status):
                if status:
                    print(f"Monitoring callback status: {status}")
                
                try:
                    # Get audio data from queue with timeout
                    indata = self.audio_queue.get(timeout=0.01)
                    
                    # Handle buffer size mismatch properly
                    if indata.shape[0] == frames:
                        outdata[:] = indata
                    elif indata.shape[0] > frames:
                        # Trim if input is larger
                        outdata[:] = indata[:frames]
                    else:
                        # Pad with zeros if input is smaller
                        outdata[:] = 0
                        outdata[:indata.shape[0]] = indata
                        
                except queue.Empty:
                    # If no data available, output silence
                    outdata[:] = 0
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    outdata[:] = 0
                    
            with sd.OutputStream(samplerate=sample_rate,
                              channels=2,
                              dtype='float32',
                              device=output_device,
                              callback=callback,
                              blocksize=1024) as stream:
                self.monitoring_stream = stream
                while self.is_recording:
                    sd.sleep(100)
                    
        except Exception as e:
            print(f"Monitoring error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.monitoring_stream = None
            
    def monitor_audio_simple(self):
        """Simple monitoring using direct audio routing with less processing"""
        try:
            sample_rate = int(self.recording_data['sample_rate'])
            
            # Get default output device
            output_device = sd.default.device[1]  # Default output device
            
            print(f"Simple monitoring using device {output_device}")
                
            def callback(outdata, frames, time, status):
                if status:
                    print(f"Simple monitoring status: {status}")
                
                try:
                    # Get audio data from queue
                    indata = self.audio_queue.get_nowait()
                    # Simple copy - assume sizes match for simple mode
                    if indata.shape[0] == frames:
                        outdata[:] = indata
                    else:
                        outdata[:] = 0  # Silence if size mismatch
                except queue.Empty:
                    outdata[:] = 0
                except Exception as e:
                    outdata[:] = 0
                    
            with sd.OutputStream(samplerate=sample_rate,
                              channels=2,
                              dtype='float32',
                              device=output_device,
                              callback=callback,
                              blocksize=1024) as stream:
                self.monitoring_stream = stream
                while self.is_recording:
                    sd.sleep(50)
                    
        except Exception as e:
            print(f"Simple monitoring error: {e}")
        finally:
            self.monitoring_stream = None
            
    def test_monitoring(self):
        """Generate a test tone to verify monitoring works"""
        try:
            import numpy as np
            sample_rate = int(self.recording_data['sample_rate'])
            duration = 0.5  # 500ms test tone
            frequency = 440  # A4 note
            
            # Generate test tone
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(2 * np.pi * frequency * t)
            stereo_tone = np.column_stack((tone, tone))  # Make it stereo
            
            # Put test tone in queue
            if self.audio_queue:
                for _ in range(5):  # Send 5 times to ensure it's heard
                    try:
                        self.audio_queue.put_nowait(stereo_tone.astype('float32'))
                    except queue.Full:
                        break
                        
        except Exception as e:
            print(f"Test tone error: {e}")
                
    def simulate_recording(self):
        # Simulate recording for testing without PyAudio
        import time
        while self.is_recording:
            time.sleep(0.1)
            # Simulate audio frames
            self.frames.append(b'simulated_audio_data')
            
    def update_progress(self):
        if self.is_recording:
            elapsed = datetime.now() - self.start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.progress_label.setText(f"Recording... {minutes:02d}:{seconds:02d}")
            
    def detect_track_boundaries(self, audio_data):
        """Detect track boundaries based on silence detection (optimized)"""
        # Use pre-calculated RMS from waveform buffer if available
        if hasattr(self, 'waveform_buffer') and self.waveform_buffer:
            rms_level = self.waveform_buffer[-1] if self.waveform_buffer else 0
        else:
            # Fallback calculation
            rms_level = np.sqrt(np.mean(audio_data**2))
        
        # Check if we're in silence (below threshold)
        is_silence = rms_level < self.silence_threshold
        
        # Track silence duration
        if not hasattr(self, 'silence_duration'):
            self.silence_duration = 0
        if not hasattr(self, 'consecutive_silence'):
            self.consecutive_silence = 0
            
        if is_silence:
            self.silence_duration += len(audio_data)
            self.consecutive_silence += 1
        else:
            # Only process silence if we had enough consecutive silence
            if self.consecutive_silence > 10:  # At least 10 consecutive silent chunks
                silence_samples = int(self.silence_duration)
                sample_rate = int(float(self.project_settings['sample_rate']))
                min_silence = int(sample_rate * 2.0)  # 2 seconds minimum silence
                min_track_length = int(sample_rate * 30)  # 30 seconds minimum track length
                
                if silence_samples > min_silence:
                    # Found a track boundary
                    track_end = len(self.frames) - int(self.silence_duration / 2)
                    if track_end > self.current_track_start + min_track_length:
                        self.track_boundaries.append((self.current_track_start, track_end))
                        print(f"Track boundary detected at frame {track_end} (silence: {silence_samples/sample_rate:.1f}s)")
                        self.current_track_start = track_end
                        
            self.silence_duration = 0
            self.consecutive_silence = 0
            
    def stop_recording(self):
        """Stop recording with proper cleanup"""
        try:
            self.is_recording = False
            
            # Stop progress timer
            if self.progress_timer:
                self.progress_timer.stop()
            
            # Wait for threads with timeout
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2.0)
            
            if hasattr(self, 'monitoring_thread') and self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)
            
            # Clear audio queue
            if self.audio_queue:
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        break
            
            # Add final track boundary
            sample_rate = int(float(self.project_settings['sample_rate']))
            with QMutexLocker(self.frames_mutex):
                total_frames = len(self.frames)
            
            if total_frames > self.current_track_start + int(sample_rate * 2):
                self.track_boundaries.append((self.current_track_start, total_frames))
                
            # Process detected tracks
            self.process_detected_tracks()
                        
            # Save the recording
            self.save_recording()
            
        except Exception as e:
            QMessageBox.critical(self, "Stop Error", f"Error stopping recording: {e}")
        finally:
            # Update UI and cleanup
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4aff4a;
                    font-size: 16px;
                    padding: 16px 32px;
                }
                QPushButton:hover {
                    background-color: #35cc35;
                }
            """)
        
    def process_detected_tracks(self):
        """Process detected tracks and prompt for names"""
        with QMutexLocker(self.frames_mutex):
            total_frames = len(self.frames)
            
        if not self.track_boundaries:
            # No tracks detected, treat as single track
            self.track_boundaries = [(0, total_frames)]
            print("No tracks detected - treating as single track")
        else:
            print(f"Detected {len(self.track_boundaries)} tracks")
            
        # Clear track list
        self.track_list.clear()
        
        # Process each detected track
        for i, (start, end) in enumerate(self.track_boundaries):
            # Get track name from user
            dialog = TrackNamingDialog(i + 1, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                track_name = dialog.get_track_name()
            else:
                track_name = f"Track {i + 1}"
                
            # Store track info (thread-safe)
            with QMutexLocker(self.frames_mutex):
                track_frames = self.frames[start:end]
                
            track_info = {
                'name': track_name,
                'start': start,
                'end': end,
                'frames': track_frames
            }
            self.detected_tracks.append(track_info)
            
            # Add to track list
            sample_rate = int(float(self.project_settings['sample_rate']))
            duration = (end - start) / sample_rate
            self.track_list.addItem(f"{i + 1}. {track_name} ({duration:.1f}s)")
            
    def save_recording(self):
        """Save recording with improved error handling and filename sanitization"""
        try:
            saved_files = []
            
            # Save each detected track separately
            for i, track in enumerate(self.detected_tracks):
                # Generate filename for this track with proper sanitization
                artist_name = self.sanitize_filename(self.recording_data['artist_name'])
                album_name = self.sanitize_filename(self.recording_data['album_name'])
                track_name_clean = self.sanitize_filename(track['name'])
                side = self.sanitize_filename(self.recording_data['side'])
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                format_type = self.recording_data['format'].upper()
                
                # Handle MP3 format properly
                if format_type == 'MP3':
                    # For now, save as WAV and notify user
                    format_ext = 'wav'
                    filename = f"{artist_name}_{album_name}_{side}_{track_name_clean}_{timestamp}.{format_ext}"
                    QMessageBox.information(self, "MP3 Format", 
                                          "MP3 encoding is not yet implemented. Saving as WAV format instead.")
                else:
                    format_ext = format_type.lower()
                    filename = f"{artist_name}_{album_name}_{side}_{track_name_clean}_{timestamp}.{format_ext}"
                
                filepath = os.path.join(self.recording_data['directory'], filename)
                
                # Validate path exists
                if not os.path.exists(self.recording_data['directory']):
                    os.makedirs(self.recording_data['directory'], exist_ok=True)
                
                if SOUND_AVAILABLE and track['frames'] and hasattr(track['frames'][0], '__len__') and len(track['frames'][0]) > 1:
                    # Save actual audio
                    sample_rate = int(self.recording_data['sample_rate'])
                    
                    # Convert frames to numpy array with validation
                    try:
                        audio_data = np.concatenate(track['frames'], axis=0)
                        
                        if format_type in ['WAV', 'FLAC']:
                            sf.write(filepath, audio_data, sample_rate, format=format_type)
                        else:  # MP3 (saved as WAV)
                            sf.write(filepath, audio_data, sample_rate, format='WAV')
                        
                        saved_files.append(f"{track['name']} -> {os.path.basename(filepath)}")
                        
                    except Exception as audio_error:
                        print(f"Audio processing error: {audio_error}")
                        saved_files.append(f"{track['name']} -> ERROR: {audio_error}")
                        
                else:
                    # Save simulated file
                    with open(filepath, 'w') as f:
                        f.write(f"Simulated recording for {track['name']}\n")
                        f.write(f"Artist: {self.recording_data['artist_name']}\n")
                        f.write(f"Album: {self.recording_data['album_name']}\n")
                        f.write(f"Side: {self.recording_data['side']}\n")
                        f.write(f"Format: {self.recording_data['format']}\n")
                        f.write(f"Sample Rate: {self.recording_data['sample_rate']} Hz\n")
                        f.write(f"Device: {self.recording_data['device_name']}\n")
                        f.write(f"Frames recorded: {len(track['frames'])}\n")
                        
                    saved_files.append(f"{track['name']} -> {os.path.basename(filepath)}")
                    
            # Show completion message
            if saved_files:
                files_text = "\n".join(saved_files)
                self.progress_label.setText(f"Saved {len(saved_files)} tracks")
                QMessageBox.information(self, "Recording Complete", 
                                      f"Successfully saved {len(saved_files)} tracks:\n\n{files_text}")
            else:
                QMessageBox.warning(self, "No Tracks", "No tracks were detected or saved.")
                                   
        except Exception as e:
            error_msg = f"Error saving recording: {e}"
            self.progress_label.setText("Error saving recording")
            QMessageBox.critical(self, "Save Error", error_msg)
            import traceback
            traceback.print_exc()


    def closeEvent(self, event):
        """Handle application close event with proper cleanup"""
        try:
            # Stop recording if active
            if self.is_recording:
                reply = QMessageBox.question(self, 'Quit Application', 
                                           'You are currently recording. Stop recording and quit?',
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.stop_recording()
                else:
                    event.ignore()
                    return
            
            # Clean up resources
            self.cleanup_resources()
            
            # Stop UI timer
            if self.ui_update_timer:
                self.ui_update_timer.stop()
            
            # Save configuration
            self.save_config()
            
            event.accept()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(26, 26, 26))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(74, 158, 255))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(74, 158, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(74, 158, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = GrooveRipApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
