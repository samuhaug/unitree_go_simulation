const keys = new Set();
let currentMode = "UNKNOWN";
let modeRequestInProgress = false;
let activeDirection = null;
let requestInProgress = false;

const connection = document.getElementById("connection");
const movement = document.getElementById("movement");
const commandStatus = document.getElementById("command-status");

const sliders = {
    forward: document.getElementById("forward"),
    backward: document.getElementById("backward"),
    turn: document.getElementById("turn")
};

function updateSliderLabels() {
    document.getElementById("forward-value").textContent =
        Number(sliders.forward.value).toFixed(2) + " m/s";

    document.getElementById("backward-value").textContent =
        Number(sliders.backward.value).toFixed(2) + " m/s";

    document.getElementById("turn-value").textContent =
        Number(sliders.turn.value).toFixed(2) + " rad/s";
}

Object.values(sliders).forEach(slider => {
    slider.addEventListener("input", updateSliderLabels);
});

updateSliderLabels();

function getCommand() {
    const direction = activeDirection;

    if (direction === "w") {
        return {
            linear: Number(sliders.forward.value),
            angular: 0,
            name: "Vorwärts"
        };
    }

    if (direction === "s") {
        return {
            linear: -Number(sliders.backward.value),
            angular: 0,
            name: "Rückwärts"
        };
    }

    if (direction === "a") {
        return {
            linear: 0,
            angular: Number(sliders.turn.value),
            name: "Links"
        };
    }

    if (direction === "d") {
        return {
            linear: 0,
            angular: -Number(sliders.turn.value),
            name: "Rechts"
        };
    }

    return { linear: 0, angular: 0, name: "Stopp" };
}

async function sendCommand() {
    if (currentMode !== "MANUAL" || modeRequestInProgress) return;
    if (requestInProgress) return;

    requestInProgress = true;
    const command = getCommand();

    movement.textContent = "Aktuelle Bewegung: " + command.name;
    commandStatus.textContent = command.name;

    try {
        const response = await fetch("/api/control", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                linear: command.linear,
                angular: command.angular
            })
        });

        if (!response.ok) throw new Error("Steuerbefehl fehlgeschlagen");
    } catch (error) {
        connection.textContent = "Verbindung unterbrochen";
        connection.className = "status offline";
    } finally {
        requestInProgress = false;
    }
}

function updateDirection() {
    if (currentMode !== "MANUAL") {
        keys.clear();
    }

    activeDirection = ["w", "s", "a", "d"].find(key => keys.has(key)) || null;

    document.querySelectorAll(".move").forEach(button => {
        button.classList.toggle(
            "pressed",
            button.dataset.direction === activeDirection
        );
    });

    sendCommand();
}

function stopRobot() {
    keys.clear();
    activeDirection = null;
    updateDirection();

    fetch("/api/stop", { method: "POST", keepalive: true }).catch(() => {});
}

document.addEventListener("keydown", event => {
    const key = event.key.toLowerCase();

    if (event.code === "Space") {
        event.preventDefault();
        stopRobot();
        return;
    }

    if (!["w", "a", "s", "d"].includes(key)) return;
    if (currentMode !== "MANUAL" || modeRequestInProgress) return;

    if (event.target.tagName === "INPUT") return;

    event.preventDefault();
    keys.add(key);
    updateDirection();
});

document.addEventListener("keyup", event => {
    const key = event.key.toLowerCase();

    if (!["w", "a", "s", "d"].includes(key)) return;

    keys.delete(key);
    updateDirection();
});

document.querySelectorAll(".move").forEach(button => {
    const direction = button.dataset.direction;

    button.addEventListener("pointerdown", event => {
        event.preventDefault();
        keys.add(direction);
        updateDirection();
    });

    button.addEventListener("pointerup", stopRobot);
    button.addEventListener("pointercancel", stopRobot);
    button.addEventListener("lostpointercapture", stopRobot);
});

document.getElementById("stop").addEventListener("click", stopRobot);

window.addEventListener("blur", stopRobot);
window.addEventListener("pagehide", stopRobot);

document.addEventListener("visibilitychange", () => {
    if (document.hidden) stopRobot();
});

document.querySelectorAll(".tab").forEach(tab => {
    tab.addEventListener("click", () => {
        stopRobot();

        document.querySelectorAll(".tab").forEach(item => {
            item.classList.remove("active");
        });

        document.querySelectorAll(".page").forEach(page => {
            page.classList.remove("active");
        });

        tab.classList.add("active");
        document.getElementById(tab.dataset.page).classList.add("active");
    });
});

function applyMode(mode, connected) {
    const previousMode = currentMode;

    currentMode = connected ? mode : "UNKNOWN";

    if (previousMode !== currentMode || currentMode !== "MANUAL") {
        keys.clear();
        activeDirection = null;

        document.querySelectorAll(".move").forEach(button => {
            button.classList.remove("pressed");
        });

        movement.textContent = "Aktuelle Bewegung: Stopp";
        commandStatus.textContent = "Stopp";
    }

    const label = currentMode === "UNKNOWN"
        ? "Nicht verbunden"
        : currentMode;

    document.getElementById("current-mode").textContent = label;
    document.getElementById("system-mode").textContent = label;

    document.querySelectorAll(".mode-button").forEach(button => {
        button.disabled = !connected || modeRequestInProgress;
        button.classList.toggle(
            "active",
            connected && button.dataset.mode === currentMode
        );
    });

    document.querySelectorAll(".move").forEach(button => {
        button.disabled = currentMode !== "MANUAL";
    });
}

async function changeMode(mode) {
    if (modeRequestInProgress || currentMode === "UNKNOWN") return;

    modeRequestInProgress = true;
    keys.clear();
    activeDirection = null;

    // Zuerst vorhandene manuelle Bewegung stoppen.
    await fetch("/api/stop", { method: "POST" }).catch(() => {});

    applyMode(currentMode, true);

    try {
        const response = await fetch("/api/mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode })
        });

        if (!response.ok) throw new Error("Moduswechsel fehlgeschlagen");

        // Tatsächlichen Modus anschließend vom Mux lesen.
        await checkStatus();
    } catch (error) {
        connection.textContent = "Moduswechsel fehlgeschlagen";
        connection.className = "status offline";
    } finally {
        modeRequestInProgress = false;
        await checkStatus();
    }
}

document.querySelectorAll(".mode-button").forEach(button => {
    button.addEventListener("click", async () => {
        if (
            button.dataset.mode === "STOP" &&
            button.closest("#navigation")
        ) {
            // Sofort STOP anfordern und Nav2-Ziel abbrechen.
            button.disabled = true;

            try {
                const response = await fetch("/api/emergency_stop", {
                    method: "POST"
                });

                if (!response.ok) {
                    throw new Error("Not-Stopp fehlgeschlagen");
                }
            } catch (error) {
                alert(error.message);
            } finally {
                await checkStatus();
            }

            return;
        }

        changeMode(button.dataset.mode);
    });
});

async function checkStatus() {
    try {
        const response = await fetch("/api/status", {
            cache: "no-store"
        });

        if (!response.ok) throw new Error();

        const data = await response.json();
        const connected = data.connected === true;

        applyMode(data.mode, connected);

        connection.textContent = connected
            ? "Control Mux verbunden"
            : "Control Mux offline";

        connection.className = connected
            ? "status online"
            : "status offline";

        document.getElementById("server-status").textContent =
            "Flask online";

    } catch {
        applyMode("UNKNOWN", false);

        connection.textContent = "Dashboard offline";
        connection.className = "status offline";

        document.getElementById("server-status").textContent =
            "Offline";
    }
}

setInterval(() => {
    if (activeDirection !== null) sendCommand();
}, 100);

setInterval(checkStatus, 2000);
checkStatus();

// Simulation: Status anzeigen und Startbutton steuern.
const simulationButton = document.getElementById("start-simulation");
const simulationStatus = document.getElementById("simulation-status");
let simulationStarting = false;

async function checkSimulation() {
    try {
        const response = await fetch("/api/simulation", {
            cache: "no-store"
        });

        if (!response.ok) throw new Error("Statusabfrage fehlgeschlagen");

        const data = await response.json();

        simulationStatus.textContent = data.running
            ? "🟢 Läuft"
            : simulationStarting
                ? "🟡 Startet ..."
                : "⚪ Gestoppt";

        if (data.running) simulationStarting = false;

        simulationButton.disabled = data.running || simulationStarting;
    } catch {
        simulationStatus.textContent = "🔴 Status unbekannt";
        simulationButton.disabled = true;
    }
}

simulationButton.addEventListener("click", async () => {
    if (simulationStarting) return;

    simulationStarting = true;
    simulationButton.disabled = true;
    simulationStatus.textContent = "🟡 Startet ...";

    try {
        const response = await fetch("/api/simulation/start", {
            method: "POST"
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || "Start fehlgeschlagen");
        }
    } catch (error) {
        simulationStarting = false;
        simulationStatus.textContent = error.message;
    }

    await checkSimulation();
});

setInterval(checkSimulation, 3000);
checkSimulation();
