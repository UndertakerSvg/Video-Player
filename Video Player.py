import sys
import os
import random
from PyQt6.QtCore import QUrl, Qt, QTime, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton,
                             QHBoxLayout, QVBoxLayout, QFileDialog, QListWidget,
                             QLabel, QSlider, QComboBox, QSplitter, QMessageBox, QLineEdit)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from pymediainfo import MediaInfo


class AdvancedVideoWidget(QVideoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_player = parent

    def wheelEvent(self, event):
        if self.parent_player:
            self.parent_player.handle_wheel_volume(event.angleDelta().y())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.parent_player:
                self.parent_player.play_video()
        event.accept()


class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProVideo Player — Crimson Cyber Edition")
        self.setGeometry(100, 100, 1200, 800)

        self.recent_videos = []
        self.favorite_videos = []
        self.current_playlist = []
        self.current_file_path = ""
        self.is_shuffle_mode = False
        self.show_remaining_time = False

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)

        self.init_ui()
        self.apply_crimson_theme()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        self.overlay_timer = QTimer()
        self.overlay_timer.setSingleShot(True)
        self.overlay_timer.timeout.connect(self.hide_volume_overlay)

    def init_ui(self):
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)

        self.btn_open = QPushButton("📂 Открыть файл")
        self.btn_open.clicked.connect(self.open_file)

        self.btn_fav_add = QPushButton("⭐ В избранное")
        self.btn_fav_add.clicked.connect(self.add_to_favorites)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Быстрый поиск по названию...")
        self.search_bar.textChanged.connect(self.filter_library)
        self.search_bar.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.btn_open.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_fav_add.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        sidebar_layout.addWidget(self.btn_open)
        sidebar_layout.addWidget(self.btn_fav_add)
        sidebar_layout.addWidget(self.search_bar)

        sidebar_layout.addWidget(QLabel("<b>⭐ Избранное:</b>"))
        self.fav_list_widget = QListWidget()
        self.fav_list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.fav_list_widget.itemDoubleClicked.connect(self.play_from_fav_list)
        sidebar_layout.addWidget(self.fav_list_widget)

        sidebar_layout.addWidget(QLabel("<b>🕒 Недавно открытые:</b>"))
        self.recent_list_widget = QListWidget()
        self.recent_list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.recent_list_widget.itemDoubleClicked.connect(self.play_from_recent_list)
        sidebar_layout.addWidget(self.recent_list_widget)

        self.main_splitter.addWidget(sidebar)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)

        self.video_container = QWidget()
        video_container_layout = QVBoxLayout(self.video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = AdvancedVideoWidget(self)
        video_container_layout.addWidget(self.video_widget)
        right_layout.addWidget(self.video_container, stretch=5)
        self.media_player.setVideoOutput(self.video_widget)

        self.volume_overlay = QLabel("[ 🔊 Громкость: 70% ]", self.video_widget)
        self.volume_overlay.setObjectName("volumeOverlay")
        self.volume_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_overlay.hide()

        timeline_layout = QHBoxLayout()
        self.time_current_label = QLabel("00:00:00")

        self.time_total_label = QLabel("00:00:00")
        self.time_total_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.time_total_label.mousePressEvent = self.toggle_time_label_mode

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timeline_slider.sliderMoved.connect(self.set_position)

        timeline_layout.addWidget(self.time_current_label)
        timeline_layout.addWidget(self.timeline_slider)
        timeline_layout.addWidget(self.time_total_label)
        right_layout.addLayout(timeline_layout)

        controls_layout = QHBoxLayout()

        left_controls = QHBoxLayout()
        left_controls.addWidget(QLabel("Экран:"))
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["Оригинал", "16:9", "4:3", "Заполнить"])
        self.aspect_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.aspect_combo.currentTextChanged.connect(self.change_aspect_ratio)
        left_controls.addWidget(self.aspect_combo)

        left_controls.addWidget(QLabel("Скорость:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        left_controls.addWidget(self.speed_combo)

        center_controls = QHBoxLayout()
        self.btn_shuffle = QPushButton("🔀")
        self.btn_shuffle.setCheckable(True)
        self.btn_prev = QPushButton("⏮")
        self.btn_rewind = QPushButton("⏪")
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("btnPlay")
        self.btn_forward = QPushButton("⏩")
        self.btn_next = QPushButton("⏭")
        self.btn_stop = QPushButton("⏹")

        for btn in [self.btn_shuffle, self.btn_prev, self.btn_rewind, self.btn_play,
                    self.btn_forward, self.btn_next, self.btn_stop]:
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        center_controls.addWidget(self.btn_shuffle)
        center_controls.addWidget(self.btn_prev)
        center_controls.addWidget(self.btn_rewind)
        center_controls.addWidget(self.btn_play)
        center_controls.addWidget(self.btn_forward)
        center_controls.addWidget(self.btn_next)
        center_controls.addWidget(self.btn_stop)

        right_controls = QHBoxLayout()
        self.btn_screenshot = QPushButton("📷 Кадр")
        self.btn_screenshot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_screenshot.clicked.connect(self.take_screenshot)

        self.btn_fav_control = QPushButton("⭐ В Избранное")
        self.btn_fav_control.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_fav_control.clicked.connect(self.add_to_favorites)

        right_controls.addWidget(self.btn_screenshot)
        right_controls.addWidget(self.btn_fav_control)

        controls_layout.addLayout(left_controls)
        controls_layout.addStretch(1)
        controls_layout.addLayout(center_controls)
        controls_layout.addStretch(1)
        controls_layout.addLayout(right_controls)

        right_layout.addLayout(controls_layout)

        self.info_label = QLabel(
            "Файл не выбран\n"
            "Разрешение: — | Частота кадров: — | Формат: —"
        )
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setObjectName("infoLabel")
        right_layout.addWidget(self.info_label)

        self.main_splitter.addWidget(right_widget)
        self.main_splitter.setSizes([260, 940])

        self.btn_prev.clicked.connect(self.play_previous)
        self.btn_rewind.clicked.connect(lambda: self.seek_relative(-10000))
        self.btn_play.clicked.connect(self.play_video)
        self.btn_forward.clicked.connect(lambda: self.seek_relative(10000))
        self.btn_next.clicked.connect(self.play_next)
        self.btn_stop.clicked.connect(self.stop_video)
        self.btn_shuffle.clicked.connect(self.toggle_shuffle_mode)

        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

    # ---------------- СТИЛЬ: БАГРОВЫЕ КНОПКИ + БЕЛЫЕ ТЕКСТЫ ----------------
    def apply_crimson_theme(self):
        crimson_style = """
            QMainWindow { background-color: #0d0709; }

            /* Все тексты и шрифты принудительно белые */
            QWidget { color: #ffffff !important; font-family: "Segoe UI", sans-serif; font-size: 13px; }
            QSplitter::handle { background-color: #2a1115; }

            /* Поисковая строка */
            QLineEdit {
                background-color: #140a0d;
                border: 1px solid #4c1d24;
                border-radius: 6px;
                padding: 6px;
                color: #ffffff !important;
                margin-bottom: 4px;
            }
            QLineEdit:focus {
                border-color: #ef4444;
            }

            /* Кнопки теперь чисто багровые, текст на них белый */
            QPushButton { 
                background-color: #4c1d24; 
                border: 1px solid #5c1d24; 
                border-radius: 6px; 
                padding: 8px 14px; 
                color: #ffffff !important; 
                font-weight: 500; 
            }
            QPushButton:hover { 
                background-color: #7f1d1d; 
                border-color: #b91c1c;
            }
            QPushButton:pressed { 
                background-color: #991b1b; 
            }

            /* Главная кнопка «Плей» — чуть ярче для акцента */
            QPushButton#btnPlay {
                font-size: 16px;
                padding: 8px 18px;
                background-color: #991b1b;
                border: 1px solid #dc2626;
            }
            QPushButton#btnPlay:hover { 
                background-color: #dc2626; 
                border-color: #f87171; 
            }

            /* Списки библиотеки */
            QListWidget { background-color: #140a0d; border: 1px solid #2a1115; border-radius: 8px; padding: 6px; color: #ffffff; }
            QListWidget::item { padding: 5px; color: #ffffff !important; }
            QListWidget::item:hover { background-color: #4c1d24; color: #ffffff !important; border-radius: 6px; }
            QListWidget::item:selected { background-color: #991b1b; color: #ffffff !important; border-radius: 6px; }

            /* Выпадающие меню (Экран/Скорость) */
            QComboBox { background-color: #4c1d24; border: 1px solid #5c1d24; border-radius: 6px; padding: 6px 20px 6px 10px; color: #ffffff !important; }
            QComboBox QAbstractItemView { background-color: #140a0d; color: #ffffff !important; selection-background-color: #991b1b; border: 1px solid #4c1d24; }

            /* Багровый неоновый таймлайн */
            QSlider::groove:horizontal { height: 4px; background: #2a1115; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #dc2626; border-radius: 2px; }
            QSlider::handle:horizontal { background: #ffffff; width: 12px; height: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
            QSlider::handle:horizontal:hover { background: #f87171; }

            /* Всплывающий оверлей громкости */
            QLabel#volumeOverlay {
                background-color: rgba(20, 10, 13, 0.9);
                border: 1px solid #ef4444;
                border-radius: 8px;
                color: #ffffff !important;
                font-size: 14px;
                font-weight: bold;
            }

            /* Информационная панель */
            QLabel#infoLabel { background-color: #140a0d; border-top: 1px solid #2a1115; color: #ffffff !important; font-size: 12px; padding: 10px; }
        """
        self.setStyleSheet(crimson_style)

    def handle_wheel_volume(self, delta):
        current_vol = self.audio_output.volume()
        step = 0.05 if delta > 0 else -0.05
        new_vol = max(0.0, min(1.0, current_vol + step))
        self.audio_output.setVolume(new_vol)

        self.volume_overlay.setText(f"[ 🔊 Громкость: {int(new_vol * 100)}% ]")
        self.volume_overlay.resize(200, 40)
        self.volume_overlay.move(
            (self.video_widget.width() - self.volume_overlay.width()) // 2,
            (self.video_widget.height() - self.volume_overlay.height()) // 2
        )
        self.volume_overlay.show()
        self.overlay_timer.start(1000)

    def hide_volume_overlay(self):
        self.volume_overlay.hide()

    def filter_library(self, text):
        for i in range(self.recent_list_widget.count()):
            item = self.recent_list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())
        for i in range(self.fav_list_widget.count()):
            item = self.fav_list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def toggle_time_label_mode(self, event):
        self.show_remaining_time = not self.show_remaining_time
        self.duration_changed(self.media_player.duration())
        self.position_changed(self.media_player.position())

    def take_screenshot(self):
        if not self.current_file_path:
            return
        try:
            os.makedirs("Screenshots", exist_ok=True)
            screenshot = self.video_widget.grab()
            filename = f"Screenshots/Screen_{QTime.currentTime().toString('HH_mm_ss')}.png"
            screenshot.save(filename)
            self.volume_overlay.setText("📷 Кадр сохранен!")
            self.volume_overlay.resize(180, 40)
            self.volume_overlay.move(
                (self.video_widget.width() - self.volume_overlay.width()) // 2,
                (self.video_widget.height() - self.volume_overlay.height()) // 2
            )
            self.volume_overlay.show()
            self.overlay_timer.start(800)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сделать снимок: {str(e)}")

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in [Qt.Key.Key_F11, Qt.Key.Key_F, Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            self.toggle_fullscreen()
            event.accept()
        elif key == Qt.Key.Key_Space:
            self.play_video()
            event.accept()
        elif key == Qt.Key.Key_Right:
            self.seek_relative(10000)
            event.accept()
        elif key == Qt.Key.Key_Left:
            self.seek_relative(-10000)
            event.accept()
        elif key == Qt.Key.Key_S:
            self.take_screenshot()
            event.accept()
        elif key == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
            event.accept()
        else:
            super().keyPressEvent(event)

    def toggle_shuffle_mode(self):
        self.is_shuffle_mode = self.btn_shuffle.isChecked()
        if self.is_shuffle_mode:
            self.btn_shuffle.setStyleSheet("background-color: #dc2626; border-color: #f87171;")
        else:
            self.btn_shuffle.setStyleSheet("")
        self.setFocus()

    def play_next(self):
        if not self.current_playlist:
            return
        if self.is_shuffle_mode and len(self.current_playlist) > 1:
            next_file = random.choice(self.current_playlist)
            while next_file == self.current_file_path:
                next_file = random.choice(self.current_playlist)
            self.load_video(next_file)
        else:
            if self.current_file_path in self.current_playlist:
                current_idx = self.current_playlist.index(self.current_file_path)
                next_idx = (current_idx + 1) % len(self.current_playlist)
                self.load_video(self.current_playlist[next_idx])
        self.setFocus()

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next()

    def change_aspect_ratio(self, ratio_text):
        if ratio_text == "Оригинал":
            self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        elif ratio_text == "16:9":
            self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio)
        elif ratio_text == "4:3":
            self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        elif ratio_text == "Заполнить":
            self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio)
        self.setFocus()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.main_splitter.widget(0).show()
            self.info_label.show()
        else:
            self.showFullScreen()
            self.main_splitter.widget(0).hide()
            self.info_label.hide()
        self.setFocus()

    def get_video_meta(self, file_path):
        try:
            media_info = MediaInfo.parse(file_path)
            resolution = "Неизвестно"
            fps = "Неизвестно"
            file_format = os.path.splitext(file_path)[1].upper().replace('.', '')
            for track in media_info.tracks:
                if track.track_type == 'Video':
                    resolution = f"{track.width}x{track.height}"
                    if track.frame_rate:
                        fps = f"{track.frame_rate} FPS"
            return f"Играет: {os.path.basename(file_path)}\nРазрешение: {resolution} | Частота кадров: {fps} | Формат: {file_format}"
        except Exception:
            return f"Играет: {os.path.basename(file_path)}\nРазрешение: Ошибка чтения | Формат: {os.path.splitext(file_path)[1].upper()}"

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Открыть видео", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if file_name:
            if file_name not in self.recent_videos:
                self.recent_videos.insert(0, file_name)
                self.recent_list_widget.insertItem(0, os.path.basename(file_name))
            self.current_playlist = list(self.recent_videos)
            self.load_video(file_name)
        self.setFocus()

    def load_video(self, file_path):
        self.current_file_path = file_path
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        meta_text = self.get_video_meta(file_path)
        self.info_label.setText(meta_text)
        self.speed_combo.setCurrentText("1.0x")
        self.media_player.play()
        self.btn_play.setText("⏸")
        self.setFocus()

    def play_video(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.btn_play.setText("▶")
        else:
            self.media_player.play()
            self.btn_play.setText("⏸")
        self.setFocus()

    def stop_video(self):
        self.media_player.stop()
        self.timeline_slider.setValue(0)
        self.btn_play.setText("▶")
        self.setFocus()

    def seek_relative(self, milliseconds):
        current_pos = self.media_player.position()
        self.media_player.setPosition(max(0, current_pos + milliseconds))
        self.setFocus()

    def change_speed(self, speed_text):
        speed = float(speed_text.replace("x", ""))
        self.media_player.setPlaybackRate(speed)
        self.setFocus()

    def play_previous(self):
        if self.current_file_path in self.current_playlist:
            current_idx = self.current_playlist.index(self.current_file_path)
            prev_idx = (current_idx - 1) % len(self.current_playlist)
            self.load_video(self.current_playlist[prev_idx])
        self.setFocus()

    def add_to_favorites(self):
        if self.current_file_path:
            if self.current_file_path not in self.favorite_videos:
                self.favorite_videos.append(self.current_file_path)
                self.fav_list_widget.addItem(os.path.basename(self.current_file_path))
        else:
            QMessageBox.information(self, "Инфо", "Сначала откройте видео!")
        self.setFocus()

    def play_from_recent_list(self, item):
        self.current_playlist = list(self.recent_videos)
        self.find_and_play(item.text())

    def play_from_fav_list(self, item):
        self.current_playlist = list(self.favorite_videos)
        self.find_and_play(item.text())

    def find_and_play(self, filename):
        for path in self.recent_videos + self.favorite_videos:
            if os.path.basename(path) == filename:
                self.load_video(path)
                break

    def position_changed(self, position):
        self.timeline_slider.setValue(position)
        time_obj = QTime(0, 0, 0).addMSecs(position)
        self.time_current_label.setText(time_obj.toString("HH:mm:ss"))

        if self.show_remaining_time:
            rem_ms = max(0, self.media_player.duration() - position)
            rem_time = QTime(0, 0, 0).addMSecs(rem_ms)
            self.time_total_label.setText("-" + rem_time.toString("HH:mm:ss"))

    def duration_changed(self, duration):
        self.timeline_slider.setRange(0, duration)
        if not self.show_remaining_time:
            time_obj = QTime(0, 0, 0).addMSecs(duration)
            self.time_total_label.setText(time_obj.toString("HH:mm:ss"))

    def set_position(self, position):
        self.media_player.setPosition(position)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())