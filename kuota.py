import sys

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import Qt

import gettext
gt = gettext.translation('kuota',localedir='locale')
#,languages=['en','es','ca'])
gt.install()
_ = gt.gettext

import signal

class ImageListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set the scrolling mode to scroll per pixel instead of per item
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Disable the focus rect for the items
        self.setFocusPolicy(Qt.NoFocus)

        # Set the default item size to 150 pixels in height
        self.setIconSize(QSize(150, 150))

        # Set the default spacing between items
        self.setSpacing(10)

        # Add some example items
        for i in range(5):
            text = _('Description')+f' {i}'
            item = QListWidgetItem(QIcon('drive-harddisk.png'), ' '*10+text)
            item.setData(Qt.UserRole,{'text':text,'status':False})
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            font = QFont()
            font.setPixelSize(14)
            item.setFont(font)
            self.addItem(item)

        # Connect signal to list items
        self.itemClicked.connect(self.item_clicked)

        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        

        color = 'transparent'
        # color = 'grey'
        self.setStyleSheet(
            f""" 
            QListWidget {{ border: none; background-color: {color}; padding: 0% 0%; margin-left: 20%;}} 
            QListWidget::item:hover {{ border: none; background-color: {color}; margin-left: 30%;}} 
            """)
        
    def item_clicked(self, item):
        data = item.data(Qt.UserRole)
        print(f"{data.get('text')} clicked")
        if data.get('status'):
            item.setIcon(QIcon('drive-harddisk.png'))
        else:
            item.setIcon(QIcon('drive-harddisk-ok.png'))
        data['status']= not data['status']
        item.setData(Qt.UserRole,data)
        scroll = self.parent()
        stack = scroll.parent()
        while not isinstance(scroll, QScrollArea):
            scroll = scroll.parent()
        while not isinstance(stack, QStackedWidget):
            stack = stack.parent()
        duration = 800
        idx = stack.currentIndex()
        next_idx = (idx+1) % stack.count()
        current = stack.currentWidget()
        next_widget = stack.widget(next_idx)

        a1 = QPropertyAnimation(current, b'pos')
        a1.setDuration(duration)
        a1.setStartValue(QPoint(0,0))
        a1.setEndValue(QPoint(-scroll.width(),0))
        a1.setEasingCurve(QEasingCurve.OutQuad)

        a2 = QPropertyAnimation(next_widget, b'pos')
        a2.setDuration(duration)
        a2.setStartValue(QPoint(scroll.width(),0))
        a2.setEndValue(QPoint(0,0))
        a2.setEasingCurve(QEasingCurve.OutQuad)

        a_group = QParallelAnimationGroup(self)
        a_group.addAnimation(a1)
        a_group.addAnimation(a2)

        a1.finished.connect(lambda : stack.setCurrentIndex(next_idx))
        a_group.finished.connect(lambda : print('Animation ended'))
        a_group.start(QAbstractAnimation.DeleteWhenStopped)

        timer = QTimer().singleShot(duration*10,lambda : (current.move(0,0),stack.setCurrentIndex(idx)))

class DriveView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        lbl = QTextEdit(_('Detected filesystems:'))
        lbl.setReadOnly(True)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background-color: transparent; border: none; padding: 0px;")
        lbl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lbl.setMaximumHeight(lbl.document().size().height())
        lbl.setMinimumHeight(lbl.document().size().height())
        font = QFont()
        font.setPointSize(16)
        lbl.setFont(font)
        l = ImageListWidget()
        layout.addWidget(lbl)
        #layout.addSpacerItem(QSpacerItem(0,10))
        layout.addWidget(l)
        self.setLayout(layout)

class MainContent(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        stack = QStackedWidget(self)
        
        # Create a scroll area to contain the image list widget
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        # Create the image list widget and set it as the widget for the scroll area
        #image_list_widget = ImageListWidget()
        drive_view = DriveView(self)
        scroll_area.setWidget(drive_view)

        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; height: 300%; }")
        stack.addWidget(scroll_area)

        # Add a example button
        button = QPushButton(_('New action'),self)
        button.clicked.connect(lambda : print('Button pressed'))

        layout = QVBoxLayout(self)
        layout.addWidget(stack)
        layout.addWidget(button)
        
        self.setLayout(layout)
        
        # Creación de la tabla de valores
        tabla_widget = QTableWidget(5, 5)
        tabla_widget.setHorizontalHeaderLabels(["Columna 1", "Columna 2", "Columna 3", "Columna 4", "Columna 5"])
        for i in range(5):
            for j in range(5):
                item_widget = QTableWidgetItem(f"Valor {i},{j}")
                tabla_widget.setItem(i, j, item_widget)
        tabla_widget.setSortingEnabled(True)
        stack.addWidget(tabla_widget)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1024,768)
        
        content = MainContent()

        self.add_action(type='toolbar',text=_('Users'),data='users')
        self.add_action(type='toolbar',text=_('Groups'),data='groups')
        self.add_action(type='toolbar',text=_('Exit'),data='exit')
        self.add_action(type='menu',text=_('Exit'),data='exit')

        self.create_menu_bar()
        self.create_actions_toolbar()

        # Set the central widget for the main window
        self.setCentralWidget(content)

    def add_action(self,type='toolbar',icon='drive-harddisk.png',text='action',data='action'):
        if type not in ['toolbar','menu']:
            return None
        
        if not hasattr(self,'_actions'):
            self._actions = {}
        self._actions.setdefault(type,[])
        
        action = QAction(QIcon(icon),_(text),self)
        action.setData(data)

        self._actions[type].append(action)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu(_('File'))
        
        for a in self._actions['menu']:
            a.triggered.connect(self.action_pressed)
            file_menu.addAction(a)

    def create_actions_toolbar(self):
        toolbar = self.addToolBar(_('Toolbar'))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setMovable(False)
        # toolbar.setStyleSheet("QToolBar { border: none; background-color: transparent; }")

        for a in self._actions['toolbar']:
            a.triggered.connect(self.action_pressed)
            toolbar.addAction(a)

    def action_pressed(self):
        sender = self.sender()
        data = sender.data()
        print(f'{data} pressed')
        if data == 'exit':
            self.close()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('kuota.svg'))
    window = MainWindow()
    window.setWindowTitle('Kuota')
    window.show()
    sys.exit(app.exec_())