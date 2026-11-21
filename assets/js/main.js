/* Site-wide behaviour: mobile nav, active link, reveal on scroll, lightbox, back-to-top. */
(function () {
  "use strict";

  // Mobile navigation
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      document.body.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.querySelector("i").className = open ? "bi bi-x-lg" : "bi bi-list";
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a") && nav.classList.contains("open")) toggle.click();
    });
  }

  // Highlight the current page in the nav
  var page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav a.nav-link").forEach(function (a) {
    var href = a.getAttribute("href");
    var group = a.getAttribute("data-group") || "";
    if (href === page || group.split(" ").indexOf(page) !== -1) a.classList.add("active");
  });

  // Reveal on scroll
  var items = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add("in"); });
  }

  // Gallery lightbox
  var lb = document.querySelector(".lightbox");
  if (lb) {
    var lbImg = lb.querySelector("img");
    var close = function () { lb.classList.remove("open"); lbImg.src = ""; };
    document.querySelectorAll("[data-lightbox]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        lbImg.src = btn.getAttribute("data-lightbox");
        lbImg.alt = btn.querySelector("img").alt;
        lb.classList.add("open");
        lb.querySelector("button").focus();
      });
    });
    lb.addEventListener("click", function (e) { if (e.target === lb || e.target.closest("button")) close(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  // Back to top
  var top = document.querySelector(".back-to-top");
  if (top) {
    window.addEventListener("scroll", function () { top.classList.toggle("show", window.scrollY > 500); }, { passive: true });
    top.addEventListener("click", function () { window.scrollTo({ top: 0 }); });
  }

  // Footer year
  document.querySelectorAll("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });
})();
