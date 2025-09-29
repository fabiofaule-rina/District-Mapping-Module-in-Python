import reflex as rx


def map_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Visualizzazione Mappa", class_name="text-3xl font-bold text-gray-900 mb-6"
        ),
        rx.el.div(
            rx.el.h2("Pagina Mappa", class_name="text-xl font-semibold text-gray-800"),
            rx.el.p(
                "Contenuto della pagina della mappa.", class_name="mt-2 text-gray-600"
            ),
            class_name="p-6 bg-white rounded-lg border border-gray-200",
        ),
        class_name="w-full",
    )