const taskForm = document.getElementById("taskForm");
const taskList = document.getElementById("taskList");
const message = document.getElementById("message");
const filterButton = document.getElementById("filterButton");

let onlyOpen = false;

function showMessage(text) {
  message.textContent = text;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 204) {
    return null;
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  }
  return data;
}

async function loadTasks() {
  const url = onlyOpen ? "/tasks/?done=false" : "/tasks/";
  try {
    const tasks = await apiFetch(url);
    if (tasks.length === 0) {
      taskList.innerHTML = "<li>Brak elementów.</li>";
      return;
    }

    taskList.innerHTML = tasks.map((task) => `
      <li>
        <label>
          <input
            type="checkbox"
            ${task.done ? "checked" : ""}
            onchange="toggleTask(${task.id}, this.checked)"
          >
          <strong>${escapeHtml(task.title)}</strong>
        </label>
        <div>${task.description ? escapeHtml(task.description) : ""}</div>
        <button type="button" onclick="deleteTask(${task.id})">Usuń</button>
      </li>
    `).join("");
  } catch (error) {
    taskList.innerHTML = "<li>Nie udało się pobrać listy.</li>";
    showMessage(error.message);
  }
}

async function toggleTask(taskId, done) {
  try {
    await apiFetch(`/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ done }),
    });
    showMessage("Zapisano zmianę.");
    await loadTasks();
  } catch (error) {
    showMessage(error.message);
  }
}

async function deleteTask(taskId) {
  try {
    await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
    showMessage("Usunięto element.");
    await loadTasks();
  } catch (error) {
    showMessage(error.message);
  }
}

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();

  if (!title) {
    showMessage("Tytuł jest wymagany.");
    return;
  }

  try {
    await apiFetch("/tasks/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        description: description || null,
      }),
    });
    taskForm.reset();
    showMessage("Dodano element.");
    await loadTasks();
  } catch (error) {
    showMessage(error.message);
  }
});

filterButton.addEventListener("click", async () => {
  onlyOpen = !onlyOpen;
  filterButton.textContent = onlyOpen ? "Pokaż wszystkie" : "Pokaż tylko niezrobione";
  await loadTasks();
});

window.toggleTask = toggleTask;
window.deleteTask = deleteTask;

loadTasks();
