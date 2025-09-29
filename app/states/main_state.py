import reflex as rx
from typing import Literal

PageLiteral = Literal["project", "data_import", "map", "parameters", "kpi"]


class MainState(rx.State):
    active_page: PageLiteral = "project"

    @rx.event
    def set_active_page(self, page: PageLiteral):
        self.active_page = page