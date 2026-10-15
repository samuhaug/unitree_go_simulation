const keys = new Set();
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

async function checkStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) throw new Error();

        connection.textContent = "Dashboard verbunden";
        connection.className = "status online";
        document.getElementById("server-status").textContent = "Online";
    } catch {
        connection.textContent = "Dashboard offline";
        connection.className = "status offline";
        document.getElementById("server-status").textContent = "Offline";
        stopRobot();
    }
}

setInterval(() => {
    if (activeDirection !== null) sendCommand();
}, 100);

setInterval(checkStatus, 2000);
checkStatus();
