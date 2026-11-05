"use strict";

const editor = document.querySelector("[data-page-editor]");

if (editor) {
  const markdownInput = editor.querySelector("[data-markdown]");
  const preview = document.querySelector("[data-preview-content]");
  const message = editor.querySelector("[data-form-message]");

  function showError(text) {
    message.textContent = text;
    message.setAttribute("role", "alert");
  }

  function showRequestError(error) {
    showError(error instanceof TypeError
      ? "Не удалось связаться с сервисом. Проверьте соединение."
      : error.message);
  }

  function describeError(statusCode) {
    if (statusCode === 404) return "Страница не найдена. Обновите список и попробуйте снова.";
    if (statusCode === 409) return "Страница с таким путём уже существует. Выберите другой путь.";
    if (statusCode === 422) return "Проверьте путь, заголовок и текст. Исправьте поля и повторите попытку.";
    return "Не удалось выполнить запрос. Проверьте соединение и попробуйте ещё раз.";
  }

  async function requestJson(url, method, body) {
    const headers = { "Content-Type": "application/json" };
    if (method !== "GET") {
      const tokenResponse = await fetch("/api/auth/csrf", { credentials: "same-origin" });
      if (!tokenResponse.ok) throw new Error("Сессия завершилась. Войдите снова.");
      headers["X-CSRF-Token"] = (await tokenResponse.json()).csrf_token;
    }
    const response = await fetch(url, {
      method,
      headers,
      body: JSON.stringify(body),
    });
    let payload = null;
    if (response.status !== 204) {
      try {
        payload = await response.json();
      } catch {
        throw new Error("Сервис вернул неожиданный ответ. Попробуйте ещё раз.");
      }
    }
    if (!response.ok) {
      throw new Error(describeError(response.status));
    }
    return payload;
  }

  async function updatePreview() {
    message.textContent = "";
    const button = editor.querySelector("[data-preview]");
    button.disabled = true;
    try {
      const result = await requestJson("/api/markdown/preview", "POST", {
        markdown: markdownInput.value,
      });
      preview.innerHTML = result.html;
    } catch (error) {
      showRequestError(error);
    } finally {
      button.disabled = false;
    }
  }

  editor.querySelector("[data-preview]").addEventListener("click", updatePreview);

  editor.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";
    const create = editor.dataset.mode === "create";
    const body = {
      title: editor.querySelector("[name='title']").value,
      markdown: markdownInput.value,
      tags: editor.querySelector("[name='tags']").value.split(",").map((tag) => tag.trim()).filter(Boolean),
    };
    const url = create ? "/api/pages" : `/api/pages/${editor.dataset.pageId}`;
    if (create) {
      body.path = editor.querySelector("[name='path']").value;
    }
    const button = editor.querySelector("[type='submit']");
    button.disabled = true;
    try {
      const page = await requestJson(url, create ? "POST" : "PATCH", body);
      window.location.assign(`/wiki${page.path}`);
    } catch (error) {
      showRequestError(error);
    } finally {
      button.disabled = false;
    }
  });

  const deleteButton = editor.querySelector("[data-delete]");
  if (deleteButton) {
    deleteButton.addEventListener("click", async () => {
      if (!window.confirm("Удалить эту страницу? Вложенные страницы сохранятся.")) {
        return;
      }
      deleteButton.disabled = true;
      try {
        await requestJson(`/api/pages/${editor.dataset.pageId}`, "DELETE");
        window.location.assign("/pages");
      } catch (error) {
        showRequestError(error);
        deleteButton.disabled = false;
      }
    });
  }
}
