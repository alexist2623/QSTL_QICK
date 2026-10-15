import pytest
from PyQt5 import QtWidgets
from test_square_awg_exclusion import window
from test_acquisition_preview import test_gui_selected_hold_translates_rf_and_acquisition_without_mutating_settings as original_test

def test_visible_timeline_geometry(window):
    window.show()
    QtWidgets.QApplication.processEvents()
    original_test(window)
