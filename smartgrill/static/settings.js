const form = document.getElementById("settings-form");
const message = document.getElementById("message");
const saveButton = document.getElementById("save-button");
const probeFields = document.getElementById("probe-fields");
const defaultProbeLabels = ["Ambiance", "Probe 1", "Probe 2", "Probe 3", "Probe 4"];
const sensorKeys = ["kamado", "probe_1", "probe_2", "probe_3", "probe_4"];
const alertsForm = document.getElementById("alerts-form");
const alertsMessage = document.getElementById("alerts-message");
const alertFields = document.getElementById("alert-fields");
const saveAlertsButton = document.getElementById("save-alerts-button");

function showMessage(text, type = "") {
  message.textContent = text;
  message.className = `form-message ${type}`.trim();
}

function createProbeFields(names) {
  probeFields.replaceChildren();

  defaultProbeLabels.forEach((labelText, index) => {
    const label = document.createElement("label");
    label.textContent = labelText;

    const input = document.createElement("input");
    input.type = "text";
    input.required = true;
    input.maxLength = 40;
    input.dataset.probeIndex = String(index);
    input.value = names[index] || labelText;

    label.appendChild(input);
    probeFields.appendChild(label);
  });
}

function showAlertsMessage(text, type = "") {
  alertsMessage.textContent = text;
  alertsMessage.className = `form-message ${type}`.trim();
}

function createAlertFields(data) {
  alertFields.replaceChildren();
  const probeNames = data.probe_names || defaultProbeLabels;

  sensorKeys.forEach((key, index) => {
    const config = data.sensors?.[key] || {};
    const row = document.createElement("div");
    row.className = "alert-row";
    row.dataset.sensorKey = key;

    const toggleLabel = document.createElement("label");
    toggleLabel.className = "alert-toggle";
    const toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.checked = Boolean(config.enabled);
    toggle.dataset.field = "enabled";
    const name = document.createElement("span");
    name.textContent = probeNames[index] || defaultProbeLabels[index];
    toggleLabel.append(toggle, name);

    const minimumLabel = document.createElement("label");
    minimumLabel.textContent = "Minimum °C";
    const minimum = document.createElement("input");
    minimum.type = "number";
    minimum.min = "-50";
    minimum.max = "400";
    minimum.step = "0.1";
    minimum.placeholder = "Niet ingesteld";
    minimum.value = config.minimum ?? "";
    minimum.dataset.field = "minimum";
    minimumLabel.appendChild(minimum);

    const maximumLabel = document.createElement("label");
    maximumLabel.textContent = "Maximum / doel °C";
    const maximum = document.createElement("input");
    maximum.type = "number";
    maximum.min = "-50";
    maximum.max = "400";
    maximum.step = "0.1";
    maximum.placeholder = "Niet ingesteld";
    maximum.value = config.maximum ?? "";
    maximum.dataset.field = "maximum";
    maximumLabel.appendChild(maximum);

    row.append(toggleLabel, minimumLabel, maximumLabel);
    alertFields.appendChild(row);
  });
}

async function loadSettings() {
  showMessage("Instellingen laden...");
  saveButton.disabled = true;

  try {
    const response = await fetch("/api/settings", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    document.getElementById("address").value = data.address || "";
    document.getElementById("reconnect-delay").value = data.reconnect_delay;
    document.getElementById("stale-after").value = data.stale_after;
    createProbeFields(data.probe_names || defaultProbeLabels);
    showMessage("");
  } catch (error) {
    console.error(error);
    createProbeFields(defaultProbeLabels);
    showMessage("De instellingen konden niet worden geladen.", "error");
  } finally {
    saveButton.disabled = false;
  }
}

async function loadAlerts() {
  showAlertsMessage("Alarmgrenzen laden...");
  saveAlertsButton.disabled = true;
  try {
    const response = await fetch("/api/alerts", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    createAlertFields(data);
    document.getElementById("battery-alert-enabled").checked = Boolean(
      data.battery?.enabled,
    );
    document.getElementById("battery-minimum").value =
      data.battery?.minimum ?? 15;
    document.getElementById("connection-lost").checked = Boolean(
      data.connection_lost,
    );
    document.getElementById("hysteresis").value = data.hysteresis ?? 1;
    showAlertsMessage("");
  } catch (error) {
    console.error(error);
    showAlertsMessage("De alarmgrenzen konden niet worden geladen.", "error");
  } finally {
    saveAlertsButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!form.reportValidity()) {
    return;
  }

  const probeNames = [...probeFields.querySelectorAll("input")]
    .sort((a, b) => Number(a.dataset.probeIndex) - Number(b.dataset.probeIndex))
    .map((input) => input.value.trim());

  const payload = {
    address: document.getElementById("address").value.trim(),
    reconnect_delay: Number(document.getElementById("reconnect-delay").value),
    stale_after: Number(document.getElementById("stale-after").value),
    probe_names: probeNames,
  };

  saveButton.disabled = true;
  showMessage("Instellingen opslaan...");

  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    const suffix = data.restart_required
      ? " Herstart SmartGrill om het nieuwe Bluetooth-adres te gebruiken."
      : "";
    showMessage(`Instellingen opgeslagen.${suffix}`, "success");
  } catch (error) {
    console.error(error);
    showMessage(error.message || "De instellingen konden niet worden opgeslagen.", "error");
  } finally {
    saveButton.disabled = false;
  }
});

alertsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!alertsForm.reportValidity()) {
    return;
  }

  const sensors = {};
  alertFields.querySelectorAll(".alert-row").forEach((row) => {
    const value = (field) => row.querySelector(`[data-field="${field}"]`);
    sensors[row.dataset.sensorKey] = {
      enabled: value("enabled").checked,
      minimum: value("minimum").value === ""
        ? null
        : Number(value("minimum").value),
      maximum: value("maximum").value === ""
        ? null
        : Number(value("maximum").value),
    };
  });

  const payload = {
    sensors,
    battery: {
      enabled: document.getElementById("battery-alert-enabled").checked,
      minimum: Number(document.getElementById("battery-minimum").value),
    },
    connection_lost: document.getElementById("connection-lost").checked,
    hysteresis: Number(document.getElementById("hysteresis").value),
  };

  saveAlertsButton.disabled = true;
  showAlertsMessage("Alarmgrenzen opslaan...");
  try {
    const response = await fetch("/api/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    createAlertFields(data);
    showAlertsMessage("Alarmgrenzen opgeslagen.", "success");
  } catch (error) {
    console.error(error);
    showAlertsMessage(
      error.message || "De alarmgrenzen konden niet worden opgeslagen.",
      "error",
    );
  } finally {
    saveAlertsButton.disabled = false;
  }
});

loadSettings();
loadAlerts();
