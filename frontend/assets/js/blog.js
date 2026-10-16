/*
 * Blog: articles are written in /admin and loaded from the API.
 *   - index.html : latest 3 posts (the whole section stays hidden until there is one)
 *   - blog.html  : all posts with a filter by type
 *   - post.html  : one article, served at /blog/<slug>
 * Article text is built by blog-render.js with textContent, never as HTML, so an article cannot inject code.
 */
(function () {
  "use strict";

  var cfg = window.CLINIC_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/$/, "");
  var home = document.getElementById("home-blog");
  var list = document.getElementById("blog-list");
  var article = document.getElementById("post-body");
  if (!home && !list && !article) return;

  function api(path) {
    return fetch(API + path, { headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); });
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function pretty(iso) {
    if (!iso) return "";
    var d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }

  function meta(p) {
    return [pretty(p.published_at), p.read_minutes ? p.read_minutes + " min read" : ""].filter(Boolean).join("  \u00b7  ");
  }

  function card(p) {
    var a = el("article", "card in");
    var href = "/blog/" + encodeURIComponent(p.slug);
    if (p.cover) {
      var img = el("img", "card-img");
      img.src = p.cover.charAt(0) === "/" ? API + p.cover : p.cover;
      img.alt = "";
      img.loading = "lazy";
      a.appendChild(img);
    } else {
      var ph = el("div", "card-noimg");
      ph.innerHTML = '<i class="bi bi-journal-text" aria-hidden="true"></i>';
      a.appendChild(ph);
    }
    var body = el("div", "card-body");
    body.appendChild(el("span", "tag", p.category));
    body.appendChild(el("div", "card-meta", meta(p)));
    var h = el("h3");
    var link = el("a", "", p.title);
    link.href = href;
    h.appendChild(link);
    body.appendChild(h);
    body.appendChild(el("p", "", p.excerpt));
    var more = el("a", "more", "Read article ");
    more.href = href;
    more.innerHTML += '<i class="bi bi-arrow-right"></i>';
    body.appendChild(more);
    a.appendChild(body);
    return a;
  }

  function fill(grid, posts) {
    grid.textContent = "";
    posts.forEach(function (p) { grid.appendChild(card(p)); });
  }

  if (home) {
    api("/api/posts?limit=3").then(function (d) {
      if (!d.posts.length) return;
      fill(home.querySelector("[data-blog-grid]"), d.posts);
      home.hidden = false;
    }).catch(function () { /* no posts or API down: leave the section hidden */ });
  }

  if (list) {
    var chips = document.getElementById("blog-chips");
    var empty = document.getElementById("blog-empty");
    var search = document.getElementById("blog-search");
    var current = "", all = [];
    var show = function () {
      var q = search ? search.value.trim().toLowerCase() : "";
      var posts = all.filter(function (p) {
        return !q || (p.title + " " + p.excerpt + " " + p.category).toLowerCase().indexOf(q) !== -1;
      });
      fill(list, posts);
      empty.hidden = posts.length > 0;
      empty.textContent = all.length ? "No articles match your search." : "No articles yet. Please check back soon.";
    };
    var load = function () {
      api("/api/posts" + (current ? "?category=" + encodeURIComponent(current) : "")).then(function (d) {
        all = d.posts;
        show();
        if (!chips.children.length && d.categories.length > 1) {
          ["All"].concat(d.categories).forEach(function (c) {
            var b = el("button", "chip" + (c === "All" ? " active" : ""), c);
            b.type = "button";
            b.addEventListener("click", function () {
              current = c === "All" ? "" : c;
              chips.querySelectorAll(".chip").forEach(function (x) { x.classList.toggle("active", x === b); });
              load();
            });
            chips.appendChild(b);
          });
        }
      }).catch(function () { empty.hidden = false; });
    };
    if (search) search.addEventListener("input", show);
    load();
  }

  if (article) {
    var slug = decodeURIComponent(location.pathname.replace(/\/$/, "").split("/").pop());
    api("/api/posts/" + encodeURIComponent(slug)).then(function (d) {
      var p = d.post;
      document.title = p.title + " | Dr. Feysel Dermatology Specialty Clinic";
      document.getElementById("post-title").textContent = p.title;
      document.getElementById("post-crumb").textContent = p.category;
      var meta = document.getElementById("post-meta");
      meta.appendChild(el("span", "tag", p.category));
      meta.appendChild(el("span", "", pretty(p.published_at)));
      if (p.cover) {
        var c = document.getElementById("post-cover");
        c.src = p.cover.charAt(0) === "/" ? API + p.cover : p.cover;
        c.alt = p.title;
        c.hidden = false;
      }
      if (window.renderBlogBody) window.renderBlogBody(p.body, article, API);
      if (p.read_minutes) meta.appendChild(el("span", "", p.read_minutes + " min read"));
      var related = document.getElementById("post-related");
      if (related) {
        api("/api/posts?limit=4").then(function (d) {
          var others = d.posts.filter(function (x) { return x.slug !== p.slug; }).slice(0, 3);
          if (!others.length) return;
          fill(related.querySelector("[data-blog-grid]"), others);
          related.hidden = false;
        }).catch(function () {});
      }
    }).catch(function () {
      document.title = "Article not found | Dr. Feysel Dermatology Specialty Clinic";
      document.getElementById("post-title").textContent = "Article not found";
      article.appendChild(el("p", "", "Sorry, we could not find that article. It may have been removed."));
    });
  }
})();
