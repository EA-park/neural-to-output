(() => {
  const search = document.querySelector(".md-search");
  if (!search) return;

  const updatePosition = () => {
    const content = document.querySelector(".md-content__inner");
    const anchor = document.querySelector(".md-header .md-logo");
    if (!content || !anchor) return;
    search.style.left = `${content.getBoundingClientRect().left}px`;
    search.style.top = `${anchor.getBoundingClientRect().top}px`;
  };

  window.addEventListener("resize", updatePosition, { passive: true });
  updatePosition();
})();
