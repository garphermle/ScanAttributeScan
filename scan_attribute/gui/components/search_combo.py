"""
Searchable ComboBox widget for selecting Communes and Land Use Types.
"""

from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore import Qt, Signal

class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer().setFilterMode(Qt.MatchFlag.MatchContains)

    def set_items(self, items: list, data_list: list = None):
        self.clear()
        if data_list and len(data_list) == len(items):
            for text, data in zip(items, data_list):
                self.addItem(text, data)
        else:
            self.addItems(items)

    def get_selected_data(self):
        return self.currentData()
