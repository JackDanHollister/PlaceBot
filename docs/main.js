/* PlaceBot landing page — dynamic latest-release fetch + copy buttons.
 *
 * On load, asks the GitHub API for the latest release and updates:
 *   - the "Latest release" pill in the hero,
 *   - the release line in the installer card,
 *   - the Windows (.exe) and macOS (.dmg) download buttons.
 *
 * Everything degrades gracefully: the HTML ships with working fallback links
 * to .../releases/latest, so if the API call fails or is rate-limited the page
 * still works — we just leave the fallback links in place.
 */

(function () {
  "use strict";

  var REPO = "JackDanHollister/PlaceBot";
  var API = "https://api.github.com/repos/" + REPO + "/releases/latest";

  /* ---- copy-to-clipboard buttons ---- */
  document.querySelectorAll(".copy-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy") || "";
      navigator.clipboard.writeText(text).then(function () {
        var original = btn.textContent;
        btn.textContent = "Copied";
        btn.classList.add("copied");
        setTimeout(function () {
          btn.textContent = original;
          btn.classList.remove("copied");
        }, 1600);
      }).catch(function () {
        /* clipboard blocked (e.g. file://) — ignore silently */
      });
    });
  });

  /* ---- latest release ---- */
  function applyRelease(data) {
    if (!data || !data.tag_name) return;
    var tag = data.tag_name;

    var pill = document.getElementById("latest-version-pill");
    if (pill) pill.textContent = "Latest: " + tag;

    var line = document.getElementById("release-line");
    if (line) {
      line.textContent =
        "No Python setup required. Latest version: " + tag + ".";
    }

    var assets = data.assets || [];
    function findAsset(suffix) {
      for (var i = 0; i < assets.length; i++) {
        var name = (assets[i].name || "").toLowerCase();
        if (name.indexOf(suffix) === name.length - suffix.length &&
            assets[i].browser_download_url) {
          return assets[i].browser_download_url;
        }
      }
      return null;
    }

    var win = findAsset(".exe");
    var mac = findAsset(".dmg");

    var winBtn = document.getElementById("download-windows");
    if (winBtn && win) winBtn.href = win;

    var macBtn = document.getElementById("download-macos");
    if (macBtn && mac) macBtn.href = mac;
  }

  fetch(API, { headers: { Accept: "application/vnd.github+json" } })
    .then(function (resp) {
      if (!resp.ok) throw new Error("GitHub API " + resp.status);
      return resp.json();
    })
    .then(applyRelease)
    .catch(function () {
      /* keep the static fallback links already in the HTML */
    });
})();
