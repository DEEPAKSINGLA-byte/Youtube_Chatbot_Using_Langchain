const videoInput = document.getElementById("video");
const questionInput = document.getElementById("question");
const languageInput = document.getElementById("language");
const loadButton = document.getElementById("load-btn");
const askButton = document.getElementById("ask-btn");
const statusBox = document.getElementById("status");
const chatBox = document.getElementById("chat-box");

let loadedVideoLanguage = null;


async function loadVideo() {
    const videoId = videoInput.value.trim();

    if (videoId === "") {
        statusBox.innerText = "Please enter a video ID.";
        return;
    }

    setButtonState(loadButton, true, "Loading...");
    statusBox.innerText = "Loading video...";
    chatBox.innerHTML = "";

    try {
        const response = await fetchJson("/load_video", {
            video_id: videoId,
            language: languageInput.value
        });

        if (!response.ok) {
            statusBox.innerText = response.data.error || "Unable to load video.";
            return;
        }

        showVideoStatus(response.data);
    }
    catch (error) {
        statusBox.innerText = "Something went wrong while loading the video.";
    }
    finally {
        setButtonState(loadButton, false, "Load Video");
    }
}


async function askQuestion() {
    const question = questionInput.value.trim();

    if (question === "") {
        addMessage("bot", "Please enter a question.");
        return;
    }

    if (loadedVideoLanguage !== languageInput.value) {
        addMessage("bot", "Please load the video again for the selected language.");
        return;
    }

    setButtonState(askButton, true, "Thinking...");
    addMessage("user", question);
    addMessage("bot", "Thinking...");

    try {
        const response = await fetchJson("/ask", {
            question: question,
            language: languageInput.value
        });

        if (!response.ok) {
            updateLastBotMessage(response.data.error || "Unable to answer question.");
            return;
        }

        updateLastBotMessage(response.data.answer);

        addSources(response.data.sources || []);
    }
    catch (error) {
        updateLastBotMessage("Something went wrong while answering.");
    }
    finally {
        setButtonState(askButton, false, "Ask");
    }
}


function addMessage(sender, text) {
    const message = document.createElement("div");

    message.classList.add("message");
    message.classList.add(sender);
    message.innerHTML = `
    <strong>${sender === "user" ? "You" : "AI"}</strong><br>
    ${sender === "bot" ? marked.parse(text) : escapeHtml(text)}
`;

    chatBox.appendChild(message);
    chatBox.scrollTop = chatBox.scrollHeight;
}


function addSources(sources) {
    if (sources.length === 0) {
        return;
    }

    const sourceGroup = document.createElement("div");
    sourceGroup.classList.add("source-group");
    sourceGroup.innerHTML = `
        <div class="source-heading">
            <span>Sources</span>
            <span>${sources.length} retrieved chunks</span>
        </div>
    `;

    sources.forEach((sourceText, index) => {
        const source = document.createElement("details");
        const preview = getSourcePreview(sourceText);

        source.classList.add("source");
        source.innerHTML = `
            <summary>
                <span class="source-number">${index + 1}</span>
                <span class="source-preview">${escapeHtml(preview)}</span>
            </summary>
            <p>${escapeHtml(sourceText)}</p>
        `;

        sourceGroup.appendChild(source);
    });

    chatBox.appendChild(sourceGroup);
    chatBox.scrollTop = chatBox.scrollHeight;
}


function getSourcePreview(text) {
    const normalizedText = text.replace(/\s+/g, " ").trim();

    if (normalizedText.length <= 140) {
        return normalizedText;
    }

    return `${normalizedText.slice(0, 140)}...`;
}


function updateLastBotMessage(text) {
    const messages = chatBox.querySelectorAll(".message.bot");
    const lastBotMessage = messages[messages.length - 1];

    if (!lastBotMessage) {
        addMessage("bot", text);
        return;
    }

    lastBotMessage.innerHTML = `
        <strong>AI</strong><br>
        ${marked.parse(text)}
    `;

    chatBox.scrollTop = chatBox.scrollHeight;
}


function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}


async function fetchJson(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(body)
    });

    const data = await response.json();

    return {
        ok: response.ok,
        data: data
    };
}


function showVideoStatus(data) {
    loadedVideoLanguage = data.language;
    statusBox.innerText =
        `${data.message}\n\n` +
        `Language: ${data.language_name}\n` +
        `Chunks created: ${data.chunks}\n` +
        `Embedding model: ${data.embedding_model}\n\n` +
        "Ready to answer questions.";
}


function setButtonState(button, isLoading, text) {
    button.disabled = isLoading;
    button.innerText = text;
}

loadButton.addEventListener("click", loadVideo);
askButton.addEventListener("click", askQuestion);
languageInput.addEventListener("change", () => {
    loadedVideoLanguage = null;
    statusBox.innerText = "Load the video for the selected language.";
    chatBox.innerHTML = "";
});
