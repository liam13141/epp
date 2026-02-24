const lessons = [
  {
    id: "lesson_1",
    title: "Lesson 1: What Programming Is",
    summary: "A program is just a list of instructions. E++ uses plain sentences.",
    example: 'say "Hello, world"',
  },
  {
    id: "lesson_2",
    title: "Lesson 2: Variables (Storing Information)",
    summary: "Use variables like labeled boxes to store numbers and text.",
    example: 'set name to "Ava"\nsay name',
  },
  {
    id: "lesson_3",
    title: "Lesson 3: Decisions (if / otherwise)",
    summary: "Teach your program how to choose between actions.",
    example: 'if score is at least 5 then\n  say "Pass"\notherwise\n  say "Retry"\nend if',
  },
  {
    id: "lesson_4",
    title: "Lesson 4: Loops (Repeating Work)",
    summary: "Repeat steps many times without rewriting the same line.",
    example: 'repeat 3 times\n  say "Practice makes progress"\nend repeat',
  },
  {
    id: "lesson_5",
    title: "Lesson 5: Lists and For-Each",
    summary: "Store many values and handle them one by one.",
    example: "create list fruits\nadd \"apple\" to fruits\nfor each item in fruits\n  say item\nend for",
  },
  {
    id: "lesson_6",
    title: "Lesson 6: Functions (Reusable Tools)",
    summary: "Group instructions into named actions you can call later.",
    example: "define greet with name\n  say \"Hi \" + name\nend define\ncall greet with \"Nia\"",
  },
];

const quizQuestions = [
  {
    id: "q1",
    prompt: "Which E++ line creates a variable named age with value 12?",
    options: ["say age 12", "set age to 12", "create age = 12"],
    answer: 1,
  },
  {
    id: "q2",
    prompt: "How do you print text?",
    options: ['say "Hello"', 'print "Hello"', 'set text to "Hello"'],
    answer: 0,
  },
  {
    id: "q3",
    prompt: "Which line starts a 5-time loop?",
    options: ["repeat while 5", "repeat 5 times", "for each 5 in loop"],
    answer: 1,
  },
  {
    id: "q4",
    prompt: "Which line closes an if block?",
    options: ["close if", "otherwise", "end if"],
    answer: 2,
  },
  {
    id: "q5",
    prompt: "What does `add 3 to points` mean?",
    options: ["points = 3", "points += 3", "print 3 points"],
    answer: 1,
  },
];

const LESSON_STATE_KEY = "epp_course_lesson_state_v1";
const STEP_STATE_KEY = "epp_course_step_state_v1";

const lessonList = document.getElementById("lessonList");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");
const quizForm = document.getElementById("quizForm");
const quizResult = document.getElementById("quizResult");
const translateMode = document.getElementById("translateMode");
const eppInput = document.getElementById("eppInput");
const inputLabel = document.getElementById("inputLabel");
const outputLabel = document.getElementById("outputLabel");
const pythonOutput = document.getElementById("pythonOutput");
const translateHelp = document.getElementById("translateHelp");

function readJsonState(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw);
  } catch (error) {
    return fallback;
  }
}

function saveJsonState(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function renderLessons() {
  const doneMap = readJsonState(LESSON_STATE_KEY, {});
  lessonList.innerHTML = "";

  lessons.forEach((lesson) => {
    const done = Boolean(doneMap[lesson.id]);
    const card = document.createElement("article");
    card.className = "lesson-card";
    card.innerHTML = `
      <h3>${lesson.title}</h3>
      <p class="lesson-meta">${lesson.summary}</p>
      <pre class="lesson-example">${lesson.example}</pre>
      <button type="button" class="btn ${done ? "btn-success" : "btn-muted"}" data-lesson-id="${lesson.id}">
        ${done ? "Completed" : "Mark as Complete"}
      </button>
    `;
    lessonList.appendChild(card);
  });

  lessonList.querySelectorAll("button[data-lesson-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const lessonId = button.getAttribute("data-lesson-id");
      const current = readJsonState(LESSON_STATE_KEY, {});
      current[lessonId] = !current[lessonId];
      saveJsonState(LESSON_STATE_KEY, current);
      renderLessons();
      updateProgress();
    });
  });

  updateProgress();
}

function updateProgress() {
  const doneMap = readJsonState(LESSON_STATE_KEY, {});
  const doneCount = lessons.filter((lesson) => doneMap[lesson.id]).length;
  const percent = Math.round((doneCount / lessons.length) * 100);
  progressFill.style.width = `${percent}%`;
  progressText.textContent = `${doneCount}/${lessons.length} lessons complete (${percent}%)`;
}

function normalizePyLiterals(expr) {
  return expr
    .replace(/\bTrue\b/g, "true")
    .replace(/\bFalse\b/g, "false")
    .replace(/\bNone\b/g, "nothing");
}

function translateEppConditionToPython(text) {
  return text
    .replace(/\bis at least\b/gi, ">=")
    .replace(/\bis at most\b/gi, "<=")
    .replace(/\bis greater than\b/gi, ">")
    .replace(/\bis less than\b/gi, "<")
    .replace(/\bequals\b/gi, "==")
    .replace(/\bis not\b/gi, "!=")
    .replace(/\bdoes not contain\b/gi, " not in ")
    .replace(/\bcontains\b/gi, " in ")
    .trim();
}

function translateEppLineToPython(line) {
  const trimmed = line.trim();
  if (!trimmed) {
    return "";
  }
  if (trimmed.startsWith("#")) {
    return trimmed;
  }

  let match;

  match = trimmed.match(/^set\s+([A-Za-z_]\w*)\s+to\s+(.+)$/i);
  if (match) {
    return `${match[1]} = ${match[2]}`;
  }

  match = trimmed.match(/^say\s+(.+)$/i);
  if (match) {
    return `print(${match[1]})`;
  }

  match = trimmed.match(/^add\s+(.+)\s+to\s+([A-Za-z_]\w*)$/i);
  if (match) {
    return `${match[2]} += ${match[1]}`;
  }

  match = trimmed.match(/^subtract\s+(.+)\s+from\s+([A-Za-z_]\w*)$/i);
  if (match) {
    return `${match[2]} -= ${match[1]}`;
  }

  match = trimmed.match(/^multiply\s+([A-Za-z_]\w*)\s+by\s+(.+)$/i);
  if (match) {
    return `${match[1]} *= ${match[2]}`;
  }

  match = trimmed.match(/^divide\s+([A-Za-z_]\w*)\s+by\s+(.+)$/i);
  if (match) {
    return `${match[1]} /= ${match[2]}`;
  }

  match = trimmed.match(/^if\s+(.+)\s+then$/i);
  if (match) {
    return `if ${translateEppConditionToPython(match[1])}:`;
  }

  match = trimmed.match(/^otherwise if\s+(.+)\s+then$/i);
  if (match) {
    return `elif ${translateEppConditionToPython(match[1])}:`;
  }

  if (/^otherwise$/i.test(trimmed)) {
    return "else:";
  }

  if (/^end if$/i.test(trimmed)) {
    return "# end if";
  }

  match = trimmed.match(/^repeat\s+(.+)\s+times$/i);
  if (match) {
    return `for _ in range(${match[1]}):`;
  }

  match = trimmed.match(/^repeat while\s+(.+)$/i);
  if (match) {
    return `while ${translateEppConditionToPython(match[1])}:`;
  }

  if (/^end repeat$/i.test(trimmed)) {
    return "# end repeat";
  }

  match = trimmed.match(/^for each\s+([A-Za-z_]\w*)\s+in\s+(.+)$/i);
  if (match) {
    return `for ${match[1]} in ${match[2]}:`;
  }

  if (/^end for$/i.test(trimmed)) {
    return "# end for";
  }

  match = trimmed.match(/^define\s+([A-Za-z_]\w*)(?:\s+with\s+(.+))?$/i);
  if (match) {
    const rawArgs = match[2] ? match[2].replace(/\s+and\s+/gi, ", ") : "";
    return `def ${match[1]}(${rawArgs}):`;
  }

  match = trimmed.match(/^call\s+([A-Za-z_]\w*)(?:\s+with\s+(.+))?$/i);
  if (match) {
    const rawArgs = match[2] ? match[2].replace(/\s+and\s+/gi, ", ") : "";
    return `${match[1]}(${rawArgs})`;
  }

  match = trimmed.match(/^return(?:\s+(.+))?$/i);
  if (match) {
    return match[1] ? `return ${match[1]}` : "return";
  }

  if (/^end define$/i.test(trimmed)) {
    return "# end define";
  }

  match = trimmed.match(/^create list\s+([A-Za-z_]\w*)$/i);
  if (match) {
    return `${match[1]} = []`;
  }

  match = trimmed.match(/^remove\s+(.+)\s+from\s+([A-Za-z_]\w*)$/i);
  if (match) {
    return `${match[2]}.remove(${match[1]})`;
  }

  match = trimmed.match(/^ask\s+(.+)\s+and store in\s+([A-Za-z_]\w*)$/i);
  if (match) {
    return `${match[2]} = input(${match[1]})`;
  }

  if (/^stop(?:\s+(?:repeat|for|loop))?$/i.test(trimmed)) {
    return "break";
  }

  if (/^skip(?:\s+(?:repeat|for|loop))?$/i.test(trimmed)) {
    return "continue";
  }

  return "I do not recognize this sentence yet. Try one command on one line.";
}

function splitPyArgsToEpp(rawArgs) {
  const clean = rawArgs.trim();
  if (!clean) {
    return "";
  }
  return clean.replace(/\s*,\s*/g, ", ");
}

function translateSimplePythonConditionToEpp(condition) {
  let expr = normalizePyLiterals(condition.trim());
  if (/\b(and|or|not)\b/.test(expr)) {
    return expr;
  }

  let match = expr.match(/^(.+)\s+not\s+in\s+(.+)$/);
  if (match) {
    return `${match[2].trim()} does not contain ${match[1].trim()}`;
  }

  match = expr.match(/^(.+)\s+in\s+(.+)$/);
  if (match) {
    return `${match[2].trim()} contains ${match[1].trim()}`;
  }

  return expr
    .replace(/>=/g, " is at least ")
    .replace(/<=/g, " is at most ")
    .replace(/==/g, " equals ")
    .replace(/!=/g, " is not ")
    .replace(/>/g, " is greater than ")
    .replace(/</g, " is less than ")
    .replace(/\s+/g, " ")
    .trim();
}

function translatePythonLineToEpp(trimmed) {
  if (!trimmed) {
    return { text: "", openKind: null };
  }
  if (trimmed.startsWith("#")) {
    return { text: trimmed, openKind: null };
  }

  let match;

  match = trimmed.match(/^if\s+(.+)\s*:\s*$/i);
  if (match) {
    return { text: `if ${translateSimplePythonConditionToEpp(match[1])} then`, openKind: "if" };
  }

  match = trimmed.match(/^elif\s+(.+)\s*:\s*$/i);
  if (match) {
    return { text: `otherwise if ${translateSimplePythonConditionToEpp(match[1])} then`, openKind: null };
  }

  if (/^else\s*:\s*$/i.test(trimmed)) {
    return { text: "otherwise", openKind: null };
  }

  match = trimmed.match(/^while\s+(.+)\s*:\s*$/i);
  if (match) {
    return { text: `repeat while ${translateSimplePythonConditionToEpp(match[1])}`, openKind: "repeat" };
  }

  match = trimmed.match(/^for\s+_\s+in\s+range\((.+)\)\s*:\s*$/i);
  if (match) {
    return { text: `repeat ${normalizePyLiterals(match[1].trim())} times`, openKind: "repeat" };
  }

  match = trimmed.match(/^for\s+([A-Za-z_]\w*)\s+in\s+(.+)\s*:\s*$/i);
  if (match) {
    return { text: `for each ${match[1]} in ${normalizePyLiterals(match[2].trim())}`, openKind: "for" };
  }

  match = trimmed.match(/^def\s+([A-Za-z_]\w*)\s*\((.*)\)\s*:\s*$/i);
  if (match) {
    const params = splitPyArgsToEpp(match[2]);
    if (params) {
      return { text: `define ${match[1]} with ${params}`, openKind: "define" };
    }
    return { text: `define ${match[1]}`, openKind: "define" };
  }

  match = trimmed.match(/^return(?:\s+(.+))?$/i);
  if (match) {
    return { text: match[1] ? `return ${normalizePyLiterals(match[1])}` : "return", openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*=\s*input\((.+)\)\s*$/i);
  if (match) {
    return { text: `ask ${normalizePyLiterals(match[2])} and store in ${match[1]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*=\s*\[\s*\]\s*$/);
  if (match) {
    return { text: `create list ${match[1]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\.append\((.+)\)\s*$/i);
  if (match) {
    return { text: `add ${normalizePyLiterals(match[2])} to ${match[1]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\.remove\((.+)\)\s*$/i);
  if (match) {
    return { text: `remove ${normalizePyLiterals(match[2])} from ${match[1]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*\+=\s*(.+)$/);
  if (match) {
    return { text: `add ${normalizePyLiterals(match[2])} to ${match[1]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*-=\s*(.+)$/);
  if (match) {
    return { text: `subtract ${normalizePyLiterals(match[2])} from ${match[1]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*\*=\s*(.+)$/);
  if (match) {
    return { text: `multiply ${match[1]} by ${normalizePyLiterals(match[2])}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*\/=\s*(.+)$/);
  if (match) {
    return { text: `divide ${match[1]} by ${normalizePyLiterals(match[2])}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\((.*)\)\s*$/);
  if (match) {
    const args = splitPyArgsToEpp(match[3]);
    if (args) {
      return { text: `set ${match[1]} to call ${match[2]} with ${normalizePyLiterals(args)}`, openKind: null };
    }
    return { text: `set ${match[1]} to call ${match[2]}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\s*=\s*(.+)$/);
  if (match) {
    return { text: `set ${match[1]} to ${normalizePyLiterals(match[2])}`, openKind: null };
  }

  match = trimmed.match(/^print\((.+)\)\s*$/i);
  if (match) {
    return { text: `say ${normalizePyLiterals(match[1])}`, openKind: null };
  }

  match = trimmed.match(/^([A-Za-z_]\w*)\((.*)\)\s*$/);
  if (match) {
    const args = splitPyArgsToEpp(match[2]);
    if (args) {
      return { text: `call ${match[1]} with ${normalizePyLiterals(args)}`, openKind: null };
    }
    return { text: `call ${match[1]}`, openKind: null };
  }

  if (/^break$/i.test(trimmed)) {
    return { text: "stop repeat", openKind: null };
  }

  if (/^continue$/i.test(trimmed)) {
    return { text: "skip repeat", openKind: null };
  }

  if (/^pass$/i.test(trimmed)) {
    return { text: "# pass", openKind: null };
  }

  return { text: "# unsupported python line: " + trimmed, openKind: null };
}

function closingForEppBlock(kind) {
  if (kind === "if") {
    return "end if";
  }
  if (kind === "repeat") {
    return "end repeat";
  }
  if (kind === "for") {
    return "end for";
  }
  if (kind === "define") {
    return "end define";
  }
  return "# end";
}

function leadingIndentWidth(rawLine) {
  const leading = rawLine.match(/^\s*/)[0].replace(/\t/g, "    ");
  return leading.length;
}

function translatePythonBlockToEpp(source) {
  const lines = source.split("\n");
  const out = [];
  const blocks = [];

  lines.forEach((rawLine) => {
    const trimmed = rawLine.trim();
    if (!trimmed) {
      out.push("");
      return;
    }

    const indent = leadingIndentWidth(rawLine);
    while (blocks.length > 0) {
      const top = blocks[blocks.length - 1];
      const elifOrElseAtIfLevel = top.kind === "if" && indent === top.indent && /^(elif\b|else\s*:)/i.test(trimmed);
      if (elifOrElseAtIfLevel) {
        break;
      }
      if (indent <= top.indent) {
        out.push(closingForEppBlock(top.kind));
        blocks.pop();
      } else {
        break;
      }
    }

    const translated = translatePythonLineToEpp(trimmed);
    out.push(translated.text);

    if (translated.openKind) {
      blocks.push({ kind: translated.openKind, indent });
    }
  });

  while (blocks.length > 0) {
    const top = blocks.pop();
    out.push(closingForEppBlock(top.kind));
  }

  return out.join("\n");
}

function updateTranslatorUI() {
  const mode = translateMode.value;
  if (mode === "python_to_epp") {
    inputLabel.textContent = "Python input";
    outputLabel.textContent = "E++ output";
    eppInput.placeholder = 'Example:\nscore = 10\nif score >= 5:\n    print("Pass")';
    translateHelp.textContent = "Tip: paste a small Python block with indentation; the converter adds end if/end repeat/end define.";
    pythonOutput.textContent = "Your E++ translation will appear here.";
    return;
  }

  inputLabel.textContent = "E++ input";
  outputLabel.textContent = "Python output";
  eppInput.placeholder = "Example:\nset score to 10\nif score is at least 5 then\n  say \"Pass\"\nend if";
  translateHelp.textContent = "Supports common beginner syntax: variables, output, loops, if blocks, functions, lists, input, and comments.";
  pythonOutput.textContent = "Your Python translation will appear here.";
}

function handleTranslate() {
  const input = eppInput.value.trim();
  if (!input) {
    pythonOutput.textContent = translateMode.value === "python_to_epp"
      ? "Please type some Python code first."
      : "Please type some E++ code first.";
    return;
  }

  if (translateMode.value === "python_to_epp") {
    pythonOutput.textContent = translatePythonBlockToEpp(input);
    return;
  }

  const lines = input.split("\n").map((line) => translateEppLineToPython(line));
  pythonOutput.textContent = lines.join("\n");
}

function renderQuiz() {
  quizForm.innerHTML = "";

  quizQuestions.forEach((question, index) => {
    const wrapper = document.createElement("fieldset");
    wrapper.className = "quiz-card";
    wrapper.innerHTML = `<legend>${index + 1}. ${question.prompt}</legend>`;

    const options = document.createElement("div");
    options.className = "quiz-options";

    question.options.forEach((option, optionIndex) => {
      const id = `${question.id}_${optionIndex}`;
      const label = document.createElement("label");
      label.setAttribute("for", id);
      label.innerHTML = `
        <input type="radio" id="${id}" name="${question.id}" value="${optionIndex}">
        ${option}
      `;
      options.appendChild(label);
    });

    wrapper.appendChild(options);
    quizForm.appendChild(wrapper);
  });
}

function gradeQuiz() {
  let score = 0;

  quizQuestions.forEach((question) => {
    const selected = quizForm.querySelector(`input[name="${question.id}"]:checked`);
    if (selected && Number(selected.value) === question.answer) {
      score += 1;
    }
  });

  const total = quizQuestions.length;
  const percent = Math.round((score / total) * 100);
  if (percent === 100) {
    quizResult.textContent = `Excellent: ${score}/${total}. You are ready to build your own script.`;
    quizResult.style.color = "#2a9d8f";
    return;
  }
  if (percent >= 70) {
    quizResult.textContent = `Great work: ${score}/${total}. Review one lesson and try again.`;
    quizResult.style.color = "#05668d";
    return;
  }
  quizResult.textContent = `You got ${score}/${total}. Revisit lessons 1-4 and test commands in the translator.`;
  quizResult.style.color = "#bc4749";
}

function resetQuiz() {
  quizForm.reset();
  quizResult.textContent = "";
}

function setupChecklist() {
  const checkboxes = Array.from(document.querySelectorAll("input[data-step]"));
  const state = readJsonState(STEP_STATE_KEY, {});

  checkboxes.forEach((checkbox) => {
    const stepId = checkbox.getAttribute("data-step");
    checkbox.checked = Boolean(state[stepId]);
    checkbox.addEventListener("change", () => {
      const updated = readJsonState(STEP_STATE_KEY, {});
      updated[stepId] = checkbox.checked;
      saveJsonState(STEP_STATE_KEY, updated);
    });
  });

  const resetStepsBtn = document.getElementById("resetStepsBtn");
  resetStepsBtn.addEventListener("click", () => {
    checkboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
    saveJsonState(STEP_STATE_KEY, {});
  });
}

function setupCopyScript() {
  const button = document.getElementById("copyScriptBtn");
  const status = document.getElementById("copyStatus");
  const scriptText = document.getElementById("firstScript").textContent;

  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(scriptText);
      status.textContent = "Copied.";
    } catch (error) {
      status.textContent = "Clipboard blocked. Copy manually from the code box.";
    }
  });
}

document.getElementById("translateBtn").addEventListener("click", handleTranslate);
document.getElementById("clearBtn").addEventListener("click", () => {
  eppInput.value = "";
  updateTranslatorUI();
});
translateMode.addEventListener("change", updateTranslatorUI);
document.getElementById("gradeQuizBtn").addEventListener("click", gradeQuiz);
document.getElementById("resetQuizBtn").addEventListener("click", resetQuiz);

renderLessons();
renderQuiz();
setupChecklist();
setupCopyScript();
updateTranslatorUI();
