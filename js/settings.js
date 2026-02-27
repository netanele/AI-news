/* Settings page — reads/writes localStorage preferences */

(function () {
  "use strict";

  function init() {
    // Theme
    var saved = localStorage.getItem("theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
    var themeSelect = document.getElementById("theme-select");
    if (themeSelect) {
      themeSelect.value = saved;
      themeSelect.addEventListener("change", function () {
        var theme = themeSelect.value;
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
      });
    }

    // Days filter
    var daysInput = document.getElementById("days-filter");
    if (daysInput) {
      var savedDays = localStorage.getItem("daysFilter");
      if (savedDays) {
        daysInput.value = savedDays;
      }
      daysInput.addEventListener("change", function () {
        var val = parseInt(daysInput.value, 10);
        if (val > 0) {
          localStorage.setItem("daysFilter", val);
        }
      });
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
