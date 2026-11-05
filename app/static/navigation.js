// Accessible sidebar collapse control.

const sidebarToggle = document.querySelector("[data-sidebar-toggle]");

if (sidebarToggle) {
  sidebarToggle.addEventListener("click", () => {
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
    sidebarToggle.setAttribute(
      "aria-label",
      collapsed ? "Открыть боковое меню" : "Свернуть боковое меню",
    );
  });
}
