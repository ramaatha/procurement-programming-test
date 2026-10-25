// filepath: static/js/ai-assistant.js
(() => {
  "use strict";
  const panel = document.getElementById("ai-assistant");
  const form = document.querySelector("form.document-form");
  if (!panel || !form) return;
  const get = (name) => panel.querySelector(`[data-ai-${name}]`);
  const text = panel.querySelector("#ai-text");
  const file = panel.querySelector("#ai-image");
  const reviewed = get("reviewed");
  const analyze = get("analyze");
  const apply = get("apply");
  let result = null,
    controller = null,
    generation = 0,
    previewURL = null;
  get("controls").hidden = false;
  const mode = () => panel.querySelector("input[name='ai-mode']:checked").value;
  const displayError = (message) => {
    get("error").textContent = message;
    get("error").hidden = !message;
    if (message) get("error").setAttribute("role", "alert");
    else get("error").removeAttribute("role");
  };
  const invalidate = () => {
    generation += 1;
    controller?.abort();
    controller = null;
    result = null;
    reviewed.checked = false;
    apply.disabled = true;
    analyze.disabled = false;
    get("result").hidden = true;
    get("empty").hidden = false;
    get("status").textContent = "";
    panel.removeAttribute("aria-busy");
    displayError("");
  };
  const sourceChanged = () => {
    invalidate();
    get("text-panel").hidden = mode() !== "text";
    get("image-panel").hidden = mode() !== "image";
  };
  panel
    .querySelectorAll("input[name='ai-mode']")
    .forEach((input) => input.addEventListener("change", sourceChanged));
  text.addEventListener("input", invalidate);
  file.addEventListener("change", () => {
    invalidate();
    if (previewURL) URL.revokeObjectURL(previewURL);
    previewURL = null;
    get("image-preview").hidden = true;
    get("preview-link").hidden = true;
    const selected = file.files[0];
    if (!selected) return;
    if (
      !["image/jpeg", "image/png"].includes(selected.type) ||
      selected.size > 2 * 1024 * 1024
    ) {
      displayError("Gunakan satu JPG/PNG maksimal 2 MB.");
      file.value = "";
      return;
    }
    previewURL = URL.createObjectURL(selected);
    get("image-preview").src = previewURL;
    get("image-preview").hidden = false;
    get("preview-link").href = previewURL;
    get("preview-link").hidden = false;
  });
  const addText = (parent, tag, value) => {
    const element = document.createElement(tag);
    element.textContent = value;
    parent.append(element);
    return element;
  };
  if (form.dataset.aiBound === "true")
    form.elements.namedItem("kind").dataset.userEdited = "true";
  const labels = {
    kind: "Jenis pengadaan",
    title: "Judul",
    reason: "Alasan kebutuhan",
    destination: "Tujuan penerimaan / layanan",
    needed_on: "Tanggal kebutuhan",
  };
  const price = (value) => {
    if (!value) return "Belum tersedia";
    const [whole, fraction = "00"] = value.split(".");
    return (
      "IDR " + whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + "," + fraction
    );
  };
  const render = (data) => {
    const values = get("values");
    values.replaceChildren();
    const list = document.createElement("dl");
    for (const key of Object.keys(labels)) {
      addText(list, "dt", labels[key]);
      let value = data[key];
      if (key === "kind") value = { GOODS: "Barang", SERVICES: "Jasa" }[value];
      addText(list, "dd", value || "Belum tersedia");
    }
    values.append(list);
    for (const [index, item] of data.items.entries()) {
      const row = addText(values, "section", "");
      row.className = "ai-result-item";
      addText(
        row,
        "h3",
        `Item ${index + 1}: ${item.name || "Nama belum tersedia"}`,
      );
      addText(
        row,
        "p",
        `Jumlah: ${item.quantity || "belum tersedia"} · Satuan: ${item.unit || "belum tersedia"}`,
      );
      addText(row, "p", `Harga per unit: ${price(item.unit_price)}`);
    }
    get("warnings").replaceChildren();
    for (const warning of data.warnings)
      addText(get("warnings"), "li", warning);
    get("empty").hidden = true;
    get("result").hidden = false;
  };
  analyze.addEventListener("click", async () => {
    invalidate();
    if (mode() === "text" && !text.value.trim())
      return displayError("Tulis kebutuhan terlebih dahulu.");
    if (mode() === "image" && !file.files[0])
      return displayError("Pilih gambar kebutuhan terlebih dahulu.");
    const current = generation;
    const aborter = new AbortController();
    controller = aborter;
    analyze.disabled = true;
    panel.setAttribute("aria-busy", "true");
    get("status").textContent =
      "Sedang membaca kebutuhan. Form manual tetap dapat diisi.";
    const body = new FormData();
    body.set("mode", mode());
    if (mode() === "text") body.set("text", text.value);
    else body.set("image", file.files[0]);
    const timer = window.setTimeout(() => aborter.abort(), 25000);
    try {
      const response = await fetch(panel.dataset.endpoint, {
        method: "POST",
        body,
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        signal: aborter.signal,
      });
      if (current !== generation) return;
      if (response.redirected)
        throw new Error(
          "Sesi berakhir. Simpan isian penting, lalu masuk kembali.",
        );
      const data = await response.json();
      if (current !== generation) return;
      if (!response.ok)
        throw new Error(
          data.error || "Bantuan AI belum tersedia. Silakan lanjutkan manual.",
        );
      if (
        !data.suggestion ||
        !Array.isArray(data.suggestion.items) ||
        data.suggestion.items.length > 10
      )
        throw new Error("Hasil AI tidak dapat dibaca. Lanjutkan manual.");
      result = data.suggestion;
      render(result);
      get("status").textContent =
        "Analisis selesai. Periksa hasil sebelum menerapkan ke form.";
    } catch (error) {
      if (current !== generation) return;
      displayError(
        error.name === "AbortError"
          ? "Analisis dihentikan karena terlalu lama. Anda dapat lanjutkan manual."
          : error.message,
      );
      get("status").textContent = "";
    } finally {
      window.clearTimeout(timer);
      if (current === generation) {
        analyze.disabled = false;
        panel.removeAttribute("aria-busy");
        controller = null;
      }
    }
  });
  reviewed.addEventListener("change", () => {
    apply.disabled = !result || !reviewed.checked;
  });
  apply.addEventListener("click", () => {
    if (!result || !reviewed.checked) return;
    const data = result;
    const total = form.querySelector("[name=items-TOTAL_FORMS]");
    const max = Number(form.querySelector("[name=items-MAX_NUM_FORMS]").value);
    const sets = [...form.querySelectorAll(":scope > fieldset")];
    const fields = ["name", "unit", "quantity", "unit_price"];
    const blank = sets.filter(
      (set) =>
        !set.querySelector("[name$='-DELETE']")?.checked &&
        fields.every(
          (key) => !set.querySelector(`[name$='-${key}']`).value.trim(),
        ),
    );
    const newCount = Math.max(0, data.items.length - blank.length);
    if (Number(total.value) + newCount > max)
      return displayError(
        "Batas item form tercapai. Kurangi item sebelum menerapkan hasil.",
      );
    for (const key of Object.keys(labels)) {
      const field = form.elements.namedItem(key);
      if (field && !field.value.trim() && data[key]) field.value = data[key];
    }
    // The initial kind is a default, not proof the user selected Goods.
    const kind = form.elements.namedItem("kind");
    if (!kind.dataset.userEdited && data.kind) kind.value = data.kind;
    for (const item of data.items) {
      let row = blank.shift();
      if (!row) {
        const index = Number(total.value);
        const fragment = document
          .getElementById("ai-item-template")
          .content.cloneNode(true);
        row = fragment.querySelector("fieldset");
        for (const element of row.querySelectorAll(
          "[name], [id], [for], [aria-describedby]",
        )) {
          for (const attribute of ["name", "id", "for", "aria-describedby"]) {
            if (element.hasAttribute(attribute))
              element.setAttribute(
                attribute,
                element
                  .getAttribute(attribute)
                  .replaceAll("__prefix__", String(index)),
              );
          }
        }
        row.querySelector("legend").textContent = `Item ${index + 1}`;
        form.querySelector(".form-actions").before(fragment);
        total.value = String(index + 1);
      }
      for (const key of fields)
        row.querySelector(`[name$='-${key}']`).value = item[key] || "";
    }
    invalidate();
    panel.open = false;
    const notice = document.createElement("p");
    notice.className = "ai-applied-notice";
    notice.setAttribute("role", "status");
    notice.textContent =
      "Usulan AI diterapkan ke kolom kosong. Lengkapi dan periksa form, lalu Simpan Draf.";
    form.querySelector(".ai-applied-notice")?.remove();
    form.prepend(notice);
    form.querySelector("[name=title]").focus();
  });
  form.elements.namedItem("kind").addEventListener("change", (event) => {
    event.target.dataset.userEdited = "true";
  });
  get("cancel").addEventListener("click", () => {
    invalidate();
    panel.open = false;
    panel.querySelector("summary").focus();
  });
  panel.addEventListener("toggle", () => {
    if (!panel.open) invalidate();
  });
  get("example").addEventListener("click", () => {
    invalidate();
    panel.querySelector("[name='ai-mode'][value=text]").checked = true;
    sourceChanged();
    text.value =
      "Butuh pemeriksaan jaringan 1 paket, estimasi Rp250.000 per paket, untuk Kantor Demo.";
    text.focus();
  });
  window.addEventListener("pagehide", () => {
    invalidate();
    if (previewURL) URL.revokeObjectURL(previewURL);
  });
})();
