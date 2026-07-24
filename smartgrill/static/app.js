const temperatureKeys = ["kamado", "probe_1", "probe_2", "probe_3", "probe_4"];
const defaultProbeNames = ["Ambiance", "Probe 1", "Probe 2", "Probe 3", "Probe 4"];
const showTemperature = (value) =>
  value === null || value === undefined ? "--" : Number(value).toFixed(1);

async function loadProbeNames() {
  try {
    const response = await fetch("/api/settings", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const probeNames = data.probe_names || defaultProbeNames;
    temperatureKeys.forEach((key, index) => {
      document.getElementById(`label-${key}`).textContent =
        probeNames[index] || defaultProbeNames[index];
    });
  } catch (error) {
    console.error("Probe-namen konden niet worden geladen", error);
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

loadProbeNames();
refresh();
setInterval(refresh, 2000);
