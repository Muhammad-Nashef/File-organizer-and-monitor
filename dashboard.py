import sys
import os
import shutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QIcon
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CircularProgressBar(QWidget):
    def __init__(self, folder_name, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.total_items = 0
        self.setFixedSize(120, 120)

    def set_total_items(self, total_items):
        self.total_items = total_items
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background circle
        painter.setBrush(QColor(50, 50, 50))  # Dark background
        painter.drawEllipse(10, 10, 100, 100)

        # Progress arc
        if self.total_items > 0:
            painter.setBrush(QColor(255, 215, 0))  # Gold progress
            painter.drawArc(10, 10, 100, 100, 90 * 16, -self.total_items * 3.6 * 16)

        # Folder name and item count
        painter.setPen(QColor(255, 255, 255))  # White text
        painter.setFont(QFont("Arial", 10))
        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.folder_name}\n{self.total_items}")


class FileOrganizerHandler(FileSystemEventHandler):
    def __init__(self, app):
        super().__init__()
        self.app = app

    def on_created(self, event):
        if not event.is_directory:
            self.app.organize_file(event.src_path)


class MonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Organizer Monitor")
        self.setGeometry(100, 100, 400, 300)
        self.setStyleSheet("background-color: #000000;")  # Black background

        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'dashboard.png')
        self.setWindowIcon(QIcon(icon_path))
        #self.setWindowIcon(QIcon("icons/dashboard.png"))

        self.folders = ['images', 'videos', 'audio', 'documents',
                        'spreadsheets', 'archives', 'software', 'others']
        self.progress_bars = []
        self.base_folder = None

        self.init_ui()
        self.center_window()  # Call the center_window method

        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.update_folder_counts)

    def center_window(self):
        # Center the window on the screen
        qr = self.frameGeometry()  # Get the frame geometry
        cp = QApplication.primaryScreen().availableGeometry().center()  # Get screen center
        qr.moveCenter(cp)  # Move the window's center to the screen's center
        self.move(qr.topLeft())  # Move the window to the top-left of the centered frame

    def init_ui(self):
        layout = QGridLayout()

        title_label = QLabel("File Organizer Status")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 14))
        title_label.setStyleSheet("color: white;")  # White title
        layout.addWidget(title_label, 0, 0, 1, 3)

        # Progress bars for folders
        for i, folder in enumerate(self.folders):
            progress_bar = CircularProgressBar(folder)
            layout.addWidget(progress_bar, (i // 3) + 1, i % 3)
            self.progress_bars.append(progress_bar)

        # Folder selection button
        select_folder_button = QPushButton("Select Main Folder to Organize")
        select_folder_button.setStyleSheet(
            "background-color: #444; color: white; padding: 10px; font-size: 12px;"
        )
        select_folder_button.clicked.connect(self.select_folder)
        layout.addWidget(select_folder_button, 4, 0, 1, 3)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", options=QFileDialog.ShowDirsOnly
        )
        if folder:
            self.base_folder = folder
            print(f"Selected folder: {self.base_folder}")
            QMessageBox.information(self, "Folder Selected", f"Organizing: {self.base_folder}")
            self.start_watching()
        else:
            QMessageBox.warning(self, "No Folder Selected", "Please select a valid folder.")

    def start_watching(self):
        if not self.base_folder:
            QMessageBox.warning(self, "No Folder", "Please select a folder first.")
            return

        event_handler = FileOrganizerHandler(self)
        observer = Observer()
        observer.schedule(event_handler, self.base_folder, recursive=True)
        observer.start()
        self.update_folder_counts()
        self.timer.start()

    def organize_file(self, file_path):
        # Extract the filename
        filename = os.path.basename(file_path)

        # Exclude specific files
        excluded_files = ["README.txt", "dashboard.png"]
        if filename in excluded_files:
            print(f"Skipping: {filename}")
            return

        print(f"Organizing: {file_path}")
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        FOLDERS = {
            "images": ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'],
            "videos": ['.mp4', '.mkv', '.mov', '.avi'],
            "audio": ['.mp3', '.wav', '.aac', '.flac'],
            "documents": ['.pdf', '.docx', '.txt', '.pptx'],
            "spreadsheets": ['.xls', '.xlsx', '.csv'],
            "archives": ['.zip', '.rar', '.7z', '.tar', '.gz'],
            "software": ['.exe', '.msi', '.apk', '.iso'],
            "others": []
        }

        for folder in FOLDERS:
            os.makedirs(os.path.join(self.base_folder, folder), exist_ok=True)

        destination_folder = None
        for folder, extensions in FOLDERS.items():
            if ext in extensions:
                destination_folder = os.path.join(self.base_folder, folder)
                break

        if not destination_folder:
            destination_folder = os.path.join(self.base_folder, 'others')

        try:
            shutil.move(file_path, os.path.join(destination_folder, os.path.basename(file_path)))
            print(f"Moved: {file_path} -> {destination_folder}")
        except Exception as e:
            print(f"Error moving {file_path}: {e}")

    def update_folder_counts(self):
        if not self.base_folder:
            return

        for i, folder in enumerate(self.folders):
            folder_path = os.path.join(self.base_folder, folder)
            if os.path.exists(folder_path):
                total_items = len(os.listdir(folder_path))
                self.progress_bars[i].set_total_items(total_items)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MonitorApp()
    window.show()
    sys.exit(app.exec())
