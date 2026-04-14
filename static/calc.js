const calcButton = document.getElementById("calcButton");
const calcResult = document.getElementById("calcResult");

calcButton.addEventListener("click", async () => {
  const a = Number.parseFloat(document.getElementById("numA").value);
  const b = Number.parseFloat(document.getElementById("numB").value);
  const op = document.getElementById("operator").value;

  if (Number.isNaN(a) || Number.isNaN(b)) {
    calcResult.textContent = "Podaj dwie liczby.";
    return;
  }

  try {
    const response = await fetch(`/calc/${op}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ a, b }),
    });
    const data = await response.json();

    if (response.ok) {
      calcResult.textContent = `${data.operation} = ${data.result}`;
    } else {
      calcResult.textContent = data.detail || data.error || "Błąd";
    }
  } catch {
    calcResult.textContent = "Brak połączenia z serwerem.";
  }
});
