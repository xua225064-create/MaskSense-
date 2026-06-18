(function () {
  var DEFAULT_API_BASE_URL = "https://marksense-backend.onrender.com";
  var rawBase = window.MARKSENSE_API_BASE_URL || DEFAULT_API_BASE_URL;
  var apiBase = String(rawBase).trim().replace(/\/+$/, "");
  window.MARKSENSE_API_BASE_URL = apiBase;

  var backendPaths = [
    "/api/",
    "/contact/send",
    "/login",
    "/register",
    "/social-login",
    "/memorize",
    "/?admin_page_scan"
  ];

  var localUploadAssets = {
    "marksense-mark.svg": true,
    "favicon-marksense.png": true,
    "logo_marksense.png": true,
    "chatbot-avatar.png": true,
    "home-hero-poster.jpg": true,
    "home-hero.mp4": true,
    "marksense-logo.svg": true,
    "logo.png": true,
    "favicon.png": true
  };

  function shouldUseBackend(url) {
    if (!apiBase || typeof url !== "string") return false;
    if (!url || /^(data:|blob:|https?:\/\/|mailto:|tel:|#)/i.test(url)) return false;
    return backendPaths.some(function (path) {
      return url === path || url.indexOf(path) === 0;
    });
  }

  function uploadShouldUseBackend(url) {
    if (!apiBase || typeof url !== "string") return false;
    if (url.indexOf("/uploads/") !== 0) return false;
    var clean = url.split("?")[0].split("#")[0];
    var fileName = clean.substring(clean.lastIndexOf("/") + 1);
    return !localUploadAssets[fileName];
  }

  function toBackendUrl(url) {
    if (shouldUseBackend(url) || uploadShouldUseBackend(url)) {
      return apiBase + url;
    }
    return url;
  }

  var nativeFetch = window.fetch;
  if (nativeFetch) {
    window.fetch = function (input, init) {
      if (typeof input === "string") {
        return nativeFetch.call(this, toBackendUrl(input), init);
      }
      if (input && typeof input.url === "string") {
        var nextUrl = toBackendUrl(input.url);
        if (nextUrl !== input.url) {
          return nativeFetch.call(this, new Request(nextUrl, input), init);
        }
      }
      return nativeFetch.call(this, input, init);
    };
  }

  function rewriteUploadAttrs(root) {
    if (!apiBase || !root || !root.querySelectorAll) return;
    root.querySelectorAll("[src^='/uploads/'], [href^='/uploads/']").forEach(function (el) {
      ["src", "href"].forEach(function (attr) {
        var value = el.getAttribute(attr);
        if (uploadShouldUseBackend(value)) {
          el.setAttribute(attr, toBackendUrl(value));
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    rewriteUploadAttrs(document);
    if (!window.MutationObserver) return;
    new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (mutation.type === "attributes") {
          rewriteUploadAttrs(mutation.target.parentNode || document);
          return;
        }
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType === 1) rewriteUploadAttrs(node);
        });
      });
    }).observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["src", "href"]
    });
  });
})();
