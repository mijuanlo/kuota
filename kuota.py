import sys
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

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
        self.addItem(QListWidgetItem(QIcon('drive-harddisk.png'), 'Description of image 1'))
        self.addItem(QListWidgetItem(QIcon('drive-harddisk.png'), 'Description of image 2'))
        self.addItem(QListWidgetItem(QIcon('drive-harddisk.png'), 'Description of image 3'))

        # Connect signal to list items
        self.itemClicked.connect(self.item_clicked)

        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        
    def item_clicked(self, item):
        print(item.text())
        scroll = self.parent().parent()
        stack = scroll.parent()
        duration = 500
        idx = stack.currentIndex()
        print(idx)
        next_idx = (idx+1) % stack.count()
        current = stack.currentWidget()
        next_widget = stack.widget(next_idx)

        a1 = QPropertyAnimation(current, b'pos')
        a1.setDuration(duration)
        a1.setStartValue(QPoint(0,0))
        a1.setEndValue(QPoint(-scroll.width(),0))
        a1.setEasingCurve(QEasingCurve.OutQuad)

        a_group = QSequentialAnimationGroup(self)
        a_group.addAnimation(a1)

        a1.finished.connect(lambda : stack.setCurrentIndex(next_idx))
        a_group.finished.connect(lambda : print('ended'))
        a_group.start(QAbstractAnimation.KeepWhenStopped)

        timer = QTimer().singleShot(duration*2,lambda : (print(stack.currentIndex()),current.move(0,0),stack.setCurrentIndex(idx),print('done')))



class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1024,768)
        
        stack = QStackedWidget(self)
        
        # Create a scroll area to contain the image list widget
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Create the image list widget and set it as the widget for the scroll area
        image_list_widget = ImageListWidget()
        scroll_area.setWidget(image_list_widget)

        stack.addWidget(scroll_area)
        layout = QVBoxLayout(self)
        layout.addWidget(stack)
        #scroll_area.setStyleSheet("background-color: #F5F5F5;")
        # Set the scroll area as the central widget for the main window
        self.setCentralWidget(stack)
        #self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())