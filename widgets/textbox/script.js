const tabsContainer = document.querySelector(".tabs");
const editor = document.querySelector(".code-editor");
const lineNumbers = document.querySelector(".line-numbers");

let files = {};
let currentFile = null;

function openFile(name) {
  currentFile = name;
  editor.value = files[name];
  updateLineNumbers();

  document.querySelectorAll(".tab").forEach(tab =>
    tab.classList.remove("active")
  );

  document.querySelector(`[data-file="${name}"]`)
    .classList.add("active");
}

function createTab(name) {
  files[name] = "";

  const tab = document.createElement("div");
  tab.className = "tab";
  tab.textContent = name;
  tab.dataset.file = name;

  tab.onclick = () => openFile(name);
  tabsContainer.appendChild(tab);

  openFile(name);
}

editor.addEventListener("input", () => {
  files[currentFile] = editor.value;
  updateLineNumbers();
});

// Create default tabs
createTab("folder1/main.py");
createTab("folder2/file_b.py");
