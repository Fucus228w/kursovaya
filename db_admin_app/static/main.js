// static/main.js

document.addEventListener("DOMContentLoaded", function () {
  // ---------- Тёмная тема ----------
  const body = document.body;
  const themeToggle = document.getElementById("theme-toggle");
  const savedTheme = localStorage.getItem("theme") || "light";

  body.setAttribute("data-theme", savedTheme);
  updateThemeToggleText(themeToggle, savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const current = body.getAttribute("data-theme") || "light";
      const next = current === "light" ? "dark" : "light";
      body.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      updateThemeToggleText(themeToggle, next);
    });
  }

  function updateThemeToggleText(btn, theme) {
    if (!btn) return;
    if (theme === "dark") {
      btn.textContent = "☀ Светлая тема";
    } else {
      btn.textContent = "🌙 Тёмная тема";
    }
  }

  // ---------- Поиск по таблице (как было) ----------
  const searchInput = document.getElementById("user-search");
  if (searchInput) {
    const tableId = searchInput.getAttribute("data-table-id");
    const table = document.getElementById(tableId);
    if (table) {
      const tbody = table.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr"));

      searchInput.addEventListener("input", function () {
        const query = searchInput.value.toLowerCase().trim();

        rows.forEach((row) => {
          const cellsText = row.innerText.toLowerCase();
          row.style.display = !query || cellsText.includes(query) ? "" : "none";
        });
      });
    }
  }

  // ---------- Автоудаление флешей после анимации ----------
  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((el) => {
    el.addEventListener("animationend", (e) => {
      if (e.animationName === "flashAutoHide") {
        el.remove();
      }
    });
  });
});
