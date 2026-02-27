/* AI News Dashboard — main application script */

(function () {
  "use strict";

  // --- Theme ---

  function initTheme() {
    var saved = localStorage.getItem("theme") || "dark";
    applyTheme(saved);

    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var current = document.documentElement.getAttribute("data-theme");
        var next = current === "dark" ? "light" : "dark";
        applyTheme(next);
        localStorage.setItem("theme", next);
      });
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var icon = document.querySelector(".theme-icon");
    if (icon) {
      icon.textContent = theme === "dark" ? "\u263E" : "\u2600";
    }
  }

  // --- Data loading ---

  async function loadData() {
    var dashboard = document.getElementById("dashboard");
    try {
      var response = await fetch("data.json");
      if (!response.ok) throw new Error("HTTP " + response.status);
      var data = await response.json();
      renderDashboard(data);
    } catch (e) {
      dashboard.innerHTML =
        '<div class="fallback-message">Data unavailable \u2014 check back later.</div>';
    }
  }

  // --- Rendering ---

  function renderDashboard(data) {
    var dashboard = document.getElementById("dashboard");
    dashboard.innerHTML = "";

    // Last updated
    var updatedEl = document.getElementById("last-updated");
    if (updatedEl && data.lastUpdated) {
      updatedEl.textContent = "Updated " + formatRelativeTime(data.lastUpdated);
    }

    if (!data.days || data.days.length === 0) {
      dashboard.innerHTML =
        '<div class="fallback-message">No videos found in the last ' +
        (data.config ? data.config.daysToShow : 7) +
        " days.</div>";
      return;
    }

    // Apply daysFilter from localStorage
    var daysFilter = parseInt(localStorage.getItem("daysFilter"), 10);
    var days = data.days;
    if (daysFilter && daysFilter > 0 && daysFilter < days.length) {
      days = days.slice(0, daysFilter);
    }

    var todayStr = new Date().toISOString().slice(0, 10);

    days.forEach(function (day) {
      var section = document.createElement("details");
      section.className = "day-section";
      if (day.date === todayStr) {
        section.setAttribute("open", "");
      }

      var summary = document.createElement("summary");
      summary.className = "day-heading";
      summary.textContent = formatDateHeading(day.date);
      section.appendChild(summary);

      if (day.dailyDigest) {
        var digest = document.createElement("p");
        digest.className = "daily-digest";
        digest.textContent = day.dailyDigest;
        section.appendChild(digest);
      }

      day.channels.forEach(function (channel) {
        section.appendChild(renderChannel(channel));
      });

      dashboard.appendChild(section);
    });
  }

  function renderChannel(channel) {
    var container = document.createElement("div");
    container.className = "channel-group";

    var header = document.createElement("h3");
    header.className = "channel-name";
    if (channel.channelUrl) {
      var link = document.createElement("a");
      link.href = channel.channelUrl;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = channel.channelName;
      header.appendChild(link);
    } else {
      header.textContent = channel.channelName;
    }
    container.appendChild(header);

    channel.videos.forEach(function (video) {
      container.appendChild(renderVideoCard(video));
    });

    return container;
  }

  function renderVideoCard(video) {
    var card = document.createElement("div");
    card.className = "video-card";

    // Thumbnail
    var thumbWrap = document.createElement("div");
    thumbWrap.className = "thumbnail-wrap";
    var thumb = document.createElement("img");
    thumb.src = video.thumbnailUrl;
    thumb.alt = video.title;
    thumb.loading = "lazy";
    thumb.width = 168;
    thumb.height = 94;
    thumbWrap.appendChild(thumb);

    if (video.duration) {
      var badge = document.createElement("span");
      badge.className = "duration-badge";
      badge.textContent = video.duration;
      thumbWrap.appendChild(badge);
    }

    // Content
    var content = document.createElement("div");
    content.className = "video-content";

    var title = document.createElement("h4");
    title.className = "video-title";
    title.textContent = video.title;
    content.appendChild(title);

    // Summary
    var summaryEl = document.createElement("div");
    summaryEl.className = "video-summary";
    if (!video.transcriptAvailable) {
      summaryEl.classList.add("fallback-text");
      summaryEl.textContent = "Transcript not available for this video.";
    } else if (
      video.summary &&
      video.summary.indexOf("Summary generation failed") === 0
    ) {
      summaryEl.classList.add("fallback-text", "warning-text");
      summaryEl.textContent = video.summary;
    } else {
      summaryEl.textContent = video.summary || "";
    }
    content.appendChild(summaryEl);

    // Watch button
    var watchBtn = document.createElement("button");
    watchBtn.className = "btn-watch";
    watchBtn.textContent = "Watch";
    watchBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      togglePlayer(video.id, card);
    });
    content.appendChild(watchBtn);

    card.appendChild(thumbWrap);
    card.appendChild(content);

    // Click card to toggle player too
    card.addEventListener("click", function () {
      togglePlayer(video.id, card);
    });

    return card;
  }

  // --- Inline player ---

  function togglePlayer(videoId, cardEl) {
    var existing = cardEl.querySelector(".player-container");
    if (existing) {
      existing.remove();
      return;
    }

    // Validate videoId — only allow alphanumeric, hyphens, underscores
    if (!videoId || !/^[\w-]+$/.test(videoId)) {
      return;
    }

    var container = document.createElement("div");
    container.className = "player-container";
    var iframe = document.createElement("iframe");
    iframe.src =
      "https://www.youtube.com/embed/" + encodeURIComponent(videoId) + "?autoplay=1";
    iframe.setAttribute("allowfullscreen", "");
    iframe.setAttribute(
      "sandbox",
      "allow-scripts allow-same-origin allow-presentation allow-popups"
    );
    iframe.setAttribute(
      "allow",
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    );
    iframe.title = "YouTube video player";
    container.appendChild(iframe);
    cardEl.appendChild(container);
  }

  // --- Utility ---

  function formatRelativeTime(isoString) {
    var then = new Date(isoString);
    var now = new Date();
    var diffMs = now - then;
    var diffMin = Math.floor(diffMs / 60000);
    var diffHr = Math.floor(diffMs / 3600000);
    var diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return "just now";
    if (diffMin < 60) return diffMin + " min ago";
    if (diffHr < 24) return diffHr + " hour" + (diffHr > 1 ? "s" : "") + " ago";
    return diffDay + " day" + (diffDay > 1 ? "s" : "") + " ago";
  }

  function formatDateHeading(dateStr) {
    var d = new Date(dateStr + "T12:00:00Z"); // noon UTC to avoid timezone shift
    var days = [
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ];
    var months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return days[d.getUTCDay()] + ", " + months[d.getUTCMonth()] + " " + d.getUTCDate();
  }

  // --- Init ---

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    loadData();
  });
})();
