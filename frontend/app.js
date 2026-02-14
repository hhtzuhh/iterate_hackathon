/**
 * SSE chat client using fetch() + ReadableStream.
 * EventSource only supports GET, so we use fetch for POST + SSE.
 */

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function setStatus(text) {
  // Reuse or create status line
  let statusEl = messagesEl.querySelector(".message.status");
  if (!statusEl) {
    statusEl = document.createElement("div");
    statusEl.className = "message status";
    messagesEl.appendChild(statusEl);
  }
  statusEl.textContent = text;
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return statusEl;
}

function removeStatus() {
  const statusEl = messagesEl.querySelector(".message.status");
  if (statusEl) statusEl.remove();
}

async function sendMessage() {
  const message = inputEl.value.trim();
  if (!message) return;

  inputEl.value = "";
  sendBtn.disabled = true;

  appendMessage("user", message);
  const statusEl = setStatus("Thinking…");

  // Create agent response container with blink cursor
  const agentEl = document.createElement("div");
  agentEl.className = "message agent";
  const cursor = document.createElement("span");
  cursor.className = "blink";
  agentEl.appendChild(cursor);
  messagesEl.appendChild(agentEl);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  let buffer = "";
  let textContent = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      console.log("[SSE raw chunk]", JSON.stringify(buffer.slice(-200)));

      // SSE frames are separated by a blank line (\n\n or \r\n\r\n).
      // Normalise \r\n → \n so both delimiters work.
      const normalised = buffer.replace(/\r\n/g, "\n");
      const frames = normalised.split("\n\n");
      buffer = frames.pop(); // keep the trailing incomplete fragment

      for (const frame of frames) {
        if (!frame.trim()) continue;

        // Collect data lines within the frame (ignores event:/id:/comment lines)
        const dataLines = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("data:")) {
            dataLines.push(line.slice("data:".length).trimStart());
          }
        }
        if (dataLines.length === 0) continue;

        const jsonStr = dataLines.join("\n");
        console.log("[SSE frame data]", jsonStr);

        let evt;
        try {
          evt = JSON.parse(jsonStr);
        } catch (e) {
          console.warn("[SSE parse error]", e, jsonStr);
          continue;
        }

        console.log("[SSE event]", evt.type, evt);

        switch (evt.type) {
          case "agent_start":
            statusEl.textContent = "Thinking…";
            break;

          case "text_chunk":
            removeStatus();
            textContent += evt.data;
            // Replace cursor with growing text + cursor at end
            agentEl.textContent = textContent;
            agentEl.appendChild(cursor);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            break;

          case "complete":
            cursor.remove();
            if (!textContent) {
              agentEl.textContent = "(no response)";
            }
            removeStatus();
            break;

          case "error":
            cursor.remove();
            agentEl.className = "message error";
            agentEl.textContent = `Error: ${evt.error}`;
            removeStatus();
            break;

          default:
            console.warn("[SSE unknown type]", evt.type);
        }
      }
    }
  } catch (err) {
    cursor.remove();
    agentEl.className = "message error";
    agentEl.textContent = `Error: ${err.message}`;
    removeStatus();
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
