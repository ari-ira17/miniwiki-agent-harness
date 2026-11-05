/* Accessible keyboard and pointer toggles for the page tree. */

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-tree-toggle]");
  if (!button) return;

  const children = document.getElementById(button.getAttribute("aria-controls"));
  if (!children) return;

  const expanded = button.getAttribute("aria-expanded") === "true";
  const noun = {
    folder: "раздел",
    document: "содержание",
    heading: "подразделы",
  }[button.dataset.treeKind] || "раздел";
  button.setAttribute("aria-expanded", String(!expanded));
  button.setAttribute(
    "aria-label",
    `${expanded ? "Развернуть" : "Свернуть"} ${noun} ${button.dataset.treeTitle}`,
  );
  children.hidden = expanded;
});
