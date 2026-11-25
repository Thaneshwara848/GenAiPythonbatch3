let mode = "rag";

const chatBox = document.getElementById("chatBox");

const questionInput =
    document.getElementById("questionInput");


// Common API function

async function apiRequest(url, options = {}) {

    const response = await fetch(url, options);

    const data = await response.json();

    if (!response.ok) {

        const message =
            typeof data.detail === "string"
                ? data.detail
                : "Request failed";

        throw new Error(message);
    }

    return data;
}


// Upload Document

async function uploadDocument() {

    const fileInput =
        document.getElementById("fileInput");

    const status =
        document.getElementById("uploadStatus");

    const button =
        document.getElementById("uploadBtn");

    if (!fileInput.files.length) {

        status.textContent = "Please select a document.";

        return;
    }

    const file = fileInput.files[0];

    if (file.size > 10 * 1024 * 1024) {

        status.textContent = "Maximum file size is 10 MB.";

        return;
    }

    const formData = new FormData();

    formData.append("file", file);

    button.disabled = true;

    status.textContent =
        "Extracting text and generating embeddings...";

    try {

        const data = await apiRequest(
            "/documents/upload",
            {
                method: "POST",
                body: formData
            }
        );

        status.textContent =
            `Uploaded successfully! ${data.total_chunks} chunks created.`;

        fileInput.value = "";

        await loadDocuments();

    } catch (error) {

        status.textContent = error.message;

    } finally {

        button.disabled = false;
    }
}


// Load documents

async function loadDocuments() {

    const documentList =
        document.getElementById("documentList");

    try {

        const data = await apiRequest("/documents");

        documentList.replaceChildren();

        document.getElementById("documentCount")
            .textContent = data.total_documents;

        let totalChunks = 0;

        data.documents.forEach(doc => {

            totalChunks += doc.chunks;

            const card = document.createElement("div");

            card.className = "document-card";

            const name = document.createElement("strong");

            name.textContent = doc.filename;

            const details = document.createElement("p");

            details.textContent =
                `Chunks: ${doc.chunks} | Indexed successfully`;

            card.append(name, details);

            documentList.appendChild(card);
        });

        document.getElementById("chunkCount")
            .textContent = totalChunks;

        if (data.documents.length === 0) {

            documentList.textContent =
                "No documents uploaded.";
        }

    } catch (error) {

        documentList.textContent = error.message;
    }
}


// Select RAG or Agent mode

function setMode(selectedMode) {

    mode = selectedMode;

    document.getElementById("ragBtn")
        .classList.toggle("active", mode === "rag");

    document.getElementById("agentBtn")
        .classList.toggle("active", mode === "agent");
}


// Add message to UI

function addMessage(text, sender) {

    const message = document.createElement("div");

    message.className = `message ${sender}`;

    message.textContent = text;

    chatBox.appendChild(message);

    chatBox.scrollTop = chatBox.scrollHeight;

    return message;
}


// Display source references

function displaySources(message, sources) {

    if (!sources || sources.length === 0) {
        return;
    }

    const sourceBox = document.createElement("div");

    sourceBox.className = "sources";

    const heading = document.createElement("strong");

    heading.textContent = "Source References";

    sourceBox.appendChild(heading);

    sources.forEach(source => {

        const details = document.createElement("details");

        const summary = document.createElement("summary");

        const page = source.page
            ? ` | Page: ${source.page}`
            : "";

        summary.textContent =
            `${source.filename}${page}`;

        const content = document.createElement("p");

        content.textContent =
            `Chunk: ${source.chunk_number}\n` +
            `Cosine similarity: ${source.similarity}\n\n` +
            source.text;

        details.append(summary, content);

        sourceBox.appendChild(details);
    });

    message.appendChild(sourceBox);
}


// Display tools used

function displayTools(message, tools) {

    if (!tools || tools.length === 0) {
        return;
    }

    const toolBox = document.createElement("div");

    toolBox.className = "tool-info";

    toolBox.textContent =
        "Tools Used: " + tools.join(", ");

    message.appendChild(toolBox);
}


// Ask question

async function askQuestion() {

    const question = questionInput.value.trim();

    const button = document.getElementById("sendBtn");

    if (!question || button.disabled) {
        return;
    }

    if (question.length < 2) {
        return;
    }

    addMessage(question, "user");

    questionInput.value = "";

    const loading = addMessage(
        "Processing your question...",
        "assistant"
    );

    button.disabled = true;

    const endpoint = mode === "rag"
        ? "/chat/ask"
        : "/agent/chat";

    try {

        const data = await apiRequest(
            endpoint,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    question: question
                })
            }
        );

        loading.textContent = data.answer;

        displayTools(loading, data.tools_used);

        displaySources(loading, data.sources);

    } catch (error) {

        loading.textContent = error.message;

    } finally {

        button.disabled = false;

        chatBox.scrollTop = chatBox.scrollHeight;

        questionInput.focus();
    }
}


// Load chat history

async function loadHistory() {

    if (document.getElementById("sendBtn").disabled) {
        return;
    }

    try {

        const data = await apiRequest("/chat/history");

        chatBox.replaceChildren();

        if (!data.history.length) {

            addMessage("No chat history.", "assistant");

            return;
        }

        data.history.reverse().forEach(item => {

            addMessage(item.question, "user");

            addMessage(
                `[${item.mode}]\n${item.answer}`,
                "assistant"
            );
        });

    } catch (error) {

        addMessage(error.message, "assistant");
    }
}


// Submit question using Enter key

questionInput.addEventListener("keydown", event => {

    if (event.key === "Enter") {

        askQuestion();
    }
});


// Load documents when the application starts

loadDocuments();