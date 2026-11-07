/*
 * Contact and appointment forms.
 * Both submit JSON to the Flask backend (see assets/js/config.js for API_BASE).
 */
(function () {
  "use strict";

  var cfg = window.CLINIC_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/$/, "");
  var FALLBACK_MSG = "We could not reach the booking system. Please call us on 0920 201 929 (Bole) or 0919 237 070 (Zenebework).";

  function request(method, path, body) {
    var ctrl = "AbortController" in window ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, cfg.REQUEST_TIMEOUT_MS || 15000) : null;
    return fetch(API + path, {
      method: method,
      headers: body ? { "Content-Type": "application/json", "Accept": "application/json" } : { "Accept": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl ? ctrl.signal : undefined
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        return { status: res.status, ok: res.ok, data: data };
      });
    }).finally(function () { if (timer) clearTimeout(timer); });
  }

  function formData(form) {
    var out = {};
    new FormData(form).forEach(function (v, k) { out[k] = typeof v === "string" ? v.trim() : v; });
    return out;
  }

  function clearErrors(form) {
    form.querySelectorAll(".field.invalid").forEach(function (f) { f.classList.remove("invalid"); });
  }

  function showErrors(form, errors) {
    var first = null;
    Object.keys(errors || {}).forEach(function (name) {
      var input = form.querySelector('[name="' + name + '"]') || form.querySelector('[data-field="' + name + '"]');
      if (!input) return;
      var field = input.closest(".field");
      if (!field) return;
      field.classList.add("invalid");
      var err = field.querySelector(".err");
      if (err) err.textContent = errors[name];
      if (!first) first = input;
    });
    if (first) { first.focus({ preventScroll: true }); first.scrollIntoView({ behavior: "smooth", block: "center" }); }
  }

  function alertBox(form, type, msg) {
    var box = form.querySelector(".alert");
    box.className = "alert alert-" + type + " show";
    box.textContent = msg;
    box.setAttribute("role", type === "error" ? "alert" : "status");
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function validate(form) {
    var errors = {};
    form.querySelectorAll("[required]").forEach(function (el) {
      if (el.type === "radio") {
        if (!form.querySelector('[name="' + el.name + '"]:checked')) errors[el.name] = "Please choose an option.";
      } else if (!el.value.trim()) {
        errors[el.name] = "This field is required.";
      }
    });
    if (form.querySelector('[data-field="time"]') && !form.querySelector('[name="time"]:checked')) {
      errors.time = "Please choose an appointment time.";
    }
    var email = form.querySelector('[name="email"]');
    if (email && email.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) errors.email = "Enter a valid email address.";
    var phone = form.querySelector('[name="phone"]');
    if (phone && phone.value && !/^\+?[0-9\s-]{9,15}$/.test(phone.value)) errors.phone = "Enter a valid phone number.";
    return errors;
  }

  function bindForm(form, path, onSuccess) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      clearErrors(form);
      var errors = validate(form);
      if (Object.keys(errors).length) { showErrors(form, errors); return; }

      var btn = form.querySelector('button[type="submit"]');
      var label = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Sending...';

      request("POST", path, formData(form)).then(function (res) {
        if (res.ok) {
          onSuccess(res.data);
          form.reset();
          form.dispatchEvent(new Event("reset-done"));
        } else if (res.data && res.data.errors) {
          showErrors(form, res.data.errors);
          alertBox(form, "error", res.data.message || "Please check the highlighted fields.");
        } else {
          alertBox(form, "error", (res.data && res.data.message) || FALLBACK_MSG);
        }
      }).catch(function () {
        alertBox(form, "error", FALLBACK_MSG);
      }).finally(function () {
        btn.disabled = false;
        btn.innerHTML = label;
      });
    });
  }

  // ---------- Contact form ----------
  var contact = document.getElementById("contact-form");
  if (contact) {
    bindForm(contact, "/api/contact", function () {
      alertBox(contact, "success", "Thank you. Your message has been sent and our team will get back to you soon.");
    });
  }

  // ---------- Appointment form ----------
  var appt = document.getElementById("appointment-form");
  if (!appt) return;

  var dateInput = appt.querySelector('[name="date"]');
  var doctorSelect = appt.querySelector('[name="doctor"]');
  var branchSelect = appt.querySelector('[name="branch"]');
  var slotBox = document.getElementById("slots");
  var DEFAULT_SLOTS = ["08:30","09:00","09:30","10:00","10:30","11:00","11:30","12:00","14:00","14:30","15:00","15:30","16:00","16:30"];

  // Earliest bookable day is today; latest is 90 days out.
  var today = new Date();
  var iso = function (d) { return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
  dateInput.min = iso(today);
  dateInput.max = iso(new Date(today.getTime() + 90 * 86400000));

  // Pre-select a service passed in the URL, e.g. appointment.html?service=cosmetic-dermatology
  var params = new URLSearchParams(location.search);
  ["service", "doctor"].forEach(function (k) {
    var v = params.get(k), sel = appt.querySelector('[name="' + k + '"]');
    if (v && sel && sel.querySelector('option[value="' + v + '"]')) sel.value = v;
  });

  function renderSlots(slots, message) {
    slotBox.innerHTML = "";
    if (message) {
      slotBox.innerHTML = '<p class="slots-empty">' + message + "</p>";
      return;
    }
    slots.forEach(function (s, i) {
      var id = "slot-" + i;
      var label = document.createElement("label");
      label.setAttribute("for", id);
      label.innerHTML = '<input type="radio" name="time" id="' + id + '" value="' + s.time + '"' +
        (i === 0 ? " required" : "") + (s.available ? "" : " disabled") + "><span>" + s.time + "</span>";
      if (!s.available) label.title = "Already booked";
      slotBox.appendChild(label);
    });
  }

  function loadSlots() {
    if (!dateInput.value) { renderSlots([], "Choose a date to see available times."); return; }
    renderSlots([], "Checking availability...");
    var q = "?date=" + encodeURIComponent(dateInput.value) +
      "&doctor=" + encodeURIComponent(doctorSelect.value || "") +
      "&branch=" + encodeURIComponent(branchSelect.value || "");
    request("GET", "/api/availability" + q).then(function (res) {
      if (!res.ok) throw new Error();
      if (res.data.closed) { renderSlots([], res.data.message || "The clinic is closed on this day. Please choose another date."); return; }
      if (!res.data.slots.some(function (s) { return s.available; })) { renderSlots([], "No times left on this day. Please choose another date."); return; }
      renderSlots(res.data.slots);
    }).catch(function () {
      // Backend unreachable: show the standard slots so the visitor can still fill in the form.
      renderSlots(DEFAULT_SLOTS.map(function (t) { return { time: t, available: true }; }));
    });
  }

  // Load doctors and services from the backend so the lists stay in sync with the admin settings.
  request("GET", "/api/meta").then(function (res) {
    if (!res.ok || !res.data.doctors) return;
    var fill = function (sel, items) {
      var current = sel.value;
      sel.querySelectorAll("option:not([value=''])").forEach(function (o) { o.remove(); });
      items.forEach(function (it) {
        var o = document.createElement("option"); o.value = it.slug; o.textContent = it.name; sel.appendChild(o);
      });
      if (current) sel.value = current;
    };
    fill(doctorSelect, res.data.doctors);
    fill(appt.querySelector('[name="service"]'), res.data.services);
    if (res.data.branches) fill(branchSelect, res.data.branches);
    ["service", "doctor"].forEach(function (k) {
      var v = params.get(k); if (v) appt.querySelector('[name="' + k + '"]').value = v;
    });
  }).catch(function () { /* keep the static options */ });

  [dateInput, doctorSelect, branchSelect].forEach(function (el) { el.addEventListener("change", loadSlots); });
  appt.addEventListener("reset-done", function () { renderSlots([], "Choose a date to see available times."); });
  renderSlots([], "Choose a date to see available times.");

  bindForm(appt, "/api/appointments", function (data) {
    var ref = data && data.reference ? " Your reference is " + data.reference + "." : "";
    alertBox(appt, "success", "Thank you. Your appointment request has been received." + ref +
      " We will call you to confirm.");
  });
})();
