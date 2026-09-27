/* Small progressive enhancements. All messages go through Django's
   JavaScript catalogue (gettext / interpolate from /jsi18n/), so they appear
   in the user's language: Uzbek Latin or Uzbek Cyrillic. */
(function () {
  "use strict";

  // Confirm destructive actions.
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-confirm]");
    if (!el) return;
    if (!window.confirm(gettext("Are you sure you want to delete this?"))) {
      e.preventDefault();
    }
  });

  // Photo size check before upload (the server checks again).
  document.addEventListener("change", function (e) {
    var input = e.target;
    if (input.type !== "file" || !input.files || !input.files[0]) return;
    var form = input.closest("[data-photo-limit]");
    if (!form) return;
    var limitMb = parseInt(form.getAttribute("data-photo-limit"), 10);
    if (input.files[0].size > limitMb * 1024 * 1024) {
      window.alert(interpolate(gettext("The photo is too large. The maximum size is %(size)s MB."), { size: limitMb }, true));
      input.value = "";
    }
  });

  // Show the death fields only for deceased people.
  document.querySelectorAll("[data-show-if]").forEach(function (block) {
    var box = document.getElementById(block.getAttribute("data-show-if"));
    if (!box) return;
    var sync = function () { block.hidden = !box.checked; };
    box.addEventListener("change", sync);
    sync();
  });

  // "Add relative": hide new-person fields when linking an existing person,
  // the gender choice for father/mother, and "other parent" unless adding a child.
  var relation = document.getElementById("id_relation");
  var existing = document.getElementById("id_existing");
  if (relation) {
    var newPerson = document.querySelector("[data-new-person]");
    var otherParent = document.querySelector("[data-show-if-relation]");
    var genderField = document.getElementById("id_gender") && document.getElementById("id_gender").closest(".field");
    var syncRelation = function () {
      if (newPerson && existing) newPerson.hidden = !!existing.value;
      if (otherParent) otherParent.hidden = relation.value !== otherParent.getAttribute("data-show-if-relation");
      if (genderField) genderField.hidden = relation.value === "father" || relation.value === "mother";
    };
    relation.addEventListener("change", syncRelation);
    if (existing) existing.addEventListener("change", syncRelation);
    syncRelation();
  }

  // Prevent double submission and show progress.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (form.method.toLowerCase() !== "post" || form.classList.contains("langsw")) return;
    var btn = e.submitter;
    if (!btn || btn.name === "delete") return;
    window.setTimeout(function () {
      btn.disabled = true;
      btn.setAttribute("data-label", btn.textContent);
      btn.textContent = gettext("Saving…");
    }, 0);
  });

  // Close the user menu when clicking elsewhere.
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.usermenu[open]").forEach(function (d) {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });
})();
