(() => {
  const SHOW_AFTER_PX = 400;

  const button = document.createElement("button");
  button.className = "n2o-back-to-top";
  button.setAttribute("aria-label", "Back to top");
  button.innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">' +
    '<path fill="currentColor" d="M12 8l-6 6 1.41 1.41L12 10.83l4.59 4.58L18 14z"/>' +
    "</svg>";
  button.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.body.appendChild(button);

  const updateVisibility = () => {
    button.classList.toggle("n2o-back-to-top--visible", window.scrollY > SHOW_AFTER_PX);
  };
  window.addEventListener("scroll", updateVisibility, { passive: true });
  updateVisibility();

  // Align horizontally with where the TOC sidebar's own link text starts,
  // instead of a fixed distance from the viewport's right edge -- falls
  // back to that fixed distance if the TOC sidebar isn't present/visible
  // (e.g. a page with no headings, or a narrow viewport where it's hidden).
  const updatePosition = () => {
    const tocLink = document.querySelector(
      ".md-sidebar--secondary .md-nav__link, .md-sidebar--secondary .md-nav__title"
    );
    const rect = tocLink ? tocLink.getBoundingClientRect() : null;
    if (rect && rect.width > 0) {
      button.style.left = `${rect.left}px`;
      button.style.right = "auto";
    } else {
      button.style.left = "";
      button.style.right = "1.2rem";
    }
  };
  window.addEventListener("resize", updatePosition, { passive: true });
  updatePosition();
})();
