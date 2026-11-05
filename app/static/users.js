"use strict";

async function csrfHeaders() {
  let response;
  try {
    response = await fetch("/api/auth/csrf", { credentials: "same-origin" });
  } catch {
    throw new Error("Сервис недоступен. Проверьте соединение и повторите попытку.");
  }
  if (!response.ok) throw new Error("Сессия завершилась. Войдите снова.");
  const { csrf_token: token } = await response.json();
  return { "X-CSRF-Token": token };
}

async function apiRequest(url, method, body) {
  const headers = await csrfHeaders();
  if (body) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(url, {
      method, credentials: "same-origin", headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Сервис недоступен. Проверьте соединение и повторите попытку.");
  }
  if (response.status === 204) return null;
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401) throw new Error("Сессия завершилась. Войдите снова.");
    if (response.status === 403) throw new Error("Недостаточно прав для этого действия.");
    if (response.status === 409) {
      const detail = Array.isArray(result.detail) ? "" : result.detail || "";
      throw new Error(detail.toLowerCase().includes("last active")
        ? "Нельзя удалить, отключить или понизить последнего активного администратора."
        : "Имя пользователя уже занято или операция нарушит защиту последнего admin.");
    }
    if (response.status === 422) throw new Error("Проверьте логин, имя, фамилию, роль и пароль (12–256 символов).");
    throw new Error("Не удалось выполнить запрос. Повторите попытку.");
  }
  return result;
}

const createForm = document.querySelector("[data-create-user]");
if (createForm) {
  const message = createForm.querySelector("[data-create-message]");
  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";
    const button = createForm.querySelector("button[type='submit']");
    button.disabled = true;
    try {
      await apiRequest("/api/users", "POST", {
        username: createForm.elements.username.value,
        first_name: createForm.elements.first_name.value,
        last_name: createForm.elements.last_name.value,
        password: createForm.elements.password.value,
        role: createForm.elements.role.value,
      });
      window.location.reload();
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

for (const row of document.querySelectorAll("[data-user-row]")) {
  const message = row.querySelector("[data-user-message]");
  const saveButton = row.querySelector("[data-save-user]");
  saveButton.addEventListener("click", async () => {
    message.textContent = "";
    saveButton.disabled = true;
    const body = {
      role: row.querySelector("[name='role']").value,
      is_active: row.querySelector("[name='is_active']").checked,
      first_name: row.querySelector("[name='first_name']").value,
      last_name: row.querySelector("[name='last_name']").value,
    };
    const password = row.querySelector("[name='password']").value;
    if (password) body.password = password;
    const identityChanged = body.role !== row.dataset.role
      || String(body.is_active) !== row.dataset.active
      || Boolean(password);
    const nameChanged = body.first_name.trim() !== row.dataset.firstName
      || body.last_name.trim() !== row.dataset.lastName;
    try {
      const updated = await apiRequest(`/api/users/${row.dataset.userId}`, "PATCH", body);
      message.textContent = "Изменения сохранены.";
      row.querySelector(".user-identity strong").textContent = updated.full_name;
      row.querySelector("[name='password']").value = "";
      row.dataset.role = body.role;
      row.dataset.active = String(body.is_active);
      row.dataset.firstName = body.first_name.trim();
      row.dataset.lastName = body.last_name.trim();
      if (identityChanged && row.dataset.userId === document.body.dataset.userId) {
        window.location.assign("/login");
      } else if (nameChanged && row.dataset.userId === document.body.dataset.userId) {
        window.location.reload();
      }
    } catch (error) {
      message.textContent = error.message;
    } finally {
      saveButton.disabled = false;
    }
  });

  row.querySelector("[data-delete-user]").addEventListener("click", async () => {
    if (!window.confirm(`Удалить пользователя ${row.querySelector(".user-identity strong").textContent}?`)) return;
    message.textContent = "";
    try {
      await apiRequest(`/api/users/${row.dataset.userId}`, "DELETE");
      if (row.dataset.userId === document.body.dataset.userId) {
        window.location.assign("/login");
        return;
      }
      row.remove();
    } catch (error) {
      message.textContent = error.message;
    }
  });
}
