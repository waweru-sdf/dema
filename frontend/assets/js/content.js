/*
 * Editable content: doctors and gallery come from the backend (/api/site), so staff can
 * change them in /admin. The HTML already contains the original doctors and photos, so the
 * page still works if the API is slow or offline; this script only swaps in the live list.
 */
(function () {
  "use strict";

  var cfg = window.CLINIC_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/$/, "");
  var doctorBoxes = document.querySelectorAll(".doctors-grid");
  var galleryBoxes = document.querySelectorAll(".gallery");
  if (!doctorBoxes.length && !galleryBoxes.length) return;

  function src(url) { return url.charAt(0) === "/" ? API + url : url; }
  function esc(text) {
    return String(text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  fetch(API + "/api/site", { headers: { Accept: "application/json" } })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (data) {
      if (data.doctors && data.doctors.length) {
        var html = data.doctors.map(function (d) {
          return '<article class="card doctor in">' +
            '<img src="' + esc(src(d.photo)) + '" alt="Portrait of ' + esc(d.name) + '" loading="lazy" width="800" height="1000">' +
            '<div class="card-body"><h3>' + esc(d.name) + '</h3><span>' + esc(d.role) + '</span></div></article>';
        }).join("");
        doctorBoxes.forEach(function (box) { box.innerHTML = html; });
      }
      if (data.gallery && data.gallery.length) {
        var pics = data.gallery.map(function (g, i) {
          return '<button type="button" data-lightbox="' + esc(src(g.url)) + '" aria-label="Open image ' + (i + 1) + '">' +
            '<img src="' + esc(src(g.url)) + '" alt="' + esc(g.caption) + '" loading="lazy"></button>';
        }).join("");
        galleryBoxes.forEach(function (box) { box.innerHTML = pics; });
      }
    })
    .catch(function () { /* keep the built-in markup */ });
})();
