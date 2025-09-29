import reflex as rx


def parameters_page() -> rx.Component:
    return rx.el.div(
        rx.el.h1(
            "Parametri & Calcolo Domanda",
            class_name="text-3xl font-bold text-gray-900 mb-6",
        ),
        rx.el.div(
            rx.el.h2(
                "Pagina Parametri", class_name="text-xl font-semibold text-gray-800"
            ),
            rx.el.p(
                "Contenuto della pagina dei parametri.", class_name="mt-2 text-gray-600"
            ),
            class_name="p-6 bg-white rounded-lg border border-gray-200",
        ),
        class_name="w-full",
    )