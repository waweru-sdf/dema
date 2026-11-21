/*
 * Turns article text into safe page elements. Used by the article page and by the
 * admin editor's preview, so what staff preview is exactly what visitors see.
 *
 * Writing guide (also shown in the admin editor):
 *   ## Heading            ### Smaller heading            ---  (divider line)
 *   **bold**   *italic*   [link text](https://example.com)
 *   - bullet item         1. numbered item               > quote
 *   ![Caption text](/media/12)          picture with caption (leave [] empty for none)
 *   @[youtube](https://www.youtube.com/watch?v=VIDEOID)   embedded video
 *
 * Nothing is ever inserted as HTML: every piece is built with textContent, so an
 * article cannot run code. Only http(s), mailto, tel, "/" and "#" links are allowed.
 */
(function () {
  "use strict";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function safeUrl(u, allowMail) {
    u = (u || "").trim();
    if (/^(https?:\/\/|\/(?!\/)|#)/i.test(u)) return u;
    if (allowMail && /^(mailto:|tel:)/i.test(u)) return u;
    return "";
  }

  // **bold**, *italic*, [text](url)
  var INLINE = /\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)\s]+)\)/g;
  function inline(parent, text, api) {
    var last = 0, m;
    INLINE.lastIndex = 0;
    while ((m = INLINE.exec(text))) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      if (m[1] !== undefined) parent.appendChild(el("strong", "", m[1]));
      else if (m[2] !== undefined) parent.appendChild(el("em", "", m[2]));
      else {
        var href = safeUrl(m[4], true);
        if (href) {
          var a = el("a", "", m[3]);
          a.href = href;
          if (/^https?:/i.test(href)) { a.target = "_blank"; a.rel = "noopener"; }
          parent.appendChild(a);
        } else parent.appendChild(document.createTextNode(m[3]));
      }
      last = INLINE.lastIndex;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
  }
  function lines(parent, arr) {
    arr.forEach(function (line, i) {
      if (i) parent.appendChild(document.createElement("br"));
      inline(parent, line);
    });
  }

  function mediaSrc(src, api) { return src.charAt(0) === "/" && api ? api + src : src; }

  window.renderBlogBody = function (text, box, api) {
    api = (api || "").replace(/\/$/, "");
    box.textContent = "";
    var blocks = String(text || "").replace(/\r\n?/g, "\n").split(/\n{2,}/);
    blocks.forEach(function (raw) {
      var block = raw.replace(/^\n+|\s+$/g, "");
      if (!block) return;
      var rows = block.split("\n");
      var first = rows[0].trim();
      var m;

      if (/^---+$/.test(first) && rows.length === 1) { box.appendChild(el("hr")); return; }
      if ((m = /^(#{2,3}) (.+)$/.exec(first)) && rows.length === 1) {
        var h = el(m[1].length === 2 ? "h2" : "h3");
        inline(h, m[2]);
        box.appendChild(h);
        return;
      }
      if ((m = /^!\[([^\]]*)\]\(([^)\s]+)\)$/.exec(first)) && rows.length === 1) {
        var src = safeUrl(m[2], false);
        if (src) {
          var fig = el("figure", "article-figure");
          var img = el("img");
          img.src = mediaSrc(src, api);
          img.alt = m[1];
          img.loading = "lazy";
          fig.appendChild(img);
          if (m[1]) fig.appendChild(el("figcaption", "", m[1]));
          box.appendChild(fig);
        }
        return;
      }
      if ((m = /^@\[youtube\]\(([^)]+)\)$/.exec(first)) && rows.length === 1) {
        var id = /(?:v=|youtu\.be\/|embed\/|^)([A-Za-z0-9_-]{11})(?:[?&#]|$)/.exec(m[1].trim());
        if (id) {
          var wrap = el("div", "article-video");
          var f = el("iframe");
          f.src = "https://www.youtube-nocookie.com/embed/" + id[1];
          f.title = "Video";
          f.loading = "lazy";
          f.allowFullscreen = true;
          f.setAttribute("allow", "accelerometer; encrypted-media; gyroscope; picture-in-picture");
          f.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
          wrap.appendChild(f);
          box.appendChild(wrap);
        }
        return;
      }
      if (rows.every(function (r) { return /^[-*] /.test(r.trim()); })) {
        var ul = el("ul");
        rows.forEach(function (r) { var li = el("li"); inline(li, r.trim().slice(2)); ul.appendChild(li); });
        box.appendChild(ul);
        return;
      }
      if (rows.every(function (r) { return /^\d+[.)] /.test(r.trim()); })) {
        var ol = el("ol");
        rows.forEach(function (r) { var li = el("li"); inline(li, r.trim().replace(/^\d+[.)] /, "")); ol.appendChild(li); });
        box.appendChild(ol);
        return;
      }
      if (rows.every(function (r) { return /^>/.test(r.trim()); })) {
        var q = el("blockquote");
        lines(q, rows.map(function (r) { return r.trim().replace(/^>\s?/, ""); }));
        box.appendChild(q);
        return;
      }
      var p = el("p");
      lines(p, rows);
      box.appendChild(p);
    });
  };
})();
