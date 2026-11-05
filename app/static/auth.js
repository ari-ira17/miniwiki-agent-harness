"use strict";

const loginForm = document.querySelector("[data-login-form]");
if (loginForm) {
  const message = loginForm.querySelector("[data-login-message]");
  let csrfToken = "";
  fetch("/api/auth/csrf", { credentials: "same-origin" })
    .then(async (response) => {
      if (!response.ok) throw new Error("Не удалось открыть форму входа.");
      csrfToken = (await response.json()).csrf_token;
    })
    .catch((error) => { message.textContent = error.message; });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";
    const button = loginForm.querySelector("button[type='submit']");
    button.disabled = true;
    try {
      if (!csrfToken) throw new Error("Обновите страницу и попробуйте снова.");
      const response = await fetch("/api/auth/login", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify({ username: loginForm.elements.username.value, password: loginForm.elements.password.value }),
      });
      if (!response.ok) throw new Error(response.status === 401 ? "Неверное имя пользователя или пароль." : "Не удалось выполнить вход.");
      window.location.assign("/");
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

const logoutButton = document.querySelector("[data-logout]");
if (logoutButton) {
  logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    try {
      const tokenResponse = await fetch("/api/auth/csrf", { credentials: "same-origin" });
      const { csrf_token: csrfToken } = await tokenResponse.json();
      const response = await fetch("/api/auth/logout", {
        method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": csrfToken },
      });
      if (!response.ok) throw new Error("Не удалось выйти.");
      window.location.assign("/login");
    } catch {
      logoutButton.textContent = "Не удалось выйти. Повторить?";
      logoutButton.disabled = false;
    }
  });
}
