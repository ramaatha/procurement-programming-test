// filepath: static/js/forms.js
(() => {
  document.documentElement.classList.add("js-enabled");
  const menu = document.querySelector(".sidebar details");
  const wide = window.matchMedia("(min-width: 64rem)");
  if (menu) {
    const setMenu = () => {
      menu.open = wide.matches;
    };
    setMenu();
    wide.addEventListener("change", setMenu);
    menu.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !wide.matches) {
        menu.open = false;
        menu.querySelector("summary").focus();
      }
    });
  }
  const passwordControls = [];
  document
    .querySelectorAll('input[type="password"]')
    .forEach((input, index) => {
      if (!input.id) input.id = `password-visibility-${index}`;
      const fieldName =
        input.labels?.[0]?.textContent.trim().replace(/:$/, "") || "password";
      const wrapper = document.createElement("span");
      wrapper.className = "password-control";
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "secondary password-toggle";
      toggle.setAttribute("aria-controls", input.id);
      toggle.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/><path class="eye-slash" d="m3 3 18 18"/></svg>';
      const setVisible = (visible) => {
        input.type = visible ? "text" : "password";
        toggle.dataset.visible = String(visible);
        const label = `${visible ? "Sembunyikan" : "Tampilkan"} ${fieldName}`;
        toggle.setAttribute("aria-label", label);
        toggle.title = label;
      };
      input.before(wrapper);
      wrapper.append(input, toggle);
      setVisible(false);
      toggle.addEventListener("click", () =>
        setVisible(input.type === "password"),
      );
      passwordControls.push({ input, hide: () => setVisible(false) });
    });
  const logoutDialog = document.getElementById("logout-dialog");
  if (logoutDialog && typeof logoutDialog.showModal === "function") {
    let opener;
    document.querySelectorAll("[data-logout-confirm]").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        opener = link;
        logoutDialog.showModal();
        logoutDialog.querySelector("[data-dialog-close]").focus();
      });
    });
    logoutDialog
      .querySelector("[data-dialog-close]")
      .addEventListener("click", () => logoutDialog.close());
    logoutDialog.addEventListener("close", () => opener?.focus());
  }
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (
      !(form instanceof HTMLFormElement) ||
      form.method.toLowerCase() !== "post"
    )
      return;
    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }
    for (const control of passwordControls) {
      if (control.input.form === form) control.hide();
    }
    form.dataset.submitting = "true";
    form.setAttribute("aria-busy", "true");
    const feedback = document.createElement("p");
    feedback.className = "submit-status";
    feedback.setAttribute("role", "status");
    feedback.textContent = "Permintaan sedang diproses...";
    form.append(feedback);
    // Keep the submitter name/value in POST; disabling it would lose the intent.
    for (const button of form.querySelectorAll('button[type="submit"]'))
      button.setAttribute("aria-disabled", "true");
  });
  window.addEventListener("pageshow", () => {
    for (const control of passwordControls) control.hide();
    for (const form of document.querySelectorAll("form[data-submitting]")) {
      delete form.dataset.submitting;
      form.removeAttribute("aria-busy");
      form.querySelector(".submit-status")?.remove();
      for (const button of form.querySelectorAll("[aria-disabled]"))
        button.removeAttribute("aria-disabled");
    }
  });
})();
