"""Hogwarts-inspired Qt stylesheet."""

DARK_QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; color: #EAF6FF; }
QMainWindow, QWidget { background: #060914; }
QFrame#GlassPanel { background: rgba(12, 20, 42, 208); border: 1px solid rgba(215,169,63,125); border-radius: 18px; }
QLabel#Title { color: #F8D978; font-size: 30px; font-weight: 800; letter-spacing: 2px; }
QLabel#Metric { color: #9EEBFF; font-size: 14px; }
QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #182A58, stop:1 #0B1428); border: 1px solid #D7A93F; border-radius: 12px; padding: 10px 14px; font-weight: 700; }
QPushButton:hover { background: #203C78; border-color: #75E7FF; }
QPushButton:pressed { background: #0B1428; }
QProgressBar { border: 1px solid #D7A93F; border-radius: 8px; text-align: center; background: #101827; }
QProgressBar::chunk { border-radius: 8px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2C7BFF, stop:1 #91F4FF); }
QListWidget, QTextEdit { background: rgba(6,9,20,180); border: 1px solid rgba(117,231,255,90); border-radius: 12px; padding: 8px; }
QTabWidget::pane { border: 1px solid rgba(215,169,63,120); border-radius: 12px; }
QTabBar::tab { background: #111B35; border: 1px solid #28395D; padding: 10px 16px; border-top-left-radius: 10px; border-top-right-radius: 10px; }
QTabBar::tab:selected { color: #F8D978; border-color: #D7A93F; }
"""
