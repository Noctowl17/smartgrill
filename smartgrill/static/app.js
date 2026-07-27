const temperatureKeys = ["kamado", "probe_1", "probe_2", "probe_3", "probe_4"];
const defaultProbeNames = ["Ambiance", "Probe 1", "Probe 2", "Probe 3", "Probe 4"];
const alarmStatus = document.getElementById("alarm-save-status");
const alarmCards = [...document.querySelectorAll("[data-sensor-key]")];

let alertsState = null;
let alarmSaveTimer = null;
let alarmRevision = 0;

const showTemperature = (value) =>
  value === null || value === undefined ? "--" : Number(value).toFixed(1);

function showAlarmStatus(text, type = "") {
  alarmStatus.textContent = text;
  alarmStatus.className = `dashboard-status ${type}`.trim();
}

function field(card, name) {
  return card.querySelector(`[data-alarm-field="${name}"]`);
}

function optionalNumber(input) {
  return input.value === "" ? null : Number(input.value);
}

function updateCardAlarmState(card) {
  const enabled = field(card, "enabled").checked;
  card.classList.toggle("alarm-enabled", enabled);
}

function populateAlarmCards(data) {
  alertsState = data;

  alarmCards.forEach((card) => {
    const config = data.sensors?.[card.dataset.sensorKey] || {};
    field(card, "enabled").checked = Boolean(config.enabled);
    field(card, "minimum").value = config.minimum ?? "";
    field(card, "maximum").value = config.maximum ?? "";
    updateCardAlarmState(card);
  });
}

function readSensorConfig(card) {
  const minimumInput = field(card, "minimum");
  const maximumInput = field(card, "maximum");
  const minimum = optionalNumber(minimumInput);
  const maximum = optionalNumber(maximumInput);

  minimumInput.setCustomValidity("");
  maximumInput.setCustomValidity("");
  card.classList.remove("alarm-invalid");

  if (minimum !== null && maximum !== null && minimum >= maximum) {
    const message = "De minimumtemperatuur moet lager zijn dan de maximumtemperatuur.";
    maximumInput.setCustomValidity(message);
    card.classList.add("alarm-invalid");
    showAlarmStatus(message, "error");
    return null;
  }

  return {
    enabled: field(card, "enabled").checked,
    minimum,
    maximum,
  };
}

function queueAlarmSave(card) {
  if (!alertsState) {
    return;
  }

  const sensor = readSensorConfig(card);
  updateCardAlarmState(card);
  if (!sensor) {
    return;
  }

  alertsState.sensors[card.dataset.sensorKey] = sensor;
  alarmRevision += 1;
  const queuedRevision = alarmRevision;

  window.clearTimeout(alarmSaveTimer);
  showAlarmStatus("Alarmgrenzen opslaan...");
  alarmSaveTimer = window.setTimeout(() => saveAlerts(queuedRevision), 450);
}

async function saveAlerts(revision) {
  const payload = {
    sensors: alertsState.sensors,
    battery: alertsState.battery,
    connection_lost: alertsState.connection_lost,
    alarm_interval_minutes: alertsState.alarm_interval_minutes,
  };

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

    if (revision === alarmRevision) {
      alertsState = data;
      showAlarmStatus("Alarmgrenzen opgeslagen.", "success");
    }
  } catch (error) {
    console.error("Alarmgrenzen konden niet worden opgeslagen", error);
    showAlarmStatus(
      error.message || "De alarmgrenzen konden niet worden opgeslagen.",
      "error",
    );
  }
}

async function loadDashboardConfiguration() {
  try {
    const [settingsResponse, alertsResponse] = await Promise.all([
      fetch("/api/settings", { cache: "no-store" }),
      fetch("/api/alerts", { cache: "no-store" }),
    ]);
    if (!settingsResponse.ok || !alertsResponse.ok) {
      throw new Error("Dashboardconfiguratie kon niet worden geladen");
    }

    const [settings, alerts] = await Promise.all([
      settingsResponse.json(),
      alertsResponse.json(),
    ]);
    const probeNames = settings.probe_names || defaultProbeNames;

    temperatureKeys.forEach((key, index) => {
      const name = probeNames[index] || defaultProbeNames[index];
      document.getElementById(`label-${key}`).textContent = name;

      const card = document.querySelector(`[data-sensor-key="${key}"]`);
      field(card, "enabled").setAttribute(
        "aria-label",
        `Alarm voor ${name} inschakelen`,
      );
      field(card, "minimum").setAttribute(
        "aria-label",
        `Minimumtemperatuur ${name}`,
      );
      field(card, "maximum").setAttribute(
        "aria-label",
        `Maximumtemperatuur ${name}`,
      );
    });

    populateAlarmCards(alerts);
  } catch (error) {
    console.error("Dashboardconfiguratie kon niet worden geladen", error);
    showAlarmStatus("Alarmgrenzen konden niet worden geladen.", "error");
  }
}

async function refresh() {
  const connection = document.querySelector(".connection");

  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    document.getElementById("connection").textContent = data.connected
      ? "Verbonden"
      : "Niet verbonden";
    connection.classList.toggle("online", data.connected);
    document.getElementById("battery").textContent =
      data.battery === null ? "--" : `${data.battery}%`;

    temperatureKeys.forEach((key) => {
      document.getElementById(key).textContent = showTemperature(
        data.temperatures[key],
      );
    });

    document.getElementById("updated").textContent = data.last_update
      ? new Date(data.last_update).toLocaleTimeString("nl-NL")
      : "--";
  } catch (error) {
    console.error("Status kon niet worden geladen", error);
    connection.classList.remove("online");
    document.getElementById("connection").textContent = "Webserverfout";
  }
}

alarmCards.forEach((card) => {
  card.querySelectorAll("[data-alarm-field]").forEach((control) => {
    control.addEventListener("change", () => queueAlarmSave(card));
  });
});

loadDashboardConfiguration();
refresh();
setInterval(refresh, 2000);
