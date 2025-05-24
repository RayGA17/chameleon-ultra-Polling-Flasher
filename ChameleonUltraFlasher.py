import sys
import time
import serial
import serial.tools.list_ports
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QProgressBar, QMessageBox, QLabel, QCheckBox,
    QToolButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QPalette, QColor, QIcon
import darkdetect
import ntplib
import queue
import random
import string
from qt_material import apply_stylesheet

# 调试日志队列
debug_queue = queue.Queue()

# 全局调试信号
class DebugSignal(QObject):
    debug_message = Signal(str)

debug_signal = DebugSignal()

# 调试日志线程
class DebugLoggerThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            try:
                message = debug_queue.get(timeout=0.1)
                debug_signal.debug_message.emit(f"[DEBUG] {message}")
                print(f"[DEBUG] {message}")
                debug_queue.task_done()
            except queue.Empty:
                continue

    def stop(self):
        self.running = False
        self.wait()

# 调试日志函数
def log_debug(message):
    debug_queue.put(message)

# 自定义标题栏
class CustomTitleBar(QWidget):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.theme = theme
        self.setStyleSheet(self.get_title_bar_style())
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        self.title = QLabel("变色龙 Ultra 刷写工具", self)
        self.title.setStyleSheet(self.get_title_text_style())
        layout.addWidget(self.title)
        layout.addStretch()

        # 按钮样式
        button_style = self.get_button_style()

        # 最小化按钮
        self.min_button = QToolButton(self)
        self.min_button.setText("-")
        self.min_button.setStyleSheet(button_style)
        self.min_button.clicked.connect(parent.showMinimized)
        layout.addWidget(self.min_button)

        # 最大化/还原按钮
        self.max_button = QToolButton(self)
        self.max_button.setText("□")
        self.max_button.setStyleSheet(button_style)
        self.max_button.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.max_button)

        # 关闭按钮
        self.close_button = QToolButton(self)
        self.close_button.setText("×")
        self.close_button.setStyleSheet(button_style)
        self.close_button.clicked.connect(parent.close)
        layout.addWidget(self.close_button)

        self.drag_position = None
        self.parent = parent

    def get_title_bar_style(self):
        if self.theme == "dark":
            return "background-color: rgba(0, 0, 50, 100);"
        else:
            return "background-color: rgba(173, 216, 230, 100);"

    def get_title_text_style(self):
        if self.theme == "dark":
            return "color: white; font-size: 14px; margin-left: 10px; background-color: transparent;"
        else:
            return "color: black; font-size: 14px; margin-left: 10px; background-color: transparent;"

    def get_button_style(self):
        if self.theme == "dark":
            return """
                QToolButton {
                    color: white;
                    background-color: transparent;
                    border: none;
                    font-size: 14px;
                    padding: 5px;
                }
                QToolButton:hover {
                    background-color: rgba(255, 255, 255, 50);
                }
            """
        else:
            return """
                QToolButton {
                    color: black;
                    background-color: transparent;
                    border: none;
                    font-size: 14px;
                    padding: 5px;
                }
                QToolButton:hover {
                    background-color: rgba(0, 0, 0, 50);
                }
            """

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.max_button.setText("□")
        else:
            self.parent.showMaximized()
            self.max_button.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            self.parent.move(event.globalPos() - self.drag_position)
            event.accept()

# 自定义二态开关控件
class ToggleButton(QPushButton):
    def __init__(self, text, theme, parent=None):
        super().__init__(text, parent)
        self.theme = theme
        self._state = False
        self.setFixedSize(120, 30)
        self.update_style()
        self.clicked.connect(self.toggle)

    def toggle(self):
        self._state = not self._state
        self.update_style()

    def update_style(self):
        if self.theme == "dark":
            if self._state:
                gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #26A69A, stop:1 #4DB6AC)"
                hover_gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4DB6AC, stop:1 #26A69A)"
                text_color = "white"
            else:
                gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF5350, stop:1 #F44336)"
                hover_gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F44336, stop:1 #EF5350)"
                text_color = "white"
        else:
            if self._state:
                gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66BB6A, stop:1 #4CAF50)"
                hover_gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CAF50, stop:1 #66BB6A)"
                text_color = "black"
            else:
                gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EF5350, stop:1 #F44336)"
                hover_gradient = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F44336, stop:1 #EF5350)"
                text_color = "black"

        self.setText("启用" if self._state else "禁用")
        self.setStyleSheet(f"""
            QPushButton {{
                background: {gradient};
                border-radius: 15px;
                color: {text_color};
                font-size: 14px;
                text-align: center;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
            }}
            QPushButton:hover {{
                background: {hover_gradient};
            }}
        """)

    def state(self):
        return self._state

    def set_state(self, state):
        self._state = state
        self.update_style()

# CRC16-IBM 计算函数
def crc16_ibm(data):
    crc = 0xFFFF
    polynomial = 0xA001
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder='big')

# 生成随机 14 位序列号并构造指令
def generate_serial_number_command():
    characters = string.ascii_letters + string.digits
    serial_number = ''.join(random.choices(characters, k=14))
    log_debug(f"生成随机序列号: {serial_number}")
    serial_bytes = bytes([0xD2]) + serial_number.encode('ascii')
    cmd_base = bytes.fromhex('11 EF 04 1B 00 00 00 0F')
    cmd = cmd_base + serial_bytes
    crc = crc16_ibm(cmd)
    full_cmd = cmd + crc
    return full_cmd, serial_number

# 指令定义
COMMANDS = {
    "activate": [
        bytes.fromhex('11 EF 04 1C 00 00 00 00 E0 00'),
    ],
    "low_freq_on": bytes.fromhex('11 EF 04 19 00 00 00 01 E2 01 FF'),
    "low_freq_off": bytes.fromhex('11 EF 04 19 00 00 00 01 E2 00 00'),
    "high_freq_on": bytes.fromhex('11 EF 04 18 00 00 00 01 E3 01 FF'),
    "high_freq_off": bytes.fromhex('11 EF 04 18 00 00 00 01 E3 00 00'),
    "light_on": bytes.fromhex('11 EF 04 1A 00 00 00 01 E1 01 FF'),
    "light_off": bytes.fromhex('11 EF 04 1A 00 00 00 01 E1 00 00'),
    "get_status": [
        bytes.fromhex('11 EF 03 F5 00 00 00 00 08 00'),
        bytes.fromhex('11 EF 04 0A 00 00 00 00 F2 00')
    ],
    "get_firmware_version": bytes.fromhex('11 EF 03 FB 00 00 00 00 02 00')
}

# 时间校验
def check_time():
    try:
        client = ntplib.NTPClient()
        response = client.request('ntp.aliyun.com')
        current_time = datetime.fromtimestamp(response.tx_time)
        expiry_date = datetime(2099, 9, 29)
        if current_time > expiry_date:
            return True,
        return True, "版本校验通过"
    except Exception as e:
        return True, "跳过版本校验"

# 串口操作类
class SerialDevice:
    def __init__(self, port):
        self.port = port
        self.serial = None
        self.is_connected = False

    def connect(self):
        log_debug(f"尝试连接串口: {self.port}")
        try:
            self.serial = serial.Serial(self.port, baudrate=115200, timeout=1)
            self.is_connected = True
            log_debug(f"{self.port} 连接成功")
            return True, "连接成功"
        except serial.SerialException as e:
            self.is_connected = False
            log_debug(f"{self.port} 连接失败: {str(e)}")
            return False, f"连接失败: {str(e)}"

    def send_command(self, command):
        if not self.is_connected:
            log_debug(f"{self.port} 未连接，无法发送命令")
            return False, "未连接"
        try:
            log_debug(f"{self.port} 发送命令: {command.hex()}")
            self.serial.write(command)
            response = self.serial.read(64)
            log_debug(f"{self.port} 接收响应: {response.hex()}")
            return True, response.hex()
        except serial.SerialException as e:
            log_debug(f"{self.port} 命令发送失败: {str(e)}")
            return False, f"命令发送失败: {str(e)}"

    def close(self):
        if self.serial and self.is_connected:
            log_debug(f"关闭串口: {self.port}")
            self.serial.close()
            self.is_connected = False

# 设备连接检测线程
class ConnectionThread(QThread):
    result = Signal(str, bool, str)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.detected_result = None

    def run(self):
        device = SerialDevice(self.port)
        is_chameleon, message = self.check_chameleon_ultra(device)
        self.result.emit(self.port, is_chameleon, message)
        device.close()

    def check_chameleon_ultra(self, device):
        if not device.is_connected:
            success, message = device.connect()
            if not success:
                return False, message
        try:
            device.serial.write(COMMANDS["get_firmware_version"])
            log_debug(f"{device.port} 发送 GET_FIRMWARE_VERSION 命令: {COMMANDS['get_firmware_version'].hex()}")
            response = device.serial.read(64)
            log_debug(f"{device.port} GET_FIRMWARE_VERSION 响应: {response.hex()}")
            if len(response) < 6:
                log_debug(f"{device.port} 响应数据过短: {len(response)} 字节")
                return False, "响应数据过短"
            if response[0:2] != b'\x11\xEF':
                log_debug(f"{device.port} 无效 SYNC: {response[0:2].hex()}")
                return False, "无效 SYNC"
            if response[2:4] != b'\x03\xFB':
                log_debug(f"{device.port} 无效 CMD: {response[2:4].hex()}")
                return False, "无效 CMD"
            status = response[4:6]
            if status not in [b'\x00\x68', b'\x00\x00']:
                log_debug(f"{device.port} 无效 STATUS: {status.hex()}")
                return False, "无效 STATUS"
            log_debug(f"{device.port} 检测到 ChameleonUltra")
            return True, "检测到 ChameleonUltra"
        except Exception as e:
            log_debug(f"{device.port} 检测失败: {str(e)}")
            return False, f"检测失败: {str(e)}"

# 设备检测线程
class DeviceDetectionThread(QThread):
    device_detected = Signal(list)
    device_update = Signal(str, bool)

    def __init__(self):
        super().__init__()
        self.connection_threads = []

    def run(self):
        log_debug("开始设备检测")
        ports = serial.tools.list_ports.comports()
        chameleon_ports = []

        for port in ports:
            log_debug(f"检测串口: {port.device}")
            connection_thread = ConnectionThread(port.device)
            connection_thread.result.connect(self.on_connection_result)
            self.connection_threads.append(connection_thread)
            connection_thread.start()

        for thread in self.connection_threads:
            thread.wait()

        for thread in self.connection_threads:
            if hasattr(thread, 'detected_result'):
                port, is_chameleon, _ = thread.detected_result
                if is_chameleon:
                    chameleon_ports.append(port)

        log_debug(f"检测完成，发现 ChameleonUltra 设备: {chameleon_ports}")
        self.device_detected.emit(chameleon_ports)

    def on_connection_result(self, port, is_chameleon, message):
        log_debug(f"{port} 检测结果: {is_chameleon}, 信息: {message}")
        for thread in self.connection_threads:
            if thread.port == port:
                thread.detected_result = (port, is_chameleon, message)
                break
        self.device_update.emit(port, is_chameleon)

# 工作线程
class WorkerThread(QThread):
    update_progress = Signal(int)
    update_task = Signal(str)
    update_result = Signal(str)
    update_debug = Signal(str)
    error_occurred = Signal(list)

    def __init__(self, ports, settings, serial_numbers):
        super().__init__()
        self.ports = ports
        self.settings = settings
        self.serial_numbers = serial_numbers
        self.errors = []

    def run(self):
        try:
            log_debug(f"WorkerThread 启动，处理设备: {self.ports}, 配置: {self.settings}")
            total_tasks = 0
            for port in self.ports:
                if self.settings["firmware"]:
                    total_tasks += 2  # 固定激活命令 + 动态序列号命令
                if "low_freq" in self.settings and self.settings["low_freq"] is not None:
                    total_tasks += 1
                if "high_freq" in self.settings and self.settings["high_freq"] is not None:
                    total_tasks += 1
                if "light" in self.settings and self.settings["light"] is not None:
                    total_tasks += 1
                total_tasks += len(COMMANDS["get_status"])

            log_debug(f"总任务数: {total_tasks}")
            completed_tasks = 0

            for port in self.ports:
                log_debug(f"开始处理设备: {port}")
                device = SerialDevice(port)
                try:
                    success, message = device.connect()
                    if not success:
                        self.errors.append(f"{port} 连接失败: {message}")
                        self.update_result.emit(f"{port} 连接失败: {message}")
                        self.update_debug.emit(f"{port} 连接失败: {message}")
                        continue

                    self.update_debug.emit(f"{port} 连接成功")

                    if self.settings["firmware"]:
                        self.update_task.emit(f"当前执行项目: 激活 {port} 设备")
                        # 发送固定激活命令
                        for cmd in COMMANDS["activate"]:
                            success, response = device.send_command(cmd)
                            self.update_debug.emit(f"{port} 发送固定激活命令: {cmd.hex()} 返回: {response}")
                            if success:
                                self.update_result.emit(f"{port} 固定激活命令执行成功")
                            else:
                                self.errors.append(f"{port} 固定激活命令执行失败: {response}")
                                self.update_result.emit(f"{port} 固定激活命令执行失败: {response}")
                            completed_tasks += 1
                            self.update_progress.emit(int(completed_tasks / total_tasks * 100))

                        # 发送动态序列号命令
                        sn_cmd, _ = self.serial_numbers[port]
                        success, response = device.send_command(sn_cmd)
                        self.update_debug.emit(f"{port} 发送序列号命令: {sn_cmd.hex()} 返回: {response}")
                        if success:
                            self.update_result.emit(f"{port} 序列号命令执行成功")
                        else:
                            self.errors.append(f"{port} 序列号命令执行失败: {response}")
                            self.update_result.emit(f"{port} 序列号命令执行失败: {response}")
                        completed_tasks += 1
                        self.update_progress.emit(int(completed_tasks / total_tasks * 100))

                    if "low_freq" in self.settings and self.settings["low_freq"] is not None:
                        self.update_task.emit(f"当前执行项目: 设置 {port} 低频ID循环")
                        cmd = COMMANDS["low_freq_on"] if self.settings["low_freq"] else COMMANDS["low_freq_off"]
                        success, response = device.send_command(cmd)
                        self.update_debug.emit(f"{port} 发送低频ID命令: {cmd.hex()} 返回: {response}")
                        if success:
                            self.update_result.emit(f"{port} 低频ID循环 {'开启' if self.settings['low_freq'] else '关闭'}成功")
                        else:
                            self.errors.append(f"{port} 低频ID循环设置失败: {response}")
                            self.update_result.emit(f"{port} 低频ID循环设置失败: {response}")
                        completed_tasks += 1
                        self.update_progress.emit(int(completed_tasks / total_tasks * 100))

                    if "high_freq" in self.settings and self.settings["high_freq"] is not None:
                        self.update_task.emit(f"当前执行项目: 设置 {port} 高频IC循环")
                        cmd = COMMANDS["high_freq_on"] if self.settings["high_freq"] else COMMANDS["high_freq_off"]
                        success, response = device.send_command(cmd)
                        self.update_debug.emit(f"{port} 发送高频IC命令: {cmd.hex()} 返回: {response}")
                        if success:
                            self.update_result.emit(f"{port} 高频IC循环 {'开启' if self.settings['high_freq'] else '关闭'}成功")
                        else:
                            self.errors.append(f"{port} 高频IC循环设置失败: {response}")
                            self.update_result.emit(f"{port} 高频IC循环设置失败: {response}")
                        completed_tasks += 1
                        self.update_progress.emit(int(completed_tasks / total_tasks * 100))

                    if "light" in self.settings and self.settings["light"] is not None:
                        self.update_task.emit(f"当前执行项目: 设置 {port} 按亮循环")
                        cmd = COMMANDS["light_on"] if self.settings["light"] else COMMANDS["light_off"]
                        success, response = device.send_command(cmd)
                        self.update_debug.emit(f"{port} 发送按亮命令: {cmd.hex()} 返回: {response}")
                        if success:
                            self.update_result.emit(f"{port} 按亮循环 {'开启' if self.settings['light'] else '关闭'}成功")
                        else:
                            self.errors.append(f"{port} 按亮循环设置失败: {response}")
                            self.update_result.emit(f"{port} 按亮循环设置失败: {response}")
                        completed_tasks += 1
                        self.update_progress.emit(int(completed_tasks / total_tasks * 100))

                    self.update_task.emit(f"当前执行项目: 获取 {port} 状态")
                    for cmd in COMMANDS["get_status"]:
                        success, response = device.send_command(cmd)
                        self.update_debug.emit(f"{port} 发送状态命令: {cmd.hex()} 返回: {response}")
                        if success:
                            self.update_result.emit(f"{port} 状态获取成功: {response}")
                        else:
                            self.errors.append(f"{port} 状态获取失败: {response}")
                            self.update_result.emit(f"{port} 状态获取失败: {response}")
                        completed_tasks += 1
                        self.update_progress.emit(int(completed_tasks / total_tasks * 100))
                finally:
                    device.close()

            self.update_task.emit("当前执行项目: 完成")
            log_debug("WorkerThread 完成")
            if self.errors:
                self.error_occurred.emit(self.errors)
        except Exception as e:
            error_message = f"WorkerThread 错误退出: {str(e)}"
            self.errors.append(error_message)
            log_debug(error_message)
            self.error_occurred.emit(self.errors)

# GUI 主窗口
class MainWindow(QMainWindow):
    def __init__(self, theme):
        super().__init__()
        self.setWindowTitle("变色龙 Ultra 刷写工具")
        self.setGeometry(100, 100, 900, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon('logo.ico'))
        self.devices = {}
        self.previous_states = {}
        self.running = False
        self.detected_ports = set()
        self.device_detection_enabled = True
        self.is_flashing_finished = False
        self.theme = theme
        self.init_ui()
        self.debug_logger = DebugLoggerThread()
        self.debug_logger.start()
        debug_signal.debug_message.connect(self.debug_text.append)
        self.start_device_detection()

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 自定义标题栏
        self.title_bar = CustomTitleBar(self, self.theme)
        main_layout.addWidget(self.title_bar)

        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(10)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 0)
        content_widget.setGraphicsEffect(shadow)

        self.device_layout = QVBoxLayout()
        content_layout.addWidget(QLabel("可用 ChameleonUltra 设备:"))
        content_layout.addLayout(self.device_layout)

        config_widget = QWidget()
        config_layout = QHBoxLayout(config_widget)
        config_layout.setSpacing(10)

        self.firmware_toggle = ToggleButton("固件激活", self.theme)
        config_layout.addWidget(QLabel("固件激活:"))
        config_layout.addWidget(self.firmware_toggle)

        self.low_freq_toggle = ToggleButton("低频ID循环", self.theme)
        config_layout.addWidget(QLabel("低频ID循环:"))
        config_layout.addWidget(self.low_freq_toggle)

        self.high_freq_toggle = ToggleButton("高频IC循环", self.theme)
        config_layout.addWidget(QLabel("高频IC循环:"))
        config_layout.addWidget(self.high_freq_toggle)

        self.light_toggle = ToggleButton("按亮循环", self.theme)
        config_layout.addWidget(QLabel("按亮循环:"))
        config_layout.addWidget(self.light_toggle)

        content_layout.addWidget(QLabel("配置选项:"))
        content_layout.addWidget(config_widget)

        self.start_button = QPushButton("开始刷写")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_flashing)
        content_layout.addWidget(self.start_button)

        self.current_task_label = QLabel("当前执行项目: 无")
        content_layout.addWidget(self.current_task_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        content_layout.addWidget(self.progress_bar)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        content_layout.addWidget(QLabel("执行结果:"))
        content_layout.addWidget(self.result_text)

        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        content_layout.addWidget(QLabel("调试信息:"))
        content_layout.addWidget(self.debug_text)

        main_layout.addWidget(content_widget)
        self.setCentralWidget(central_widget)

        # 设置开始按钮和内容区域样式
        if self.theme == "dark":
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: rgba(38, 50, 56, 200);
                    border-radius: 8px;
                }
            """)
            self.start_button.setStyleSheet("""
                QPushButton#startButton {
                    background-color: rgba(50, 50, 50, 180);
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 14px;
                    color: white;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
                }
                QPushButton#startButton:hover {
                    background-color: rgba(70, 70, 70, 180);
                }
            """)
        else:
            content_widget.setStyleSheet("""
                QWidget {
                    background-color: rgba(240, 245, 250, 200);
                    border-radius: 8px;
                }
            """)
            self.start_button.setStyleSheet("""
                QPushButton#startButton {
                    background-color: rgba(200, 200, 200, 180);
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 14px;
                    color: black;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
                }
                QPushButton#startButton:hover {
                    background-color: rgba(220, 220, 220, 180);
                }
            """)

    def start_device_detection(self):
        if not self.device_detection_enabled:
            log_debug("设备检测已暂停")
            return
        self.detection_thread = DeviceDetectionThread()
        self.detection_thread.device_detected.connect(self.update_device_list)
        self.detection_thread.device_update.connect(self.update_device_list_realtime)
        self.detection_thread.finished.connect(self.on_detection_finished)
        self.detection_thread.start()

    def on_detection_finished(self):
        self.detection_thread.deleteLater()
        self.schedule_next_detection()

    def schedule_next_detection(self):
        if not self.running and self.device_detection_enabled:
            QTimer.singleShot(2000, self.start_device_detection)
        else:
            log_debug("设备检测暂停，等待刷写完成")

    def update_device_list_realtime(self, port, is_chameleon):
        if is_chameleon:
            if port not in self.detected_ports:
                self.detected_ports.add(port)
                device_name = f"Chameleon Ultra - {port}"
                checkbox = QCheckBox(device_name)
                if port in self.previous_states:
                    checkbox.setChecked(self.previous_states[port]["selected"])
                self.device_layout.addWidget(checkbox)
                self.devices[port] = {"checkbox": checkbox}
                log_debug(f"实时添加设备: {port}")

    def update_device_list(self, ports):
        log_debug(f"最终更新设备列表: {ports}")
        for port, info in self.devices.items():
            self.previous_states[port] = {
                "selected": info["checkbox"].isChecked()
            }

        for i in reversed(range(self.device_layout.count())):
            self.device_layout.itemAt(i).widget().deleteLater()

        self.devices.clear()
        self.detected_ports.clear()
        for port in ports:
            self.detected_ports.add(port)
            device_name = f"Chameleon Ultra - {port}"
            checkbox = QCheckBox(device_name)
            if port in self.previous_states:
                checkbox.setChecked(self.previous_states[port]["selected"])
            self.device_layout.addWidget(checkbox)
            self.devices[port] = {"checkbox": checkbox}
        log_debug(f"设备列表更新完成，显示设备: {list(self.devices.keys())}")

    def start_flashing(self):
        log_debug("开始刷写按钮点击")
        valid, message = check_time()
        if not valid:
            log_debug(f"时间校验失败: {message}")
            QMessageBox.critical(self, "错误", message)
            return

        selected_devices = [port for port, info in self.devices.items() if info["checkbox"].isChecked()]
        log_debug(f"选中的设备: {selected_devices}")
        if not selected_devices:
            log_debug("未选择任何设备")
            QMessageBox.warning(self, "警告", "请至少选择一个设备")
            return

        settings = {
            "firmware": self.firmware_toggle.state(),
            "low_freq": self.low_freq_toggle.state(),
            "high_freq": self.high_freq_toggle.state(),
            "light": self.light_toggle.state()
        }
        log_debug(f"配置选项: {settings}")

        #if not any(settings.values()):
        #    log_debug("未启用任何配置选项")
        #    QMessageBox.warning(self, "警告", "请至少启用一个配置选项")
        #    return

        serial_numbers = {}
        for port in selected_devices:
            sn_cmd, sn = generate_serial_number_command()
            serial_numbers[port] = (sn_cmd, sn)
            self.result_text.append(f"设备 {port} 的新序列号: {sn}")

        self.running = True
        self.device_detection_enabled = False
        self.is_flashing_finished = False
        log_debug("暂停设备检测")
        self.start_button.setEnabled(False)
        for port, info in self.devices.items():
            info["checkbox"].setEnabled(False)
        self.firmware_toggle.setEnabled(False)
        self.low_freq_toggle.setEnabled(False)
        self.high_freq_toggle.setEnabled(False)
        self.light_toggle.setEnabled(False)
        log_debug("禁用设备选择和配置选项")

        QMessageBox.warning(self, "警告", "请勿关闭窗口或移除设备，否则可能导致设备损坏！")

        self.result_text.clear()
        self.debug_text.clear()
        self.progress_bar.setValue(0)
        log_debug("清空输出和进度条")

        for port in selected_devices:
            _, sn = serial_numbers[port]
            self.result_text.append(f"设备 {port} 的新序列号: {sn}")

        try:
            log_debug("启动 WorkerThread")
            self.worker = WorkerThread(selected_devices, settings, serial_numbers)
            self.worker.update_progress.connect(self.progress_bar.setValue)
            self.worker.update_task.connect(self.current_task_label.setText)
            self.worker.update_result.connect(self.result_text.append)
            self.worker.update_debug.connect(self.debug_text.append)
            self.worker.error_occurred.connect(self.on_error_occurred)
            self.worker.finished.connect(self.on_flashing_finished)
            self.worker.start()
        except Exception as e:
            log_debug(f"WorkerThread 启动失败: {str(e)}")
            self.on_error_occurred([f"WorkerThread 启动失败: {str(e)}"])
            self.on_flashing_finished()

    def on_error_occurred(self, errors):
        if errors:
            error_message = "以下错误发生:\n" + "\n".join(errors)
            self.result_text.append(f"错误汇总:\n{error_message}")
            QMessageBox.critical(self, "错误", error_message)

    def on_flashing_finished(self):
        if self.is_flashing_finished:
            log_debug("on_flashing_finished 已执行，忽略重复调用")
            return
        self.is_flashing_finished = True
        log_debug("刷写完成或错误退出")
        self.running = False
        self.device_detection_enabled = True
        log_debug("恢复设备检测")

        try:
            # 启用开始按钮
            self.start_button.setEnabled(True)
            log_debug("开始按钮已启用")

            # 启用设备选择
            for port, info in self.devices.items():
                try:
                    info["checkbox"].setEnabled(True)
                    log_debug(f"设备 {port} 的选择框已启用")
                except Exception as e:
                    log_debug(f"启用设备 {port} 选择框失败: {str(e)}")

            # 启用配置选项
            self.firmware_toggle.setEnabled(True)
            self.low_freq_toggle.setEnabled(True)
            self.high_freq_toggle.setEnabled(True)
            self.light_toggle.setEnabled(True)
            log_debug("所有配置选项已启用")

        except Exception as e:
            log_debug(f"恢复控件启用状态时发生错误: {str(e)}")

        try:
            self.worker.finished.disconnect(self.on_flashing_finished)
            self.worker.error_occurred.disconnect(self.on_error_occurred)
        except Exception as e:
            log_debug(f"断开信号失败: {str(e)}")

        self.worker.deleteLater()
        self.start_device_detection()

    def closeEvent(self, event):
        self.debug_logger.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    theme = darkdetect.theme().lower() if darkdetect.theme() else "light"
    apply_stylesheet(app, theme='dark_teal.xml' if theme == "dark" else 'light_blue.xml')
    window = MainWindow(theme)
    window.show()
    sys.exit(app.exec())