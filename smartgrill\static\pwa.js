let smartGrillRegistration = null;

function pushElements() {
  return {
    message: document.getElementById("push-message"),
    enable: document.getElementById("enable-push"),
    disable: document.getElementById("disable-push"),
    test: document.getElementById("test-push"),
    installHint: document.getElementById("install-hint"),
  };
}

function showPushMessage(text, type = "") {
  const { message } = pushElements();
  if (!message) {
    return;
  }
  message.textContent = text;
  message.className = `form-message ${type}`.trim();
}

function urlBase64ToUint8Array(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((character) => character.charCodeAt(0)));
}

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

async function currentSubscription() {
  if (!smartGrillRegistration) {
    return null;
  }
  return smartGrillRegistration.pushManager.getSubscription();
}

async function updatePushControls() {
  const elements = pushElements();
  if (!elements.enable) {
    return;
  }

  const subscription = await currentSubscription();
  elements.enable.hidden = Boolean(subscription);
  elements.disable.hidden = !subscription;
  elements.test.disabled = !subscription;

  if (elements.installHint) {
    elements.installHint.hidden = isStandalone();
  }

  if (subscription) {
    showPushMessage("Pushmeldingen zijn op dit apparaat ingeschakeld.", "success");
  }
}

async function enablePush() {
  showPushMessage("Pushmeldingen inschakelen...");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Toestemming voor meldingen is niet gegeven.");
  }

  const response = await fetch("/api/push/public-key", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("De publieke pushsleutel kon niet worden geladen.");
  }
  const { public_key: publicKey } = await response.json();

  let subscription = await currentSubscription();
  if (!subscription) {
    subscription = await smartGrillRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey),
    });
  }

  const saveResponse = await fetch("/api/push/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(subscription),
  });
  if (!saveResponse.ok) {
    const data = await saveResponse.json().catch(() => ({}));
    throw new Error(data.detail || "Het pushabonnement kon niet worden opgeslagen.");
  }
  await updatePushControls();
}

async function disablePush() {
  const subscription = await currentSubscription();
  if (!subscription) {
    return;
  }

  await fetch("/api/push/subscribe", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint: subscription.endpoint }),
  });
  await subscription.unsubscribe();
  showPushMessage("Pushmeldingen zijn uitgeschakeld.");
  await updatePushControls();
}

async function testPush() {
  const subscription = await currentSubscription();
  if (!subscription) {
    throw new Error("Schakel pushmeldingen eerst in.");
  }
  showPushMessage("Testmelding versturen...");
  const response = await fetch("/api/push/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint: subscription.endpoint }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "De testmelding kon niet worden verstuurd.");
  }
  showPushMessage("Testmelding verstuurd.", "success");
}

async function initializePwa() {
  if (!("serviceWorker" in navigator)) {
    showPushMessage("Deze browser ondersteunt geen service workers.", "error");
    return;
  }

  smartGrillRegistration = await navigator.serviceWorker.register(
    "/service-worker.js",
    { scope: "/" },
  );

  const elements = pushElements();
  if (!elements.enable) {
    return;
  }

  if (!window.isSecureContext) {
    elements.enable.disabled = true;
    elements.test.disabled = true;
    showPushMessage(
      "Pushmeldingen vereisen een HTTPS-adres via je reverse proxy.",
      "error",
    );
    return;
  }
  if (!("PushManager" in window) || !("Notification" in window)) {
    elements.enable.disabled = true;
    elements.test.disabled = true;
    showPushMessage(
      "Installeer SmartGrill eerst op het beginscherm en open de webapp vanaf het pictogram.",
      "error",
    );
    return;
  }

  elements.enable.addEventListener("click", async () => {
    try {
      await enablePush();
    } catch (error) {
      console.error(error);
      showPushMessage(error.message, "error");
    }
  });
  elements.disable.addEventListener("click", async () => {
    try {
      await disablePush();
    } catch (error) {
      console.error(error);
      showPushMessage(error.message, "error");
    }
  });
  elements.test.addEventListener("click", async () => {
    try {
      await testPush();
    } catch (error) {
      console.error(error);
      showPushMessage(error.message, "error");
    }
  });

  await updatePushControls();
}

initializePwa().catch((error) => {
  console.error("PWA kon niet worden gestart", error);
  showPushMessage("De webapp kon niet volledig worden gestart.", "error");
});
