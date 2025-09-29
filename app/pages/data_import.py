import reflex as rx


def data_import_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Importazione Dati", class_name="text-3xl font-bold text-gray-900 mb-6"
        ),
        rx.el.div(
            rx.el.h2(
                "Pagina di Importazione Dati",
                class_name="text-xl font-semibold text-gray-800",
            ),
            rx.el.p(
                "Contenuto della pagina di importazione dati.",
                class_name="mt-2 text-gray-600",
            ),
            class_name="p-6 bg-white rounded-lg border border-gray-200",
        ),
        class_name="w-full",
    )