(() => {
  const TARGET_PRICE_USD = Object.freeze({
    "L03-M01": 59, "L03-M02": 79, "L03-M03": 69, "L03-M04": 79, "L03-M05": 49,
    "L04-M01": 99, "L04-M02": 129, "L04-M03": 129, "L04-M04": 99, "L04-M05": 149,
    "L05-M01": 79, "L05-M02": 99, "L05-M03": 109, "L05-M04": 89, "L05-M05": 69,
    "L06-M01": 69, "L06-M02": 59, "L06-M03": 69, "L06-M04": 79, "L06-M05": 59,
    "L07-M01": 69, "L07-M02": 79, "L07-M03": 89, "L07-M04": 79, "L07-M05": 69,
    "L08-M01": 89, "L08-M02": 99, "L08-M03": 129, "L08-M04": 149, "L08-M05": 79,
    "L09-M01": 89, "L09-M02": 99, "L09-M03": 99, "L09-M04": 119, "L09-M05": 79,
    "L10-M01": 99, "L10-M02": 149, "L10-M03": 129, "L10-M04": 99, "L10-M05": 199
  });

  const FREE_FOUNDATION = new Set([
    "L01-M01", "L01-M02", "L01-M03", "L01-M04",
    "L02-M01", "L02-M02", "L02-M03", "L02-M04", "L02-M05", "L02-M06"
  ]);

  function replacePrice(template, price) {
    return String(template || '').replace('{price}', String(price));
  }

  function renderPrice(node) {
    const moduleId = String(node.dataset.moduleId || "").toUpperCase();
    if (FREE_FOUNDATION.has(moduleId)) {
      node.textContent = node.dataset.labelFree || "Free now & planned to remain free";
      node.dataset.priceClass = "foundation-free";
      return;
    }
    const price = TARGET_PRICE_USD[moduleId];
    if (typeof price === "number") {
      node.textContent = replacePrice(node.dataset.labelTarget || "Free during Alpha · target launch ${price} one-time", price);
      node.dataset.priceClass = "alpha-free-target-price";
      return;
    }
    node.textContent = node.dataset.labelReview || "Free during Alpha · target price under review";
    node.dataset.priceClass = "alpha-free-price-review";
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-academy-course-price]").forEach(renderPrice);
  });

  window.TotalWaterAcademyPricing = Object.freeze({
    alphaFree: true,
    targetPriceUsd: TARGET_PRICE_USD,
    freeFoundation: Object.freeze(Array.from(FREE_FOUNDATION))
  });
})();
