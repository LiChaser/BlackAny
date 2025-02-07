import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                            QCheckBox, QLineEdit, QLabel, QHBoxLayout, QFrame, QSlider, QComboBox, QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu, QDialog)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QIcon, QFont, QColor, QKeySequence, QPixmap
import keyboard
import os
import winreg as reg
import json
import wmi  # 添加到文件顶部的导入部分

class FloatingButton(QWidget):
    def __init__(self):
        super().__init__()
        self.is_black_screen = False
        self.hide_cursor = True
        self.shortcut = 'ctrl+alt+b'
        self.settings_visible = False
        self.old_pos = None
        self.mouse_exit_enabled = True  # 改名，避免与控件名冲突
        self.recording_shortcut = False  # 添加标志来追踪是否正在记录快捷键
        self.temp_shortcut = None  # 添加临时快捷键存储
        self.temp_keys = set()  # 用于临时存储按下的键
        self.initUI()
        self.load_settings()  # 加载设置
        
        # 添加一个计时器来检查快捷键状态
        self.shortcut_timer = QTimer()
        self.shortcut_timer.timeout.connect(self.check_shortcut)
        self.shortcut_timer.start(100)  # 每100ms检查一次
        
        # 保存快捷键组合键的状态
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.key_pressed = False

        # 创建系统托盘图标
        self.create_tray_icon()
        self.tray_icon.show()  # 始终显示托盘图标

        # 初始化 WMI
        self.wmi = wmi.WMI(namespace='wmi')
        self.original_brightness = None  # 存储原始亮度

        # 设置应用程序图标
        icon_path = os.path.join('resources', 'icon.png')
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'icon.png')
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def initUI(self):
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建主按钮
        self.main_button = QPushButton('⬤', self)
        self.main_button.setFixedSize(50, 50)
        self.main_button.clicked.connect(self.toggle_black_screen)
        self.main_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #6366f1, stop:1 #8b5cf6);
                border-radius: 25px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #818cf8, stop:1 #9333ea);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """)
        main_layout.addWidget(self.main_button)

        # 创建设置面板
        self.settings_panel = QFrame(self)
        self.settings_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 rgba(40, 40, 50, 245), 
                                          stop:1 rgba(45, 45, 55, 245));
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            QLabel {
                color: #e2e8f0;
                font-size: 14px;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 5px;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding: 12px;
                font-size: 14px;
                min-height: 25px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(99, 102, 241, 0.5);
                background: rgba(255, 255, 255, 0.15);
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 14px;
                padding: 8px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 6px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #6366f1, stop:1 #8b5cf6);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #6366f1, stop:1 #8b5cf6);
                border: none;
                border-radius: 8px;
                color: white;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #818cf8, stop:1 #9333ea);
            }
            QComboBox {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding: 12px;
                font-size: 14px;
                min-height: 25px;
            }
            QComboBox:hover {
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        
        # 设置面板布局
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(12)
  
        # 快捷键设置
        shortcut_label = QLabel('快捷键设置:', self.settings_panel)  
        self.shortcut_input = QLineEdit(self.shortcut, self.settings_panel)
        self.shortcut_input.setPlaceholderText('点击此处按下快捷键组合')
        self.shortcut_input.setReadOnly(True)  # 设置为只读
        self.shortcut_input.setMinimumWidth(250)
        self.shortcut_input.installEventFilter(self)  # 安装事件过滤器

        # 鼠标设置
        mouse_settings_label = QLabel('鼠标设置:', self.settings_panel)
        self.hide_cursor_checkbox = QCheckBox('隐藏鼠标', self.settings_panel)
        self.hide_cursor_checkbox.setChecked(self.hide_cursor)
        self.hide_cursor_checkbox.stateChanged.connect(self.toggle_cursor_visibility)

        # 启动设置
        startup_label = QLabel('启动设置:', self.settings_panel)
        self.startup_checkbox = QCheckBox('开机自启动', self.settings_panel)
        self.startup_checkbox.stateChanged.connect(self.toggle_startup)

        # 位置设置
        position_label = QLabel('默认位置:', self.settings_panel)
        self.position_combo = QComboBox(self.settings_panel)
        self.position_combo.addItems(['左上角', '右上角', '左下角', '右下角', '屏幕中间'])
        self.position_combo.currentIndexChanged.connect(self.update_default_position)

        # 鼠标移动设置
        mouse_label = QLabel('鼠标移动设置:', self.settings_panel)
        self.enable_mouse_exit = QCheckBox('启用鼠标移动退出', self.settings_panel)
        self.enable_mouse_exit.setChecked(self.mouse_exit_enabled)
        self.enable_mouse_exit.stateChanged.connect(self.toggle_mouse_exit)

        # 在设置面板中添加隐藏悬浮窗选项
        hide_button_label = QLabel('悬浮窗设置:', self.settings_panel)
        self.hide_button_checkbox = QCheckBox('隐藏悬浮窗', self.settings_panel)
        self.hide_button_checkbox.setChecked(False)
        self.hide_button_checkbox.stateChanged.connect(self.toggle_button_visibility)

        # 添加所有控件到布局
        settings_layout.addWidget(shortcut_label)
        settings_layout.addWidget(self.shortcut_input)
        settings_layout.addWidget(mouse_settings_label)
        settings_layout.addWidget(self.hide_cursor_checkbox)
        settings_layout.addWidget(startup_label)
        settings_layout.addWidget(self.startup_checkbox)
        settings_layout.addWidget(position_label)
        settings_layout.addWidget(self.position_combo)
        settings_layout.addWidget(mouse_label)
        settings_layout.addWidget(self.enable_mouse_exit)
        settings_layout.addWidget(hide_button_label)
        settings_layout.addWidget(self.hide_button_checkbox)

        # 添加保存按钮
        save_button = QPushButton('保存设置', self.settings_panel)
        save_button.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_button)

        self.settings_panel.hide()
        
        # 初始位置
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 60, screen.height() // 2)

        # 设置面板位置
        self.settings_panel.setGeometry(50, 0, 350, 600)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.main_button.setGraphicsEffect(shadow)

        settings_shadow = QGraphicsDropShadowEffect(self)
        settings_shadow.setBlurRadius(20)
        settings_shadow.setXOffset(0)
        settings_shadow.setYOffset(0)
        settings_shadow.setColor(QColor(0, 0, 0, 100))
        self.settings_panel.setGraphicsEffect(settings_shadow)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 记录鼠标按下时的位置
            self.old_pos = event.globalPos()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.toggle_settings()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            # 计算移动的距离
            delta = event.globalPos() - self.old_pos
            # 更新窗口位置
            self.move(self.pos() + delta)
            # 更新鼠标位置
            self.old_pos = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None
            self.snap_to_edge()
            event.accept()

    def snap_to_edge(self):
        screen = QApplication.primaryScreen().geometry()
        pos = self.pos()
        
        # 吸附到屏幕边缘的距离阈值
        threshold = 20
        
        # 吸附到屏幕边缘
        if pos.x() < threshold:
            pos.setX(0)
        elif pos.x() > screen.width() - self.width() - threshold:
            pos.setX(screen.width() - self.width())
            
        if pos.y() < threshold:
            pos.setY(0)
        elif pos.y() > screen.height() - self.height() - threshold:
            pos.setY(screen.height() - self.height())
            
        self.move(pos)

    def toggle_settings(self):
        if self.settings_visible:
            # 关闭设置面板时，如果有未保存的快捷键，恢复为原来的快捷键
            if self.temp_shortcut is not None:
                self.shortcut_input.setText(self.shortcut)
                self.temp_shortcut = None
            self.settings_panel.hide()
            self.setFixedSize(50, 50)
        else:
            # 打开设置面板时，显示当前保存的快捷键
            self.shortcut_input.setText(self.shortcut)
            
            # 根据屏幕位置调整设置面板的显示方向
            screen = QApplication.primaryScreen().geometry()
            current_pos = self.pos()
            
            # 如果靠近右边缘，设置面板显示在左边
            if current_pos.x() + 400 > screen.width():
                self.settings_panel.move(-350, 0)
            else:
                self.settings_panel.move(50, 0)
            
            # 如果靠近底部，设置面板向上显示
            if current_pos.y() + 600 > screen.height():
                self.settings_panel.move(self.settings_panel.x(), -600 + 50)
            
            self.settings_panel.show()
            self.setFixedSize(400, 600)
        self.settings_visible = not self.settings_visible

    def toggle_black_screen(self):
        if self.is_black_screen:
            # 先恢复亮度
            if self.original_brightness is not None:
                self.set_brightness(self.original_brightness)
                self.original_brightness = None

            if hasattr(self, 'black_screen') and self.black_screen:
                self.black_screen.hide()
            
            self.is_black_screen = False
            self.main_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #6366f1, stop:1 #8b5cf6);
                    border-radius: 25px;
                    border: 2px solid rgba(255, 255, 255, 0.2);
                    color: white;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #818cf8, stop:1 #9333ea);
                    border: 2px solid rgba(255, 255, 255, 0.3);
                }
            """)
        else:
            # 先显示黑屏，再降低亮度
            if not hasattr(self, 'black_screen') or not self.black_screen:
                self.black_screen = BlackScreen(self.hide_cursor)
                self.black_screen.closeSignal.connect(self.on_black_screen_closed)
            self.black_screen.showFullScreen()

            # 保存当前亮度并设置为最低
            QTimer.singleShot(500, self._set_brightness_to_zero)  # 延迟500ms降低亮度
            
            self.is_black_screen = True
            self.main_button.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #dc2626, stop:1 #b91c1c);
                    border-radius: 25px;
                    border: 2px solid rgba(255, 255, 255, 0.2);
                    color: white;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 #ef4444, stop:1 #dc2626);
                    border: 2px solid rgba(255, 255, 255, 0.3);
                }
            """)

    def _set_brightness_to_zero(self):
        """延迟执行降低亮度的操作"""
        self.original_brightness = self.get_current_brightness()
        if self.original_brightness is not None:
            self.set_brightness(0)

    def check_shortcut(self):
        try:
            # 如果正在记录快捷键，不要检查快捷键
            if self.recording_shortcut:
                return
            
            keys = self.shortcut.split('+')
            all_pressed = all(keyboard.is_pressed(key.strip()) for key in keys)
            if all_pressed and not self.key_pressed:
                self.toggle_black_screen()
                self.key_pressed = True
            elif not all_pressed:
                self.key_pressed = False
        except Exception as e:
            print(f"检查快捷键失败: {e}")

    def register_shortcut(self):
        # 不再使用 keyboard.add_hotkey
        pass

    def update_shortcut(self):
        new_shortcut = self.shortcut_input.text().lower()
        if new_shortcut:
            self.shortcut = new_shortcut
            self.save_settings()
            # 重置按键状态
            self.ctrl_pressed = False
            self.alt_pressed = False
            self.key_pressed = False

    def toggle_cursor_visibility(self, state):
        self.hide_cursor = (state == Qt.Checked)
        if hasattr(self, 'black_screen') and self.black_screen:
            if self.hide_cursor:
                self.black_screen.setCursor(Qt.BlankCursor)
            else:
                self.black_screen.setCursor(Qt.ArrowCursor)
        self.save_settings()

    def toggle_startup(self, state):
        startup_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, startup_path, 0, reg.KEY_ALL_ACCESS)
            if state == Qt.Checked:
                reg.SetValueEx(key, "BlackScreenApp", 0, reg.REG_SZ, sys.argv[0])
            else:
                try:
                    reg.DeleteValue(key, "BlackScreenApp")
                except WindowsError:
                    pass
            reg.CloseKey(key)
        except WindowsError:
            print("无法设置开机自启动")

    def update_default_position(self, index):
        screen = QApplication.primaryScreen().geometry()
        positions = {
            0: QPoint(0, 0),  # 左上角
            1: QPoint(screen.width() - self.width(), 0),  # 右上角
            2: QPoint(0, screen.height() - self.height()),  # 左下角
            3: QPoint(screen.width() - self.width(), screen.height() - self.height()),  # 右下角
            4: QPoint(screen.width()//2 - self.width()//2, screen.height()//2 - self.height()//2)  # 中间
        }
        self.move(positions[index])
        self.save_settings()

    def toggle_mouse_exit(self, state):
        self.mouse_exit_enabled = (state == Qt.Checked)  # 使用新的变量名
        if hasattr(self, 'black_screen') and self.black_screen:
            self.black_screen.set_mouse_exit(self.mouse_exit_enabled)
        self.save_settings()

    def toggle_button_visibility(self, state):
        if state == Qt.Checked:
            self.hide()
        else:
            self.show()

    def create_tray_icon(self):
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 使用自定义图标
        icon_path = os.path.join('resources', 'icon.png')
        if hasattr(sys, '_MEIPASS'):  # 检查是否是打包后的环境
            icon_path = os.path.join(sys._MEIPASS, 'icon.png')
        
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # 如果图标不存在，使用默认图标
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_DialogNoButton))
        
        self.tray_icon.setToolTip('BlackAny')
        
        # 创建右键菜单
        tray_menu = QMenu()
        
        # 添加黑屏选项
        black_screen_action = tray_menu.addAction('切换黑屏')
        black_screen_action.triggered.connect(self.toggle_black_screen)
        tray_menu.addSeparator()
        
        # 添加显示/隐藏悬浮窗选项
        show_action = tray_menu.addAction('显示悬浮窗')
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addSeparator()
        
        settings_action = tray_menu.addAction('设置')
        settings_action.triggered.connect(self.show_settings_from_tray)
        tray_menu.addSeparator()
        
        # 添加作者信息选项
        about_action = tray_menu.addAction('作者有话说')
        about_action.triggered.connect(self.show_author_info)
        tray_menu.addSeparator()      
        
        quit_action = tray_menu.addAction('退出')
        quit_action.triggered.connect(self.quit_app)
        
        self.tray_icon.setContextMenu(tray_menu)
          
        # 双击托盘图标显示悬浮窗
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def show_from_tray(self):
        self.hide_button_checkbox.setChecked(False)
        self.show()

    def show_settings_from_tray(self):
        self.show_from_tray()
        self.toggle_settings()

    def quit_app(self):
        # 保存设置
        self.save_settings()
        # 清理托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        QApplication.quit()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def save_settings(self):
        app_data_dir = os.path.join(os.getenv('APPDATA'), 'BlackScreenApp')
        
        if not os.path.exists(app_data_dir):
            os.makedirs(app_data_dir)
        
        settings_file = os.path.join(app_data_dir, 'settings.json')
        
        settings = {
            'shortcut': self.shortcut,
            'hide_cursor': self.hide_cursor,
            'startup': self.startup_checkbox.isChecked(),
            'position': self.position_combo.currentIndex(),
            'enable_mouse_exit': self.mouse_exit_enabled,
            'hide_button': self.hide_button_checkbox.isChecked()
        }
        
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            print("设置已保存")  # 添加保存确认
        except Exception as e:
            print(f"保存设置失败: {e}")

    def load_settings(self):
        app_data_dir = os.path.join(os.getenv('APPDATA'), 'BlackScreenApp')
        settings_file = os.path.join(app_data_dir, 'settings.json')
        
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                
                # 加载所有设置
                self.shortcut = settings.get('shortcut', 'ctrl+alt+b')
                self.hide_cursor = settings.get('hide_cursor', True)
                self.startup = settings.get('startup', False)
                self.default_position = settings.get('position', 3)
                self.mouse_exit_enabled = settings.get('enable_mouse_exit', True)
                
                # 更新UI
                self.shortcut_input.setText(self.shortcut)
                self.hide_cursor_checkbox.setChecked(self.hide_cursor)
                self.startup_checkbox.setChecked(self.startup)
                self.position_combo.setCurrentIndex(self.default_position)
                self.enable_mouse_exit.setChecked(self.mouse_exit_enabled)
                
                # 应用设置
                if hasattr(self, 'black_screen') and self.black_screen:
                    self.black_screen.set_mouse_exit(self.mouse_exit_enabled)
                
                # 加载隐藏状态
                hide_button = settings.get('hide_button', False)
                self.hide_button_checkbox.setChecked(hide_button)
                if hide_button:
                    self.toggle_button_visibility(Qt.Checked)
                
        except FileNotFoundError:
            # 使用默认设置
            pass

    def on_black_screen_closed(self):
        # 恢复原始亮度
        if self.original_brightness is not None:
            self.set_brightness(self.original_brightness)
            self.original_brightness = None
            
        self.is_black_screen = False
        self.main_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #6366f1, stop:1 #8b5cf6);
                border-radius: 25px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #818cf8, stop:1 #9333ea);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """)

    def eventFilter(self, obj, event):
        if obj == self.shortcut_input:
            if event.type() == QEvent.MouseButtonPress:
                # 开始记录快捷键
                self.recording_shortcut = True
                self.temp_keys = set()  # 用于临时存储按下的键
                self.shortcut_input.setText("按下快捷键...")
                self.shortcut_input.setStyleSheet("""
                    QLineEdit {
                        background: rgba(255, 255, 255, 0.15);
                        border: 1px solid rgba(99, 102, 241, 0.5);
                    }
                """)
                return True
            
            elif event.type() == QEvent.KeyPress and self.recording_shortcut:
                # 记录按下的键
                key = event.key()
                key_text = QKeySequence(key).toString().lower()
                
                # 忽略单独的修饰键
                if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift):
                    return True
                
                # 处理修饰键
                modifiers = event.modifiers()
                if modifiers & Qt.ControlModifier:
                    self.temp_keys.add('ctrl')
                if modifiers & Qt.AltModifier:
                    self.temp_keys.add('alt')
                if modifiers & Qt.ShiftModifier:
                    self.temp_keys.add('shift')
                
                # 添加非修饰键（如果是有效的按键）
                if key_text and key_text not in ('ctrl', 'alt', 'shift', ''):
                    # 处理特殊按键
                    key_map = {
                        'esc': 'escape',
                        'return': 'enter',
                        'del': 'delete',
                        'ins': 'insert',
                        'pgup': 'pageup',
                        'pgdown': 'pagedown',
                        'space': 'spacebar'
                    }
                    key_text = key_map.get(key_text, key_text)
                    self.temp_keys.add(key_text)
                
                # 更新显示
                if self.temp_keys:
                    current_keys = '+'.join(sorted(self.temp_keys))
                    self.shortcut_input.setText(current_keys)
                
                return True
            
            elif event.type() == QEvent.KeyRelease and self.recording_shortcut:
                # 当所有键都释放时，完成快捷键设置
                if not event.modifiers() and len(self.temp_keys) > 0:
                    try:
                        # 验证快捷键是否有效
                        new_shortcut = '+'.join(sorted(self.temp_keys))
                        # 测试快捷键是否可用
                        for key in new_shortcut.split('+'):
                            if not keyboard.key_to_scan_codes(key):
                                raise ValueError(f"无效的按键: {key}")
                        
                        self.shortcut = new_shortcut
                        self.shortcut_input.setText(new_shortcut)
                        self.save_settings()
                        self.recording_shortcut = False
                        self.shortcut_input.setStyleSheet("")
                        self.temp_keys.clear()
                        
                        # 重置按键状态
                        self.key_pressed = False
                    except Exception as e:
                        print(f"无效的快捷键组合: {e}")
                        self.shortcut_input.setText(self.shortcut)  # 恢复原来的快捷键
                        self.recording_shortcut = False
                        self.shortcut_input.setStyleSheet("")
                        self.temp_keys.clear()
                
                return True
            
            elif event.type() == QEvent.FocusOut and self.recording_shortcut:
                # 取消记录快捷键
                self.recording_shortcut = False
                self.shortcut_input.setText(self.shortcut)
                self.shortcut_input.setStyleSheet("")
                self.temp_keys.clear()
                return True
            
        return super().eventFilter(obj, event)

    def set_brightness(self, value):
        """设置显示器亮度"""
        try:
            for monitor in self.wmi.WmiMonitorBrightnessMethods():
                monitor.WmiSetBrightness(value, 0)
        except Exception as e:
            print(f"设置亮度失败: {e}")

    def get_current_brightness(self):
        """获取当前亮度"""
        try:
            for monitor in self.wmi.WmiMonitorBrightness():
                return monitor.CurrentBrightness
        except Exception as e:
            print(f"获取亮度失败: {e}")
            return None

    def show_author_info(self):
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('作者有话说')
        dialog.setFixedSize(400, 400)
        
        # 获取二维码图片路径
        qrcode_path = 'qrcode.jpg'
        if hasattr(sys, '_MEIPASS'):  # 检查是否是打包后的环境
            qrcode_path = os.path.join(sys._MEIPASS, 'qrcode.jpg')
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10) 

        # 添加标题
        title = QLabel('BlackAny')
        title.setObjectName('title') 
        title.setAlignment(Qt.AlignCenter) 
        layout.addWidget(title) 

        # 添加作者信息
        author = QLabel('作者: Licharse & cursor\n\n如果你对我感兴趣可以关注我😊')
        author.setObjectName('关注我了解有用工具') 
        author.setAlignment(Qt.AlignCenter) 
        layout.addWidget(author) 

        # 添加微信公众号图片
        wechat_image = QLabel()
        wechat_image.setObjectName('wechat')
        
        # 检查图片文件是否存在
        if os.path.exists(qrcode_path):
            wechat_image.setPixmap(QPixmap(qrcode_path).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # 如果图片不存在，显示提示文本
            wechat_image.setText('微信公众号: BlackAny')
            wechat_image.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #e2e8f0;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }
            """)
        
        wechat_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(wechat_image)

        # 显示对话框
        dialog.exec_() 

class BlackScreen(QWidget):
    closeSignal = pyqtSignal()

    def __init__(self, exit_on_move):
        super().__init__()
        self.exit_on_move = exit_on_move
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet("background-color: black;")
        if self.exit_on_move:
            self.setCursor(Qt.BlankCursor)

    def showEvent(self, event):
        # 每次显示时都确保是全屏的
        self.showFullScreen()
        super().showEvent(event)

    def keyPressEvent(self, event):
        # 删除这个方法，因为我们使用全局快捷键来控制
        pass

    def mouseMoveEvent(self, event):
        if self.exit_on_move:
            self.closeSignal.emit()
            self.hide()
            event.accept()  # 确保事件被处理

    def closeEvent(self, event):
        self.closeSignal.emit()
        self.hide()
        event.ignore()  # 防止窗口被销毁

    def set_mouse_exit(self, enable):
        self.exit_on_move = enable

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用程序范围的样式表
    app.setStyleSheet("""
        QToolTip {
            background-color: rgba(40, 40, 40, 240);
            color: white;
            border: 1px solid rgba(255, 255, 255, 30);
            border-radius: 4px;
            padding: 4px;
        }
    """)
    
    ex = FloatingButton()
    ex.show()
    sys.exit(app.exec_())
